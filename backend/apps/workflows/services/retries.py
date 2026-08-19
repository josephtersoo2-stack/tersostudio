"""Deterministic retry policy and exponential backoff calculations."""
from datetime import timedelta
from typing import Optional
from django.conf import settings
from django.utils import timezone

from apps.generations.enums import GenerationStatus
from apps.workflows.enums import WorkflowRunStatus, WorkPackageStatus
from apps.workflows.models import WorkPackage, WorkPackageAttempt


class WorkflowRetryService:
    """Service governing work package retry eligibility and scheduling."""

    @classmethod
    def calculate_retry_delay(
        cls,
        attempt_number: int,
        base_seconds: Optional[int] = None,
        max_seconds: Optional[int] = None,
    ) -> int:
        """Calculate deterministic exponential backoff delay in seconds.

        Formula: min(base_seconds * 2 ** (attempt_number - 1), max_seconds)
        """
        base = base_seconds or getattr(settings, "WORKFLOW_RETRY_BASE_SECONDS", 30)
        cap = max_seconds or getattr(settings, "WORKFLOW_RETRY_MAX_SECONDS", 900)

        if attempt_number <= 1:
            delay = base
        else:
            delay = base * (2 ** (attempt_number - 1))

        return min(delay, cap)

    @classmethod
    def should_retry(
        cls,
        work_package: WorkPackage,
        attempt: Optional[WorkPackageAttempt] = None,
    ) -> bool:
        """Determine if a failed package is eligible for another attempt."""
        if attempt is not None and not attempt.retryable:
            return False

        if work_package.attempt_count >= work_package.max_attempts:
            return False

        run = work_package.workflow_run
        if run.status in [
            WorkflowRunStatus.PAUSED,
            WorkflowRunStatus.CANCELLING,
            WorkflowRunStatus.CANCELLED,
            WorkflowRunStatus.FAILED,
            WorkflowRunStatus.TIMED_OUT,
        ]:
            return False

        generation = run.generation
        if generation.status in [
            GenerationStatus.PAUSED,
            GenerationStatus.CANCELLING,
            GenerationStatus.CANCELLED,
            GenerationStatus.FAILED,
            GenerationStatus.TIMED_OUT,
        ]:
            return False

        return True

    @classmethod
    def schedule_retry(
        cls,
        work_package: WorkPackage,
        now=None,
    ) -> WorkPackage:
        """Place work package into RETRY_WAIT status with calculated next_attempt_at."""
        current_time = now or timezone.now()
        delay_seconds = cls.calculate_retry_delay(
            attempt_number=work_package.attempt_count,
            base_seconds=work_package.retry_base_seconds,
        )
        work_package.status = WorkPackageStatus.RETRY_WAIT
        work_package.next_attempt_at = current_time + timedelta(seconds=delay_seconds)
        work_package.save(update_fields=["status", "next_attempt_at", "updated_at"])
        return work_package
