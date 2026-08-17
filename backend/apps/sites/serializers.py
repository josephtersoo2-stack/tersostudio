"""Serializers for WordPress Sites and Profile Snapshots."""
from rest_framework import serializers
from apps.core.validators import (
    find_forbidden_json_key,
    normalize_wordpress_url,
    validate_safe_json_object,
)
from .enums import SiteConnectionStatus, SiteEnvironment, SiteProfileSource
from .models import SiteProfileSnapshot, WordPressSite


class SiteProfileSnapshotSerializer(serializers.ModelSerializer):
    """Full representation of an immutable point-in-time SiteProfileSnapshot."""

    organization_id = serializers.UUIDField(source="organization.id", read_only=True)
    site_id = serializers.UUIDField(source="site.id", read_only=True)
    created_by_id = serializers.UUIDField(source="created_by.id", read_only=True)

    class Meta:
        model = SiteProfileSnapshot
        fields = [
            "id",
            "organization_id",
            "site_id",
            "version",
            "source",
            "wordpress_version",
            "php_version",
            "multisite",
            "locale",
            "timezone",
            "active_theme",
            "active_plugins",
            "server",
            "capabilities",
            "health",
            "checksum_sha256",
            "created_by_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class SiteProfileSnapshotCreateSerializer(serializers.Serializer):
    """Payload serializer for submitting a new site profile snapshot."""

    source = serializers.ChoiceField(
        choices=SiteProfileSource.choices,
        default=SiteProfileSource.MANUAL,
    )
    wordpress_version = serializers.CharField(max_length=50, required=False, allow_blank=True, default="")
    php_version = serializers.CharField(max_length=50, required=False, allow_blank=True, default="")
    multisite = serializers.BooleanField(required=False, default=False)
    locale = serializers.CharField(max_length=50, required=False, default="en_US")
    timezone = serializers.CharField(max_length=100, required=False, default="UTC")
    active_theme = serializers.JSONField(required=False, default=dict)
    active_plugins = serializers.ListField(required=False, default=list)
    server = serializers.JSONField(required=False, default=dict)
    capabilities = serializers.JSONField(required=False, default=dict)
    health = serializers.JSONField(required=False, default=dict)

    def validate(self, attrs):
        forbidden_key = find_forbidden_json_key(attrs)
        if forbidden_key:
            raise serializers.ValidationError(
                f"Forbidden secret key '{forbidden_key}' detected in snapshot payload. Credentials cannot be stored.",
                code="forbidden_secret_key",
            )
        return attrs


class WordPressSiteSerializer(serializers.ModelSerializer):
    """Full serializer for WordPressSite metadata."""

    organization_id = serializers.UUIDField(source="organization.id", read_only=True)
    created_by_id = serializers.UUIDField(source="created_by.id", read_only=True)
    updated_by_id = serializers.UUIDField(source="updated_by.id", read_only=True)

    class Meta:
        model = WordPressSite
        fields = [
            "id",
            "organization_id",
            "name",
            "url",
            "environment",
            "connection_status",
            "next_profile_version",
            "last_profiled_at",
            "metadata",
            "is_archived",
            "created_by_id",
            "updated_by_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "organization_id",
            "connection_status",
            "next_profile_version",
            "last_profiled_at",
            "created_by_id",
            "updated_by_id",
            "created_at",
            "updated_at",
        ]

    def validate_url(self, value):
        return normalize_wordpress_url(value)

    def validate_metadata(self, value):
        validate_safe_json_object(value)
        return value
