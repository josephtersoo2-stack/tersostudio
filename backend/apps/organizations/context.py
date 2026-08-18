"""Tenant context resolution and header enforcement."""
import uuid
from rest_framework import status
from rest_framework.exceptions import APIException
from .models import Organization, OrganizationMembership

ORGANIZATION_HEADER = "HTTP_X_TERSUITE_ORGANIZATION_ID"


class OrganizationContextRequired(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Multiple active organization memberships found. Header 'X-Tersuite-Organization-ID' is required."
    default_code = "organization_context_required"


class InvalidOrganizationContext(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "The provided 'X-Tersuite-Organization-ID' header is not a valid UUID."
    default_code = "invalid_organization_context"


class OrganizationNotFound(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "Organization not found or you do not have an active membership in this organization."
    default_code = "organization_not_found"


def resolve_request_organization(request) -> tuple[Organization, OrganizationMembership]:
    """Resolve the active organization context for the current request.

    Caches results as request.tersuite_organization and request.tersuite_membership.
    """
    if hasattr(request, "tersuite_organization") and hasattr(request, "tersuite_membership"):
        return request.tersuite_organization, request.tersuite_membership

    if not request.user or not request.user.is_authenticated:
        raise OrganizationNotFound()

    header_val = request.META.get(ORGANIZATION_HEADER)

    if header_val:
        header_val = header_val.strip()
        try:
            org_id = uuid.UUID(header_val)
        except (ValueError, TypeError):
            raise InvalidOrganizationContext()

        membership = OrganizationMembership.objects.select_related("organization").filter(
            user=request.user,
            organization_id=org_id,
            is_active=True,
            organization__is_active=True,
        ).first()

        if not membership:
            raise OrganizationNotFound()

        request.tersuite_organization = membership.organization
        request.tersuite_membership = membership
        return membership.organization, membership

    # Header was omitted. Check user's active memberships.
    active_memberships = list(
        OrganizationMembership.objects.select_related("organization").filter(
            user=request.user,
            is_active=True,
            organization__is_active=True,
        )
    )

    if len(active_memberships) == 1:
        membership = active_memberships[0]
        request.tersuite_organization = membership.organization
        request.tersuite_membership = membership
        return membership.organization, membership

    if len(active_memberships) > 1:
        raise OrganizationContextRequired()

    # len == 0
    raise OrganizationNotFound()


class OrganizationContextMixin:
    """View / ViewSet mixin that resolves organization context on incoming requests."""

    def initial(self, request, *args, **kwargs):
        self.format_kwarg = self.get_format_suffix(**kwargs)
        neg = self.perform_content_negotiation(request)
        request.accepted_renderer, request.accepted_media_type = neg
        version, scheme = self.determine_version(request, *args, **kwargs)
        request.version, request.versioning_scheme = version, scheme

        self.perform_authentication(request)
        if request.user and request.user.is_authenticated:
            resolve_request_organization(request)

        self.check_permissions(request)
        self.check_throttles(request)


    def get_organization(self) -> Organization:
        """Return the resolved organization for the current request."""
        if hasattr(self.request, "tersuite_organization"):
            return self.request.tersuite_organization
        org, _ = resolve_request_organization(self.request)
        return org

    def get_membership(self) -> OrganizationMembership:
        """Return the user's active membership in the current organization."""
        if hasattr(self.request, "tersuite_membership"):
            return self.request.tersuite_membership
        _, membership = resolve_request_organization(self.request)
        return membership
