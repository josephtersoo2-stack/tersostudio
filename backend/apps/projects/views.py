"""REST API ViewSets for the Project domain."""
import uuid
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Count, Q
from django.http import Http404
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.organizations.context import OrganizationContextMixin
from apps.organizations.permissions import HasOrganizationReadAccess, HasOrganizationWriteAccess
from apps.sites.models import WordPressSite
from .enums import ProjectSitePurpose
from .models import Project, ProjectSite
from .serializers import (
    ProjectSerializer,
    ProjectSiteCreateSerializer,
    ProjectSiteSerializer,
)
from .services import ProjectService


class ProjectViewSet(OrganizationContextMixin, viewsets.ModelViewSet):
    """ViewSet for creating, listing, retrieving, updating (PATCH), and archiving Projects.
    Root DELETE and PUT are not supported and return 405.
    """

    http_method_names = ["get", "post", "patch", "delete", "head", "options"]
    serializer_class = ProjectSerializer
    lookup_field = "id"

    def destroy(self, request, *args, **kwargs):
        """Hard deletion of projects is disallowed via API (use /archive/ action)."""
        return Response(
            {
                "error": {
                    "code": "method_not_allowed",
                    "message": "Projects cannot be deleted via API. Use /archive/ instead.",
                    "status_code": status.HTTP_405_METHOD_NOT_ALLOWED,
                    "details": {},
                }
            },
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [permissions.IsAuthenticated(), HasOrganizationReadAccess()]
        return [permissions.IsAuthenticated(), HasOrganizationWriteAccess()]

    def get_queryset(self):
        """Scope project queryset strictly to the resolved organization."""
        if getattr(self, "swagger_fake_view", False) or not self.request.user.is_authenticated:
            return Project.objects.none()

        org = self.get_organization()
        qs = Project.objects.select_related("organization", "product", "product__plugin_target", "created_by").filter(
            organization=org
        ).annotate(
            generations_count_annotated=Count("generations")
        )

        # Filtering by archive status
        archived_param = self.request.query_params.get("archived")
        if archived_param is not None:
            if archived_param.lower() in ("true", "1", "t"):
                qs = qs.archived()
            elif archived_param.lower() in ("false", "0", "f"):
                qs = qs.active()

        # Search by name or description or plugin_slug
        search_query = self.request.query_params.get("search")
        if search_query:
            search_query = search_query.strip()
            qs = qs.filter(
                Q(name__icontains=search_query)
                | Q(slug__icontains=search_query)
                | Q(description__icontains=search_query)
                | Q(product__plugin_target__plugin_slug__icontains=search_query)
            )

        return qs.order_by("-created_at")

    def perform_create(self, serializer):
        """Save project within resolved tenant organization."""
        serializer.save(
            organization=self.get_organization(),
        )

    def perform_update(self, serializer):
        """Track user updating project."""
        serializer.save(
            updated_by=self.request.user,
        )

    @action(detail=True, methods=["post"])
    def archive(self, request, id=None):
        """Archive a project and its underlying product target."""
        project = self.get_object()
        archived = ProjectService.archive_project(project, request.user)
        return Response(self.get_serializer(archived).data)

    @action(detail=True, methods=["post"])
    def unarchive(self, request, id=None):
        """Restore an archived project and its underlying product target."""
        project = self.get_object()
        restored = ProjectService.unarchive_project(project, request.user)
        return Response(self.get_serializer(restored).data)

    @action(detail=True, methods=["get", "post"], url_path="sites")
    def sites(self, request, id=None):
        """List or attach WordPress sites to this project."""
        project = self.get_object()

        if request.method == "GET":
            links = ProjectSite.objects.select_related("site", "project", "organization").filter(
                project=project,
                organization=self.get_organization(),
            ).order_by("-created_at")
            return Response(ProjectSiteSerializer(links, many=True).data)

        elif request.method == "POST":
            serializer = ProjectSiteCreateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            site_id = serializer.validated_data["site_id"]
            site = WordPressSite.objects.filter(
                id=site_id,
                organization=self.get_organization(),
                is_archived=False,
            ).first()

            if not site:
                raise Http404("Site not found in this organization.")

            try:
                link = ProjectService.add_site_to_project(
                    project=project,
                    site=site,
                    actor=request.user,
                    purpose=serializer.validated_data.get("purpose", ProjectSitePurpose.PRIMARY),
                )
            except DjangoValidationError as exc:
                raise ValidationError({"detail": exc.message}, code=getattr(exc, "code", "error"))

            return Response(
                ProjectSiteSerializer(link).data,
                status=status.HTTP_201_CREATED,
            )

    @action(detail=True, methods=["delete"], url_path="sites/(?P<project_site_id>[^/.]+)")
    def site_detail(self, request, id=None, project_site_id=None):
        """Detach a site from this project by its ProjectSite link ID."""
        project = self.get_object()

        try:
            parsed_link_id = uuid.UUID(str(project_site_id))
        except (ValueError, TypeError):
            raise Http404("Project site link not found.")

        deleted = ProjectService.remove_site_from_project(
            project=project,
            project_site_id=parsed_link_id,
            actor=request.user,
        )
        if not deleted:
            raise Http404("Project site link not found.")

        return Response(status=status.HTTP_204_NO_CONTENT)
