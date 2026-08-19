"""Django admin registration for Generation, Milestone, StateTransition, GenerationStep, AgentRun, Workspace, and Artifact models."""
from django.contrib import admin
from .models import (
    AgentRun,
    Artifact,
    Generation,
    GenerationMilestone,
    GenerationStateTransition,
    GenerationStep,
    Workspace,
)


class GenerationStepInline(admin.TabularInline):
    """Inline view for GenerationStep items inside Generation."""

    model = GenerationStep
    extra = 0
    readonly_fields = ("id", "created_at", "updated_at")
    fields = ("step_number", "milestone", "name", "agent_role", "status", "started_at", "completed_at")
    show_change_link = True


class GenerationMilestoneInline(admin.TabularInline):
    """Inline view for GenerationMilestone items inside Generation."""

    model = GenerationMilestone
    extra = 0
    readonly_fields = ("id", "created_at", "updated_at")
    fields = ("sequence", "name", "status", "started_at", "completed_at")
    show_change_link = True


class ArtifactInline(admin.TabularInline):
    """Inline view for Artifact items inside Generation."""

    model = Artifact
    extra = 0
    readonly_fields = ("id", "checksum_sha256", "size_bytes", "created_at", "updated_at")
    fields = ("name", "artifact_type", "file_path", "size_bytes", "storage_backend")
    show_change_link = True


class AgentRunInline(admin.TabularInline):
    """Inline view for AgentRun items inside GenerationStep."""

    model = AgentRun
    extra = 0
    readonly_fields = ("id", "created_at", "updated_at")
    fields = ("run_number", "runtime_type", "status", "model_name", "started_at", "completed_at")
    show_change_link = True


@admin.register(Generation)
class GenerationAdmin(admin.ModelAdmin):
    """Admin configuration for Generation."""

    list_display = (
        "id",
        "project",
        "organization",
        "created_by",
        "status",
        "state_version",
        "current_step_number",
        "total_steps",
        "created_at",
    )
    list_filter = ("status", "created_at")
    search_fields = ("id", "prompt", "project__name", "organization__name", "created_by__email", "error_message")
    readonly_fields = (
        "id",
        "state_version",
        "next_transition_sequence",
        "status_changed_at",
        "created_by",
        "updated_by",
        "created_at",
        "updated_at",
        "completed_at",
        "failed_at",
        "cancelled_at",
        "paused_at",
    )
    inlines = [GenerationMilestoneInline, GenerationStepInline, ArtifactInline]


@admin.register(GenerationMilestone)
class GenerationMilestoneAdmin(admin.ModelAdmin):
    """Admin configuration for GenerationMilestone."""

    list_display = ("id", "generation", "sequence", "name", "status", "started_at", "completed_at")
    list_filter = ("status", "created_at")
    search_fields = ("name", "generation__id")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(GenerationStateTransition)
class GenerationStateTransitionAdmin(admin.ModelAdmin):
    """Admin configuration for GenerationStateTransition."""

    list_display = ("id", "generation", "sequence", "from_status", "to_status", "command_id", "actor", "created_at")
    list_filter = ("from_status", "to_status", "created_at")
    search_fields = ("generation__id", "reason", "command_id")
    readonly_fields = ("id", "generation", "sequence", "from_status", "to_status", "command_id", "actor", "reason", "metadata", "created_at", "updated_at")


@admin.register(GenerationStep)
class GenerationStepAdmin(admin.ModelAdmin):
    """Admin configuration for GenerationStep."""

    list_display = (
        "step_number",
        "name",
        "generation",
        "milestone",
        "agent_role",
        "status",
        "started_at",
        "completed_at",
    )
    list_filter = ("status", "agent_role", "created_at")
    search_fields = ("name", "generation__id", "error_message")
    readonly_fields = ("id", "created_at", "updated_at")
    inlines = [AgentRunInline]


@admin.register(AgentRun)
class AgentRunAdmin(admin.ModelAdmin):
    """Admin configuration for AgentRun."""

    list_display = (
        "id",
        "step",
        "run_number",
        "runtime_type",
        "status",
        "model_name",
        "started_at",
        "completed_at",
    )
    list_filter = ("status", "runtime_type", "model_name", "failure_category")
    search_fields = ("id", "session_id", "remote_conversation_id", "prompt", "output")
    readonly_fields = (
        "id",
        "session_id",
        "remote_conversation_id",
        "token_usage",
        "error_details",
        "created_at",
        "updated_at",
    )


@admin.register(Workspace)
class WorkspaceAdmin(admin.ModelAdmin):
    """Admin configuration for Workspace."""

    list_display = (
        "id",
        "generation",
        "workspace_path",
        "storage_type",
        "is_active",
        "disk_usage_bytes",
        "created_at",
    )
    list_filter = ("storage_type", "is_active", "created_at")
    search_fields = ("id", "generation__id", "workspace_path")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(Artifact)
class ArtifactAdmin(admin.ModelAdmin):
    """Admin configuration for Artifact."""

    list_display = (
        "name",
        "generation",
        "agent_run",
        "artifact_type",
        "file_path",
        "size_bytes",
        "checksum_sha256",
        "created_at",
    )
    list_filter = ("artifact_type", "storage_backend", "created_at")
    search_fields = ("name", "file_path", "checksum_sha256", "generation__id")
    readonly_fields = ("id", "checksum_sha256", "size_bytes", "created_at", "updated_at")
