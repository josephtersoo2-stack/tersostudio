"""Django admin configuration for Projects domain."""
from django.contrib import admin
from .models import Project, ProjectSite


class ProjectSiteInline(admin.TabularInline):
    model = ProjectSite
    extra = 0
    readonly_fields = ("created_at", "updated_at")


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "organization", "product", "is_archived", "created_by", "created_at")
    list_filter = ("is_archived", "created_at")
    search_fields = ("name", "slug", "organization__name", "created_by__email")
    readonly_fields = ("id", "created_at", "updated_at")
    inlines = [ProjectSiteInline]


@admin.register(ProjectSite)
class ProjectSiteAdmin(admin.ModelAdmin):
    list_display = ("project", "site", "purpose", "organization", "created_at")
    list_filter = ("purpose", "created_at")
    search_fields = ("project__name", "site__name", "organization__name")
    readonly_fields = ("id", "created_at", "updated_at")
