"""Enums and choices for Generations, Steps, Agent Runs, Workspaces, and Artifacts."""
from django.db import models


class GenerationStatus(models.TextChoices):
    """Lifecycle and control statuses for a Generation."""

    # Forward lifecycle progression
    DRAFT = "DRAFT", "Draft"
    SPECIFICATION = "SPECIFICATION", "Specification"
    APPROVED = "APPROVED", "Approved"
    PLANNING = "PLANNING", "Planning"
    BUILDING = "BUILDING", "Building"
    TESTING = "TESTING", "Testing"
    REVIEW = "REVIEW", "Review"
    PACKAGING = "PACKAGING", "Packaging"
    COMPLETED = "COMPLETED", "Completed"

    # Control and terminal/failure states
    FAILED = "FAILED", "Failed"
    CANCELLED = "CANCELLED", "Cancelled"
    PAUSED = "PAUSED", "Paused"
    RETRYING = "RETRYING", "Retrying"


class StepStatus(models.TextChoices):
    """Execution status for a logical GenerationStep."""

    PENDING = "PENDING", "Pending"
    RUNNING = "RUNNING", "Running"
    COMPLETED = "COMPLETED", "Completed"
    FAILED = "FAILED", "Failed"
    CANCELLED = "CANCELLED", "Cancelled"
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
