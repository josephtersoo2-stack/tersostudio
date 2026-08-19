"""REST API ViewSets for the Generations domain."""
from typing import Optional
import uuid
from django.core.exceptions import ValidationError
from django.http import Http404, HttpResponse
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.organizations.context import OrganizationContextMixin
from apps.workflows.enums import CommandType
from apps.workflows.services.commands import WorkflowCommandService
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

    def _get_idempotency_key(self, request) -> Optional[str]:
        """Extract Idempotency-Key header from request."""
        return (
            request.headers.get("Idempotency-Key")
            or request.META.get("HTTP_IDEMPOTENCY_KEY")
        )

    @action(detail=True, methods=["post"], url_path="transition")
    def transition_state(self, request, id=None):
        """Compatibility endpoint for state transitions.

        Direct forward state transitions are rejected with 409 because state progression
        is owned by the deterministic workflow coordinator.
        """
        generation = self.get_object()
        serializer = StateTransitionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        target_status = serializer.validated_data["target_status"]

        # Control transitions can route through the command service
        if target_status == GenerationStatus.PAUSED:
            return self.pause(request, id=id)
        elif target_status == GenerationStatus.CANCELLED:
            return self.cancel(request, id=id)
        elif target_status == GenerationStatus.SCHEDULED and generation.status in [
            GenerationStatus.FAILED,
            GenerationStatus.TIMED_OUT,
            GenerationStatus.BLOCKED,
        ]:
            return self.retry(request, id=id)

        # Arbitrary forward transitions are strictly forbidden
        return Response(
            {
                "error": {
                    "code": "direct_transition_requires_coordinator",
                    "message": "Direct state transitions cannot bypass the deterministic coordinator workflow engine.",
                    "status_code": status.HTTP_409_CONFLICT,
                    "details": {
                        "current_status": generation.status,
                        "target_status": target_status,
                    },
                }
            },
            status=status.HTTP_409_CONFLICT,
        )

    @action(detail=True, methods=["post"], url_path="pause")
    def pause(self, request, id=None):
        """Pause an ongoing generation via idempotent command."""
        generation = self.get_object()
        idempotency_key = self._get_idempotency_key(request)

        if not idempotency_key:
            # Fallback UUID for internal/legacy callers without header
            idempotency_key = str(uuid.uuid4())

        try:
            result = WorkflowCommandService.execute_command(
                generation=generation,
                command_type=CommandType.PAUSE,
                idempotency_key=idempotency_key,
                payload=request.data if isinstance(request.data, dict) else {},
                actor=request.user,
            )
            generation.refresh_from_db()
            response_data = {
                "command_id": result["command_id"],
                "idempotent_replay": result["idempotent_replay"],
                "generation": GenerationDetailSerializer(generation, context={"request": request}).data,
            }
            status_code = status.HTTP_200_OK if result["idempotent_replay"] else status.HTTP_200_OK
            return Response(response_data, status=status_code)
        except ValidationError as exc:
            err_code = getattr(exc, "code", "invalid_command")
            status_code = status.HTTP_409_CONFLICT if "conflict" in str(err_code) or "invalid_state" in str(err_code) else status.HTTP_400_BAD_REQUEST
            return Response(
                {
                    "error": {
                        "code": err_code or "invalid_command",
                        "message": exc.message if hasattr(exc, "message") else str(exc),
                        "status_code": status_code,
                        "details": {},
                    }
                },
                status=status_code,
            )

    @action(detail=True, methods=["post"], url_path="resume")
    def resume(self, request, id=None):
        """Resume a paused generation via idempotent command."""
        generation = self.get_object()
        idempotency_key = self._get_idempotency_key(request)

        if not idempotency_key:
            idempotency_key = str(uuid.uuid4())

        try:
            result = WorkflowCommandService.execute_command(
                generation=generation,
                command_type=CommandType.RESUME,
                idempotency_key=idempotency_key,
                payload=request.data if isinstance(request.data, dict) else {},
                actor=request.user,
            )
            generation.refresh_from_db()
            response_data = {
                "command_id": result["command_id"],
                "idempotent_replay": result["idempotent_replay"],
                "generation": GenerationDetailSerializer(generation, context={"request": request}).data,
            }
            return Response(response_data, status=status.HTTP_200_OK)
        except ValidationError as exc:
            err_code = getattr(exc, "code", "invalid_command")
            status_code = status.HTTP_409_CONFLICT if "conflict" in str(err_code) or "invalid_state" in str(err_code) else status.HTTP_400_BAD_REQUEST
            return Response(
                {
                    "error": {
                        "code": err_code or "invalid_command",
                        "message": exc.message if hasattr(exc, "message") else str(exc),
                        "status_code": status_code,
                        "details": {},
                    }
                },
                status=status_code,
            )

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, id=None):
        """Cancel a generation via idempotent command."""
        generation = self.get_object()
        idempotency_key = self._get_idempotency_key(request)

        if not idempotency_key:
            idempotency_key = str(uuid.uuid4())

        try:
            result = WorkflowCommandService.execute_command(
                generation=generation,
                command_type=CommandType.CANCEL,
                idempotency_key=idempotency_key,
                payload=request.data if isinstance(request.data, dict) else {},
                actor=request.user,
            )
            generation.refresh_from_db()
            response_data = {
                "command_id": result["command_id"],
                "idempotent_replay": result["idempotent_replay"],
                "generation": GenerationDetailSerializer(generation, context={"request": request}).data,
            }
            return Response(response_data, status=status.HTTP_200_OK)
        except ValidationError as exc:
            err_code = getattr(exc, "code", "invalid_command")
            status_code = status.HTTP_409_CONFLICT if "conflict" in str(err_code) or "invalid_state" in str(err_code) else status.HTTP_400_BAD_REQUEST
            return Response(
                {
                    "error": {
                        "code": err_code or "invalid_command",
                        "message": exc.message if hasattr(exc, "message") else str(exc),
                        "status_code": status_code,
                        "details": {},
                    }
                },
                status=status_code,
            )

    @action(detail=True, methods=["post"], url_path="retry")
    def retry(self, request, id=None):
        """Retry a failed generation via idempotent command."""
        generation = self.get_object()
        idempotency_key = self._get_idempotency_key(request)

        if not idempotency_key:
            idempotency_key = str(uuid.uuid4())

        try:
            result = WorkflowCommandService.execute_command(
                generation=generation,
                command_type=CommandType.RETRY,
                idempotency_key=idempotency_key,
                payload=request.data if isinstance(request.data, dict) else {},
                actor=request.user,
            )
            generation.refresh_from_db()
            response_data = {
                "command_id": result["command_id"],
                "idempotent_replay": result["idempotent_replay"],
                "generation": GenerationDetailSerializer(generation, context={"request": request}).data,
            }
            return Response(response_data, status=status.HTTP_200_OK)
        except ValidationError as exc:
            err_code = getattr(exc, "code", "invalid_command")
            status_code = status.HTTP_409_CONFLICT if "conflict" in str(err_code) or "retry_not_available" in str(err_code) else status.HTTP_400_BAD_REQUEST
            return Response(
                {
                    "error": {
                        "code": err_code or "invalid_command",
                        "message": exc.message if hasattr(exc, "message") else str(exc),
                        "status_code": status_code,
                        "details": {},
                    }
                },
                status=status_code,
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
