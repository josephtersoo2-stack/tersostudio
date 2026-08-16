"""Views for staff-only Control Center API endpoints."""
import os

from django.conf import settings
from django.db.models import Count, Q
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.pagination import StandardResultsSetPagination
from apps.generations.enums import (
    AgentRunStatus,
    ArtifactType,
    GenerationStatus,
    StepStatus,
)
from apps.generations.models import AgentRun, Artifact, Generation, GenerationStep
from apps.projects.models import Project

from .permissions import IsStaffControlCenterUser
from .serializers import (
    ControlCenterAgentRunListSerializer,
    ControlCenterGenerationListSerializer,
    ControlCenterSummarySerializer,
)


class ControlCenterSummaryView(APIView):
    """Aggregate operational metrics across all projects, generations, and agent runs."""

    permission_classes = [IsStaffControlCenterUser]

    def get(self, request, *args, **kwargs):
        # 1. Projects Metrics
        total_projects = Project.objects.count()
        active_projects = Project.objects.filter(is_archived=False).count()
        archived_projects = Project.objects.filter(is_archived=True).count()

        # 2. Generations Metrics
        total_generations = Generation.objects.count()
        active_generations = Generation.objects.exclude(
            status__in=[
                GenerationStatus.COMPLETED,
                GenerationStatus.FAILED,
                GenerationStatus.CANCELLED,
            ]
        ).count()

        generations_by_status = {
            "total": total_generations,
            "active": active_generations,
            "draft": Generation.objects.filter(status=GenerationStatus.DRAFT).count(),
            "specification": Generation.objects.filter(status=GenerationStatus.SPECIFICATION).count(),
            "approved": Generation.objects.filter(status=GenerationStatus.APPROVED).count(),
            "planning": Generation.objects.filter(status=GenerationStatus.PLANNING).count(),
            "building": Generation.objects.filter(status=GenerationStatus.BUILDING).count(),
            "testing": Generation.objects.filter(status=GenerationStatus.TESTING).count(),
            "review": Generation.objects.filter(status=GenerationStatus.REVIEW).count(),
            "packaging": Generation.objects.filter(status=GenerationStatus.PACKAGING).count(),
            "completed": Generation.objects.filter(status=GenerationStatus.COMPLETED).count(),
            "failed": Generation.objects.filter(status=GenerationStatus.FAILED).count(),
            "cancelled": Generation.objects.filter(status=GenerationStatus.CANCELLED).count(),
            "paused": Generation.objects.filter(status=GenerationStatus.PAUSED).count(),
            "retrying": Generation.objects.filter(status=GenerationStatus.RETRYING).count(),
        }

        # 3. Agent Runs Metrics
        total_runs = AgentRun.objects.count()
        runs_by_status = {
            "total": total_runs,
            "queued": AgentRun.objects.filter(status=AgentRunStatus.QUEUED).count(),
            "running": AgentRun.objects.filter(status=AgentRunStatus.RUNNING).count(),
            "completed": AgentRun.objects.filter(status=AgentRunStatus.COMPLETED).count(),
            "failed": AgentRun.objects.filter(status=AgentRunStatus.FAILED).count(),
            "cancelled": AgentRun.objects.filter(status=AgentRunStatus.CANCELLED).count(),
            "timed_out": AgentRun.objects.filter(status=AgentRunStatus.TIMED_OUT).count(),
        }

        # 4. Steps Metrics
        total_steps = GenerationStep.objects.count()
        steps_by_status = {
            "total": total_steps,
            "pending": GenerationStep.objects.filter(status=StepStatus.PENDING).count(),
            "running": GenerationStep.objects.filter(status=StepStatus.RUNNING).count(),
            "completed": GenerationStep.objects.filter(status=StepStatus.COMPLETED).count(),
            "failed": GenerationStep.objects.filter(status=StepStatus.FAILED).count(),
            "cancelled": GenerationStep.objects.filter(status=StepStatus.CANCELLED).count(),
            "skipped": GenerationStep.objects.filter(status=StepStatus.SKIPPED).count(),
        }

        # 5. Artifacts Metrics
        total_artifacts = Artifact.objects.count()
        artifacts_by_type = {
            "total": total_artifacts,
            "source_code": Artifact.objects.filter(artifact_type=ArtifactType.SOURCE_CODE).count(),
            "configuration": Artifact.objects.filter(artifact_type=ArtifactType.CONFIGURATION).count(),
            "test_report": Artifact.objects.filter(artifact_type=ArtifactType.TEST_REPORT).count(),
            "documentation": Artifact.objects.filter(artifact_type=ArtifactType.DOCUMENTATION).count(),
            "zip_archive": Artifact.objects.filter(artifact_type=ArtifactType.ZIP_ARCHIVE).count(),
            "security_report": Artifact.objects.filter(artifact_type=ArtifactType.SECURITY_REPORT).count(),
            "other": Artifact.objects.filter(artifact_type=ArtifactType.OTHER).count(),
        }

        # 6. Runtime Metrics (Zero Credential Exposure)
        openrouter_key = getattr(settings, "OPENROUTER_API_KEY", "") or os.getenv("OPENROUTER_API_KEY", "")
        openhands_key = getattr(settings, "OPENHANDS_API_KEY", "") or os.getenv("OPENHANDS_API_KEY", "")
        openhands_url = getattr(settings, "OPENHANDS_SERVER_URL", "http://localhost:8010")

        runtime_summary = {
            "default_backend": getattr(settings, "AGENT_RUNTIME_BACKEND", "mock"),
            "openhands_server_url": openhands_url,
            "openrouter_configured": bool(openrouter_key),
            "openhands_api_key_configured": bool(openhands_key),
        }

        data = {
            "projects": {
                "total": total_projects,
                "active": active_projects,
                "archived": archived_projects,
            },
            "generations": generations_by_status,
            "agent_runs": runs_by_status,
            "steps": steps_by_status,
            "artifacts": artifacts_by_type,
            "runtime": runtime_summary,
        }

        serializer = ControlCenterSummarySerializer(data)
        return Response(serializer.data)


class ControlCenterGenerationsListView(generics.ListAPIView):
    """Staff-facing paginated list of all generations with filtering and search."""

    permission_classes = [IsStaffControlCenterUser]
    serializer_class = ControlCenterGenerationListSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        queryset = Generation.objects.select_related(
            "project", "user", "workspace"
        ).annotate(
            steps_count=Count("steps", distinct=True),
            runs_count=Count("steps__runs", distinct=True),
            artifacts_count=Count("artifacts", distinct=True),
        ).order_by("-created_at")

        params = self.request.query_params

        status = params.get("status")
        if status:
            queryset = queryset.filter(status=status.upper())

        project_id = params.get("project_id")
        if project_id:
            queryset = queryset.filter(project_id=project_id)

        user_id = params.get("user_id")
        if user_id:
            queryset = queryset.filter(user_id=user_id)

        search = params.get("search")
        if search:
            queryset = queryset.filter(
                Q(prompt__icontains=search)
                | Q(project__name__icontains=search)
                | Q(user__email__icontains=search)
                | Q(failure_category__icontains=search)
                | Q(error_message__icontains=search)
            )

        return queryset


class ControlCenterAgentRunsListView(generics.ListAPIView):
    """Staff-facing paginated list of all AgentRuns with filtering and search."""

    permission_classes = [IsStaffControlCenterUser]
    serializer_class = ControlCenterAgentRunListSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        queryset = AgentRun.objects.select_related(
            "step",
            "step__generation",
            "step__generation__project",
            "step__generation__user",
        ).order_by("-created_at")

        params = self.request.query_params

        status = params.get("status")
        if status:
            queryset = queryset.filter(status=status.upper())

        runtime_type = params.get("runtime_type")
        if runtime_type:
            queryset = queryset.filter(runtime_type=runtime_type)

        model = params.get("model")
        if model:
            queryset = queryset.filter(model_name__icontains=model)

        failure_category = params.get("failure_category")
        if failure_category:
            queryset = queryset.filter(failure_category__iexact=failure_category)

        generation_id = params.get("generation_id")
        if generation_id:
            queryset = queryset.filter(step__generation_id=generation_id)

        step_id = params.get("step_id")
        if step_id:
            queryset = queryset.filter(step_id=step_id)

        search = params.get("search")
        if search:
            queryset = queryset.filter(
                Q(prompt__icontains=search)
                | Q(output__icontains=search)
                | Q(model_name__icontains=search)
                | Q(session_id__icontains=search)
                | Q(remote_conversation_id__icontains=search)
                | Q(step__name__icontains=search)
                | Q(step__generation__project__name__icontains=search)
                | Q(step__generation__user__email__icontains=search)
            )

        return queryset
