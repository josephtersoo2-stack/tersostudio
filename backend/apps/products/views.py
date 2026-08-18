"""Views for WordPress Products domain."""
from django.db.models import Q
from rest_framework import mixins, permissions, viewsets

from apps.organizations.context import OrganizationContextMixin
from apps.organizations.permissions import HasOrganizationReadAccess, HasOrganizationWriteAccess
from .models import WordPressProduct
from .serializers import WordPressProductSerializer


class WordPressProductViewSet(
    OrganizationContextMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """ViewSet for managing tenant-scoped WordPress Products and targets (List, Retrieve, Patch)."""

    http_method_names = ["get", "patch", "head", "options"]
    lookup_field = "id"
    serializer_class = WordPressProductSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [permissions.IsAuthenticated(), HasOrganizationReadAccess()]
        return [permissions.IsAuthenticated(), HasOrganizationWriteAccess()]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False) or not self.request.user.is_authenticated:
            return WordPressProduct.objects.none()

        org = self.get_organization()
        qs = WordPressProduct.objects.select_related("organization", "plugin_target").filter(organization=org)

        kind = self.request.query_params.get("kind")
        if kind:
            qs = qs.filter(kind=kind.upper())

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
                Q(display_name__icontains=search)
                | Q(slug__icontains=search)
                | Q(plugin_target__plugin_slug__icontains=search)
            )

        return qs.order_by("-created_at")
