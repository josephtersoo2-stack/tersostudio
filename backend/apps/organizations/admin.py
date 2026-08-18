"""Django admin registrations for Organizations."""
from django.contrib import admin
from .models import Organization, OrganizationMembership


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_personal", "is_active", "created_by", "created_at")
    list_filter = ("is_personal", "is_active", "created_at")
    search_fields = ("name", "slug", "created_by__email")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(OrganizationMembership)
class OrganizationMembershipAdmin(admin.ModelAdmin):
    list_display = ("organization", "user", "role", "is_active", "created_at")
    list_filter = ("role", "is_active", "created_at")
    search_fields = ("organization__name", "organization__slug", "user__email")
    readonly_fields = ("id", "created_at", "updated_at")
