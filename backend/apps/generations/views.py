"""REST API ViewSets for the Generations domain."""
from django.http import Http404, HttpResponse
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.organizations.context import OrganizationContextMixin
from .enums import GenerationStatus
from .exceptions import InvalidStateTransitionError
from .models import AgentRun, Artifact, Generation, GenerationStep, Workspace
from .permissions import (
    IsArtifactOwner,
    IsGenerationOwner,
    IsRunOwner,
    IsStepOwner,
    IsWorkspaceOwner,
)
from .serializers import (
    AgentRunSerializer,
    ArtifactSerializer,
    GenerationCreateSerializer,
    GenerationDetailSerializer,
    GenerationListSerializer,
    GenerationStepSerializer,
    GenerationUpdateSerializer,
    StateTransitionRequestSerializer,
    WorkspaceSerializer,
)
from .services.state_machine import GenerationStateMachine
from .storage import get_artifact_storage


class GenerationViewSet(
    OrganizationContextMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """ViewSet for managing Generations and their state transitions.

    Destructive DELETE is intentionally not supported to preserve durable generation history.
    """

    permission_classes = [permissions.IsAuthenticated, IsGenerationOwner]
    lookup_field = "id"
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False) or not self.request.user.is_authenticated:
            return Generation.objects.none()

        org = self.get_organization()
        qs = Generation.objects.select_related("project", "organization", "created_by").filter(organization=org)

        project_id = self.request.query_params.get("project_id")
        if project_id:
            qs = qs.filter(project_id=project_id)

        status_param = self.request.query_params.get("status")
        if status_param:
            qs = qs.filter(status=status_param)

        return qs.order_by("-created_at")

    def get_serializer_class(self):
        if self.action == "create":
            return GenerationCreateSerializer
        if self.action in ("update", "partial_update"):
            return GenerationUpdateSerializer
        if self.action == "retrieve":
            return GenerationDetailSerializer
        return GenerationListSerializer

    @action(detail=True, methods=["post"], url_path="transition")
    def transition_state(self, request, id=None):
        """Perform a validated state transition on the generation."""
        generation = self.get_object()
        serializer = StateTransitionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        try:
            updated_gen = GenerationStateMachine.transition(
                generation=generation,
                target_status=data["target_status"],
                reason=data.get("reason", ""),
                error_message=data.get("error_message", ""),
                failure_category=data.get("failure_category", ""),
                metadata_update=data.get("metadata"),
            )
            return Response(
                GenerationDetailSerializer(updated_gen, context={"request": request}).data,
                status=status.HTTP_200_OK,
            )
        except InvalidStateTransitionError as exc:
            return Response(
                {
                    "error": "invalid_state_transition",
                    "detail": str(exc),
                    "current_status": exc.current_status,
                    "target_status": exc.target_status,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=["post"], url_path="pause")
    def pause(self, request, id=None):
        """Pause an ongoing generation."""
        generation = self.get_object()
        reason = request.data.get("reason", "Paused by user.")
        try:
            updated_gen = GenerationStateMachine.transition(
                generation=generation,
                target_status=GenerationStatus.PAUSED,
                reason=reason,
            )
            return Response(GenerationDetailSerializer(updated_gen, context={"request": request}).data)
        except InvalidStateTransitionError as exc:
            return Response(
                {"error": "invalid_state_transition", "detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, id=None):
        """Cancel a generation."""
        generation = self.get_object()
        reason = request.data.get("reason", "Cancelled by user.")
        try:
            updated_gen = GenerationStateMachine.transition(
                generation=generation,
                target_status=GenerationStatus.CANCELLED,
                reason=reason,
            )
            return Response(GenerationDetailSerializer(updated_gen, context={"request": request}).data)
        except InvalidStateTransitionError as exc:
            return Response(
                {"error": "invalid_state_transition", "detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=["post"], url_path="retry")
    def retry(self, request, id=None):
        """Retry a failed generation."""
        generation = self.get_object()
        reason = request.data.get("reason", "Retrying failed generation.")
        try:
            updated_gen = GenerationStateMachine.transition(
                generation=generation,
                target_status=GenerationStatus.RETRYING,
                reason=reason,
            )
            return Response(GenerationDetailSerializer(updated_gen, context={"request": request}).data)
        except InvalidStateTransitionError as exc:
            return Response(
                {"error": "invalid_state_transition", "detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=["get"], url_path="workspace")
    def get_workspace(self, request, id=None):
        """Retrieve workspace for the generation."""
        generation = self.get_object()
        try:
            workspace = generation.workspace
            return Response(WorkspaceSerializer(workspace).data)
        except Workspace.DoesNotExist:
            raise Http404("Workspace not provisioned for this generation.")

    @action(detail=True, methods=["get"], url_path="artifacts")
    def list_artifacts(self, request, id=None):
        """List artifacts produced by this generation."""
        generation = self.get_object()
        artifacts = generation.artifacts.all()
        return Response(ArtifactSerializer(artifacts, many=True).data)

    @action(detail=True, methods=["get"], url_path="steps")
    def list_steps(self, request, id=None):
        """List steps belonging to this generation."""
        generation = self.get_object()
        steps = generation.steps.all().prefetch_related("runs")
        return Response(GenerationStepSerializer(steps, many=True).data)


class GenerationStepViewSet(OrganizationContextMixin, viewsets.ReadOnlyModelViewSet):
    """ReadOnly ViewSet for inspecting GenerationSteps.

    Mutations are disallowed through the public API; steps are managed internally by workflows.
    """

    serializer_class = GenerationStepSerializer
    permission_classes = [permissions.IsAuthenticated, IsStepOwner]
    lookup_field = "id"

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False) or not self.request.user.is_authenticated:
            return GenerationStep.objects.none()

        org = self.get_organization()
        qs = GenerationStep.objects.filter(generation__organization=org).prefetch_related("runs")

        generation_id = self.request.query_params.get("generation_id")
        if generation_id:
            qs = qs.filter(generation_id=generation_id)

        return qs.order_by("step_number")


class AgentRunViewSet(OrganizationContextMixin, viewsets.ReadOnlyModelViewSet):
    """ReadOnly ViewSet for inspecting AgentRuns.

    Execution attempts are recorded internally by the agent execution engine.
    """

    serializer_class = AgentRunSerializer
    permission_classes = [permissions.IsAuthenticated, IsRunOwner]
    lookup_field = "id"

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False) or not self.request.user.is_authenticated:
            return AgentRun.objects.none()

        org = self.get_organization()
        qs = AgentRun.objects.filter(step__generation__organization=org)

        step_id = self.request.query_params.get("step_id")
        if step_id:
            qs = qs.filter(step_id=step_id)

        session_id = self.request.query_params.get("session_id")
        if session_id:
            qs = qs.filter(session_id=session_id)

        return qs.order_by("run_number")


class WorkspaceViewSet(OrganizationContextMixin, viewsets.ReadOnlyModelViewSet):
    """ReadOnly ViewSet for inspecting Workspace instances."""

    serializer_class = WorkspaceSerializer
    permission_classes = [permissions.IsAuthenticated, IsWorkspaceOwner]
    lookup_field = "id"

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False) or not self.request.user.is_authenticated:
            return Workspace.objects.none()

        org = self.get_organization()
        return Workspace.objects.filter(generation__organization=org)


class ArtifactViewSet(OrganizationContextMixin, viewsets.ReadOnlyModelViewSet):
    """ReadOnly ViewSet for inspecting and downloading generated artifacts.

    Arbitrary creation/modification is restricted; artifacts are generated by internal pipelines.
    """

    serializer_class = ArtifactSerializer
    permission_classes = [permissions.IsAuthenticated, IsArtifactOwner]
    lookup_field = "id"

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False) or not self.request.user.is_authenticated:
            return Artifact.objects.none()

        org = self.get_organization()
        qs = Artifact.objects.filter(generation__organization=org)

        generation_id = self.request.query_params.get("generation_id")
        if generation_id:
            qs = qs.filter(generation_id=generation_id)

        artifact_type = self.request.query_params.get("artifact_type")
        if artifact_type:
            qs = qs.filter(artifact_type=artifact_type)

        return qs.order_by("-created_at")

    @action(detail=True, methods=["get"], url_path="download")
    def download(self, request, id=None):
        """Download artifact content bytes."""
        artifact = self.get_object()
        storage = get_artifact_storage()
        try:
            content_bytes = storage.read_artifact(artifact.storage_key)
            response = HttpResponse(content_bytes, content_type=artifact.mime_type)
            response["Content-Disposition"] = f'attachment; filename="{artifact.name}"'
            response["Content-Length"] = str(len(content_bytes))
            return response
        except Exception as exc:
            return Response(
                {"error": "artifact_read_failed", "detail": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
