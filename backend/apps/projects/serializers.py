"""Serializers for the Project and ProjectSite models."""
from rest_framework import serializers

from apps.core.validators import validate_safe_json_object
from apps.products.serializers import WordPressProductSerializer
from .enums import ProjectSitePurpose
from .models import Project, ProjectSite
from .services import ProjectService


class ProjectSiteSerializer(serializers.ModelSerializer):
    """Serializer for ProjectSite associations."""

    organization_id = serializers.UUIDField(source="organization.id", read_only=True)
    project_id = serializers.UUIDField(source="project.id", read_only=True)
    site_id = serializers.UUIDField(source="site.id", read_only=True)
    site_name = serializers.CharField(source="site.name", read_only=True)
    site_url = serializers.CharField(source="site.url", read_only=True)
    created_by_id = serializers.UUIDField(source="created_by.id", read_only=True)

    class Meta:
        model = ProjectSite
        fields = [
            "id",
            "organization_id",
            "project_id",
            "site_id",
            "site_name",
            "site_url",
            "purpose",
            "created_by_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "organization_id",
            "project_id",
            "site_id",
            "site_name",
            "site_url",
            "created_by_id",
            "created_at",
            "updated_at",
        ]


class ProjectSiteCreateSerializer(serializers.Serializer):
    """Payload serializer for linking a site to a project."""

    site_id = serializers.UUIDField()
    purpose = serializers.ChoiceField(
        choices=ProjectSitePurpose.choices,
        default=ProjectSitePurpose.PRIMARY,
    )


class ProjectSerializer(serializers.ModelSerializer):
    """Full serializer for Project CRUD operations with product target support."""

    organization_id = serializers.UUIDField(source="organization.id", read_only=True)
    created_by_id = serializers.UUIDField(source="created_by.id", read_only=True)
    updated_by_id = serializers.UUIDField(source="updated_by.id", read_only=True)
    user_id = serializers.UUIDField(source="created_by.id", read_only=True)
    product = WordPressProductSerializer(required=False)
    generations_count = serializers.SerializerMethodField()

    # Legacy compatibility input/output fields
    plugin_slug = serializers.CharField(required=False, allow_blank=True)
    wordpress_version = serializers.CharField(required=False, default="6.7")
    php_version = serializers.CharField(required=False, default="8.2")

    class Meta:
        model = Project
        fields = [
            "id",
            "organization_id",
            "user_id",
            "created_by_id",
            "updated_by_id",
            "name",
            "slug",
            "description",
            "product",
            "plugin_slug",
            "wordpress_version",
            "php_version",
            "metadata",
            "is_archived",
            "generations_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "organization_id",
            "user_id",
            "created_by_id",
            "updated_by_id",
            "slug",
            "generations_count",
            "created_at",
            "updated_at",
        ]

    def validate_metadata(self, value):
        validate_safe_json_object(value)
        return value

    def validate(self, attrs):
        product_data = attrs.get("product")
        plugin_slug = attrs.get("plugin_slug")
        wp_ver = attrs.get("wordpress_version")
        php_ver = attrs.get("php_version")

        if product_data and isinstance(product_data, dict):
            pt_data = product_data.get("plugin_target", {})
            nested_plugin_slug = pt_data.get("plugin_slug") or product_data.get("slug")
            if plugin_slug and nested_plugin_slug and plugin_slug.strip().lower() != nested_plugin_slug.strip().lower():
                raise serializers.ValidationError(
                    "Conflicting plugin_slug values provided in top-level and nested product payload.",
                    code="conflicting_product_fields",
                )
            nested_wp = product_data.get("wordpress_version")
            if wp_ver and nested_wp and wp_ver.strip() != nested_wp.strip():
                raise serializers.ValidationError(
                    "Conflicting wordpress_version values provided in top-level and nested product payload.",
                    code="conflicting_product_fields",
                )
            nested_php = product_data.get("php_version")
            if php_ver and nested_php and php_ver.strip() != nested_php.strip():
                raise serializers.ValidationError(
                    "Conflicting php_version values provided in top-level and nested product payload.",
                    code="conflicting_product_fields",
                )

        return attrs

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret["plugin_slug"] = instance.plugin_slug
        ret["wordpress_version"] = instance.wordpress_version
        ret["php_version"] = instance.php_version
        return ret

    def get_generations_count(self, obj) -> int:
        if hasattr(obj, "generations_count_annotated"):
            return obj.generations_count_annotated
        if hasattr(obj, "generations"):
            return obj.generations.count()
        return 0

    def create(self, validated_data):
        request = self.context.get("request")
        organization = validated_data.pop("organization", None)
        if not organization and request and hasattr(request, "tersuite_organization"):
            organization = request.tersuite_organization

        actor = request.user if request and request.user.is_authenticated else None
        product_data = validated_data.pop("product", None)

        return ProjectService.create_project(
            organization=organization,
            actor=actor,
            name=validated_data.get("name"),
            description=validated_data.get("description", ""),
            slug=validated_data.get("slug"),
            product_payload=product_data,
            metadata=validated_data.get("metadata", {}),
            plugin_slug=validated_data.get("plugin_slug"),
            wordpress_version=validated_data.get("wordpress_version", "6.7"),
            php_version=validated_data.get("php_version", "8.2"),
            is_archived=validated_data.get("is_archived", False),
        )

    def update(self, instance, validated_data):
        request = self.context.get("request")
        actor = request.user if request and request.user.is_authenticated else None
        product_data = validated_data.pop("product", None)

        return ProjectService.update_project(
            project=instance,
            actor=actor,
            name=validated_data.get("name"),
            description=validated_data.get("description"),
            metadata=validated_data.get("metadata"),
            product_payload=product_data,
            plugin_slug=validated_data.get("plugin_slug"),
            wordpress_version=validated_data.get("wordpress_version"),
            php_version=validated_data.get("php_version"),
        )
