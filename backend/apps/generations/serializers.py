"""Serializers for the Generations domain."""
from rest_framework import serializers

from apps.projects.models import Project
from .enums import GenerationStatus, MilestoneStatus
from .models import (
    AgentRun,
    Artifact,
    Generation,
    GenerationMilestone,
    GenerationStateTransition,
    GenerationStep,
    Workspace,
)


class ArtifactSerializer(serializers.ModelSerializer):
    """Serializer for Artifact metadata and attributes (Read-Only)."""

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
        read_only_fields = fields


class WorkspaceSerializer(serializers.ModelSerializer):
    """Serializer for Workspace inspection (Read-Only)."""

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
        read_only_fields = fields


class AgentRunSerializer(serializers.ModelSerializer):
    """Serializer for AgentRun execution attempts (Read-Only)."""

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
        read_only_fields = fields


class GenerationStepSerializer(serializers.ModelSerializer):
    """Serializer for GenerationStep work units with nested run attempts (Read-Only)."""

    runs = AgentRunSerializer(many=True, read_only=True)
    runs_count = serializers.SerializerMethodField()

    class Meta:
        model = GenerationStep
        fields = [
            "id",
            "generation",
            "milestone",
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
        read_only_fields = fields

    def get_runs_count(self, obj) -> int:
        return obj.runs.count()


class GenerationMilestoneSerializer(serializers.ModelSerializer):
    """Serializer for GenerationMilestone groupings (Read-Only)."""

    steps_count = serializers.SerializerMethodField()

    class Meta:
        model = GenerationMilestone
        fields = [
            "id",
            "generation",
            "sequence",
            "name",
            "status",
            "metadata",
            "started_at",
            "completed_at",
            "steps_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_steps_count(self, obj) -> int:
        return obj.steps.count()


class GenerationStateTransitionSerializer(serializers.ModelSerializer):
    """Serializer for immutable GenerationStateTransition audit entries (Read-Only)."""

    class Meta:
        model = GenerationStateTransition
        fields = [
            "id",
            "generation",
            "sequence",
            "from_status",
            "to_status",
            "command_id",
            "actor",
            "reason",
            "metadata",
            "created_at",
        ]
        read_only_fields = fields


class GenerationListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing generations."""

    organization_id = serializers.UUIDField(source="organization.id", read_only=True)
    project_name = serializers.CharField(source="project.name", read_only=True)
    created_by_id = serializers.UUIDField(source="created_by.id", read_only=True)
    updated_by_id = serializers.UUIDField(source="updated_by.id", read_only=True)
    user = serializers.UUIDField(source="created_by.id", read_only=True)
    steps_count = serializers.SerializerMethodField()
    artifacts_count = serializers.SerializerMethodField()
    milestones_count = serializers.SerializerMethodField()

    class Meta:
        model = Generation
        fields = [
            "id",
            "organization_id",
            "project",
            "project_name",
            "user",
            "created_by_id",
            "updated_by_id",
            "prompt",
            "status",
            "state_version",
            "current_step_number",
            "total_steps",
            "steps_count",
            "artifacts_count",
            "milestones_count",
            "failure_category",
            "error_message",
            "status_changed_at",
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

    def get_milestones_count(self, obj) -> int:
        return obj.milestones.count()


class GenerationDetailSerializer(serializers.ModelSerializer):
    """Comprehensive serializer for Generation details with nested children."""

    organization_id = serializers.UUIDField(source="organization.id", read_only=True)
    project_name = serializers.CharField(source="project.name", read_only=True)
    created_by_id = serializers.UUIDField(source="created_by.id", read_only=True)
    updated_by_id = serializers.UUIDField(source="updated_by.id", read_only=True)
    user = serializers.UUIDField(source="created_by.id", read_only=True)
    milestones = GenerationMilestoneSerializer(many=True, read_only=True)
    steps = GenerationStepSerializer(many=True, read_only=True)
    workspace = WorkspaceSerializer(read_only=True)
    artifacts = ArtifactSerializer(many=True, read_only=True)
    state_transitions = GenerationStateTransitionSerializer(many=True, read_only=True)

    class Meta:
        model = Generation
        fields = [
            "id",
            "organization_id",
            "project",
            "project_name",
            "user",
            "created_by_id",
            "updated_by_id",
            "prompt",
            "status",
            "state_version",
            "next_transition_sequence",
            "status_changed_at",
            "resume_status",
            "cancel_requested_at",
            "timed_out_at",
            "current_step_number",
            "total_steps",
            "metadata",
            "error_message",
            "failure_category",
            "milestones",
            "steps",
            "workspace",
            "artifacts",
            "state_transitions",
            "completed_at",
            "cancelled_at",
            "failed_at",
            "paused_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


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
        """Ensure project exists and belongs to the active tenant organization."""
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError("Authentication required.")
        org = getattr(request, "tersuite_organization", None)
        try:
            if org:
                project = Project.objects.get(id=value, organization=org)
            else:
                project = Project.objects.get(id=value)
        except Project.DoesNotExist:
            raise serializers.ValidationError("Project not found or access denied.")
        return project

    def create(self, validated_data):
        project = validated_data.pop("project_id")
        request = self.context.get("request")
        actor = request.user if request and request.user.is_authenticated else None
        org = project.organization

        generation = Generation.objects.create(
            project=project,
            organization=org,
            created_by=actor,
            updated_by=actor,
            **validated_data,
        )

        # Provision initial workspace metadata (metadata initialization only)
        Workspace.objects.create(
            generation=generation,
            workspace_path=f"workspaces/{generation.id}",
            metadata={"initial_setup": True},
        )

        return generation


class GenerationUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating allowed Generation fields (metadata only)."""

    class Meta:
        model = Generation
        fields = ["metadata"]


class StateTransitionRequestSerializer(serializers.Serializer):
    """Serializer for requesting state transitions."""

    target_status = serializers.ChoiceField(choices=GenerationStatus.choices)
    reason = serializers.CharField(required=False, allow_blank=True, default="")
    error_message = serializers.CharField(required=False, allow_blank=True, default="")
    failure_category = serializers.CharField(required=False, allow_blank=True, default="")
    metadata = serializers.DictField(required=False, default=dict)
