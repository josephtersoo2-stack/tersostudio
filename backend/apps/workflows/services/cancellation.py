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
from apps.workflows.enums import WorkflowRunStatus, WorkPackageStatus
from apps.workflows.models import WorkflowRun, WorkPackage, WorkPackageLease
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
        """Deterministically finalize cancellation if no active leases remain.

        Returns:
            bool: True if finalized to CANCELLED, False if active leases remain or already cancelled.
        """
        with transaction.atomic():
            gen = Generation.objects.select_for_update().get(id=generation_id)

            if gen.status == GenerationStatus.CANCELLED:
                return False

            if gen.status != GenerationStatus.CANCELLING and not gen.cancel_requested_at:
                return False

            # Resolve active or latest workflow run
            run_qs = WorkflowRun.objects.filter(generation=gen)
            if workflow_run_id:
                run_qs = run_qs.filter(id=workflow_run_id)
            else:
                run_qs = run_qs.order_by("-run_number")

            run = run_qs.select_for_update().first()
            now = timezone.now()

            if run:
                # Check for any unreleased active leases
                active_leases_count = WorkPackageLease.objects.filter(
                    work_package__workflow_run=run,
                    released_at__isnull=True,
                ).count()

                if active_leases_count > 0:
                    logger.info("Cancellation for generation %s run %s waiting for %d active lease(s).", gen.id, run.id, active_leases_count)
                    return False

                # Quiescent: cancel all non-terminal packages
                non_terminal_statuses = [
                    WorkPackageStatus.PENDING,
                    WorkPackageStatus.READY,
                    WorkPackageStatus.RETRY_WAIT,
                    WorkPackageStatus.RUNNING,
                    WorkPackageStatus.CANDIDATE_COMPLETE,
                ]
                packages_to_cancel = list(
                    WorkPackage.objects.filter(
                        workflow_run=run,
                        status__in=non_terminal_statuses,
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
                            "workflow_run_id": str(run.id),
                            "status": WorkPackageStatus.CANCELLED,
                        },
                        generation=gen,
                        now=now,
                    )

                # Finalize workflow run
                if run.status != WorkflowRunStatus.CANCELLED:
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

            # Transition generation from CANCELLING to CANCELLED
            if gen.status == GenerationStatus.CANCELLING:
                GenerationStateMachine.transition(
                    generation=gen,
                    target_status=GenerationStatus.CANCELLED,
                    reason=reason,
                    actor=actor,
                )

            return True
