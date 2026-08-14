"""Serializers for the Generations domain."""
from rest_framework import serializers

from apps.projects.models import Project
from .enums import GenerationStatus
from .models import AgentRun, Artifact, Generation, GenerationStep, Workspace


class ArtifactSerializer(serializers.ModelSerializer):
    """Serializer for Artifact metadata and attributes."""

    class Meta:
        model = Artifact
        fields = [
            "id",
            "generation",
            "agent_run",
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
        read_only_fields = [
            "id",
            "size_bytes",
            "checksum_sha256",
            "storage_backend",
            "storage_key",
            "created_at",
            "updated_at",
        ]


class WorkspaceSerializer(serializers.ModelSerializer):
    """Serializer for Workspace inspection."""

    class Meta:
        model = Workspace
        fields = [
            "id",
            "generation",
            "workspace_path",
            "storage_type",
            "is_active",
            "disk_usage_bytes",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]


class AgentRunSerializer(serializers.ModelSerializer):
    """Serializer for AgentRun execution attempts."""

    class Meta:
        model = AgentRun
        fields = [
            "id",
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
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]

    def create(self, validated_data):
        """Auto-increment run_number for step if not specified."""
        step = validated_data.get("step")
        if step and "run_number" not in validated_data:
            last_run = step.runs.order_by("-run_number").first()
            validated_data["run_number"] = (last_run.run_number + 1) if last_run else 1
        return super().create(validated_data)


class GenerationStepSerializer(serializers.ModelSerializer):
    """Serializer for GenerationStep work units with nested run attempts."""

    runs = AgentRunSerializer(many=True, read_only=True)
    runs_count = serializers.SerializerMethodField()

    class Meta:
        model = GenerationStep
        fields = [
            "id",
            "generation",
            "step_number",
            "name",
            "agent_role",
            "status",
            "input_payload",
            "output_payload",
            "error_message",
            "started_at",
            "completed_at",
            "runs",
            "runs_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "runs",
            "runs_count",
            "created_at",
            "updated_at",
        ]

    def get_runs_count(self, obj) -> int:
        return obj.runs.count()


class GenerationListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing generations."""

    project_name = serializers.CharField(source="project.name", read_only=True)
    steps_count = serializers.SerializerMethodField()
    artifacts_count = serializers.SerializerMethodField()

    class Meta:
        model = Generation
        fields = [
            "id",
            "project",
            "project_name",
            "user",
            "prompt",
            "status",
            "current_step_number",
            "total_steps",
            "steps_count",
            "artifacts_count",
            "failure_category",
            "error_message",
            "created_at",
            "updated_at",
            "completed_at",
            "failed_at",
            "cancelled_at",
            "paused_at",
        ]
        read_only_fields = fields

    def get_steps_count(self, obj) -> int:
        return obj.steps.count()

    def get_artifacts_count(self, obj) -> int:
        return obj.artifacts.count()


class GenerationDetailSerializer(serializers.ModelSerializer):
    """Comprehensive serializer for Generation details with nested children."""

    project_name = serializers.CharField(source="project.name", read_only=True)
    steps = GenerationStepSerializer(many=True, read_only=True)
    workspace = WorkspaceSerializer(read_only=True)
    artifacts = ArtifactSerializer(many=True, read_only=True)

    class Meta:
        model = Generation
        fields = [
            "id",
            "project",
            "project_name",
            "user",
            "prompt",
            "status",
            "current_step_number",
            "total_steps",
            "metadata",
            "error_message",
            "failure_category",
            "steps",
            "workspace",
            "artifacts",
            "completed_at",
            "cancelled_at",
            "failed_at",
            "paused_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "user",
            "status",
            "steps",
            "workspace",
            "artifacts",
            "completed_at",
            "cancelled_at",
            "failed_at",
            "paused_at",
            "created_at",
            "updated_at",
        ]


class GenerationCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a new Generation under a project."""

    project_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = Generation
        fields = [
            "id",
            "project_id",
            "prompt",
            "metadata",
            "status",
            "created_at",
        ]
        read_only_fields = ["id", "status", "created_at"]

    def validate_project_id(self, value):
        """Ensure project exists and belongs to the requesting user."""
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError("Authentication required.")
        try:
            project = Project.objects.get(id=value, user=request.user)
        except Project.DoesNotExist:
            raise serializers.ValidationError("Project not found or access denied.")
        return project

    def create(self, validated_data):
        project = validated_data.pop("project_id")
        user = self.context["request"].user
        generation = Generation.objects.create(
            project=project,
            user=user,
            **validated_data,
        )

        # Automatically provision initial workspace record
        Workspace.objects.create(
            generation=generation,
            workspace_path=f"workspaces/{generation.id}",
            metadata={"initial_setup": True},
        )

        return generation


class StateTransitionRequestSerializer(serializers.Serializer):
    """Serializer for requesting state transitions."""

    target_status = serializers.ChoiceField(choices=GenerationStatus.choices)
    reason = serializers.CharField(required=False, allow_blank=True, default="")
    error_message = serializers.CharField(required=False, allow_blank=True, default="")
    failure_category = serializers.CharField(required=False, allow_blank=True, default="")
    metadata = serializers.DictField(required=False, default=dict)
