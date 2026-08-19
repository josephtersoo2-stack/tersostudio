"""Idempotent public control command service for pause, resume, cancel, and retry."""
import hashlib
import json
from typing import Any, Dict, Optional
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.generations.enums import GenerationStatus
from apps.generations.models import Generation
from apps.generations.services.state_machine import GenerationStateMachine
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

            # Create the command audit record
            try:
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
                # Race condition: re-read
                cmd = WorkflowCommand.objects.get(
                    organization=locked_gen.organization,
                    idempotency_key=key,
                )
                if cmd.request_hash == req_hash:
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
            # Pause running workflow run
            WorkflowRun.objects.filter(
                generation=generation,
                status=WorkflowRunStatus.RUNNING,
            ).update(
                status=WorkflowRunStatus.PAUSED,
                paused_at=timezone.now(),
                updated_at=timezone.now(),
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
            # Resume paused workflow run
            WorkflowRun.objects.filter(
                generation=generation,
                status=WorkflowRunStatus.PAUSED,
            ).update(
                status=WorkflowRunStatus.RUNNING,
                paused_at=None,
                updated_at=timezone.now(),
            )

        elif command_type == CommandType.CANCEL:
            if generation.status in [
                GenerationStatus.CANCELLED,
                GenerationStatus.ROLLED_BACK,
                GenerationStatus.SUPERSEDED,
            ]:
                return

            # Check if active leases exist on packages
            active_leases_exist = WorkPackageLease.objects.filter(
                work_package__workflow_run__generation=generation,
                released_at__isnull=True,
            ).exists()

            if active_leases_exist:
                GenerationStateMachine.transition(
                    generation=generation,
                    target_status=GenerationStatus.CANCELLING,
                    reason=reason,
                    command_id=command_id,
                    actor=actor,
                )
                WorkflowRun.objects.filter(
                    generation=generation,
                    status__in=[WorkflowRunStatus.PENDING, WorkflowRunStatus.RUNNING, WorkflowRunStatus.PAUSED],
                ).update(
                    status=WorkflowRunStatus.CANCELLING,
                    cancel_requested_at=timezone.now(),
                    updated_at=timezone.now(),
                )
                WorkPackage.objects.filter(
                    workflow_run__generation=generation,
                    status__in=[WorkPackageStatus.READY, WorkPackageStatus.LEASED, WorkPackageStatus.RUNNING],
                ).update(
                    cancel_requested_at=timezone.now(),
                    updated_at=timezone.now(),
                )
            else:
                GenerationStateMachine.transition(
                    generation=generation,
                    target_status=GenerationStatus.CANCELLED,
                    reason=reason,
                    command_id=command_id,
                    actor=actor,
                )
                WorkflowRun.objects.filter(
                    generation=generation,
                    status__in=[
                        WorkflowRunStatus.PENDING,
                        WorkflowRunStatus.RUNNING,
                        WorkflowRunStatus.PAUSED,
                        WorkflowRunStatus.CANCELLING,
                    ],
                ).update(
                    status=WorkflowRunStatus.CANCELLED,
                    completed_at=timezone.now(),
                    updated_at=timezone.now(),
                )
                WorkPackage.objects.filter(
                    workflow_run__generation=generation,
                    status__in=[WorkPackageStatus.PENDING, WorkPackageStatus.READY, WorkPackageStatus.RETRY_WAIT],
                ).update(
                    status=WorkPackageStatus.CANCELLED,
                    updated_at=timezone.now(),
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

            GenerationStateMachine.transition(
                generation=generation,
                target_status=GenerationStatus.SCHEDULED,
                reason=reason,
                command_id=command_id,
                actor=actor,
            )

            # Reset eligible failed packages in active workflow run
            WorkflowRun.objects.filter(
                generation=generation,
                status__in=[WorkflowRunStatus.FAILED, WorkflowRunStatus.TIMED_OUT, WorkflowRunStatus.BLOCKED],
            ).update(
                status=WorkflowRunStatus.RUNNING,
                updated_at=timezone.now(),
            )
            WorkPackage.objects.filter(
                workflow_run__generation=generation,
                status__in=[WorkPackageStatus.FAILED, WorkPackageStatus.TIMED_OUT, WorkPackageStatus.BLOCKED],
            ).update(
                status=WorkPackageStatus.READY,
                ready_at=timezone.now(),
                error_message="",
                failure_category="",
                updated_at=timezone.now(),
            )
