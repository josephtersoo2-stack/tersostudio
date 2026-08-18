"""Serializers for staff-only Control Center API endpoints."""
from rest_framework import serializers

from apps.generations.models import (
    AgentRun,
    Artifact,
    Generation,
    GenerationStep,
    Workspace,
)
from apps.projects.models import Project


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


class KnowledgeSummarySerializer(serializers.Serializer):
    total = serializers.IntegerField()
    categories = serializers.DictField(child=serializers.IntegerField())


class ControlCenterSummarySerializer(serializers.Serializer):
    projects = ProjectSummarySerializer()
    generations = GenerationSummarySerializer()
    agent_runs = AgentRunSummarySerializer()
    steps = StepSummarySerializer()
    artifacts = ArtifactSummarySerializer()
    runtime = RuntimeSummarySerializer()
    knowledge_units = KnowledgeSummarySerializer(required=False)


class ControlCenterGenerationListSerializer(serializers.ModelSerializer):
    """Staff-facing generation list item with aggregated counts and safe previews."""

    project_id = serializers.UUIDField(source="project.id", read_only=True)
    project_name = serializers.CharField(source="project.name", read_only=True)
    user_id = serializers.UUIDField(source="created_by.id", read_only=True)
    user_email = serializers.CharField(source="created_by.email", read_only=True)
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
        if not obj.prompt:
            return ""
        return obj.prompt[:137] + "..." if len(obj.prompt) > 140 else obj.prompt

    def get_error_message_preview(self, obj: Generation) -> str:
        if not obj.error_message:
            return ""
        return obj.error_message[:137] + "..." if len(obj.error_message) > 140 else obj.error_message

    def get_workspace_id(self, obj: Generation):
        if hasattr(obj, "workspace") and obj.workspace:
            return str(obj.workspace.id)
        return None


class ControlCenterAgentRunListSerializer(serializers.ModelSerializer):
    """Staff-facing agent run list item with generation and step context."""

    step_id = serializers.UUIDField(source="step.id", read_only=True)
    step_number = serializers.IntegerField(source="step.step_number", read_only=True)
    step_name = serializers.CharField(source="step.name", read_only=True)
    agent_role = serializers.CharField(source="step.agent_role", read_only=True)
    generation_id = serializers.UUIDField(source="step.generation.id", read_only=True)
    project_name = serializers.CharField(source="step.generation.project.name", read_only=True)
    user_email = serializers.CharField(source="step.generation.created_by.email", read_only=True)
    prompt_preview = serializers.SerializerMethodField()
    output_preview = serializers.SerializerMethodField()


    class Meta:
        model = AgentRun
        fields = [
            "id",
            "step_id",
            "step_number",
            "step_name",
            "agent_role",
            "generation_id",
            "project_name",
            "user_email",
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
        if not obj.prompt:
            return ""
        return obj.prompt[:137] + "..." if len(obj.prompt) > 140 else obj.prompt

    def get_output_preview(self, obj: AgentRun) -> str:
        if not obj.output:
            return ""
        return obj.output[:137] + "..." if len(obj.output) > 140 else obj.output


class ControlCenterUserSummarySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    email = serializers.CharField()


class ControlCenterProjectSummarySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()


class ControlCenterNestedAgentRunSerializer(serializers.ModelSerializer):
    """Compact serializer for AgentRun nested within GenerationStep."""

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


class ControlCenterNestedStepSerializer(serializers.ModelSerializer):
    """Step serializer nested inside Generation Detail with runs."""

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


class ControlCenterWorkspaceSerializer(serializers.ModelSerializer):
    """Workspace serializer for Generation Detail."""

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
    """Artifact serializer with download metadata."""

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


class ControlCenterStepDetailSerializer(serializers.ModelSerializer):
    """Full detail of a specific GenerationStep."""

    generation_id = serializers.UUIDField(source="generation.id", read_only=True)
    project_name = serializers.CharField(source="generation.project.name", read_only=True)
    runs = ControlCenterNestedAgentRunSerializer(many=True, read_only=True)

    class Meta:
        model = GenerationStep
        fields = [
            "id",
            "generation_id",
            "project_name",
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
    """Full operational view of a Generation including steps, runs, workspace, and artifacts."""

    project = ControlCenterProjectSummarySerializer(read_only=True)
    user = ControlCenterUserSummarySerializer(source="created_by", read_only=True)
    steps = ControlCenterNestedStepSerializer(many=True, read_only=True)
    workspace = serializers.SerializerMethodField()
    artifacts = ControlCenterArtifactSerializer(many=True, read_only=True)
    timestamps = serializers.SerializerMethodField()

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

    def get_workspace(self, obj: Generation):
        if hasattr(obj, "workspace") and obj.workspace:
            return ControlCenterWorkspaceSerializer(obj.workspace).data
        return None

    def get_timestamps(self, obj: Generation) -> dict:
        return {
            "created_at": obj.created_at,
            "updated_at": obj.updated_at,
            "completed_at": obj.completed_at,
            "failed_at": obj.failed_at,
            "cancelled_at": obj.cancelled_at,
            "paused_at": obj.paused_at,
        }


class ControlCenterAgentRunDetailSerializer(serializers.ModelSerializer):
    """Full operational and diagnostic detail of a specific AgentRun attempt."""

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
            "session_id",
            "remote_conversation_id",
            "status",
            "model_name",
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
        user_email = gen.created_by.email if gen.created_by else ""
        return {
            "id": str(gen.id),
            "status": gen.status,
            "project_name": gen.project.name,
            "user_email": user_email,
        }

    def get_step(self, obj: AgentRun) -> dict:
        step = obj.step
        return {
            "id": str(step.id),
            "name": step.name,
            "step_number": step.step_number,
        }


class ControlCenterProjectListSerializer(serializers.ModelSerializer):
    """Staff-facing project list item with owner information and generation metrics."""

    user = ControlCenterUserSummarySerializer(source="created_by", read_only=True)
    plugin_slug = serializers.SerializerMethodField()
    wordpress_version = serializers.SerializerMethodField()
    php_version = serializers.SerializerMethodField()
    generations_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Project
        fields = [
            "id",
            "name",
            "slug",
            "plugin_slug",
            "user",
            "description",
            "wordpress_version",
            "php_version",
            "metadata",
            "generations_count",
            "is_archived",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_plugin_slug(self, obj: Project) -> str:
        if hasattr(obj, "product") and obj.product and hasattr(obj.product, "plugin_target"):
            return obj.product.plugin_target.plugin_slug
        return ""

    def get_wordpress_version(self, obj: Project) -> str:
        if hasattr(obj, "product") and obj.product:
            return obj.product.wordpress_version
        return "6.7"

    def get_php_version(self, obj: Project) -> str:
        if hasattr(obj, "product") and obj.product:
            return obj.product.php_version
        return "8.2"


class KnowledgeUnitListSerializer(serializers.Serializer):
    """List serialization for Knowledge Base units."""

    id = serializers.CharField()
    title = serializers.CharField()
    category = serializers.CharField()
    domain = serializers.CharField()
    description = serializers.CharField()
    rules_count = serializers.IntegerField()
    anti_patterns_count = serializers.IntegerField()
    patterns_count = serializers.IntegerField()
    compatibility = serializers.DictField()
    confidence = serializers.FloatField()


class KnowledgeUnitDetailSerializer(serializers.Serializer):
    """Full detail serialization for a specific Knowledge Unit."""

    id = serializers.CharField()
    title = serializers.CharField()
    category = serializers.CharField()
    domain = serializers.CharField()
    description = serializers.CharField()
    rules = serializers.ListField(child=serializers.CharField())
    patterns = serializers.ListField()
    anti_patterns = serializers.ListField(child=serializers.CharField())
    compatibility = serializers.DictField()
    confidence = serializers.FloatField()
