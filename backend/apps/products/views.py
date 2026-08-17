"""Views for WordPress Products domain."""
from django.db.models import Q
from rest_framework import permissions, status, viewsets
from rest_framework.response import Response

from apps.organizations.context import OrganizationContextMixin
from apps.organizations.permissions import HasOrganizationWriteAccess
from .models import WordPressProduct
from .serializers import WordPressProductSerializer


class WordPressProductViewSet(OrganizationContextMixin, viewsets.ModelViewSet):
    """ViewSet for managing tenant-scoped WordPress Products and targets."""

    permission_classes = [permissions.IsAuthenticated, HasOrganizationWriteAccess]
    serializer_class = WordPressProductSerializer
    lookup_field = "id"

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False) or not self.request.user.is_authenticated:
            return WordPressProduct.objects.none()

        org = self.get_organization()
        qs = WordPressProduct.objects.select_related("organization", "plugin_target").filter(organization=org)

        kind = self.request.query_params.get("kind")
        if kind:
            qs = qs.filter(kind=kind.upper())

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
                Q(display_name__icontains=search)
                | Q(slug__icontains=search)
                | Q(plugin_target__plugin_slug__icontains=search)
            )

        return qs.order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(
            organization=self.get_organization(),
        )
