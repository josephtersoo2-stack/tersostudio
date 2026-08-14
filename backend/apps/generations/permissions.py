"""Ownership and tenant isolation permissions for Generations domain."""
from rest_framework import permissions


class IsGenerationOwner(permissions.BasePermission):
    """Allows access only to the owner of the generation."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        return bool(request.user and request.user.is_authenticated and obj.user_id == request.user.id)


class IsStepOwner(permissions.BasePermission):
    """Allows access only to the owner of the parent generation."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        return bool(request.user and request.user.is_authenticated and obj.generation.user_id == request.user.id)


class IsRunOwner(permissions.BasePermission):
    """Allows access only to the owner of the parent step generation."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        return bool(request.user and request.user.is_authenticated and obj.step.generation.user_id == request.user.id)


class IsWorkspaceOwner(permissions.BasePermission):
    """Allows access only to the owner of the workspace generation."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        return bool(request.user and request.user.is_authenticated and obj.generation.user_id == request.user.id)


class IsArtifactOwner(permissions.BasePermission):
    """Allows access only to the owner of the artifact generation."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        return bool(request.user and request.user.is_authenticated and obj.generation.user_id == request.user.id)
