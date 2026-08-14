"""REST API ViewSets for the Project domain."""
from django.db.models import Count
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Project
from .permissions import IsProjectOwner
from .serializers import ProjectSerializer


class ProjectViewSet(viewsets.ModelViewSet):
    """ViewSet for creating, listing, retrieving, updating, and archiving Projects."""

    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated, IsProjectOwner]
    lookup_field = "id"

    def get_queryset(self):
        """Scope project queryset strictly to the authenticated user."""
        if getattr(self, "swagger_fake_view", False) or not self.request.user.is_authenticated:
            return Project.objects.none()

        qs = Project.objects.filter(user=self.request.user).annotate(
            generations_count_annotated=Count("generations")
        )

        # Filtering by archive status
        archived_param = self.request.query_params.get("archived")
        if archived_param is not None:
            if archived_param.lower() in ("true", "1", "t"):
                qs = qs.archived()
            elif archived_param.lower() in ("false", "0", "f"):
                qs = qs.active()

        # Search by name or description
        search_query = self.request.query_params.get("search")
        if search_query:
            qs = qs.filter(name__icontains=search_query)

        return qs.order_by("-created_at")

    def perform_create(self, serializer):
        """Save project with current user as owner."""
        serializer.save(user=self.request.user)

    @action(detail=True, methods=["post"])
    def archive(self, request, id=None):
        """Archive a project."""
        project = self.get_object()
        project.is_archived = True
        project.save(update_fields=["is_archived", "updated_at"])
        return Response(self.get_serializer(project).data)

    @action(detail=True, methods=["post"])
    def unarchive(self, request, id=None):
        """Restore an archived project."""
        project = self.get_object()
        project.is_archived = False
        project.save(update_fields=["is_archived", "updated_at"])
        return Response(self.get_serializer(project).data)
