"""REST API ViewSets for WordPress Sites and Site Profile Snapshots."""
import uuid
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from django.http import Http404
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.organizations.context import OrganizationContextMixin
from apps.organizations.permissions import HasOrganizationReadAccess, HasOrganizationWriteAccess
from .enums import SiteProfileSource
from .models import SiteProfileSnapshot, WordPressSite
from .serializers import (
    SiteProfileSnapshotCreateSerializer,
    SiteProfileSnapshotSerializer,
    WordPressSiteSerializer,
)
from .services import create_site_profile_snapshot


class WordPressSiteViewSet(OrganizationContextMixin, viewsets.ModelViewSet):
    """ViewSet for managing WordPress Site metadata (List, Create, Retrieve, Patch, Archive/Unarchive).
    Root DELETE and PUT return 405 Method Not Allowed.
    """

    http_method_names = ["get", "post", "patch", "head", "options"]
    serializer_class = WordPressSiteSerializer
    lookup_field = "id"

    def get_permissions(self):
        if self.action in ("list", "retrieve", "profiles", "profile_detail"):
            if self.request.method in permissions.SAFE_METHODS:
                return [permissions.IsAuthenticated(), HasOrganizationReadAccess()]
        return [permissions.IsAuthenticated(), HasOrganizationWriteAccess()]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False) or not self.request.user.is_authenticated:
            return WordPressSite.objects.none()

        org = self.get_organization()
        qs = WordPressSite.objects.select_related("organization").filter(organization=org)

        env = self.request.query_params.get("environment")
        if env:
            qs = qs.filter(environment=env.upper())

        status_param = self.request.query_params.get("status")
        if status_param:
            qs = qs.filter(connection_status=status_param.upper())

        archived = self.request.query_params.get("archived")
        if archived is not None:
            if archived.lower() in ("true", "1", "t"):
                qs = qs.filter(is_archived=True)
            elif archived.lower() in ("false", "0", "f"):
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

    @action(detail=True, methods=["post"])
    def archive(self, request, id=None):
        """Archive a WordPress site."""
        site = self.get_object()
        site.is_archived = True
        site.updated_by = request.user
        site.save(update_fields=["is_archived", "updated_by", "updated_at"])
        return Response(self.get_serializer(site).data)

    @action(detail=True, methods=["post"])
    def unarchive(self, request, id=None):
        """Unarchive a WordPress site."""
        site = self.get_object()
        site.is_archived = False
        site.updated_by = request.user
        site.save(update_fields=["is_archived", "updated_by", "updated_at"])
        return Response(self.get_serializer(site).data)

    @action(detail=True, methods=["get", "post"], url_path="profiles")
    def profiles(self, request, id=None):
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
                    source=SiteProfileSource.MANUAL,
                )
            except DjangoValidationError as exc:
                raise ValidationError({"detail": exc.message}, code=getattr(exc, "code", "error"))

            return Response(
                SiteProfileSnapshotSerializer(snapshot).data,
                status=status.HTTP_201_CREATED,
            )

    @action(detail=True, methods=["get"], url_path="profiles/(?P<snapshot_id>[^/.]+)")
    def profile_detail(self, request, id=None, snapshot_id=None):
        """Retrieve a specific profile snapshot for this WordPress site."""
        site = self.get_object()

        try:
            parsed_snapshot_id = uuid.UUID(str(snapshot_id))
        except (ValueError, TypeError):
            raise Http404("Site profile snapshot not found.")

        snapshot = SiteProfileSnapshot.objects.filter(
            id=parsed_snapshot_id,
            site=site,
            organization=self.get_organization(),
        ).first()

        if not snapshot:
            raise Http404("Site profile snapshot not found.")

        return Response(SiteProfileSnapshotSerializer(snapshot).data)
