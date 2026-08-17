"""Permission classes for Organization-scoped tenant authorization."""
from rest_framework import permissions
from .enums import MEMBER_MANAGER_ROLES, WRITE_ROLES


def _get_membership(request):
    if not (request.user and request.user.is_authenticated):
        return None
    if not hasattr(request, "tersuite_membership"):
        try:
            from .context import resolve_request_organization
            _, membership = resolve_request_organization(request)
            return membership
        except Exception:
            return None
    return getattr(request, "tersuite_membership", None)


class HasOrganizationReadAccess(permissions.BasePermission):
    """Allows read access to any authenticated user with an active membership in the organization."""

    def has_permission(self, request, view):
        membership = _get_membership(request)
        return bool(membership and membership.is_active)


class HasOrganizationWriteAccess(permissions.BasePermission):
    """Allows safe methods to all members, but restricts mutation actions to WRITE_ROLES."""

    def has_permission(self, request, view):
        membership = _get_membership(request)
        if not membership or not membership.is_active:
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        return membership.role in WRITE_ROLES


class CanManageOrganizationMembers(permissions.BasePermission):
    """Allows member management actions only to OWNER and ADMIN roles."""

    def has_permission(self, request, view):
        membership = _get_membership(request)
        return bool(membership and membership.is_active and membership.role in MEMBER_MANAGER_ROLES)


class OrganizationScopedQuerysetMixin:
    """Mixin enforcing that views filter querysets strictly by the resolved organization."""

    def get_queryset(self):
        qs = super().get_queryset()
        if getattr(self, "swagger_fake_view", False) or not self.request.user.is_authenticated:
            return qs.none()
        org = getattr(self.request, "tersuite_organization", None)
        if not org:
            return qs.none()
        return qs.filter(organization=org)
