"""Project ownership and tenant permissions."""
from rest_framework import permissions
from apps.organizations.permissions import (
    HasOrganizationReadAccess,
    HasOrganizationWriteAccess,
)


class IsProjectOwner(permissions.BasePermission):
    """Allows read access to organization members, and write operations to WRITE_ROLES."""

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        membership = getattr(request, "tersuite_membership", None)
        if not membership or not membership.is_active:
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        return membership.role in ("OWNER", "ADMIN", "MEMBER")

    def has_object_permission(self, request, view, obj):
        if not (request.user and request.user.is_authenticated):
            return False
        org = getattr(request, "tersuite_organization", None)
        if not org or obj.organization_id != org.id:
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        membership = getattr(request, "tersuite_membership", None)
        return bool(membership and membership.is_active and membership.role in ("OWNER", "ADMIN", "MEMBER"))
