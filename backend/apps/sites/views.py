"""REST API ViewSets for WordPress Sites and Site Profile Snapshots."""
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.organizations.context import OrganizationContextMixin
from apps.organizations.permissions import HasOrganizationWriteAccess
from .models import SiteProfileSnapshot, WordPressSite
from .serializers import (
    SiteProfileSnapshotCreateSerializer,
    SiteProfileSnapshotSerializer,
    WordPressSiteSerializer,
)
from .services import create_site_profile_snapshot


class WordPressSiteViewSet(OrganizationContextMixin, viewsets.ModelViewSet):
    """ViewSet for managing WordPress Site metadata."""

    permission_classes = [permissions.IsAuthenticated, HasOrganizationWriteAccess]
    serializer_class = WordPressSiteSerializer
    lookup_field = "id"

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False) or not self.request.user.is_authenticated:
            return WordPressSite.objects.none()

        org = self.get_organization()
        qs = WordPressSite.objects.select_related("organization").filter(organization=org)

        env = self.request.query_params.get("environment")
        if env:
            qs = qs.filter(environment=env.upper())

        status_param = self.request.query_params.get("connection_status")
        if status_param:
            qs = qs.filter(connection_status=status_param.upper())

        is_archived = self.request.query_params.get("is_archived")
        if is_archived is not None:
            if is_archived.lower() in ("true", "1", "t"):
                qs = qs.filter(is_archived=True)
            elif is_archived.lower() in ("false", "0", "f"):
                qs = qs.filter(is_archived=False)

        search = self.request.query_params.get("search")
        if search:
            search = search.strip()
            qs = qs.filter(
                Q(name__icontains=search)
                | Q(url__icontains=search)
            )

        return qs.order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(
            organization=self.get_organization(),
            created_by=self.request.user,
            updated_by=self.request.user,
        )

    def perform_update(self, serializer):
        serializer.save(
            updated_by=self.request.user,
        )

    @action(detail=True, methods=["get", "post"], url_path="snapshots")
    def snapshots(self, request, id=None):
        """List snapshots or record a new snapshot for this specific WordPress site."""
        site = self.get_object()

        if request.method == "GET":
            snapshots_qs = SiteProfileSnapshot.objects.select_related("site", "organization").filter(
                site=site,
                organization=self.get_organization(),
            ).order_by("-version")
            return Response(SiteProfileSnapshotSerializer(snapshots_qs, many=True).data)

        elif request.method == "POST":
            serializer = SiteProfileSnapshotCreateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            try:
                snapshot = create_site_profile_snapshot(
                    site=site,
                    actor=request.user,
                    payload=serializer.validated_data,
                    source=serializer.validated_data.get("source", "MANUAL"),
                )
            except DjangoValidationError as exc:
                raise ValidationError({"detail": exc.message}, code=getattr(exc, "code", "error"))

            return Response(
                SiteProfileSnapshotSerializer(snapshot).data,
                status=status.HTTP_201_CREATED,
            )


class SiteProfileSnapshotViewSet(
    OrganizationContextMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Read-only viewset for inspecting recorded site profile snapshots across an organization."""

    permission_classes = [permissions.IsAuthenticated, HasOrganizationWriteAccess]
    serializer_class = SiteProfileSnapshotSerializer
    lookup_field = "id"

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False) or not self.request.user.is_authenticated:
            return SiteProfileSnapshot.objects.none()

        org = self.get_organization()
        qs = SiteProfileSnapshot.objects.select_related("site", "organization").filter(organization=org)

        site_id = self.request.query_params.get("site_id")
        if site_id:
            qs = qs.filter(site_id=site_id)

        return qs.order_by("-created_at")
