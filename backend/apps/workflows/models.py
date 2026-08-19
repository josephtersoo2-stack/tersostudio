"""Data models for Workflow Runs, Work Packages, Dependencies, Attempts, Leases, Commands, and Outbox."""
import uuid
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.core.models import OrganizationOwnedModel, TimeStampedModel
from apps.generations.models import Generation, GenerationStep
from .enums import (
    AttemptStatus,
    CommandStatus,
    CommandType,
    DependencyType,
    LeaseReleaseReason,
    WorkflowRunStatus,
    WorkPackageStatus,
)


class WorkflowRun(OrganizationOwnedModel):
    """Orchestration container tracking a full DAG execution for a Generation."""

    generation = models.ForeignKey(
        Generation,
        on_delete=models.CASCADE,
        related_name="workflow_runs",
        db_index=True,
        help_text="Parent generation this workflow run executes.",
    )
    run_number = models.PositiveIntegerField(
        default=1,
        help_text="Monotonically incrementing run number within the generation.",
    )
    status = models.CharField(
        max_length=32,
        choices=WorkflowRunStatus.choices,
        default=WorkflowRunStatus.PENDING,
        db_index=True,
        help_text="Current state of the workflow run orchestration.",
    )
    state_version = models.PositiveBigIntegerField(
        default=0,
        help_text="Monotonically incrementing version for row-level concurrency control.",
    )
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when workflow run execution commenced.",
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when workflow run finished.",
    )
    paused_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when workflow run was paused.",
    )
    cancel_requested_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when cancellation was requested.",
    )
    last_scheduler_heartbeat_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when the scheduler last evaluated this run.",
    )
    failure_category = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="Failure classification if workflow run failed.",
    )
    error_message = models.TextField(
        blank=True,
        default="",
        help_text="Error details if workflow run failed.",
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Workflow execution metadata and parameters.",
    )

    class Meta:
        ordering = ["-run_number"]
        verbose_name = "Workflow Run"
        verbose_name_plural = "Workflow Runs"
        constraints = [
            models.UniqueConstraint(
                fields=["generation", "run_number"],
                name="unique_generation_run_number",
            ),
            models.UniqueConstraint(
                fields=["generation"],
                condition=models.Q(
                    status__in=[
                        WorkflowRunStatus.PENDING,
                        WorkflowRunStatus.RUNNING,
                        WorkflowRunStatus.PAUSED,
                        WorkflowRunStatus.CANCELLING,
                    ]
                ),
                name="unique_active_workflow_run_per_generation",
            ),
        ]
        indexes = [
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["generation", "status"]),
        ]

    def __str__(self) -> str:
        return f"WorkflowRun #{self.run_number} for Gen {self.generation_id} [{self.status}]"

    def clean(self) -> None:
        super().clean()
        if self.generation_id:
            if not self.organization_id:
                self.organization = self.generation.organization
            elif self.organization_id != self.generation.organization_id:
                raise ValidationError(
                    "WorkflowRun organization must match Generation organization.",
                    code="organization_mismatch",
                )

    def save(self, *args, **kwargs):
        if self.generation_id:
            if not self.organization_id:
                self.organization = self.generation.organization
            elif self.organization_id != self.generation.organization_id:
                raise ValidationError(
                    "WorkflowRun organization must match Generation organization.",
                    code="organization_mismatch",
                )
        super().save(*args, **kwargs)


class WorkPackage(OrganizationOwnedModel):
    """Atomic task unit within a WorkflowRun DAG."""

    workflow_run = models.ForeignKey(
        WorkflowRun,
        on_delete=models.CASCADE,
        related_name="packages",
        db_index=True,
        help_text="Workflow run this package belongs to.",
    )
    generation_step = models.ForeignKey(
        GenerationStep,
        on_delete=models.PROTECT,
        related_name="work_packages",
        help_text="Link to parent generation step.",
    )
    key = models.CharField(
        max_length=128,
        db_index=True,
        help_text="Stable logical key unique within the workflow run.",
    )
    name = models.CharField(
        max_length=255,
        help_text="Descriptive task name.",
    )
    status = models.CharField(
        max_length=32,
        choices=WorkPackageStatus.choices,
        default=WorkPackageStatus.PENDING,
        db_index=True,
        help_text="Current state of the work package.",
    )
    priority = models.IntegerField(
        default=100,
        db_index=True,
        help_text="Execution priority (higher value executed first).",
    )
    max_attempts = models.PositiveIntegerField(
        default=3,
        help_text="Maximum allowed attempts before terminal failure.",
    )
    attempt_count = models.PositiveIntegerField(
        default=0,
        help_text="Total number of execution attempts initiated.",
    )
    timeout_seconds = models.PositiveIntegerField(
        default=600,
        help_text="Maximum execution duration per attempt in seconds.",
    )
    retry_base_seconds = models.PositiveIntegerField(
        default=30,
        help_text="Base backoff duration for retries in seconds.",
    )
    next_attempt_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Timestamp when next attempt can be claimed after retry backoff.",
    )
    cancel_requested_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when cancellation was requested for this package.",
    )
    input_payload = models.JSONField(
        default=dict,
        blank=True,
        help_text="Input data, context, and requirements passed to worker.",
    )
    result_payload = models.JSONField(
        default=dict,
        blank=True,
        help_text="Candidate output produced by worker.",
    )
    validation_evidence = models.JSONField(
        default=dict,
        blank=True,
        help_text="Deterministic verification proof required for completion.",
    )
    failure_category = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="Classified category of failure.",
    )
    error_message = models.TextField(
        blank=True,
        default="",
        help_text="Error message if package execution failed.",
    )
    ready_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Timestamp when dependencies resolved and package became READY.",
    )
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when first execution attempt started.",
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when validated completion occurred.",
    )
    state_version = models.PositiveBigIntegerField(
        default=0,
        help_text="Monotonically incrementing version for row-level concurrency control.",
    )

    class Meta:
        ordering = ["-priority", "ready_at", "id"]
        verbose_name = "Work Package"
        verbose_name_plural = "Work Packages"
        constraints = [
            models.UniqueConstraint(
                fields=["workflow_run", "key"],
                name="unique_workflow_run_package_key",
            )
        ]
        indexes = [
            models.Index(fields=["organization", "status"], name="idx_wp_org_status"),
            models.Index(fields=["workflow_run", "status"], name="idx_wp_run_status"),
            models.Index(fields=["status", "next_attempt_at"], name="idx_wp_status_next_attempt"),
            models.Index(fields=["status", "priority", "ready_at"], name="idx_wp_status_prio_ready"),
        ]

    def __str__(self) -> str:
        return f"Package '{self.key}' ({self.name}) [{self.status}]"

    def clean(self) -> None:
        super().clean()
        if not self.workflow_run_id:
            raise ValidationError(
                {"workflow_run": "WorkPackage workflow_run is required."},
                code="missing_workflow_run",
            )
        if not self.generation_step_id:
            raise ValidationError(
                {"generation_step": "WorkPackage generation_step is required."},
                code="missing_generation_step",
            )
        if not self.organization_id:
            self.organization = self.workflow_run.organization
        elif self.organization_id != self.workflow_run.organization_id:
            raise ValidationError(
                {"organization": "WorkPackage organization must match WorkflowRun organization."},
                code="organization_mismatch",
            )
        if self.generation_step.generation_id != self.workflow_run.generation_id:
            raise ValidationError(
                {"generation_step": "WorkPackage generation_step must belong to the same generation as its workflow_run."},
                code="cross_generation_step",
            )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


class WorkPackageDependency(TimeStampedModel):
    """Directed dependency edge in the WorkflowRun DAG."""

    workflow_run = models.ForeignKey(
        WorkflowRun,
        on_delete=models.CASCADE,
        related_name="dependencies",
        db_index=True,
        help_text="Workflow run containing this DAG edge.",
    )
    predecessor = models.ForeignKey(
        WorkPackage,
        on_delete=models.CASCADE,
        related_name="downstream_dependencies",
        help_text="Package that must complete before successor can become ready.",
    )
    successor = models.ForeignKey(
        WorkPackage,
        on_delete=models.CASCADE,
        related_name="upstream_dependencies",
        help_text="Package that depends on predecessor.",
    )
    dependency_type = models.CharField(
        max_length=20,
        choices=DependencyType.choices,
        default=DependencyType.HARD,
        help_text="HARD blocks successor; SOFT provides advisory ordering.",
    )

    class Meta:
        verbose_name = "Work Package Dependency"
        verbose_name_plural = "Work Package Dependencies"
        constraints = [
            models.UniqueConstraint(
                fields=["predecessor", "successor"],
                name="unique_package_dependency_edge",
            ),
            models.CheckConstraint(
                condition=~models.Q(predecessor=models.F("successor")),
                name="check_no_self_dependency",
            ),
        ]

    def clean(self) -> None:
        super().clean()
        if self.predecessor_id and self.successor_id and self.predecessor_id == self.successor_id:
            raise ValidationError(
                "A work package cannot depend on itself.",
                code="self_dependency",
            )
        if self.predecessor_id and self.successor_id:
            if self.predecessor.workflow_run_id != self.successor.workflow_run_id:
                raise ValidationError(
                    "Dependencies can only link work packages within the same workflow run.",
                    code="cross_run_dependency",
                )
            if self.workflow_run_id != self.predecessor.workflow_run_id:
                self.workflow_run = self.predecessor.workflow_run

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"Dependency: {self.predecessor.key} -> {self.successor.key} ({self.dependency_type})"


class WorkPackageAttempt(TimeStampedModel):
    """Append-only physical execution attempt for a WorkPackage."""

    work_package = models.ForeignKey(
        WorkPackage,
        on_delete=models.CASCADE,
        related_name="attempts",
        db_index=True,
        help_text="Parent work package.",
    )
    attempt_number = models.PositiveIntegerField(
        help_text="1-indexed attempt number for the package.",
    )
    status = models.CharField(
        max_length=32,
        choices=AttemptStatus.choices,
        default=AttemptStatus.QUEUED,
        db_index=True,
        help_text="Status of this attempt.",
    )
    worker_id = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Identifier of worker or agent claiming this attempt.",
    )
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when attempt execution began.",
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when attempt completed or terminated.",
    )
    heartbeat_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of most recent worker heartbeat.",
    )
    retryable = models.BooleanField(
        default=True,
        help_text="Whether a failure on this attempt is eligible for retry.",
    )
    failure_category = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="Failure classification.",
    )
    error_details = models.JSONField(
        default=dict,
        blank=True,
        help_text="Diagnostic failure details and traceback.",
    )
    result_payload = models.JSONField(
        default=dict,
        blank=True,
        help_text="Output payload produced by worker on this attempt.",
    )

    class Meta:
        ordering = ["attempt_number"]
        verbose_name = "Work Package Attempt"
        verbose_name_plural = "Work Package Attempts"
        constraints = [
            models.UniqueConstraint(
                fields=["work_package", "attempt_number"],
                name="unique_package_attempt_number",
            )
        ]

    def __str__(self) -> str:
        return f"Attempt #{self.attempt_number} for Package {self.work_package.key} [{self.status}]"


class WorkPackageLease(TimeStampedModel):
    """Exclusive distributed lease protecting an active WorkPackage execution attempt."""

    work_package = models.ForeignKey(
        WorkPackage,
        on_delete=models.CASCADE,
        related_name="leases",
        db_index=True,
        help_text="Work package covered by this lease.",
    )
    attempt = models.ForeignKey(
        WorkPackageAttempt,
        on_delete=models.CASCADE,
        related_name="leases",
        db_index=True,
        help_text="Attempt this lease is assigned to.",
    )
    lease_token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        db_index=True,
        help_text="Opaque secret token required for heartbeat and release.",
    )
    worker_id = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Worker identifier holding this lease.",
    )
    acquired_at = models.DateTimeField(
        default=timezone.now,
        help_text="Timestamp when lease was granted.",
    )
    heartbeat_at = models.DateTimeField(
        default=timezone.now,
        help_text="Timestamp when lease was last refreshed.",
    )
    expires_at = models.DateTimeField(
        db_index=True,
        help_text="Timestamp after which lease is considered stale and reapable.",
    )
    released_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Timestamp when lease was released.",
    )
    release_reason = models.CharField(
        max_length=50,
        choices=LeaseReleaseReason.choices,
        blank=True,
        default="",
        help_text="Reason recorded upon lease release.",
    )

    class Meta:
        ordering = ["-acquired_at"]
        verbose_name = "Work Package Lease"
        verbose_name_plural = "Work Package Leases"
        constraints = [
            models.UniqueConstraint(
                fields=["work_package"],
                condition=Q(released_at__isnull=True),
                name="unique_active_lease_per_package",
            )
        ]

    def is_expired(self, now=None) -> bool:
        """Check if lease has expired."""
        if self.released_at:
            return False
        current_time = now or timezone.now()
        return current_time >= self.expires_at

    def __str__(self) -> str:
        status = "RELEASED" if self.released_at else "ACTIVE"
        return f"Lease {self.lease_token} for Package {self.work_package.key} [{status}]"


class WorkflowCommand(OrganizationOwnedModel):
    """Idempotent control command audit and replay record."""

    generation = models.ForeignKey(
        Generation,
        on_delete=models.CASCADE,
        related_name="workflow_commands",
        db_index=True,
        help_text="Target generation for this command.",
    )
    command_type = models.CharField(
        max_length=32,
        choices=CommandType.choices,
        db_index=True,
        help_text="Command type (PAUSE, RESUME, CANCEL, RETRY).",
    )
    idempotency_key = models.CharField(
        max_length=128,
        db_index=True,
        help_text="Client-supplied idempotency key.",
    )
    request_hash = models.CharField(
        max_length=64,
        db_index=True,
        help_text="SHA-256 hash of canonical request parameters.",
    )
    request_payload = models.JSONField(
        default=dict,
        blank=True,
        help_text="Sanitized request payload.",
    )
    response_payload = models.JSONField(
        default=dict,
        blank=True,
        help_text="Stored response for idempotent replay.",
    )
    status = models.CharField(
        max_length=20,
        choices=CommandStatus.choices,
        default=CommandStatus.APPLIED,
        help_text="Outcome status of the command.",
    )
    applied_at = models.DateTimeField(
        default=timezone.now,
        help_text="Timestamp when command was applied.",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Workflow Command"
        verbose_name_plural = "Workflow Commands"
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "idempotency_key"],
                name="unique_organization_command_idempotency_key",
            )
        ]

    def __str__(self) -> str:
        return f"Command {self.command_type} ({self.idempotency_key}) for Gen {self.generation_id}"


class OutboxEvent(OrganizationOwnedModel):
    """Transactional outbox record guaranteeing at-least-once event delivery."""

    event_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        db_index=True,
        help_text="Stable event identifier across delivery attempts.",
    )
    generation = models.ForeignKey(
        Generation,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="outbox_events",
        db_index=True,
        help_text="Associated generation if applicable.",
    )
    aggregate_type = models.CharField(
        max_length=64,
        db_index=True,
        help_text="Aggregate domain classification (e.g. 'generation', 'workflow', 'work_package').",
    )
    aggregate_id = models.CharField(
        max_length=64,
        db_index=True,
        help_text="String ID of aggregate entity.",
    )
    event_type = models.CharField(
        max_length=128,
        db_index=True,
        help_text="Normalized event type string.",
    )
    payload = models.JSONField(
        default=dict,
        blank=True,
        help_text="Event payload dictionary.",
    )
    occurred_at = models.DateTimeField(
        default=timezone.now,
        help_text="Timestamp when domain event occurred.",
    )
    available_at = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        help_text="Earliest timestamp when event can be claimed for dispatch.",
    )
    claim_token = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Opaque token assigned to the claiming dispatcher worker.",
    )
    claimed_until = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Timestamp when dispatcher claim lease expires.",
    )
    published_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Timestamp when event was acknowledged published to transport.",
    )
    publish_attempts = models.PositiveIntegerField(
        default=0,
        help_text="Total delivery attempts.",
    )
    last_error = models.TextField(
        blank=True,
        default="",
        help_text="Error message from last failed publish attempt.",
    )

    class Meta:
        ordering = ["available_at", "id"]
        verbose_name = "Outbox Event"
        verbose_name_plural = "Outbox Events"
        indexes = [
            models.Index(fields=["published_at", "available_at"]),
            models.Index(fields=["claimed_until", "published_at"]),
        ]

    def __str__(self) -> str:
        status = "PUBLISHED" if self.published_at else "PENDING"
        return f"OutboxEvent {self.event_id} [{self.event_type}] [{status}]"
