"""Durable workflow scheduler managing DAG readiness, worker claims, and validated completion."""
from typing import Any, Dict, Optional, Tuple
import uuid
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.generations.enums import GenerationStatus, StepStatus
from apps.realtime.events import EventType
from apps.workflows.enums import (
    AttemptStatus,
    DependencyType,
    LeaseReleaseReason,
    WorkflowRunStatus,
    WorkPackageStatus,
)
from apps.workflows.models import (
    WorkflowRun,
    WorkPackage,
    WorkPackageAttempt,
    WorkPackageDependency,
    WorkPackageLease,
)
from .leases import WorkflowLeaseService
from .outbox import OutboxService


class WorkflowSchedulerService:
    """Scheduler engine driving work package readiness, worker leases, and task lifecycle."""

    @classmethod
    def tick(
        cls,
        workflow_run_id: Optional[int] = None,
        now=None,
        batch_size: Optional[int] = None,
    ) -> int:
        """Evaluate DAG dependencies and advance PENDING/RETRY_WAIT packages to READY."""
        current_time = now or timezone.now()
        limit = batch_size or getattr(settings, "WORKFLOW_SCHEDULER_BATCH_SIZE", 50)
        advanced_count = 0

        runs_query = WorkflowRun.objects.filter(
            status__in=[WorkflowRunStatus.PENDING, WorkflowRunStatus.RUNNING]
        )
        if workflow_run_id:
            runs_query = runs_query.filter(id=workflow_run_id)

        runs = list(runs_query[:limit])

        for run in runs:
            with transaction.atomic():
                locked_run = (
                    WorkflowRun.objects.select_for_update()
                    .filter(id=run.id)
                    .first()
                )
                if not locked_run:
                    continue

                generation = locked_run.generation

                # Check if execution is blocked by pause/cancellation/terminal state
                if locked_run.status in [
                    WorkflowRunStatus.PAUSED,
                    WorkflowRunStatus.CANCELLING,
                    WorkflowRunStatus.CANCELLED,
                    WorkflowRunStatus.FAILED,
                    WorkflowRunStatus.TIMED_OUT,
                    WorkflowRunStatus.COMPLETED,
                ] or generation.status in [
                    GenerationStatus.PAUSED,
                    GenerationStatus.CANCELLING,
                    GenerationStatus.CANCELLED,
                    GenerationStatus.FAILED,
                    GenerationStatus.TIMED_OUT,
                ]:
                    locked_run.last_scheduler_heartbeat_at = current_time
                    locked_run.save(update_fields=["last_scheduler_heartbeat_at", "updated_at"])
                    continue

                if locked_run.status == WorkflowRunStatus.PENDING:
                    locked_run.status = WorkflowRunStatus.RUNNING
                    locked_run.started_at = locked_run.started_at or current_time
                    locked_run.save(update_fields=["status", "started_at", "updated_at"])
                    OutboxService.enqueue_event(
                        organization=locked_run.organization,
                        generation=generation,
                        aggregate_type="workflow_run",
                        aggregate_id=str(locked_run.id),
                        event_type=EventType.WORKFLOW_RUN_STATUS_CHANGED,
                        payload={"workflow_run_id": locked_run.id, "status": locked_run.status},
                    )

                # Process packages in this run
                packages = list(
                    WorkPackage.objects.filter(workflow_run=locked_run)
                    .select_for_update()
                )

                pkg_by_id = {p.id: p for p in packages}
                deps = list(
                    WorkPackageDependency.objects.filter(
                        workflow_run=locked_run,
                        dependency_type=DependencyType.HARD,
                    )
                )

                # Predecessor mapping: successor_id -> list of predecessor_ids
                predecessors_map = {}
                for d in deps:
                    predecessors_map.setdefault(d.successor_id, []).append(d.predecessor_id)

                for pkg in packages:
                    # 1. PENDING -> READY or BLOCKED
                    if pkg.status == WorkPackageStatus.PENDING:
                        pred_ids = predecessors_map.get(pkg.id, [])
                        if not pred_ids:
                            # Root package with no dependencies
                            pkg.status = WorkPackageStatus.READY
                            pkg.ready_at = current_time
                            pkg.state_version += 1
                            pkg.save(update_fields=["status", "ready_at", "state_version", "updated_at"])
                            OutboxService.enqueue_event(
                                organization=pkg.organization,
                                generation=generation,
                                aggregate_type="work_package",
                                aggregate_id=str(pkg.id),
                                event_type=EventType.WORK_PACKAGE_READY,
                                payload={"work_package_id": str(pkg.id), "key": pkg.key},
                            )
                            advanced_count += 1
                        else:
                            pred_statuses = [pkg_by_id[pid].status for pid in pred_ids if pid in pkg_by_id]
                            if all(st == WorkPackageStatus.COMPLETED for st in pred_statuses):
                                pkg.status = WorkPackageStatus.READY
                                pkg.ready_at = current_time
                                pkg.state_version += 1
                                pkg.save(update_fields=["status", "ready_at", "state_version", "updated_at"])
                                OutboxService.enqueue_event(
                                    organization=pkg.organization,
                                    generation=generation,
                                    aggregate_type="work_package",
                                    aggregate_id=str(pkg.id),
                                    event_type=EventType.WORK_PACKAGE_READY,
                                    payload={"work_package_id": str(pkg.id), "key": pkg.key},
                                )
                                advanced_count += 1
                            elif any(st in [WorkPackageStatus.FAILED, WorkPackageStatus.TIMED_OUT, WorkPackageStatus.BLOCKED, WorkPackageStatus.CANCELLED] for st in pred_statuses):
                                pkg.status = WorkPackageStatus.BLOCKED
                                pkg.failure_category = "DEPENDENCY_FAILED"
                                pkg.error_message = "A predecessor work package failed or was blocked."
                                pkg.state_version += 1
                                pkg.save(update_fields=["status", "failure_category", "error_message", "state_version", "updated_at"])
                                OutboxService.enqueue_event(
                                    organization=pkg.organization,
                                    generation=generation,
                                    aggregate_type="work_package",
                                    aggregate_id=str(pkg.id),
                                    event_type=EventType.WORK_PACKAGE_FAILED,
                                    payload={"work_package_id": str(pkg.id), "key": pkg.key},
                                )
                                advanced_count += 1

                    # 2. RETRY_WAIT -> READY
                    elif pkg.status == WorkPackageStatus.RETRY_WAIT:
                        if pkg.next_attempt_at and current_time >= pkg.next_attempt_at:
                            pkg.status = WorkPackageStatus.READY
                            pkg.ready_at = current_time
                            pkg.state_version += 1
                            pkg.save(update_fields=["status", "ready_at", "state_version", "updated_at"])
                            OutboxService.enqueue_event(
                                organization=pkg.organization,
                                generation=generation,
                                aggregate_type="work_package",
                                aggregate_id=str(pkg.id),
                                event_type=EventType.WORK_PACKAGE_READY,
                                payload={"work_package_id": str(pkg.id), "key": pkg.key},
                            )
                            advanced_count += 1

                # Check if all packages are completed
                refreshed_statuses = [p.status for p in packages]
                if packages and all(st == WorkPackageStatus.COMPLETED for st in refreshed_statuses):
                    locked_run.status = WorkflowRunStatus.COMPLETED
                    locked_run.completed_at = current_time
                    locked_run.state_version += 1
                    locked_run.save(update_fields=["status", "completed_at", "state_version", "updated_at"])
                    OutboxService.enqueue_event(
                        organization=locked_run.organization,
                        generation=generation,
                        aggregate_type="workflow_run",
                        aggregate_id=str(locked_run.id),
                        event_type=EventType.WORKFLOW_RUN_STATUS_CHANGED,
                        payload={"workflow_run_id": locked_run.id, "status": locked_run.status},
                    )

                locked_run.last_scheduler_heartbeat_at = current_time
                locked_run.save(update_fields=["last_scheduler_heartbeat_at", "updated_at"])

        return advanced_count

    @classmethod
    def claim_next(
        cls,
        worker_id: str,
        workflow_run_id: Optional[int] = None,
        now=None,
    ) -> Optional[Tuple[WorkPackage, WorkPackageAttempt, WorkPackageLease]]:
        """Atomically claim the highest priority READY work package and grant a lease."""
        if not worker_id:
            raise ValidationError("Worker ID is required to claim a work package.", code="missing_worker_id")

        current_time = now or timezone.now()

        with transaction.atomic():
            query = WorkPackage.objects.filter(status=WorkPackageStatus.READY)
            if workflow_run_id:
                query = query.filter(workflow_run_id=workflow_run_id)

            package = (
                query.order_by("-priority", "ready_at", "id")
                .select_for_update(skip_locked=True)
                .first()
            )

            if not package:
                return None

            run = package.workflow_run
            generation = run.generation

            # Re-verify runnable state
            if run.status in [
                WorkflowRunStatus.PAUSED,
                WorkflowRunStatus.CANCELLING,
                WorkflowRunStatus.CANCELLED,
                WorkflowRunStatus.FAILED,
                WorkflowRunStatus.TIMED_OUT,
            ] or generation.status in [
                GenerationStatus.PAUSED,
                GenerationStatus.CANCELLING,
                GenerationStatus.CANCELLED,
                GenerationStatus.FAILED,
                GenerationStatus.TIMED_OUT,
            ]:
                return None

            package.attempt_count += 1
            package.status = WorkPackageStatus.RUNNING
            package.state_version += 1
            package.started_at = package.started_at or current_time
            package.save(update_fields=["attempt_count", "status", "state_version", "started_at", "updated_at"])

            attempt = WorkPackageAttempt.objects.create(
                work_package=package,
                attempt_number=package.attempt_count,
                status=AttemptStatus.RUNNING,
                worker_id=worker_id,
                started_at=current_time,
                heartbeat_at=current_time,
            )

            lease = WorkflowLeaseService.acquire_lease(
                work_package=package,
                attempt=attempt,
                worker_id=worker_id,
                duration_seconds=package.timeout_seconds,
                now=current_time,
            )

            OutboxService.enqueue_event(
                organization=package.organization,
                generation=generation,
                aggregate_type="work_package",
                aggregate_id=str(package.id),
                event_type=EventType.WORK_PACKAGE_LEASED,
                payload={
                    "work_package_id": str(package.id),
                    "key": package.key,
                    "worker_id": worker_id,
                    "lease_token": str(lease.lease_token),
                },
            )
            OutboxService.enqueue_event(
                organization=package.organization,
                generation=generation,
                aggregate_type="work_package_attempt",
                aggregate_id=str(attempt.id),
                event_type=EventType.WORK_PACKAGE_ATTEMPT_STARTED,
                payload={
                    "work_package_id": str(package.id),
                    "attempt_id": str(attempt.id),
                    "attempt_number": attempt.attempt_number,
                    "worker_id": worker_id,
                },
            )

            return package, attempt, lease

    @classmethod
    def record_candidate_complete(
        cls,
        attempt_id: int,
        lease_token: uuid.UUID,
        result_payload: Dict[str, Any],
        now=None,
    ) -> WorkPackage:
        """Worker registers candidate completion for an attempt; releases lease."""
        current_time = now or timezone.now()

        with transaction.atomic():
            WorkflowLeaseService.release_lease(
                lease_token=lease_token,
                reason=LeaseReleaseReason.COMPLETED,
                now=current_time,
            )

            attempt = (
                WorkPackageAttempt.objects.filter(id=attempt_id)
                .select_for_update()
                .first()
            )
            if not attempt:
                raise ValidationError("Attempt not found.", code="attempt_not_found")

            attempt.status = AttemptStatus.CANDIDATE_COMPLETE
            attempt.result_payload = result_payload or {}
            attempt.completed_at = current_time
            attempt.save(update_fields=["status", "result_payload", "completed_at", "updated_at"])

            package = (
                WorkPackage.objects.filter(id=attempt.work_package_id)
                .select_for_update()
                .first()
            )
            package.status = WorkPackageStatus.CANDIDATE_COMPLETE
            package.result_payload = result_payload or {}
            package.state_version += 1
            package.save(update_fields=["status", "result_payload", "state_version", "updated_at"])

            OutboxService.enqueue_event(
                organization=package.organization,
                generation=package.workflow_run.generation,
                aggregate_type="work_package",
                aggregate_id=str(package.id),
                event_type=EventType.WORK_PACKAGE_CANDIDATE_COMPLETE,
                payload={
                    "work_package_id": str(package.id),
                    "key": package.key,
                    "attempt_id": str(attempt.id),
                },
            )

            return package

    @classmethod
    def mark_validated_complete(
        cls,
        work_package_id: int,
        validation_evidence: Dict[str, Any],
        now=None,
    ) -> WorkPackage:
        """Mark a work package COMPLETED after deterministic verification."""
        if not validation_evidence or not isinstance(validation_evidence, dict):
            raise ValidationError(
                "Structured validation evidence dictionary is required for completion.",
                code="missing_validation_evidence",
            )

        current_time = now or timezone.now()

        with transaction.atomic():
            package = (
                WorkPackage.objects.filter(id=work_package_id)
                .select_for_update()
                .first()
            )
            if not package:
                raise ValidationError("Work package not found.", code="package_not_found")

            package.status = WorkPackageStatus.COMPLETED
            package.validation_evidence = validation_evidence
            package.completed_at = current_time
            package.state_version += 1
            package.save(update_fields=["status", "validation_evidence", "completed_at", "state_version", "updated_at"])

            if package.generation_step_id:
                step = package.generation_step
                step.status = StepStatus.COMPLETED
                step.completed_at = current_time
                step.save(update_fields=["status", "completed_at", "updated_at"])

            OutboxService.enqueue_event(
                organization=package.organization,
                generation=package.workflow_run.generation,
                aggregate_type="work_package",
                aggregate_id=str(package.id),
                event_type=EventType.WORK_PACKAGE_COMPLETED,
                payload={
                    "work_package_id": str(package.id),
                    "key": package.key,
                    "validation_evidence": validation_evidence,
                },
            )

            return package
