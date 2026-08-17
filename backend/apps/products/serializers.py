"""Serializers for WordPress Products and Plugin Targets."""
import re
from rest_framework import serializers
from apps.core.validators import validate_safe_json_object
from .enums import B2_WRITABLE_PRODUCT_KINDS
from .models import PluginTarget, WordPressProduct
from .services import update_plugin_product


class PluginTargetSerializer(serializers.ModelSerializer):
    """Serializer for plugin target details."""

    class Meta:
        model = PluginTarget
        fields = [
            "id",
            "plugin_slug",
            "text_domain",
            "namespace_prefix",
            "main_file",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_namespace_prefix(self, value):
        if value and not re.match(r"^[A-Za-z][A-Za-z0-9_]*$", value):
            raise serializers.ValidationError(
                "Namespace prefix must be a valid PHP identifier matching ^[A-Za-z][A-Za-z0-9_]*$.",
                code="invalid_namespace_prefix",
            )
        return value

    def validate_main_file(self, value):
        if value and ("/" in value or "\\" in value or not value.endswith(".php") or len(value) <= 4):
            raise serializers.ValidationError(
                "Main file must be a simple filename ending with .php without directory separators.",
                code="invalid_main_file",
            )
        return value


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
            "is_archived",
            "created_by_id",
            "updated_by_id",
            "created_at",
            "updated_at",
        ]

    def validate_metadata(self, value):
        validate_safe_json_object(value)
        return value

    def validate_kind(self, value):
        if self.instance and self.instance.kind != value:
            raise serializers.ValidationError(
                "Product kind cannot be changed.",
                code="cannot_change_product_kind",
            )
        if value not in B2_WRITABLE_PRODUCT_KINDS:
            raise serializers.ValidationError(
                "Only 'PLUGIN' product targets are supported in this milestone.",
                code="unsupported_product_kind",
            )
        return value

    def update(self, instance, validated_data):
        plugin_target_data = validated_data.pop("plugin_target", None)
        request = self.context.get("request")
        actor = request.user if request and request.user.is_authenticated else None

        pt_kwargs = {}
        if plugin_target_data:
            for k in ("plugin_slug", "text_domain", "namespace_prefix", "main_file"):
                if k in plugin_target_data:
                    pt_kwargs[k] = plugin_target_data[k]

        return update_plugin_product(
            product=instance,
            actor=actor,
            display_name=validated_data.get("display_name"),
            version=validated_data.get("version"),
            wordpress_version=validated_data.get("wordpress_version"),
            php_version=validated_data.get("php_version"),
            metadata=validated_data.get("metadata"),
            **pt_kwargs,
        )
