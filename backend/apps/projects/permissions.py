"""Project ownership permissions."""
from rest_framework import permissions


class IsProjectOwner(permissions.BasePermission):
    """Allows access only to the owner of the project."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        return bool(request.user and request.user.is_authenticated and obj.user_id == request.user.id)
