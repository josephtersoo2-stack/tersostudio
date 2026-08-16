"""Serializers for staff-only Control Center API endpoints."""
from rest_framework import serializers

from apps.generations.models import (
    AgentRun,
    Artifact,
    Generation,
    GenerationStep,
    Workspace,
)


class ProjectSummarySerializer(serializers.Serializer):
    total = serializers.IntegerField()
    active = serializers.IntegerField()
    archived = serializers.IntegerField()


class GenerationSummarySerializer(serializers.Serializer):
    total = serializers.IntegerField()
    active = serializers.IntegerField()
    draft = serializers.IntegerField()
    specification = serializers.IntegerField()
    approved = serializers.IntegerField()
    planning = serializers.IntegerField()
    building = serializers.IntegerField()
    testing = serializers.IntegerField()
    review = serializers.IntegerField()
    packaging = serializers.IntegerField()
    completed = serializers.IntegerField()
    failed = serializers.IntegerField()
    cancelled = serializers.IntegerField()
    paused = serializers.IntegerField()
    retrying = serializers.IntegerField()


class AgentRunSummarySerializer(serializers.Serializer):
    total = serializers.IntegerField()
    queued = serializers.IntegerField()
    running = serializers.IntegerField()
    completed = serializers.IntegerField()
    failed = serializers.IntegerField()
    cancelled = serializers.IntegerField()
    timed_out = serializers.IntegerField()


class StepSummarySerializer(serializers.Serializer):
    total = serializers.IntegerField()
    pending = serializers.IntegerField()
    running = serializers.IntegerField()
    completed = serializers.IntegerField()
    failed = serializers.IntegerField()
    cancelled = serializers.IntegerField()
    skipped = serializers.IntegerField()


class ArtifactSummarySerializer(serializers.Serializer):
    total = serializers.IntegerField()
    source_code = serializers.IntegerField()
    configuration = serializers.IntegerField()
    test_report = serializers.IntegerField()
    documentation = serializers.IntegerField()
    zip_archive = serializers.IntegerField()
    security_report = serializers.IntegerField()
    other = serializers.IntegerField()


class RuntimeSummarySerializer(serializers.Serializer):
    default_backend = serializers.CharField()
    openhands_server_url = serializers.CharField()
    openrouter_configured = serializers.BooleanField()
    openhands_api_key_configured = serializers.BooleanField()


class ControlCenterSummarySerializer(serializers.Serializer):
    projects = ProjectSummarySerializer()
    generations = GenerationSummarySerializer()
    agent_runs = AgentRunSummarySerializer()
    steps = StepSummarySerializer()
    artifacts = ArtifactSummarySerializer()
    runtime = RuntimeSummarySerializer()


class ControlCenterGenerationListSerializer(serializers.ModelSerializer):
    """Staff-facing generation list item with aggregated counts and safe previews."""

    project_id = serializers.UUIDField(source="project.id", read_only=True)
    project_name = serializers.CharField(source="project.name", read_only=True)
    user_id = serializers.UUIDField(source="user.id", read_only=True)
    user_email = serializers.CharField(source="user.email", read_only=True)
    prompt_preview = serializers.SerializerMethodField()
    steps_count = serializers.IntegerField(read_only=True, default=0)
    runs_count = serializers.IntegerField(read_only=True, default=0)
    artifacts_count = serializers.IntegerField(read_only=True, default=0)
    workspace_id = serializers.SerializerMethodField()
    error_message_preview = serializers.SerializerMethodField()

    class Meta:
        model = Generation
        fields = [
            "id",
            "project_id",
            "project_name",
            "user_id",
            "user_email",
            "prompt_preview",
            "status",
            "current_step_number",
            "total_steps",
            "steps_count",
            "runs_count",
            "artifacts_count",
            "workspace_id",
            "failure_category",
            "error_message_preview",
            "created_at",
            "updated_at",
            "completed_at",
            "failed_at",
            "cancelled_at",
            "paused_at",
        ]
        read_only_fields = fields

    def get_prompt_preview(self, obj: Generation) -> str:
        prompt = obj.prompt or ""
        if len(prompt) > 140:
            return prompt[:137] + "..."
        return prompt

    def get_error_message_preview(self, obj: Generation) -> str:
        err = obj.error_message or ""
        if len(err) > 140:
            return err[:137] + "..."
        return err

    def get_workspace_id(self, obj: Generation):
        if hasattr(obj, "workspace") and obj.workspace:
            return str(obj.workspace.id)
        return None


class ControlCenterAgentRunListSerializer(serializers.ModelSerializer):
    """Staff-facing AgentRun list item with parent generation/step context and safe previews."""

    generation_id = serializers.UUIDField(source="step.generation.id", read_only=True)
    generation_status = serializers.CharField(source="step.generation.status", read_only=True)
    project_id = serializers.UUIDField(source="step.generation.project.id", read_only=True)
    project_name = serializers.CharField(source="step.generation.project.name", read_only=True)
    user_id = serializers.UUIDField(source="step.generation.user.id", read_only=True)
    user_email = serializers.CharField(source="step.generation.user.email", read_only=True)
    step_id = serializers.UUIDField(source="step.id", read_only=True)
    step_name = serializers.CharField(source="step.name", read_only=True)
    step_number = serializers.IntegerField(source="step.step_number", read_only=True)
    prompt_preview = serializers.SerializerMethodField()
    output_preview = serializers.SerializerMethodField()

    class Meta:
        model = AgentRun
        fields = [
            "id",
            "generation_id",
            "generation_status",
            "project_id",
            "project_name",
            "user_id",
            "user_email",
            "step_id",
            "step_name",
            "step_number",
            "run_number",
            "runtime_type",
            "status",
            "model_name",
            "session_id",
            "remote_conversation_id",
            "prompt_preview",
            "output_preview",
            "token_usage",
            "failure_category",
            "started_at",
            "completed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_prompt_preview(self, obj: AgentRun) -> str:
        prompt = obj.prompt or ""
        if len(prompt) > 140:
            return prompt[:137] + "..."
        return prompt

    def get_output_preview(self, obj: AgentRun) -> str:
        output = obj.output or ""
        if len(output) > 180:
            return output[:177] + "..."
        return output


# ==============================================================================
# CC-02 Detail & Operational Serializers
# ==============================================================================


class ControlCenterWorkspaceSerializer(serializers.ModelSerializer):
    """Full operational view of a generation workspace."""

    class Meta:
        model = Workspace
        fields = [
            "id",
            "workspace_path",
            "storage_type",
            "is_active",
            "disk_usage_bytes",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class ControlCenterArtifactSerializer(serializers.ModelSerializer):
    """Operational artifact view with project and generation context."""

    generation_id = serializers.UUIDField(source="generation.id", read_only=True)
    project_name = serializers.CharField(source="generation.project.name", read_only=True)
    agent_run_id = serializers.UUIDField(source="agent_run.id", read_only=True, allow_null=True)

    class Meta:
        model = Artifact
        fields = [
            "id",
            "generation_id",
            "project_name",
            "agent_run_id",
            "name",
            "file_path",
            "artifact_type",
            "mime_type",
            "size_bytes",
            "checksum_sha256",
            "storage_backend",
            "storage_key",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class ControlCenterNestedAgentRunSerializer(serializers.ModelSerializer):
    """Lightweight nested run item under a step."""

    class Meta:
        model = AgentRun
        fields = [
            "id",
            "run_number",
            "runtime_type",
            "status",
            "model_name",
            "session_id",
            "remote_conversation_id",
            "failure_category",
            "started_at",
            "completed_at",
            "created_at",
        ]
        read_only_fields = fields


class ControlCenterStepDetailSerializer(serializers.ModelSerializer):
    """Detailed step view with nested run attempts."""

    runs = ControlCenterNestedAgentRunSerializer(many=True, read_only=True)

    class Meta:
        model = GenerationStep
        fields = [
            "id",
            "step_number",
            "name",
            "agent_role",
            "status",
            "input_payload",
            "output_payload",
            "error_message",
            "started_at",
            "completed_at",
            "created_at",
            "updated_at",
            "runs",
        ]
        read_only_fields = fields


class ControlCenterGenerationDetailSerializer(serializers.ModelSerializer):
    """Full operational view of a generation lifecycle, steps, workspace, and artifacts."""

    project = serializers.SerializerMethodField()
    user = serializers.SerializerMethodField()
    timestamps = serializers.SerializerMethodField()
    steps = ControlCenterStepDetailSerializer(many=True, read_only=True)
    workspace = serializers.SerializerMethodField()
    artifacts = ControlCenterArtifactSerializer(many=True, read_only=True)

    class Meta:
        model = Generation
        fields = [
            "id",
            "project",
            "user",
            "prompt",
            "status",
            "current_step_number",
            "total_steps",
            "metadata",
            "failure_category",
            "error_message",
            "timestamps",
            "steps",
            "workspace",
            "artifacts",
        ]
        read_only_fields = fields

    def get_project(self, obj: Generation) -> dict:
        return {
            "id": str(obj.project.id),
            "name": obj.project.name,
        }

    def get_user(self, obj: Generation) -> dict:
        return {
            "id": str(obj.user.id),
            "email": obj.user.email,
        }

    def get_timestamps(self, obj: Generation) -> dict:
        return {
            "created_at": obj.created_at.isoformat() if obj.created_at else None,
            "updated_at": obj.updated_at.isoformat() if obj.updated_at else None,
            "completed_at": obj.completed_at.isoformat() if obj.completed_at else None,
            "failed_at": obj.failed_at.isoformat() if obj.failed_at else None,
            "cancelled_at": obj.cancelled_at.isoformat() if obj.cancelled_at else None,
            "paused_at": obj.paused_at.isoformat() if obj.paused_at else None,
        }

    def get_workspace(self, obj: Generation):
        if hasattr(obj, "workspace") and obj.workspace:
            return ControlCenterWorkspaceSerializer(obj.workspace).data
        return None


class ControlCenterAgentRunDetailSerializer(serializers.ModelSerializer):
    """Full diagnostics view of a specific AgentRun execution attempt."""

    generation = serializers.SerializerMethodField()
    step = serializers.SerializerMethodField()

    class Meta:
        model = AgentRun
        fields = [
            "id",
            "generation",
            "step",
            "run_number",
            "runtime_type",
            "status",
            "model_name",
            "session_id",
            "remote_conversation_id",
            "prompt",
            "output",
            "token_usage",
            "failure_category",
            "error_details",
            "started_at",
            "completed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_generation(self, obj: AgentRun) -> dict:
        gen = obj.step.generation
        return {
            "id": str(gen.id),
            "status": gen.status,
            "project_name": gen.project.name,
            "user_email": gen.user.email,
        }

    def get_step(self, obj: AgentRun) -> dict:
        step = obj.step
        return {
            "id": str(step.id),
            "name": step.name,
            "step_number": step.step_number,
        }
