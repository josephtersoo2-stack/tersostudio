"""Generation lifecycle state machine service.

Enforces deterministic state transitions, database row-level locking,
monotonic state versioning, relational transition auditing, and transactional
outbox event logging.
"""
from typing import Any, Dict, Optional, Set
import uuid
from django.db import transaction
from django.utils import timezone

from apps.generations.enums import GenerationStatus
from apps.generations.exceptions import InvalidStateTransitionError
from apps.generations.models import Generation, GenerationStateTransition
from apps.realtime.events import EventType

# Canonical B3 transition graph
VALID_TRANSITIONS: Dict[str, Set[str]] = {
    GenerationStatus.DRAFT: {
        GenerationStatus.DISCOVERY,
        GenerationStatus.CANCELLING,
    },
    GenerationStatus.DISCOVERY: {
        GenerationStatus.SPECIFICATION_DRAFT,
        GenerationStatus.PAUSED,
        GenerationStatus.FAILED,
        GenerationStatus.TIMED_OUT,
        GenerationStatus.BLOCKED,
        GenerationStatus.CANCELLING,
    },
    GenerationStatus.SPECIFICATION_DRAFT: {
        GenerationStatus.PLAN_DRAFT,
        GenerationStatus.PAUSED,
        GenerationStatus.FAILED,
        GenerationStatus.TIMED_OUT,
        GenerationStatus.BLOCKED,
        GenerationStatus.CANCELLING,
    },
    GenerationStatus.PLAN_DRAFT: {
        GenerationStatus.AWAITING_APPROVAL,
        GenerationStatus.PAUSED,
        GenerationStatus.FAILED,
        GenerationStatus.TIMED_OUT,
        GenerationStatus.BLOCKED,
        GenerationStatus.CANCELLING,
    },
    GenerationStatus.AWAITING_APPROVAL: {
        GenerationStatus.APPROVED,
        GenerationStatus.SPECIFICATION_DRAFT,  # Human revision loop
        GenerationStatus.PLAN_DRAFT,           # Human revision loop
        GenerationStatus.PAUSED,
        GenerationStatus.FAILED,
        GenerationStatus.TIMED_OUT,
        GenerationStatus.BLOCKED,
        GenerationStatus.CANCELLING,
    },
    GenerationStatus.APPROVED: {
        GenerationStatus.SCHEDULED,
        GenerationStatus.CANCELLING,
    },
    GenerationStatus.SCHEDULED: {
        GenerationStatus.BUILDING,
        GenerationStatus.PAUSED,
        GenerationStatus.FAILED,
        GenerationStatus.TIMED_OUT,
        GenerationStatus.BLOCKED,
        GenerationStatus.CANCELLING,
    },
    GenerationStatus.BUILDING: {
        GenerationStatus.INTEGRATING,
        GenerationStatus.PAUSED,
        GenerationStatus.FAILED,
        GenerationStatus.TIMED_OUT,
        GenerationStatus.BLOCKED,
        GenerationStatus.CANCELLING,
    },
    GenerationStatus.INTEGRATING: {
        GenerationStatus.REVIEWING,
        GenerationStatus.PAUSED,
        GenerationStatus.FAILED,
        GenerationStatus.TIMED_OUT,
        GenerationStatus.BLOCKED,
        GenerationStatus.CANCELLING,
    },
    GenerationStatus.REVIEWING: {
        GenerationStatus.SANDBOX_QA,
        GenerationStatus.CORRECTING,  # Review findings repair loop
        GenerationStatus.PAUSED,
        GenerationStatus.FAILED,
        GenerationStatus.TIMED_OUT,
        GenerationStatus.BLOCKED,
        GenerationStatus.CANCELLING,
    },
    GenerationStatus.CORRECTING: {
        GenerationStatus.BUILDING,
        GenerationStatus.INTEGRATING,
        GenerationStatus.REVIEWING,
        GenerationStatus.PAUSED,
        GenerationStatus.FAILED,
        GenerationStatus.TIMED_OUT,
        GenerationStatus.BLOCKED,
        GenerationStatus.CANCELLING,
    },
    GenerationStatus.SANDBOX_QA: {
        GenerationStatus.RELEASE_CANDIDATE,
        GenerationStatus.CORRECTING,  # QA defect repair loop
        GenerationStatus.PAUSED,
        GenerationStatus.FAILED,
        GenerationStatus.TIMED_OUT,
        GenerationStatus.BLOCKED,
        GenerationStatus.CANCELLING,
    },
    GenerationStatus.RELEASE_CANDIDATE: {
        GenerationStatus.AWAITING_DEPLOYMENT_APPROVAL,
        GenerationStatus.PAUSED,
        GenerationStatus.FAILED,
        GenerationStatus.TIMED_OUT,
        GenerationStatus.BLOCKED,
        GenerationStatus.CANCELLING,
    },
    GenerationStatus.AWAITING_DEPLOYMENT_APPROVAL: {
        GenerationStatus.STAGED,
        GenerationStatus.PAUSED,
        GenerationStatus.FAILED,
        GenerationStatus.TIMED_OUT,
        GenerationStatus.BLOCKED,
        GenerationStatus.CANCELLING,
    },
    GenerationStatus.STAGED: {
        GenerationStatus.ACTIVE,
        GenerationStatus.CANCELLING,
    },
    GenerationStatus.ACTIVE: {
        GenerationStatus.ROLLED_BACK,
    },
    GenerationStatus.PAUSED: {
        GenerationStatus.DISCOVERY,
        GenerationStatus.SPECIFICATION_DRAFT,
        GenerationStatus.PLAN_DRAFT,
        GenerationStatus.AWAITING_APPROVAL,
        GenerationStatus.SCHEDULED,
        GenerationStatus.BUILDING,
        GenerationStatus.INTEGRATING,
        GenerationStatus.REVIEWING,
        GenerationStatus.CORRECTING,
        GenerationStatus.SANDBOX_QA,
        GenerationStatus.RELEASE_CANDIDATE,
        GenerationStatus.AWAITING_DEPLOYMENT_APPROVAL,
        GenerationStatus.CANCELLING,
        GenerationStatus.FAILED,
    },
    GenerationStatus.CANCELLING: {
        GenerationStatus.CANCELLED,
        GenerationStatus.FAILED,
    },
    GenerationStatus.FAILED: {
        GenerationStatus.SCHEDULED,  # Deterministic idempotent retry
        GenerationStatus.CANCELLING,
    },
    GenerationStatus.TIMED_OUT: {
        GenerationStatus.SCHEDULED,  # Deterministic idempotent retry
        GenerationStatus.CANCELLING,
    },
    GenerationStatus.BLOCKED: {
        GenerationStatus.SCHEDULED,  # Deterministic idempotent retry
        GenerationStatus.CANCELLING,
    },
    GenerationStatus.CANCELLED: set(),    # Terminal state
    GenerationStatus.ROLLED_BACK: set(),  # Terminal state
    GenerationStatus.SUPERSEDED: set(),   # Terminal state
}


class GenerationStateMachine:
    """State transition service for Generation models."""

    @classmethod
    def can_transition(cls, current_status: str, target_status: str) -> bool:
        """Check if transition from current_status to target_status is valid."""
        allowed = VALID_TRANSITIONS.get(current_status, set())
        return target_status in allowed

    @classmethod
    def transition(
        cls,
        generation: Generation,
        target_status: str,
        reason: str = "",
        error_message: str = "",
        failure_category: str = "",
        command_id: Optional[uuid.UUID] = None,
        actor: Optional[Any] = None,
        metadata_update: Optional[Dict[str, Any]] = None,
    ) -> Generation:
        """Execute a locked, transactional state transition on a Generation instance.

        Raises:
            InvalidStateTransitionError: If target_status is not a valid progression.
        """
        with transaction.atomic():
            # Re-fetch and lock the generation instance
            locked_gen = (
                Generation.objects.select_for_update()
                .filter(id=generation.id)
                .first()
            )
            if not locked_gen:
                raise ValueError(f"Generation with ID {generation.id} does not exist.")

            current_status = locked_gen.status

            # Idempotent no-op if already in target status
            if current_status == target_status:
                return locked_gen

            if not cls.can_transition(current_status, target_status):
                raise InvalidStateTransitionError(
                    current_status=current_status,
                    target_status=target_status,
                    message=(
                        f"Invalid generation status transition: '{current_status}' -> '{target_status}'. "
                        f"Allowed transitions from '{current_status}': {list(VALID_TRANSITIONS.get(current_status, set()))}"
                    ),
                )

            now = timezone.now()
            seq = locked_gen.next_transition_sequence
            locked_gen.next_transition_sequence += 1
            locked_gen.state_version += 1
            locked_gen.status_changed_at = now

            if metadata_update:
                locked_gen.metadata.update(metadata_update)

            # Handle pause & resume bookkeeping
            if target_status == GenerationStatus.PAUSED:
                locked_gen.resume_status = current_status
                locked_gen.paused_at = now
            elif current_status == GenerationStatus.PAUSED and target_status != GenerationStatus.PAUSED:
                locked_gen.paused_at = None
                locked_gen.resume_status = None

            # Handle milestone timestamps
            if target_status == GenerationStatus.RELEASE_CANDIDATE and not locked_gen.completed_at:
                locked_gen.completed_at = now
            elif target_status == GenerationStatus.FAILED:
                locked_gen.failed_at = now
                locked_gen.error_message = error_message or locked_gen.error_message
                locked_gen.failure_category = failure_category or locked_gen.failure_category
            elif target_status == GenerationStatus.TIMED_OUT:
                locked_gen.timed_out_at = now
                locked_gen.error_message = error_message or locked_gen.error_message
                locked_gen.failure_category = failure_category or locked_gen.failure_category
            elif target_status == GenerationStatus.CANCELLING:
                locked_gen.cancel_requested_at = now
            elif target_status == GenerationStatus.CANCELLED:
                locked_gen.cancelled_at = now
            elif current_status in [GenerationStatus.FAILED, GenerationStatus.TIMED_OUT, GenerationStatus.BLOCKED] and target_status == GenerationStatus.SCHEDULED:
                # Recovering via retry
                locked_gen.error_message = ""
                locked_gen.failure_category = ""
                locked_gen.failed_at = None
                locked_gen.timed_out_at = None

            locked_gen.status = target_status
            locked_gen.save()

            # Record relational transition history (B3 truth)
            GenerationStateTransition.objects.create(
                generation=locked_gen,
                sequence=seq,
                from_status=current_status,
                to_status=target_status,
                command_id=command_id,
                actor=actor,
                reason=reason,
                metadata=metadata_update or {},
            )

            # Enqueue transactional outbox event
            from apps.workflows.services.outbox import OutboxService

            event_type = EventType.GENERATION_STATE_CHANGED
            if target_status == GenerationStatus.PAUSED:
                event_type = EventType.GENERATION_PAUSED
            elif target_status == GenerationStatus.CANCELLING:
                event_type = EventType.GENERATION_CANCELLATION_REQUESTED
            elif target_status == GenerationStatus.CANCELLED:
                event_type = EventType.GENERATION_CANCELLED
            elif target_status == GenerationStatus.FAILED:
                event_type = EventType.GENERATION_FAILED
            elif target_status == GenerationStatus.TIMED_OUT:
                event_type = EventType.GENERATION_TIMED_OUT
            elif target_status == GenerationStatus.BLOCKED:
                event_type = EventType.GENERATION_BLOCKED
            elif current_status == GenerationStatus.PAUSED:
                event_type = EventType.GENERATION_RESUMED

            OutboxService.enqueue_event(
                organization=locked_gen.organization,
                generation=locked_gen,
                aggregate_type="generation",
                aggregate_id=str(locked_gen.id),
                event_type=event_type,
                payload={
                    "generation_id": str(locked_gen.id),
                    "from_status": current_status,
                    "to_status": target_status,
                    "sequence": seq,
                    "state_version": locked_gen.state_version,
                    "reason": reason,
                },
            )

            return locked_gen
