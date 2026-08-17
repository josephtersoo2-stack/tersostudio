"""Ownership and tenant isolation permissions for Generations domain."""
from rest_framework import permissions
from apps.organizations.models import OrganizationMembership


def _user_has_org_access(user, organization_id, write_required=False) -> bool:
    if not (user and user.is_authenticated):
        return False
    membership = OrganizationMembership.objects.filter(
        user=user,
        organization_id=organization_id,
        is_active=True,
    ).first()
    if not membership:
        return False
    if write_required and membership.role not in ("OWNER", "ADMIN", "MEMBER"):
        return False
    return True


class IsGenerationOwner(permissions.BasePermission):
    """Allows read access to organization members, and mutation to write roles."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        write_req = request.method not in permissions.SAFE_METHODS
        return _user_has_org_access(request.user, obj.organization_id, write_required=write_req)


class IsStepOwner(permissions.BasePermission):
    """Allows read access to the parent generation's organization members."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        write_req = request.method not in permissions.SAFE_METHODS
        return _user_has_org_access(request.user, obj.generation.organization_id, write_required=write_req)


class IsRunOwner(permissions.BasePermission):
    """Allows read access to the parent step generation's organization members."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        write_req = request.method not in permissions.SAFE_METHODS
        return _user_has_org_access(request.user, obj.step.generation.organization_id, write_required=write_req)


class IsWorkspaceOwner(permissions.BasePermission):
    """Allows read access to the parent workspace generation's organization members."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        write_req = request.method not in permissions.SAFE_METHODS
        return _user_has_org_access(request.user, obj.generation.organization_id, write_required=write_req)


class IsArtifactOwner(permissions.BasePermission):
    """Allows read access to the parent artifact generation's organization members."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        write_req = request.method not in permissions.SAFE_METHODS
        return _user_has_org_access(request.user, obj.generation.organization_id, write_required=write_req)
