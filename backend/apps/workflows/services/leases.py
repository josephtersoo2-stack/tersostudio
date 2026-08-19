"""Distributed lease management, heartbeat renewal, and stale lease reaping."""
from datetime import timedelta
import logging
from typing import Optional
import uuid
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.generations.enums import GenerationStatus
from apps.realtime.events import EventType
from apps.workflows.enums import (
    AttemptStatus,
    LeaseReleaseReason,
    WorkflowRunStatus,
    WorkPackageStatus,
)
from apps.workflows.models import (
    WorkPackage,
    WorkPackageAttempt,
    WorkPackageLease,
)
from .cancellation import WorkflowCancellationService
from .outbox import OutboxService
from .retries import WorkflowRetryService

logger = logging.getLogger("tersuite.workflows.leases")


class WorkflowLeaseService:
    """Service handling distributed leases for work package workers."""

    @classmethod
    def acquire_lease(
        cls,
        work_package: WorkPackage,
        attempt: WorkPackageAttempt,
        worker_id: str,
        duration_seconds: Optional[int] = None,
        now=None,
    ) -> WorkPackageLease:
        """Create and grant an exclusive execution lease for a work package attempt."""
        current_time = now or timezone.now()
        duration = duration_seconds or getattr(settings, "WORKFLOW_LEASE_SECONDS", 300)

        # Cap lease duration by absolute work package execution deadline
        deadline = attempt.started_at + timedelta(seconds=work_package.timeout_seconds)
        effective_expires_at = min(current_time + timedelta(seconds=duration), deadline)

        with transaction.atomic():
            # Check for existing active lease
            active_lease = (
                WorkPackageLease.objects.filter(
                    work_package=work_package,
                    released_at__isnull=True,
                )
                .select_for_update()
                .first()
            )
            if active_lease and not active_lease.is_expired(current_time):
                raise ValidationError(
                    f"Package '{work_package.key}' already has an active lease held by worker '{active_lease.worker_id}'.",
                    code="active_lease_exists",
                )

            lease = WorkPackageLease.objects.create(
                work_package=work_package,
                attempt=attempt,
                lease_token=uuid.uuid4(),
                worker_id=worker_id,
                acquired_at=current_time,
                heartbeat_at=current_time,
                expires_at=effective_expires_at,
            )
            return lease

    @classmethod
    def heartbeat(
        cls,
        lease_token: uuid.UUID,
        attempt_id: int,
        duration_seconds: Optional[int] = None,
        now=None,
    ) -> WorkPackageLease:
        """Extend an active lease's expiry and record worker heartbeat."""
        current_time = now or timezone.now()
        duration = duration_seconds or getattr(settings, "WORKFLOW_LEASE_SECONDS", 300)

        with transaction.atomic():
            lease = (
                WorkPackageLease.objects.filter(lease_token=lease_token)
                .select_for_update()
                .first()
            )
            if not lease:
                raise ValidationError(
                    "Invalid lease token.",
                    code="invalid_lease_token",
                )

            if lease.attempt_id != attempt_id:
                raise ValidationError(
                    "Lease token does not match specified attempt ID.",
                    code="lease_attempt_mismatch",
                )

            if lease.released_at:
                raise ValidationError(
                    "Cannot heartbeat an already released lease.",
                    code="lease_released",
                )

            if lease.is_expired(current_time):
                raise ValidationError(
                    "Lease has expired and cannot be renewed.",
                    code="lease_expired",
                )

            # Cap heartbeat extension by package timeout deadline
            deadline = lease.attempt.started_at + timedelta(seconds=lease.work_package.timeout_seconds)
            effective_expires_at = min(current_time + timedelta(seconds=duration), deadline)

            lease.heartbeat_at = current_time
            lease.expires_at = effective_expires_at
            lease.save(update_fields=["heartbeat_at", "expires_at", "updated_at"])

            WorkPackageAttempt.objects.filter(id=attempt_id).update(
                heartbeat_at=current_time,
                updated_at=current_time,
            )

            return lease

    @classmethod
    def release_lease(
        cls,
        lease_token: uuid.UUID,
        reason: str = LeaseReleaseReason.COMPLETED,
        now=None,
    ) -> WorkPackageLease:
        """Release an active lease."""
        current_time = now or timezone.now()

        with transaction.atomic():
            lease = (
                WorkPackageLease.objects.filter(lease_token=lease_token)
                .select_for_update()
                .first()
            )
            if not lease:
                raise ValidationError(
                    "Invalid lease token.",
                    code="invalid_lease_token",
                )

            if lease.released_at:
                # Idempotent return
                return lease

            lease.released_at = current_time
            lease.release_reason = reason
            lease.save(update_fields=["released_at", "release_reason", "updated_at"])

            # If generation/run is cancelling, finalize if now quiescent (Finding 08)
            gen = lease.work_package.workflow_run.generation
            if gen.status == GenerationStatus.CANCELLING or gen.cancel_requested_at:
                WorkflowCancellationService.finalize_if_quiescent(
                    generation_id=gen.id,
                    workflow_run_id=lease.work_package.workflow_run_id,
                    reason="Cancellation finalized after cooperative lease release.",
                )

            return lease

    @classmethod
    def reap_expired_leases(
        cls,
        now=None,
        batch_size: Optional[int] = None,
    ) -> int:
        """Find unreleased, expired leases and transition timed-out attempts to retry or failure."""
        current_time = now or timezone.now()
        limit = batch_size or getattr(settings, "WORKFLOW_SCHEDULER_BATCH_SIZE", 50)
        reaped_count = 0

        with transaction.atomic():
            stale_leases = list(
                WorkPackageLease.objects.filter(
                    released_at__isnull=True,
                    expires_at__lte=current_time,
                )
                .select_for_update(skip_locked=True)[:limit]
            )

            for lease in stale_leases:
                lease.released_at = current_time
                lease.release_reason = LeaseReleaseReason.EXPIRED
                lease.save(update_fields=["released_at", "release_reason", "updated_at"])

                # Lock attempt and package
                attempt = (
                    WorkPackageAttempt.objects.filter(id=lease.attempt_id)
                    .select_for_update()
                    .first()
                )
                package = (
                    WorkPackage.objects.filter(id=lease.work_package_id)
                    .select_for_update()
                    .first()
                )

                if attempt and attempt.status == AttemptStatus.RUNNING:
                    attempt.status = AttemptStatus.TIMED_OUT
                    attempt.completed_at = current_time
                    attempt.failure_category = "TIMEOUT"
                    attempt.error_details = {"error": "Lease heartbeat expired without release."}
                    attempt.save(update_fields=["status", "completed_at", "failure_category", "error_details", "updated_at"])

                if package:
                    package.state_version += 1
                    run = package.workflow_run
                    gen = run.generation

                    is_cancelling = (
                        package.cancel_requested_at
                        or run.status == WorkflowRunStatus.CANCELLING
                        or gen.status == GenerationStatus.CANCELLING
                    )

                    if is_cancelling:
                        package.status = WorkPackageStatus.CANCELLED
                        package.completed_at = current_time
                        package.save(update_fields=["status", "completed_at", "state_version", "updated_at"])
                        OutboxService.enqueue_event(
                            organization=package.organization,
                            generation=gen,
                            aggregate_type="work_package",
                            aggregate_id=str(package.id),
                            event_type=EventType.WORK_PACKAGE_CANCELLED,
                            payload={"work_package_id": str(package.id), "key": package.key},
                            now=current_time,
                        )
                        # Deterministically finalize if all active leases are now released
                        WorkflowCancellationService.finalize_if_quiescent(
                            generation_id=gen.id,
                            workflow_run_id=run.id,
                            reason="Cancellation finalized after lease expiry reap.",
                        )
                    elif WorkflowRetryService.should_retry(package, attempt):
                        WorkflowRetryService.schedule_retry(package, now=current_time)
                        OutboxService.enqueue_event(
                            organization=package.organization,
                            generation=gen,
                            aggregate_type="work_package",
                            aggregate_id=str(package.id),
                            event_type=EventType.WORK_PACKAGE_RETRY_SCHEDULED,
                            payload={
                                "work_package_id": str(package.id),
                                "key": package.key,
                                "next_attempt_at": package.next_attempt_at.isoformat() if package.next_attempt_at else None,
                            },
                            now=current_time,
                        )
                    else:
                        package.status = WorkPackageStatus.TIMED_OUT
                        package.failure_category = "TIMEOUT"
                        package.error_message = "Work package execution timed out and exhausted retries."
                        package.completed_at = current_time
                        package.save(update_fields=[
                            "status",
                            "failure_category",
                            "error_message",
                            "completed_at",
                            "state_version",
                            "updated_at",
                        ])
                        OutboxService.enqueue_event(
                            organization=package.organization,
                            generation=gen,
                            aggregate_type="work_package",
                            aggregate_id=str(package.id),
                            event_type=EventType.WORK_PACKAGE_TIMED_OUT,
                            payload={"work_package_id": str(package.id), "key": package.key},
                            now=current_time,
                        )

                reaped_count += 1

        return reaped_count
