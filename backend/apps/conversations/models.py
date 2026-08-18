"""Data models for Project Conversations and Messages."""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from apps.core.models import OrganizationOwnedModel, TimeStampedModel
from apps.core.validators import validate_safe_json_object
from .enums import ConversationPurpose, ConversationStatus, MessageFormat, MessageRole


class Conversation(OrganizationOwnedModel):
    """Represents a threaded discussion for requirements, planning, or general inquiry in a project."""

    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="conversations",
        db_index=True,
        help_text="Parent project for this conversation.",
    )
    title = models.CharField(
        max_length=255,
        help_text="Topic or human-readable title of the conversation.",
    )
    purpose = models.CharField(
        max_length=30,
        choices=ConversationPurpose.choices,
        default=ConversationPurpose.PROJECT_DISCOVERY,
        db_index=True,
        help_text="Functional purpose of the conversation.",
    )
    status = models.CharField(
        max_length=20,
        choices=ConversationStatus.choices,
        default=ConversationStatus.ACTIVE,
        db_index=True,
        help_text="Active or archived status.",
    )
    next_message_sequence = models.PositiveBigIntegerField(
        default=1,
        help_text="Monotonically increasing sequence index for next message.",
    )
    last_message_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Timestamp when the most recent message was added.",
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        validators=[validate_safe_json_object],
        help_text="Safe metadata and conversation tags.",
    )

    class Meta:
        verbose_name = "Conversation"
        verbose_name_plural = "Conversations"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["organization", "project", "status"],
                name="conversatio_organiz_e1ff9e_idx",
            ),
        ]

    def clean(self) -> None:
        super().clean()
        if self.project and self.organization_id != self.project.organization_id:
            raise ValidationError(
                "Conversation organization must match project organization.",
                code="organization_mismatch",
            )

    def __str__(self) -> str:
        return f"{self.title} ({self.project.name})"


class ConversationMessage(TimeStampedModel):
    """An individual ordered message within a conversation."""

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.PROTECT,
        related_name="conversation_messages",
        db_index=True,
        help_text="Tenant organization owning the message.",
    )
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
        db_index=True,
        help_text="Parent conversation containing this message.",
    )
    sequence = models.PositiveBigIntegerField(
        help_text="Deterministic 1-indexed order within the conversation.",
    )
    role = models.CharField(
        max_length=20,
        choices=MessageRole.choices,
        default=MessageRole.USER,
        db_index=True,
        help_text="Author role tier.",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="conversation_messages",
        help_text="User who authored this message (if role is USER).",
    )
    content = models.TextField(
        help_text="Body content of the message.",
    )
    content_format = models.CharField(
        max_length=20,
        choices=MessageFormat.choices,
        default=MessageFormat.MARKDOWN,
        help_text="Content serialization format.",
    )
    client_message_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="Client-supplied idempotency key (UUIDv4).",
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        validators=[validate_safe_json_object],
        help_text="Safe structured metadata (attachments, UI flags).",
    )

    class Meta:
        verbose_name = "Conversation Message"
        verbose_name_plural = "Conversation Messages"
        ordering = ["sequence", "created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["conversation", "sequence"],
                name="unique_conversation_sequence",
            ),
            models.UniqueConstraint(
                fields=["conversation", "client_message_id"],
                condition=models.Q(client_message_id__isnull=False),
                name="unique_conversation_client_message_id",
            ),
        ]
        indexes = [
            models.Index(
                fields=["organization", "conversation", "sequence"],
                name="conversatio_organiz_57f66a_idx",
            ),
        ]

    def clean(self) -> None:
        super().clean()
        if self.conversation and self.organization_id != self.conversation.organization_id:
            raise ValidationError(
                "Message organization must match conversation organization.",
                code="organization_mismatch",
            )

    def __str__(self) -> str:
        return f"{self.conversation.title} #{self.sequence} ({self.role})"
