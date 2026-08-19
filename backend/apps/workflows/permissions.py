"""Permissions for Workflows domain endpoints."""
from rest_framework import permissions
from apps.organizations.permissions import HasOrganizationReadAccess


class IsWorkflowReadOnly(permissions.BasePermission):
    """Workflow inspection APIs are strictly read-only for authenticated tenant members."""

    def has_permission(self, request, view) -> bool:
        if request.method in permissions.SAFE_METHODS:
            return HasOrganizationReadAccess().has_permission(request, view)
        return False
