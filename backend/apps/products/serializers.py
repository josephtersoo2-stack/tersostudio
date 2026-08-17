"""Serializers for WordPress Products and Plugin Targets."""
from rest_framework import serializers
from apps.core.validators import validate_safe_json_object
from .enums import B2_WRITABLE_PRODUCT_KINDS, ProductKind
from .models import PluginTarget, WordPressProduct
from .services import create_plugin_product


class PluginTargetSerializer(serializers.ModelSerializer):
    """Serializer for plugin target details."""

    class Meta:
        model = PluginTarget
        fields = [
            "plugin_slug",
            "text_domain",
            "namespace_prefix",
            "main_file",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class WordPressProductSerializer(serializers.ModelSerializer):
    """Full serializer for WordPressProduct with nested plugin target."""

    organization_id = serializers.UUIDField(source="organization.id", read_only=True)
    created_by_id = serializers.UUIDField(source="created_by.id", read_only=True)
    updated_by_id = serializers.UUIDField(source="updated_by.id", read_only=True)
    plugin_target = PluginTargetSerializer(required=False)

    class Meta:
        model = WordPressProduct
        fields = [
            "id",
            "organization_id",
            "kind",
            "display_name",
            "slug",
            "version",
            "wordpress_version",
            "php_version",
            "metadata",
            "is_archived",
            "plugin_target",
            "created_by_id",
            "updated_by_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "organization_id",
            "slug",
            "created_by_id",
            "updated_by_id",
            "created_at",
            "updated_at",
        ]

    def validate_metadata(self, value):
        validate_safe_json_object(value)
        return value

    def validate_kind(self, value):
        if value not in B2_WRITABLE_PRODUCT_KINDS:
            raise serializers.ValidationError(
                "Only 'PLUGIN' product targets are supported in this milestone.",
                code="unsupported_product_kind",
            )
        return value

    def create(self, validated_data):
        plugin_target_data = validated_data.pop("plugin_target", {}) or {}
        request = self.context.get("request")
        organization = validated_data.pop("organization", None)
        if not organization and request and hasattr(request, "tersuite_organization"):
            organization = request.tersuite_organization

        actor = request.user if request and request.user.is_authenticated else None

        return create_plugin_product(
            organization=organization,
            actor=actor,
            display_name=validated_data.get("display_name"),
            slug=validated_data.get("slug"),
            version=validated_data.get("version", "0.1.0"),
            wordpress_version=validated_data.get("wordpress_version", "6.7"),
            php_version=validated_data.get("php_version", "8.2"),
            metadata=validated_data.get("metadata", {}),
            plugin_slug=plugin_target_data.get("plugin_slug"),
            text_domain=plugin_target_data.get("text_domain"),
            namespace_prefix=plugin_target_data.get("namespace_prefix"),
            main_file=plugin_target_data.get("main_file"),
        )
