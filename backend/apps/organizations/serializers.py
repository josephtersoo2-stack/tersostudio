"""Serializers for Organization and Membership endpoints."""
from rest_framework import serializers
from apps.core.validators import validate_safe_json_object
from .enums import OrganizationRole
from .models import Organization, OrganizationMembership


class OrganizationSerializer(serializers.ModelSerializer):
    """Full detail representation of an Organization."""

    created_by_id = serializers.UUIDField(source="created_by.id", read_only=True)
    updated_by_id = serializers.UUIDField(source="updated_by.id", read_only=True)

    class Meta:
        model = Organization
        fields = [
            "id",
            "name",
            "slug",
            "is_personal",
            "is_active",
            "metadata",
            "created_by_id",
            "updated_by_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "slug",
            "is_personal",
            "is_active",
            "created_by_id",
            "updated_by_id",
            "created_at",
            "updated_at",
        ]

    def validate_metadata(self, value):
        validate_safe_json_object(value)
        return value


class OrganizationCreateSerializer(serializers.Serializer):
    """Payload serializer for creating a new non-personal Organization."""

    name = serializers.CharField(max_length=255)
    metadata = serializers.JSONField(required=False, default=dict)

    def validate_metadata(self, value):
        validate_safe_json_object(value)
        return value


class OrganizationMembershipSerializer(serializers.ModelSerializer):
    """Serializer for organization member listings and details."""

    organization_id = serializers.UUIDField(source="organization.id", read_only=True)
    user_id = serializers.UUIDField(source="user.id", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    full_name = serializers.CharField(source="user.full_name", read_only=True)
    created_by_id = serializers.UUIDField(source="created_by.id", read_only=True)

    class Meta:
        model = OrganizationMembership
        fields = [
            "id",
            "organization_id",
            "user_id",
            "email",
            "full_name",
            "role",
            "is_active",
            "created_by_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "organization_id",
            "user_id",
            "email",
            "full_name",
            "created_by_id",
            "created_at",
            "updated_at",
        ]


class MembershipCreateSerializer(serializers.Serializer):
    """Payload serializer for adding an existing registered user to an organization."""

    email = serializers.EmailField()
    role = serializers.ChoiceField(
        choices=OrganizationRole.choices,
        default=OrganizationRole.MEMBER,
    )

    def validate_email(self, value):
        return value.lower().strip()


class MembershipRoleSerializer(serializers.Serializer):
    """Payload serializer for updating an existing member's role."""

    role = serializers.ChoiceField(choices=OrganizationRole.choices)
