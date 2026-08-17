"""Serializers for Accounts and Authentication."""
from django.contrib.auth import authenticate
from django.db import transaction
from rest_framework import serializers

from apps.organizations.services import ensure_personal_organization
from .models import User


class UserOrganizationMembershipSummarySerializer(serializers.Serializer):
    """Lightweight membership summary for user profile."""

    id = serializers.UUIDField(read_only=True)
    organization_id = serializers.UUIDField(source="organization.id", read_only=True)
    organization_name = serializers.CharField(source="organization.name", read_only=True)
    organization_slug = serializers.CharField(source="organization.slug", read_only=True)
    role = serializers.CharField(read_only=True)
    is_personal = serializers.BooleanField(source="organization.is_personal", read_only=True)
    is_active = serializers.BooleanField(read_only=True)


class UserSerializer(serializers.ModelSerializer):
    """Public user profile serializer."""

    full_name = serializers.CharField(read_only=True)
    organization_memberships = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "is_active",
            "is_staff",
            "organization_memberships",
            "date_joined",
            "created_at",
        )
        read_only_fields = ("id", "is_active", "is_staff", "organization_memberships", "date_joined", "created_at")

    def get_organization_memberships(self, obj):
        memberships = obj.organization_memberships.select_related("organization").filter(
            is_active=True,
            organization__is_active=True,
        )
        return UserOrganizationMembershipSummarySerializer(memberships, many=True).data


class RegisterSerializer(serializers.Serializer):
    """User registration serializer with password validation and personal org provisioning."""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    first_name = serializers.CharField(required=False, allow_blank=True, default="")
    last_name = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_email(self, value):
        normalized_email = value.lower().strip()
        if User.objects.filter(email=normalized_email).exists():
            raise serializers.ValidationError("A user with this email address already exists.")
        return normalized_email

    def create(self, validated_data):
        with transaction.atomic():
            user = User.objects.create_user(
                email=validated_data["email"],
                password=validated_data["password"],
                first_name=validated_data.get("first_name", ""),
                last_name=validated_data.get("last_name", ""),
            )
            ensure_personal_organization(user)
            return user


class LoginSerializer(serializers.Serializer):
    """User login credential serializer."""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get("email", "").lower().strip()
        password = attrs.get("password")

        if not email or not password:
            raise serializers.ValidationError("Both email and password are required.")

        user = authenticate(username=email, password=password)
        if not user:
            raise serializers.ValidationError("Invalid email or password.")

        if not user.is_active:
            raise serializers.ValidationError("This user account has been deactivated.")

        attrs["user"] = user
        return attrs
