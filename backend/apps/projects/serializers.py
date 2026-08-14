"""Serializers for the Project model."""
from rest_framework import serializers
from .models import Project


class ProjectSerializer(serializers.ModelSerializer):
    """Full serializer for Project CRUD operations."""

    user_id = serializers.UUIDField(source="user.id", read_only=True)
    generations_count = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            "id",
            "user_id",
            "name",
            "slug",
            "description",
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
            "user_id",
            "slug",
            "generations_count",
            "created_at",
            "updated_at",
        ]

    def get_generations_count(self, obj) -> int:
        if hasattr(obj, "generations_count_annotated"):
            return obj.generations_count_annotated
        if hasattr(obj, "generations"):
            return obj.generations.count()
        return 0

    def create(self, validated_data):
        """Bind project to the authenticated request user."""
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data["user"] = request.user
        return super().create(validated_data)
