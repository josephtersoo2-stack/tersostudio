"""Enums and choices for Generations, Milestones, Steps, Agent Runs, Workspaces, and Artifacts."""
from django.db import models


class GenerationStatus(models.TextChoices):
    """Canonical lifecycle and control statuses for a Generation in Tersuite AI Studio."""

    # Forward lifecycle progression
    DRAFT = "DRAFT", "Draft"
    DISCOVERY = "DISCOVERY", "Discovery"
    SPECIFICATION_DRAFT = "SPECIFICATION_DRAFT", "Specification Draft"
    PLAN_DRAFT = "PLAN_DRAFT", "Plan Draft"
    AWAITING_APPROVAL = "AWAITING_APPROVAL", "Awaiting Approval"
    APPROVED = "APPROVED", "Approved"
    SCHEDULED = "SCHEDULED", "Scheduled"
    BUILDING = "BUILDING", "Building"
    INTEGRATING = "INTEGRATING", "Integrating"
    REVIEWING = "REVIEWING", "Reviewing"
    CORRECTING = "CORRECTING", "Correcting"
    SANDBOX_QA = "SANDBOX_QA", "Sandbox QA"
    RELEASE_CANDIDATE = "RELEASE_CANDIDATE", "Release Candidate"
    AWAITING_DEPLOYMENT_APPROVAL = "AWAITING_DEPLOYMENT_APPROVAL", "Awaiting Deployment Approval"
    STAGED = "STAGED", "Staged"
    ACTIVE = "ACTIVE", "Active"

    # Control and terminal/failure states
    PAUSED = "PAUSED", "Paused"
    CANCELLING = "CANCELLING", "Cancelling"
    CANCELLED = "CANCELLED", "Cancelled"
    FAILED = "FAILED", "Failed"
    TIMED_OUT = "TIMED_OUT", "Timed Out"
    BLOCKED = "BLOCKED", "Blocked"
    ROLLED_BACK = "ROLLED_BACK", "Rolled Back"
    SUPERSEDED = "SUPERSEDED", "Superseded"


class MilestoneStatus(models.TextChoices):
    """Lifecycle status for a GenerationMilestone."""

    PENDING = "PENDING", "Pending"
    IN_PROGRESS = "IN_PROGRESS", "In Progress"
    COMPLETED = "COMPLETED", "Completed"
    FAILED = "FAILED", "Failed"
    BLOCKED = "BLOCKED", "Blocked"
    CANCELLED = "CANCELLED", "Cancelled"


class StepStatus(models.TextChoices):
    """Execution status for a logical GenerationStep."""

    PENDING = "PENDING", "Pending"
    READY = "READY", "Ready"
    RUNNING = "RUNNING", "Running"
    CANDIDATE_COMPLETE = "CANDIDATE_COMPLETE", "Candidate Complete"
    COMPLETED = "COMPLETED", "Completed"
    FAILED = "FAILED", "Failed"
    BLOCKED = "BLOCKED", "Blocked"
    CANCELLED = "CANCELLED", "Cancelled"
    TIMED_OUT = "TIMED_OUT", "Timed Out"
    SKIPPED = "SKIPPED", "Skipped"


class AgentRunStatus(models.TextChoices):
    """Execution status for an individual AgentRun attempt."""

    QUEUED = "QUEUED", "Queued"
    RUNNING = "RUNNING", "Running"
    COMPLETED = "COMPLETED", "Completed"
    FAILED = "FAILED", "Failed"
    CANCELLED = "CANCELLED", "Cancelled"
    TIMED_OUT = "TIMED_OUT", "Timed Out"


class WorkspaceStorageType(models.TextChoices):
    """Type of isolation storage backing the Workspace."""

    LOCAL = "LOCAL", "Local File System"
    EPHEMERAL_CONTAINER = "EPHEMERAL_CONTAINER", "Ephemeral Container"
    REMOTE_STORAGE = "REMOTE_STORAGE", "Remote Object Storage"


class ArtifactType(models.TextChoices):
    """Classification of generated durable artifacts."""

    SOURCE_CODE = "SOURCE_CODE", "Source Code File"
    CONFIGURATION = "CONFIGURATION", "Configuration File"
    TEST_REPORT = "TEST_REPORT", "Test & Verification Report"
    DOCUMENTATION = "DOCUMENTATION", "Documentation / Readme"
    ZIP_ARCHIVE = "ZIP_ARCHIVE", "ZIP Archive Package"
    SECURITY_REPORT = "SECURITY_REPORT", "Security Audit Report"
    OTHER = "OTHER", "Other Output"
