"""Django admin configuration for Sites domain."""
from django.contrib import admin
from .models import SiteProfileSnapshot, WordPressSite


@admin.register(WordPressSite)
class WordPressSiteAdmin(admin.ModelAdmin):
    list_display = ("name", "url", "environment", "connection_status", "organization", "next_profile_version", "last_profiled_at", "is_archived")
    list_filter = ("environment", "connection_status", "is_archived", "created_at")
    search_fields = ("name", "url", "organization__name")
    readonly_fields = ("id", "next_profile_version", "last_profiled_at", "created_at", "updated_at")


@admin.register(SiteProfileSnapshot)
class SiteProfileSnapshotAdmin(admin.ModelAdmin):
    list_display = ("site", "version", "source", "wordpress_version", "php_version", "multisite", "created_at")
    list_filter = ("source", "multisite", "created_at")
    search_fields = ("site__name", "site__url", "checksum_sha256")
    readonly_fields = ("id", "version", "checksum_sha256", "created_at", "updated_at")
