"""Admin configuration for Products app."""
from django.contrib import admin
from .models import PluginTarget, WordPressProduct


class PluginTargetInline(admin.StackedInline):
    model = PluginTarget
    can_delete = False
    readonly_fields = ("created_at", "updated_at")


@admin.register(WordPressProduct)
class WordPressProductAdmin(admin.ModelAdmin):
    list_display = ("display_name", "kind", "slug", "organization", "version", "is_archived", "created_at")
    list_filter = ("kind", "is_archived", "created_at")
    search_fields = ("display_name", "slug", "organization__name")
    readonly_fields = ("id", "created_at", "updated_at")
    inlines = [PluginTargetInline]


@admin.register(PluginTarget)
class PluginTargetAdmin(admin.ModelAdmin):
    list_display = ("plugin_slug", "product", "text_domain", "namespace_prefix", "main_file", "created_at")
    search_fields = ("plugin_slug", "product__display_name", "namespace_prefix")
    readonly_fields = ("created_at", "updated_at")
