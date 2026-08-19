"""Enums and choices for Workflow Runs, Work Packages, Leases, Attempts, and Commands."""
from django.db import models


class WorkflowRunStatus(models.TextChoices):
    """Lifecycle status for a WorkflowRun orchestrator container."""

    PENDING = "PENDING", "Pending"
    RUNNING = "RUNNING", "Running"
    PAUSED = "PAUSED", "Paused"
    CANCELLING = "CANCELLING", "Cancelling"
    CANCELLED = "CANCELLED", "Cancelled"
    COMPLETED = "COMPLETED", "Completed"
    FAILED = "FAILED", "Failed"
    TIMED_OUT = "TIMED_OUT", "Timed Out"
    BLOCKED = "BLOCKED", "Blocked"


class WorkPackageStatus(models.TextChoices):
    """Lifecycle status for an individual atomic WorkPackage."""

    PENDING = "PENDING", "Pending"
    READY = "READY", "Ready"
    LEASED = "LEASED", "Leased"
    RUNNING = "RUNNING", "Running"
    CANDIDATE_COMPLETE = "CANDIDATE_COMPLETE", "Candidate Complete"
    COMPLETED = "COMPLETED", "Completed"
    RETRY_WAIT = "RETRY_WAIT", "Retry Wait"
    FAILED = "FAILED", "Failed"
    BLOCKED = "BLOCKED", "Blocked"
    CANCELLING = "CANCELLING", "Cancelling"
    CANCELLED = "CANCELLED", "Cancelled"
    TIMED_OUT = "TIMED_OUT", "Timed Out"


class DependencyType(models.TextChoices):
    """Classification of DAG work package dependencies."""

    HARD = "HARD", "Hard Dependency"
    SOFT = "SOFT", "Soft Dependency"


class AttemptStatus(models.TextChoices):
    """Execution status for a WorkPackageAttempt."""

    QUEUED = "QUEUED", "Queued"
    RUNNING = "RUNNING", "Running"
    CANDIDATE_COMPLETE = "CANDIDATE_COMPLETE", "Candidate Complete"
    FAILED = "FAILED", "Failed"
    TIMED_OUT = "TIMED_OUT", "Timed Out"
    CANCELLED = "CANCELLED", "Cancelled"


class LeaseReleaseReason(models.TextChoices):
    """Reason recorded when a WorkPackageLease is released."""

    COMPLETED = "COMPLETED", "Candidate Complete"
    FAILED = "FAILED", "Execution Failed"
    EXPIRED = "EXPIRED", "Lease Expired"
    CANCELLED = "CANCELLED", "Cancelled"
    WORKER_SHUTDOWN = "WORKER_SHUTDOWN", "Worker Shutdown"


class CommandType(models.TextChoices):
    """Classification of public idempotent workflow control commands."""

    PAUSE = "PAUSE", "Pause"
    RESUME = "RESUME", "Resume"
    CANCEL = "CANCEL", "Cancel"
    RETRY = "RETRY", "Retry"


class CommandStatus(models.TextChoices):
    """Execution status of an idempotent WorkflowCommand."""

    APPLIED = "APPLIED", "Applied"
    FAILED = "FAILED", "Failed"
