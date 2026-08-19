"""Idempotent public control command service for pause, resume, cancel, and retry."""
from datetime import timedelta
import hashlib
import json
import logging
from typing import Any, Dict, Optional
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.generations.enums import GenerationStatus
from apps.generations.models import Generation
from apps.generations.services.state_machine import GenerationStateMachine
from apps.realtime.events import EventType
from apps.workflows.enums import (
    CommandStatus,
    CommandType,
    WorkflowRunStatus,
    WorkPackageStatus,
)
from apps.workflows.models import (
    WorkflowCommand,
    WorkflowRun,
    WorkPackage,
    WorkPackageLease,
)
from apps.workflows.services.cancellation import WorkflowCancellationService
from apps.workflows.services.outbox import OutboxService
from apps.workflows.services.retries import WorkflowRetryService

logger = logging.getLogger("tersuite.workflows.commands")


class WorkflowCommandService:
    """Service executing idempotent lifecycle operations on Generations and Workflows."""

    @classmethod
    def compute_request_hash(
        cls,
        generation_id: str,
        command_type: str,
        payload: Dict[str, Any],
    ) -> str:
        """Compute SHA-256 hash over canonical sorted JSON."""
        normalized = {
            "generation_id": str(generation_id),
            "command_type": str(command_type).upper(),
            "payload": payload or {},
        }
        canonical_json = json.dumps(normalized, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

    @classmethod
    def execute_command(
        cls,
        generation: Generation,
        command_type: str,
        idempotency_key: str,
        payload: Optional[Dict[str, Any]] = None,
        actor=None,
    ) -> Dict[str, Any]:
        """Execute an idempotent command against a generation within an atomic transaction.

        Raises:
            ValidationError: If key is invalid or conflicting with a different payload.
        """
        key = (idempotency_key or "").strip()
        if not key or len(key) > 128:
            raise ValidationError(
                "Idempotency-Key must be a non-empty string with maximum 128 characters.",
                code="invalid_idempotency_key",
            )

        cmd_type = str(command_type).upper()
        if cmd_type not in CommandType.values:
            raise ValidationError(
                f"Unsupported command type: '{command_type}'.",
                code="unsupported_command_type",
            )

        req_payload = payload or {}
        req_hash = cls.compute_request_hash(
            generation_id=str(generation.id),
            command_type=cmd_type,
            payload=req_payload,
        )

        with transaction.atomic():
            # Check existing command for this organization + idempotency_key
            existing_cmd = (
                WorkflowCommand.objects.filter(
                    organization=generation.organization,
                    idempotency_key=key,
                )
                .select_for_update()
                .first()
            )

            if existing_cmd:
                if existing_cmd.request_hash == req_hash:
                    # Idempotent replay
                    response = dict(existing_cmd.response_payload)
                    response["idempotent_replay"] = True
                    return response
                else:
                    raise ValidationError(
                        "Idempotency key conflict: identical key provided with different parameters.",
                        code="idempotency_key_conflict",
                    )

            # Re-fetch and lock generation
            locked_gen = (
                Generation.objects.select_for_update()
                .filter(id=generation.id)
                .first()
            )
            if not locked_gen:
                raise ValidationError("Generation not found.", code="generation_not_found")

            # Create the command audit record with nested savepoint to handle concurrency safely
            try:
                with transaction.atomic():
                    cmd = WorkflowCommand.objects.create(
                        organization=locked_gen.organization,
                        generation=locked_gen,
                        command_type=cmd_type,
                        idempotency_key=key,
                        request_hash=req_hash,
                        request_payload=req_payload,
                        status=CommandStatus.APPLIED,
                        applied_at=timezone.now(),
                        created_by=actor,
                        updated_by=actor,
                    )
            except IntegrityError:
                # Concurrent request created the command
                cmd = (
                    WorkflowCommand.objects.filter(
                        organization=locked_gen.organization,
                        idempotency_key=key,
                    )
                    .select_for_update()
                    .first()
                )
                if cmd and cmd.request_hash == req_hash:
                    response = dict(cmd.response_payload)
                    response["idempotent_replay"] = True
                    return response
                raise ValidationError(
                    "Idempotency key conflict: identical key provided with different parameters.",
                    code="idempotency_key_conflict",
                )

            # Execute command logic
            cls._apply_command_logic(locked_gen, cmd_type, req_payload, cmd.id, actor)
            locked_gen.refresh_from_db()

            # Store response payload
            response_data = {
                "command_id": str(cmd.id),
                "idempotent_replay": False,
                "generation_id": str(locked_gen.id),
                "status": locked_gen.status,
            }
            cmd.response_payload = response_data
            cmd.save(update_fields=["response_payload", "updated_at"])

            return response_data

    @classmethod
    def _apply_command_logic(
        cls,
        generation: Generation,
        command_type: str,
        payload: Dict[str, Any],
        command_id: Any,
        actor: Any,
    ) -> None:
        """Internal router for state transitions and workflow mutations."""
        reason = payload.get("reason", f"{command_type} command executed")
        now = timezone.now()

        if command_type == CommandType.PAUSE:
            if generation.status == GenerationStatus.PAUSED:
                return
            GenerationStateMachine.transition(
                generation=generation,
                target_status=GenerationStatus.PAUSED,
                reason=reason,
                command_id=command_id,
                actor=actor,
            )
            # Pause running workflow runs
            running_runs = list(
                WorkflowRun.objects.filter(
                    generation=generation,
                    status=WorkflowRunStatus.RUNNING,
                ).select_for_update()
            )
            for run in running_runs:
                run.status = WorkflowRunStatus.PAUSED
                run.paused_at = now
                run.state_version += 1
                run.save(update_fields=["status", "paused_at", "state_version", "updated_at"])
                OutboxService.enqueue_event(
                    organization=run.organization,
                    aggregate_type="workflow_run",
                    aggregate_id=str(run.id),
                    event_type=EventType.WORKFLOW_RUN_PAUSED,
                    payload={"workflow_run_id": str(run.id), "status": WorkflowRunStatus.PAUSED},
                    generation=generation,
                    now=now,
                )

        elif command_type == CommandType.RESUME:
            if generation.status != GenerationStatus.PAUSED:
                raise ValidationError(
                    f"Only PAUSED generations can be resumed. Current status: '{generation.status}'.",
                    code="invalid_state",
                )
            target = generation.resume_status or GenerationStatus.SCHEDULED
            GenerationStateMachine.transition(
                generation=generation,
                target_status=target,
                reason=reason,
                command_id=command_id,
                actor=actor,
            )
            # Resume paused workflow runs
            paused_runs = list(
                WorkflowRun.objects.filter(
                    generation=generation,
                    status=WorkflowRunStatus.PAUSED,
                ).select_for_update()
            )
            for run in paused_runs:
                run.status = WorkflowRunStatus.RUNNING
                run.paused_at = None
                run.state_version += 1
                run.save(update_fields=["status", "paused_at", "state_version", "updated_at"])
                OutboxService.enqueue_event(
                    organization=run.organization,
                    aggregate_type="workflow_run",
                    aggregate_id=str(run.id),
                    event_type=EventType.WORKFLOW_RUN_STARTED,
                    payload={"workflow_run_id": str(run.id), "status": WorkflowRunStatus.RUNNING},
                    generation=generation,
                    now=now,
                )

        elif command_type == CommandType.CANCEL:
            if generation.status in [
                GenerationStatus.CANCELLED,
                GenerationStatus.ROLLED_BACK,
                GenerationStatus.SUPERSEDED,
            ]:
                return

            # Establish cancellation intent: transition generation to CANCELLING
            if generation.status != GenerationStatus.CANCELLING:
                GenerationStateMachine.transition(
                    generation=generation,
                    target_status=GenerationStatus.CANCELLING,
                    reason=reason,
                    command_id=command_id,
                    actor=actor,
                )

            # Update non-terminal workflow runs to CANCELLING
            runs = list(
                WorkflowRun.objects.filter(
                    generation=generation,
                    status__in=[WorkflowRunStatus.PENDING, WorkflowRunStatus.RUNNING, WorkflowRunStatus.PAUSED],
                ).select_for_update()
            )
            for run in runs:
                run.status = WorkflowRunStatus.CANCELLING
                run.cancel_requested_at = run.cancel_requested_at or now
                run.state_version += 1
                run.save(update_fields=["status", "cancel_requested_at", "state_version", "updated_at"])

            # Set cancel_requested_at on active packages
            active_pkgs = list(
                WorkPackage.objects.filter(
                    workflow_run__generation=generation,
                    status__in=[WorkPackageStatus.READY, WorkPackageStatus.LEASED, WorkPackageStatus.RUNNING],
                ).select_for_update()
            )
            for pkg in active_pkgs:
                pkg.cancel_requested_at = pkg.cancel_requested_at or now
                pkg.save(update_fields=["cancel_requested_at", "updated_at"])

            # Attempt deterministic quiescent finalization
            WorkflowCancellationService.finalize_if_quiescent(
                generation_id=generation.id,
                reason=reason,
                actor=actor,
            )

        elif command_type == CommandType.RETRY:
            if generation.status not in [
                GenerationStatus.FAILED,
                GenerationStatus.TIMED_OUT,
                GenerationStatus.BLOCKED,
            ]:
                raise ValidationError(
                    f"Only FAILED, TIMED_OUT, or BLOCKED generations can be retried. Current status: '{generation.status}'.",
                    code="retry_not_available",
                )

            # Find active or latest workflow run
            run = (
                WorkflowRun.objects.filter(generation=generation)
                .order_by("-run_number")
                .select_for_update()
                .first()
            )
            if not run:
                raise ValidationError("No workflow run exists to retry.", code="retry_not_available")

            # Inspect failed/timed_out/blocked packages
            candidate_pkgs = list(
                WorkPackage.objects.filter(
                    workflow_run=run,
                    status__in=[
                        WorkPackageStatus.FAILED,
                        WorkPackageStatus.TIMED_OUT,
                        WorkPackageStatus.BLOCKED,
                    ],
                ).select_for_update()
            )

            retried_count = 0
            for pkg in candidate_pkgs:
                latest_attempt = pkg.attempts.order_by("-attempt_number").first()
                # Check retryable flag
                if latest_attempt and latest_attempt.retryable is False:
                    continue
                # Check retry budget
                if not WorkflowRetryService.should_retry(pkg, latest_attempt, ignore_run_state=True):
                    continue

                # Schedule retry with backoff
                delay_sec = WorkflowRetryService.calculate_backoff_delay(pkg.attempt_count)
                pkg.status = WorkPackageStatus.RETRY_WAIT
                pkg.next_attempt_at = now + timedelta(seconds=delay_sec)
                pkg.error_message = ""
                pkg.failure_category = ""
                pkg.state_version += 1
                pkg.save(update_fields=["status", "next_attempt_at", "error_message", "failure_category", "state_version", "updated_at"])

                OutboxService.enqueue_event(
                    organization=pkg.organization,
                    aggregate_type="work_package",
                    aggregate_id=str(pkg.id),
                    event_type=EventType.WORK_PACKAGE_RETRY_SCHEDULED,
                    payload={
                        "work_package_id": str(pkg.id),
                        "workflow_run_id": str(run.id),
                        "attempt_count": pkg.attempt_count,
                        "next_attempt_at": pkg.next_attempt_at.isoformat(),
                        "delay_seconds": delay_sec,
                    },
                    generation=generation,
                    now=now,
                )
                retried_count += 1

            if retried_count == 0:
                raise ValidationError(
                    "No retryable work packages are eligible for retry.",
                    code="retry_not_available",
                )

            # Move workflow run to RUNNING
            if run.status in [WorkflowRunStatus.FAILED, WorkflowRunStatus.TIMED_OUT, WorkflowRunStatus.BLOCKED]:
                run.status = WorkflowRunStatus.RUNNING
                run.state_version += 1
                run.save(update_fields=["status", "state_version", "updated_at"])
                OutboxService.enqueue_event(
                    organization=run.organization,
                    aggregate_type="workflow_run",
                    aggregate_id=str(run.id),
                    event_type=EventType.WORKFLOW_RUN_STARTED,
                    payload={"workflow_run_id": str(run.id), "status": WorkflowRunStatus.RUNNING},
                    generation=generation,
                    now=now,
                )

            # Transition generation to SCHEDULED
            GenerationStateMachine.transition(
                generation=generation,
                target_status=GenerationStatus.SCHEDULED,
                reason=reason,
                command_id=command_id,
                actor=actor,
            )
