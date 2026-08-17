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
        default=ProjectSitePurpose.DEVELOPMENT,
    )


class ProjectSerializer(serializers.ModelSerializer):
    """Full serializer for Project CRUD operations with product target support."""

    organization_id = serializers.UUIDField(source="organization.id", read_only=True)
    created_by_id = serializers.UUIDField(source="created_by.id", read_only=True)
    updated_by_id = serializers.UUIDField(source="updated_by.id", read_only=True)
    product = WordPressProductSerializer(read_only=True)
    generations_count = serializers.SerializerMethodField()

    # Read-only compatibility aliases
    user_id = serializers.UUIDField(source="created_by.id", read_only=True)
    plugin_slug = serializers.SerializerMethodField()
    wordpress_version = serializers.SerializerMethodField()
    php_version = serializers.SerializerMethodField()

    # Optional write-only compatibility fields for creation
    input_plugin_slug = serializers.CharField(write_only=True, required=False, source="plugin_slug")
    input_wordpress_version = serializers.CharField(write_only=True, required=False, source="wordpress_version")
    input_php_version = serializers.CharField(write_only=True, required=False, source="php_version")

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
            "input_plugin_slug",
            "input_wordpress_version",
            "input_php_version",
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
            "product",
            "plugin_slug",
            "wordpress_version",
            "php_version",
            "generations_count",
            "created_at",
            "updated_at",
        ]

    def validate_metadata(self, value):
        validate_safe_json_object(value)
        return value

    def get_plugin_slug(self, obj) -> str:
        if hasattr(obj, "product") and obj.product and hasattr(obj.product, "plugin_target"):
            return obj.product.plugin_target.plugin_slug
        return ""

    def get_wordpress_version(self, obj) -> str:
        if hasattr(obj, "product") and obj.product:
            return obj.product.wordpress_version
        return "6.7"

    def get_php_version(self, obj) -> str:
        if hasattr(obj, "product") and obj.product:
            return obj.product.php_version
        return "8.2"

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

        plugin_slug = validated_data.pop("plugin_slug", None)
        wp_version = validated_data.pop("wordpress_version", "6.7")
        php_version = validated_data.pop("php_version", "8.2")

        product_payload = {
            "display_name": validated_data.get("name"),
            "plugin_slug": plugin_slug,
            "wordpress_version": wp_version,
            "php_version": php_version,
        }

        return ProjectService.create_project(
            organization=organization,
            actor=actor,
            name=validated_data.get("name"),
            description=validated_data.get("description", ""),
            slug=validated_data.get("slug"),
            product_payload=product_payload,
            metadata=validated_data.get("metadata", {}),
        )
