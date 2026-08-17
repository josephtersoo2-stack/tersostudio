"""Serializers for Conversations and Messages."""
from rest_framework import serializers
from apps.core.validators import validate_safe_json_object
from .enums import ConversationPurpose, ConversationStatus, MessageFormat, MessageRole
from .models import Conversation, ConversationMessage


class ConversationMessageSerializer(serializers.ModelSerializer):
    """Full representation of an immutable ConversationMessage."""

    organization_id = serializers.UUIDField(source="organization.id", read_only=True)
    conversation_id = serializers.UUIDField(source="conversation.id", read_only=True)
    author_id = serializers.UUIDField(source="author.id", read_only=True)
    author_email = serializers.EmailField(source="author.email", read_only=True)

    class Meta:
        model = ConversationMessage
        fields = [
            "id",
            "organization_id",
            "conversation_id",
            "sequence",
            "role",
            "author_id",
            "author_email",
            "content",
            "content_format",
            "client_message_id",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class ConversationMessageCreateSerializer(serializers.Serializer):
    """Payload serializer for posting a new user message to a conversation."""

    content = serializers.CharField()
    client_message_id = serializers.CharField(max_length=64, required=False, allow_blank=True, default="")
    content_format = serializers.ChoiceField(
        choices=MessageFormat.choices,
        default=MessageFormat.MARKDOWN,
    )
    metadata = serializers.JSONField(required=False, default=dict)

    def validate_metadata(self, value):
        validate_safe_json_object(value)
        return value


class ConversationSerializer(serializers.ModelSerializer):
    """Full serializer for Conversation metadata."""

    organization_id = serializers.UUIDField(source="organization.id", read_only=True)
    project_id = serializers.UUIDField(required=True)
    created_by_id = serializers.UUIDField(source="created_by.id", read_only=True)
    updated_by_id = serializers.UUIDField(source="updated_by.id", read_only=True)

    class Meta:
        model = Conversation
        fields = [
            "id",
            "organization_id",
            "project_id",
            "title",
            "purpose",
            "status",
            "next_message_sequence",
            "last_message_at",
            "metadata",
            "created_by_id",
            "updated_by_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "organization_id",
            "status",
            "next_message_sequence",
            "last_message_at",
            "created_by_id",
            "updated_by_id",
            "created_at",
            "updated_at",
        ]

    def validate_metadata(self, value):
        validate_safe_json_object(value)
        return value
