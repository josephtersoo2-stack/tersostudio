"""Django admin registration for Project model."""
from django.contrib import admin
from .models import Project


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    """Admin configuration for Project."""

    list_display = (
        "name",
        "user",
        "slug",
        "plugin_slug",
        "wordpress_version",
        "php_version",
        "is_archived",
        "created_at",
    )
    list_filter = ("is_archived", "wordpress_version", "php_version", "created_at")
    search_fields = ("name", "slug", "plugin_slug", "user__email", "description")
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("-created_at",)
