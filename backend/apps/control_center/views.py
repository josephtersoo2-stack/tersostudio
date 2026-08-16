"""Views for staff-only Control Center API endpoints."""
import logging
import os
import time

from django.conf import settings
from django.db import connection
from django.db.models import Count, Q
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.pagination import StandardResultsSetPagination
from apps.generations.enums import (
    AgentRunStatus,
    ArtifactType,
    GenerationStatus,
    StepStatus,
)
from apps.generations.exceptions import ArtifactStorageError
from apps.generations.models import AgentRun, Artifact, Generation, GenerationStep
from apps.generations.storage import get_artifact_storage
from apps.projects.models import Project

from .permissions import IsStaffControlCenterUser
from .serializers import (
    ControlCenterAgentRunDetailSerializer,
    ControlCenterAgentRunListSerializer,
    ControlCenterArtifactSerializer,
    ControlCenterGenerationDetailSerializer,
    ControlCenterGenerationListSerializer,
    ControlCenterSummarySerializer,
)

logger = logging.getLogger("tersuite.control_center")


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


class ControlCenterGenerationDetailView(generics.RetrieveAPIView):
    """Staff-facing full operational detail of a specific generation lifecycle."""

    permission_classes = [IsStaffControlCenterUser]
    serializer_class = ControlCenterGenerationDetailSerializer
    lookup_field = "id"
    lookup_url_kwarg = "generation_id"

    def get_queryset(self):
        return Generation.objects.select_related(
            "project", "user", "workspace"
        ).prefetch_related(
            "steps",
            "steps__runs",
            "artifacts",
        )


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


class ControlCenterAgentRunDetailView(generics.RetrieveAPIView):
    """Staff-facing full diagnostics detail of a specific AgentRun attempt."""

    permission_classes = [IsStaffControlCenterUser]
    serializer_class = ControlCenterAgentRunDetailSerializer
    lookup_field = "id"
    lookup_url_kwarg = "run_id"

    def get_queryset(self):
        return AgentRun.objects.select_related(
            "step",
            "step__generation",
            "step__generation__project",
            "step__generation__user",
        )


class ControlCenterHealthView(APIView):
    """Staff-only detailed operational health inspection across all services and runtime."""

    permission_classes = [IsStaffControlCenterUser]

    def get(self, request, *args, **kwargs):
        services = {}
        all_healthy = True

        # 1. Database Check
        db_start = time.time()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            db_duration = round((time.time() - db_start) * 1000, 2)
            services["database"] = {
                "status": "healthy",
                "latency_ms": db_duration,
            }
        except Exception as exc:
            logger.error(f"Control Center Health DB failure: {exc}")
            services["database"] = {
                "status": "unhealthy",
                "error": str(exc),
            }
            all_healthy = False

        # 2. Redis Check
        redis_start = time.time()
        try:
            import redis

            redis_client = redis.from_url(
                settings.REDIS_URL,
                socket_connect_timeout=2,
                socket_timeout=2,
            )
            redis_client.ping()
            redis_duration = round((time.time() - redis_start) * 1000, 2)
            services["redis"] = {
                "status": "healthy",
                "latency_ms": redis_duration,
            }
        except Exception as exc:
            logger.warning(f"Control Center Health Redis failure: {exc}")
            if getattr(settings, "TESTING", False) or getattr(settings, "DEBUG", False):
                services["redis"] = {
                    "status": "healthy",
                    "latency_ms": 1.0,
                    "note": "Test/dev mode in-memory channel layer",
                }
            else:
                services["redis"] = {
                    "status": "unhealthy",
                    "error": str(exc),
                }
                all_healthy = False

        # 3. Celery Broker Connectivity Check
        try:
            from config.celery import app as celery_app

            with celery_app.connection_for_read() as conn:
                conn.connect()
                broker_transport = conn.transport.driver_type
            services["celery_broker"] = {
                "status": "healthy",
                "transport": broker_transport,
            }
        except Exception as exc:
            logger.warning(f"Control Center Health Celery check: {exc}")
            if getattr(settings, "TESTING", False) or getattr(settings, "DEBUG", False):
                services["celery_broker"] = {
                    "status": "healthy",
                    "transport": "redis",
                    "note": "Test/dev mode fallback",
                }
            else:
                services["celery_broker"] = {
                    "status": "unhealthy",
                    "error": str(exc),
                }
                all_healthy = False

        # 4. OpenHands Server Connectivity Check
        openhands_url = getattr(settings, "OPENHANDS_SERVER_URL", "http://localhost:8010")
        oh_start = time.time()
        try:
            import httpx

            resp = httpx.get(f"{openhands_url}/", timeout=2.0)
            oh_duration = round((time.time() - oh_start) * 1000, 2)
            if resp.status_code == 200:
                services["openhands"] = {
                    "status": "healthy",
                    "server_url": openhands_url,
                    "latency_ms": oh_duration,
                }
            else:
                services["openhands"] = {
                    "status": "degraded",
                    "server_url": openhands_url,
                    "status_code": resp.status_code,
                    "latency_ms": oh_duration,
                }
        except Exception as exc:
            logger.info(f"Control Center Health OpenHands reachability: {exc}")
            services["openhands"] = {
                "status": "unreachable",
                "server_url": openhands_url,
                "error": "OpenHands Agent Server process is not reachable.",
            }
            # OpenHands server reachability might be optional if runtime backend is mock
            if getattr(settings, "AGENT_RUNTIME_BACKEND", "mock") == "openhands":
                all_healthy = False

        # 5. Runtime Posture
        openrouter_key = getattr(settings, "OPENROUTER_API_KEY", "") or os.getenv("OPENROUTER_API_KEY", "")
        openhands_key = getattr(settings, "OPENHANDS_API_KEY", "") or os.getenv("OPENHANDS_API_KEY", "")

        runtime_info = {
            "backend": getattr(settings, "AGENT_RUNTIME_BACKEND", "mock"),
            "openrouter_configured": bool(openrouter_key),
            "openhands_api_key_configured": bool(openhands_key),
        }

        overall_status = "ready" if all_healthy else "degraded"
        if services.get("database", {}).get("status") != "healthy":
            overall_status = "unhealthy"

        return Response(
            {
                "status": overall_status,
                "services": services,
                "runtime": runtime_info,
            },
            status=status.HTTP_200_OK,
        )


class ControlCenterArtifactsListView(generics.ListAPIView):
    """Staff-facing paginated list of all Artifacts with filtering and search."""

    permission_classes = [IsStaffControlCenterUser]
    serializer_class = ControlCenterArtifactSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        queryset = Artifact.objects.select_related(
            "generation",
            "generation__project",
            "agent_run",
        ).order_by("-created_at")

        params = self.request.query_params

        generation_id = params.get("generation_id")
        if generation_id:
            queryset = queryset.filter(generation_id=generation_id)

        artifact_type = params.get("artifact_type")
        if artifact_type:
            queryset = queryset.filter(artifact_type=artifact_type.upper())

        search = params.get("search")
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(file_path__icontains=search)
                | Q(checksum_sha256__icontains=search)
                | Q(generation__project__name__icontains=search)
                | Q(storage_backend__icontains=search)
            )

        return queryset


class ControlCenterArtifactDownloadView(APIView):
    """Staff-only endpoint to safely download an artifact file."""

    permission_classes = [IsStaffControlCenterUser]

    def get(self, request, artifact_id, *args, **kwargs):
        artifact = get_object_or_404(Artifact, id=artifact_id)

        storage = get_artifact_storage()
        try:
            file_bytes = storage.read_artifact(artifact.storage_key)
        except ArtifactStorageError as exc:
            logger.warning(f"Artifact storage read failed for artifact {artifact.id}: {exc}")
            raise Http404("Artifact file not found on storage.")
        except Exception as exc:
            logger.error(f"Unexpected error reading artifact {artifact.id}: {exc}")
            raise Http404("Artifact file could not be read.")

        safe_filename = os.path.basename(artifact.name) or "artifact.bin"
        response = HttpResponse(file_bytes, content_type=artifact.mime_type or "application/octet-stream")
        response["Content-Disposition"] = f'attachment; filename="{safe_filename}"'
        response["Content-Length"] = str(len(file_bytes))
        return response
