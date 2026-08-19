"""Data models for Generations, Milestones, State Transitions, Steps, Agent Runs, Workspaces, and Artifacts."""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from apps.core.models import OrganizationOwnedModel, TimeStampedModel
from apps.projects.models import Project
from .enums import (
    AgentRunStatus,
    ArtifactType,
    GenerationStatus,
    MilestoneStatus,
    StepStatus,
    WorkspaceStorageType,
)


class GenerationQuerySet(models.QuerySet):
    """Custom queryset for generations."""

    def for_organization(self, organization):
        """Filter generations owned by a specific organization."""
        return self.filter(organization=organization)

    def active(self):
        """Filter ongoing active generations (excluding terminal statuses)."""
        return self.exclude(
            status__in=[
                GenerationStatus.CANCELLED,
                GenerationStatus.FAILED,
                GenerationStatus.TIMED_OUT,
                GenerationStatus.ROLLED_BACK,
                GenerationStatus.SUPERSEDED,
            ]
        )

    def completed(self):
        """Filter successfully completed generations (post-build / release ready)."""
        return self.filter(
            status__in=[
                GenerationStatus.RELEASE_CANDIDATE,
                GenerationStatus.AWAITING_DEPLOYMENT_APPROVAL,
                GenerationStatus.STAGED,
                GenerationStatus.ACTIVE,
            ]
        )

    def failed(self):
        """Filter failed generations."""
        return self.filter(status=GenerationStatus.FAILED)


class Generation(OrganizationOwnedModel):
    """Represents an autonomous multi-agent plugin generation lifecycle."""

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="generations",
        db_index=True,
        help_text="Parent project for this generation.",
    )
    prompt = models.TextField(
        help_text="Initial natural language prompt or requirements from user.",
    )
    status = models.CharField(
        max_length=64,
        choices=GenerationStatus.choices,
        default=GenerationStatus.DRAFT,
        db_index=True,
        help_text="Current canonical state in the generation lifecycle machine.",
    )
    state_version = models.PositiveBigIntegerField(
        default=0,
        help_text="Monotonically incrementing version for row concurrency control.",
    )
    next_transition_sequence = models.PositiveBigIntegerField(
        default=1,
        help_text="Monotonically increasing sequence number for state transitions.",
    )
    status_changed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when the status last transitioned.",
    )
    resume_status = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        help_text="Saved status prior to entering PAUSED state.",
    )
    cancel_requested_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when cancellation was requested.",
    )
    timed_out_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when generation timed out.",
    )
    current_step_number = models.PositiveIntegerField(
        default=0,
        help_text="Index of the currently active generation step.",
    )
    total_steps = models.PositiveIntegerField(
        default=0,
        help_text="Total number of steps planned for this generation.",
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Config settings, model preferences, and domain tags.",
    )
    error_message = models.TextField(
        blank=True,
        default="",
        help_text="Human-readable error details if generation failed.",
    )
    failure_category = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="Classified category of failure (e.g. MODEL_ERROR, TIMEOUT, etc.).",
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when generation reached RELEASE_CANDIDATE.",
    )
    cancelled_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when generation was cancelled.",
    )
    failed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when generation encountered an unrecoverable failure.",
    )
    paused_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when generation was temporarily paused.",
    )

    objects = GenerationQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Generation"
        verbose_name_plural = "Generations"
        indexes = [
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["project", "status"]),
        ]

    def __str__(self) -> str:
        return f"Generation {self.id} [{self.status}] for Project {self.project.name}"

    def clean(self) -> None:
        super().clean()
        if self.project_id:
            if not self.organization_id:
                self.organization = self.project.organization
            elif self.organization_id != self.project.organization_id:
                raise ValidationError(
                    "Generation organization must match project organization.",
                    code="organization_mismatch",
                )

    def save(self, *args, **kwargs):
        """Validate organization matches project organization."""
        if self.project_id:
            if not self.organization_id:
                self.organization = self.project.organization
            elif self.organization_id != self.project.organization_id:
                raise ValidationError(
                    "Generation organization must match project organization.",
                    code="organization_mismatch",
                )
        super().save(*args, **kwargs)


class GenerationMilestone(TimeStampedModel):
    """Represents a high-level sequential milestone group within a Generation."""

    generation = models.ForeignKey(
        Generation,
        on_delete=models.CASCADE,
        related_name="milestones",
        db_index=True,
        help_text="Generation this milestone belongs to.",
    )
    sequence = models.PositiveIntegerField(
        help_text="Order index of this milestone within the generation sequence (1-indexed).",
    )
    name = models.CharField(
        max_length=255,
        help_text="Descriptive name of the milestone.",
    )
    status = models.CharField(
        max_length=32,
        choices=MilestoneStatus.choices,
        default=MilestoneStatus.PENDING,
        db_index=True,
        help_text="Current state of this milestone.",
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Milestone metadata and scope details.",
    )
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when milestone execution commenced.",
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when milestone completed.",
    )

    class Meta:
        ordering = ["sequence"]
        verbose_name = "Generation Milestone"
        verbose_name_plural = "Generation Milestones"
        constraints = [
            models.UniqueConstraint(
                fields=["generation", "sequence"],
                name="unique_generation_milestone_sequence",
            )
        ]

    def __str__(self) -> str:
        return f"Milestone #{self.sequence}: {self.name} [{self.status}]"


class GenerationStateTransition(TimeStampedModel):
    """Immutable transition audit record for Generation lifecycle state changes."""

    generation = models.ForeignKey(
        Generation,
        on_delete=models.CASCADE,
        related_name="state_transitions",
        db_index=True,
        help_text="Generation this transition belongs to.",
    )
    sequence = models.PositiveBigIntegerField(
        help_text="Monotonically increasing sequence number within the generation.",
    )
    from_status = models.CharField(
        max_length=64,
        help_text="Origin status before transition.",
    )
    to_status = models.CharField(
        max_length=64,
        help_text="Target status after transition.",
    )
    command_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Associated command ID if initiated by an idempotent command.",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="generation_transitions",
        help_text="User who initiated or authorized this transition.",
    )
    reason = models.TextField(
        blank=True,
        default="",
        help_text="Reason or trigger for this transition.",
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Contextual metadata recorded at transition time.",
    )

    class Meta:
        ordering = ["sequence"]
        verbose_name = "Generation State Transition"
        verbose_name_plural = "Generation State Transitions"
        constraints = [
            models.UniqueConstraint(
                fields=["generation", "sequence"],
                name="unique_generation_transition_sequence",
            )
        ]

    def __str__(self) -> str:
        return f"Transition #{self.sequence} for Gen {self.generation_id}: {self.from_status} -> {self.to_status}"


class GenerationStep(TimeStampedModel):
    """Represents a discrete logical work unit or step in a Generation."""

    generation = models.ForeignKey(
        Generation,
        on_delete=models.CASCADE,
        related_name="steps",
        db_index=True,
        help_text="Generation this step belongs to.",
    )
    milestone = models.ForeignKey(
        GenerationMilestone,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="steps",
        db_index=True,
        help_text="Milestone container this step belongs to.",
    )
    step_number = models.PositiveIntegerField(
        help_text="Order index of this step within the generation sequence (1-indexed).",
    )
    name = models.CharField(
        max_length=255,
        help_text="Descriptive name of the step (e.g. 'WordPress Architecture Blueprint').",
    )
    agent_role = models.CharField(
        max_length=100,
        help_text="Designated agent domain role (e.g. 'architect', 'coder', 'security').",
    )
    status = models.CharField(
        max_length=30,
        choices=StepStatus.choices,
        default=StepStatus.PENDING,
        db_index=True,
        help_text="Current state of this step.",
    )
    input_payload = models.JSONField(
        default=dict,
        blank=True,
        help_text="Input contracts, context, or specification passed to this step.",
    )
    output_payload = models.JSONField(
        default=dict,
        blank=True,
        help_text="Output data, architecture plan, or code metadata generated by this step.",
    )
    error_message = models.TextField(
        blank=True,
        default="",
        help_text="Error message if step failed.",
    )
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when step execution commenced.",
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when step completed or terminated.",
    )

    class Meta:
        ordering = ["step_number"]
        verbose_name = "Generation Step"
        verbose_name_plural = "Generation Steps"
        constraints = [
            models.UniqueConstraint(
                fields=["generation", "step_number"],
                name="unique_generation_step_number",
            )
        ]

    def __str__(self) -> str:
        return f"Step {self.step_number}: {self.name} [{self.status}]"


class AgentRun(TimeStampedModel):
    """Represents a specific physical execution attempt for a GenerationStep."""

    step = models.ForeignKey(
        GenerationStep,
        on_delete=models.CASCADE,
        related_name="runs",
        db_index=True,
        help_text="The generation step this run executes.",
    )
    run_number = models.PositiveIntegerField(
        default=1,
        help_text="Attempt number for this step (1, 2, 3...).",
    )
    runtime_type = models.CharField(
        max_length=50,
        default="openhands",
        help_text="The runtime adapter executing this run (e.g. 'openhands', 'mock').",
    )
    session_id = models.CharField(
        max_length=255,
        blank=True,
        default="",
        db_index=True,
        help_text="TersuiteAgentRuntime internal session identifier.",
    )
    remote_conversation_id = models.CharField(
        max_length=255,
        blank=True,
        default="",
        db_index=True,
        help_text="OpenHands Agent Server remote conversation UUID.",
    )
    status = models.CharField(
        max_length=30,
        choices=AgentRunStatus.choices,
        default=AgentRunStatus.QUEUED,
        db_index=True,
        help_text="Execution status of this agent run attempt.",
    )
    model_name = models.CharField(
        max_length=150,
        blank=True,
        default="",
        help_text="LLM model identifier used for this run.",
    )
    prompt = models.TextField(
        help_text="Exact prompt and instruction sent to the agent.",
    )
    output = models.TextField(
        blank=True,
        default="",
        help_text="Final text output or response produced by the agent.",
    )
    token_usage = models.JSONField(
        default=dict,
        blank=True,
        help_text="Token consumption stats (prompt_tokens, completion_tokens, total).",
    )
    failure_category = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="Failure categorization if execution failed.",
    )
    error_details = models.JSONField(
        default=dict,
        blank=True,
        help_text="Structured traceback and failure diagnostics.",
    )
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when run started.",
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when run ended.",
    )

    class Meta:
        ordering = ["run_number"]
        verbose_name = "Agent Run"
        verbose_name_plural = "Agent Runs"
        constraints = [
            models.UniqueConstraint(
                fields=["step", "run_number"],
                name="unique_step_run_number",
            )
        ]

    def __str__(self) -> str:
        return f"Run #{self.run_number} for Step {self.step_id} [{self.status}]"


class Workspace(TimeStampedModel):
    """Represents the isolated workspace environment for a Generation."""

    generation = models.OneToOneField(
        Generation,
        on_delete=models.CASCADE,
        related_name="workspace",
        db_index=True,
        help_text="Generation this workspace belongs to.",
    )
    workspace_path = models.CharField(
        max_length=512,
        help_text="Isolated filesystem path or relative workspace identifier.",
    )
    storage_type = models.CharField(
        max_length=50,
        choices=WorkspaceStorageType.choices,
        default=WorkspaceStorageType.LOCAL,
        help_text="Isolation storage backend backing this workspace.",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this workspace is active and mounted.",
    )
    disk_usage_bytes = models.BigIntegerField(
        default=0,
        help_text="Calculated disk space consumption in bytes.",
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Workspace container IDs, mount points, and environment tags.",
    )

    class Meta:
        verbose_name = "Workspace"
        verbose_name_plural = "Workspaces"

    def __str__(self) -> str:
        return f"Workspace for Generation {self.generation_id} ({self.workspace_path})"


class Artifact(TimeStampedModel):
    """Represents a durable output file created during a Generation."""

    generation = models.ForeignKey(
        Generation,
        on_delete=models.CASCADE,
        related_name="artifacts",
        db_index=True,
        help_text="Generation that produced this artifact.",
    )
    agent_run = models.ForeignKey(
        AgentRun,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="artifacts",
        help_text="Agent run attempt that generated this artifact.",
    )
    name = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Human-readable filename of the artifact.",
    )
    file_path = models.CharField(
        max_length=512,
        help_text="Relative path inside the WordPress plugin structure.",
    )
    artifact_type = models.CharField(
        max_length=50,
        choices=ArtifactType.choices,
        default=ArtifactType.SOURCE_CODE,
        db_index=True,
        help_text="Category of the artifact.",
    )
    mime_type = models.CharField(
        max_length=100,
        default="text/plain",
        help_text="MIME content type of the artifact.",
    )
    size_bytes = models.BigIntegerField(
        default=0,
        help_text="File size in bytes.",
    )
    checksum_sha256 = models.CharField(
        max_length=64,
        blank=True,
        default="",
        help_text="SHA-256 cryptographic checksum of the file content.",
    )
    storage_backend = models.CharField(
        max_length=50,
        default="local_filesystem",
        help_text="Storage provider backend used to persist the file.",
    )
    storage_key = models.CharField(
        max_length=512,
        help_text="Lookup key or URI within the storage backend.",
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="File attributes, syntax status, lines of code, and audit tags.",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Artifact"
        verbose_name_plural = "Artifacts"
        indexes = [
            models.Index(fields=["generation", "artifact_type"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.artifact_type}) [{self.generation_id}]"
