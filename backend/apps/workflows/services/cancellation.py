"""Deterministic cancellation finalization service for workflows and generations."""
import logging
from typing import Optional
import uuid
from django.db import transaction
from django.utils import timezone

from apps.generations.enums import GenerationStatus
from apps.generations.models import Generation
from apps.generations.services.state_machine import GenerationStateMachine
from apps.realtime.events import EventType
from apps.workflows.enums import AttemptStatus, WorkflowRunStatus, WorkPackageStatus
from apps.workflows.models import (
    WorkflowRun,
    WorkPackage,
    WorkPackageAttempt,
    WorkPackageLease,
)
from apps.workflows.services.outbox import OutboxService

logger = logging.getLogger("tersuite.workflows.cancellation")


class WorkflowCancellationService:
    """Service handling graceful cancellation propagation and quiescent finalization."""

    @classmethod
    def finalize_if_quiescent(
        cls,
        generation_id: uuid.UUID,
        workflow_run_id: Optional[uuid.UUID] = None,
        reason: str = "Cancellation finalized after quiescence.",
        actor=None,
    ) -> bool:
        """Deterministically finalize cancellation if no active leases remain across the generation.

        Returns:
            bool: True if finalized to CANCELLED, False if active leases remain or already cancelled.
        """
        with transaction.atomic():
            gen = Generation.objects.select_for_update().get(id=generation_id)

            if gen.status == GenerationStatus.CANCELLED:
                return False

            if gen.status != GenerationStatus.CANCELLING and not gen.cancel_requested_at:
                return False

            # 1. Generation-wide lease check (Finding 10)
            active_leases_count = WorkPackageLease.objects.filter(
                work_package__workflow_run__generation=gen,
                released_at__isnull=True,
            ).count()

            if active_leases_count > 0:
                logger.info("Cancellation for generation %s waiting for %d active lease(s).", gen.id, active_leases_count)
                return False

            now = timezone.now()

            # 2. Reconcile remaining active attempts across all runs for this generation (Finding 09)
            active_attempts = list(
                WorkPackageAttempt.objects.filter(
                    work_package__workflow_run__generation=gen,
                    status__in=[AttemptStatus.RUNNING, AttemptStatus.QUEUED],
                ).select_for_update()
            )
            for attempt in active_attempts:
                attempt.status = AttemptStatus.CANCELLED
                attempt.completed_at = attempt.completed_at or now
                attempt.save(update_fields=["status", "completed_at", "updated_at"])

            # 3. Quiescent: cancel all non-terminal packages across all runs
            non_terminal_package_statuses = [
                WorkPackageStatus.PENDING,
                WorkPackageStatus.READY,
                WorkPackageStatus.LEASED,
                WorkPackageStatus.RETRY_WAIT,
                WorkPackageStatus.RUNNING,
                WorkPackageStatus.CANDIDATE_COMPLETE,
            ]
            packages_to_cancel = list(
                WorkPackage.objects.filter(
                    workflow_run__generation=gen,
                    status__in=non_terminal_package_statuses,
                ).select_for_update()
            )

            for pkg in packages_to_cancel:
                pkg.status = WorkPackageStatus.CANCELLED
                pkg.completed_at = pkg.completed_at or now
                pkg.state_version += 1
                pkg.save(update_fields=["status", "completed_at", "state_version", "updated_at"])

                OutboxService.enqueue_event(
                    organization=pkg.organization,
                    aggregate_type="work_package",
                    aggregate_id=str(pkg.id),
                    event_type=EventType.WORK_PACKAGE_CANCELLED,
                    payload={
                        "work_package_id": str(pkg.id),
                        "workflow_run_id": str(pkg.workflow_run_id),
                        "status": WorkPackageStatus.CANCELLED,
                    },
                    generation=gen,
                    now=now,
                )

            # 4. Finalize all non-terminal workflow runs for this generation
            non_terminal_run_statuses = [
                WorkflowRunStatus.PENDING,
                WorkflowRunStatus.RUNNING,
                WorkflowRunStatus.PAUSED,
                WorkflowRunStatus.CANCELLING,
            ]
            runs_to_cancel = list(
                WorkflowRun.objects.filter(
                    generation=gen,
                    status__in=non_terminal_run_statuses,
                ).select_for_update()
            )

            for run in runs_to_cancel:
                run.status = WorkflowRunStatus.CANCELLED
                run.completed_at = run.completed_at or now
                run.state_version += 1
                run.save(update_fields=["status", "completed_at", "state_version", "updated_at"])

                OutboxService.enqueue_event(
                    organization=run.organization,
                    aggregate_type="workflow_run",
                    aggregate_id=str(run.id),
                    event_type=EventType.WORKFLOW_RUN_CANCELLED,
                    payload={
                        "workflow_run_id": str(run.id),
                        "generation_id": str(gen.id),
                        "status": WorkflowRunStatus.CANCELLED,
                    },
                    generation=gen,
                    now=now,
                )

            # 5. Transition generation from CANCELLING to CANCELLED
            if gen.status == GenerationStatus.CANCELLING:
                GenerationStateMachine.transition(
                    generation=gen,
                    target_status=GenerationStatus.CANCELLED,
                    reason=reason,
                    actor=actor,
                )

            return True
