"""Generation lifecycle state machine service.

Enforces valid state transitions, updates timestamp milestones, and records
state history for the multi-agent generation domain.
"""
from typing import Any, Dict, Optional, Set
from django.utils import timezone

from apps.generations.enums import GenerationStatus
from apps.generations.exceptions import InvalidStateTransitionError
from apps.generations.models import Generation

VALID_TRANSITIONS: Dict[str, Set[str]] = {
    GenerationStatus.DRAFT: {
        GenerationStatus.SPECIFICATION,
        GenerationStatus.CANCELLED,
    },
    GenerationStatus.SPECIFICATION: {
        GenerationStatus.APPROVED,
        GenerationStatus.FAILED,
        GenerationStatus.CANCELLED,
    },
    GenerationStatus.APPROVED: {
        GenerationStatus.PLANNING,
        GenerationStatus.CANCELLED,
    },
    GenerationStatus.PLANNING: {
        GenerationStatus.BUILDING,
        GenerationStatus.PAUSED,
        GenerationStatus.FAILED,
        GenerationStatus.CANCELLED,
    },
    GenerationStatus.BUILDING: {
        GenerationStatus.TESTING,
        GenerationStatus.PAUSED,
        GenerationStatus.FAILED,
        GenerationStatus.CANCELLED,
    },
    GenerationStatus.TESTING: {
        GenerationStatus.REVIEW,
        GenerationStatus.BUILDING,  # Repair loop from test failure
        GenerationStatus.PAUSED,
        GenerationStatus.FAILED,
        GenerationStatus.CANCELLED,
    },
    GenerationStatus.REVIEW: {
        GenerationStatus.PACKAGING,
        GenerationStatus.BUILDING,  # Critic / review repair loop
        GenerationStatus.PAUSED,
        GenerationStatus.FAILED,
        GenerationStatus.CANCELLED,
    },
    GenerationStatus.PACKAGING: {
        GenerationStatus.COMPLETED,
        GenerationStatus.FAILED,
        GenerationStatus.CANCELLED,
    },
    GenerationStatus.PAUSED: {
        GenerationStatus.PLANNING,
        GenerationStatus.BUILDING,
        GenerationStatus.TESTING,
        GenerationStatus.REVIEW,
        GenerationStatus.PACKAGING,
        GenerationStatus.CANCELLED,
    },
    GenerationStatus.FAILED: {
        GenerationStatus.RETRYING,
        GenerationStatus.CANCELLED,
    },
    GenerationStatus.RETRYING: {
        GenerationStatus.PLANNING,
        GenerationStatus.BUILDING,
        GenerationStatus.TESTING,
        GenerationStatus.REVIEW,
        GenerationStatus.PACKAGING,
        GenerationStatus.FAILED,
        GenerationStatus.CANCELLED,
    },
    GenerationStatus.COMPLETED: set(),  # Terminal state
    GenerationStatus.CANCELLED: set(),  # Terminal state
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
        metadata_update: Optional[Dict[str, Any]] = None,
    ) -> Generation:
        """Execute a validated state transition on a Generation instance.

        Raises:
            InvalidStateTransitionError: If target_status is not a valid progression.
        """
        current_status = generation.status

        # If already in target status, return idempotently
        if current_status == target_status:
            return generation

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
        update_fields = ["status", "updated_at", "metadata"]

        # Update metadata state history
        history_entry = {
            "from_status": current_status,
            "to_status": target_status,
            "timestamp": now.isoformat(),
            "reason": reason,
        }
        if "state_history" not in generation.metadata:
            generation.metadata["state_history"] = []
        generation.metadata["state_history"].append(history_entry)

        if metadata_update:
            generation.metadata.update(metadata_update)

        # Handle target milestone timestamps
        if target_status == GenerationStatus.COMPLETED:
            generation.completed_at = now
            update_fields.append("completed_at")
        elif target_status == GenerationStatus.FAILED:
            generation.failed_at = now
            generation.error_message = error_message or generation.error_message
            generation.failure_category = failure_category or generation.failure_category
            update_fields.extend(["failed_at", "error_message", "failure_category"])
        elif target_status == GenerationStatus.CANCELLED:
            generation.cancelled_at = now
            update_fields.append("cancelled_at")
        elif target_status == GenerationStatus.PAUSED:
            generation.paused_at = now
            update_fields.append("paused_at")
        elif current_status == GenerationStatus.PAUSED:
            generation.paused_at = None
            update_fields.append("paused_at")

        generation.status = target_status
        generation.save(update_fields=update_fields)

        return generation
