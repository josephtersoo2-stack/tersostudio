"""Services for managing conversations and deterministic message appending."""
import uuid
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.core.validators import validate_safe_json_object
from .enums import ConversationStatus, MessageFormat, MessageRole
from .models import Conversation, ConversationMessage


class ConversationMessageService:
    """Service handling ordered and idempotent message insertion."""

    @staticmethod
    def append_user_message(
        conversation: Conversation,
        author,
        content: str,
        client_message_id=None,
        content_format: str = MessageFormat.MARKDOWN,
        metadata: dict | None = None,
    ) -> tuple[ConversationMessage, bool]:
        """Append a user message to a conversation with idempotency support.

        Returns (message, created) tuple.
        """
        if conversation.status == ConversationStatus.ARCHIVED:
            raise ValidationError(
                "Cannot append messages to an archived conversation.",
                code="archived_conversation_locked",
            )

        if not content or not content.strip():
            raise ValidationError("Message content cannot be empty.", code="empty_content")

        if len(content) > 100000:
            raise ValidationError("Message content exceeds 100,000 characters limit.", code="content_too_long")

        safe_metadata = metadata or {}
        validate_safe_json_object(safe_metadata, max_bytes=16384)

        parsed_client_id = None
        if client_message_id:
            if isinstance(client_message_id, uuid.UUID):
                parsed_client_id = client_message_id
            elif isinstance(client_message_id, str) and client_message_id.strip():
                try:
                    parsed_client_id = uuid.UUID(client_message_id.strip())
                except ValueError as exc:
                    raise ValidationError("Invalid client_message_id UUID format.", code="invalid_uuid") from exc

        with transaction.atomic():
            # Check idempotency before locking
            if parsed_client_id:
                existing = ConversationMessage.objects.filter(
                    conversation=conversation,
                    client_message_id=parsed_client_id,
                ).first()
                if existing:
                    return existing, False

            # Lock the conversation record to guarantee strict sequential ordering
            locked_conv = Conversation.objects.select_for_update().get(id=conversation.id)

            if locked_conv.status == ConversationStatus.ARCHIVED:
                raise ValidationError(
                    "Cannot append messages to an archived conversation.",
                    code="archived_conversation_locked",
                )

            # Re-check idempotency under lock
            if parsed_client_id:
                existing = ConversationMessage.objects.filter(
                    conversation=locked_conv,
                    client_message_id=parsed_client_id,
                ).first()
                if existing:
                    return existing, False

            current_sequence = locked_conv.next_message_sequence

            message = ConversationMessage.objects.create(
                organization=locked_conv.organization,
                conversation=locked_conv,
                sequence=current_sequence,
                role=MessageRole.USER,
                author=author,
                content=content.strip(),
                content_format=content_format,
                client_message_id=parsed_client_id,
                metadata=safe_metadata,
            )

            locked_conv.next_message_sequence = current_sequence + 1
            locked_conv.last_message_at = timezone.now()
            locked_conv.save(update_fields=["next_message_sequence", "last_message_at", "updated_at"])

            return message, True

    @staticmethod
    def append_internal_message(
        conversation: Conversation,
        role: str,
        content: str,
        author=None,
        content_format: str = MessageFormat.MARKDOWN,
        metadata: dict | None = None,
        client_message_id=None,
    ) -> tuple[ConversationMessage, bool]:
        """Append an internal/system/assistant message to a conversation."""
        if role == MessageRole.USER:
            raise ValidationError("Internal message role cannot be USER.", code="invalid_internal_role")

        if conversation.status == ConversationStatus.ARCHIVED:
            raise ValidationError(
                "Cannot append messages to an archived conversation.",
                code="archived_conversation_locked",
            )

        if not content or not content.strip():
            raise ValidationError("Message content cannot be empty.", code="empty_content")

        safe_metadata = metadata or {}
        validate_safe_json_object(safe_metadata)

        parsed_client_id = None
        if client_message_id:
            if isinstance(client_message_id, uuid.UUID):
                parsed_client_id = client_message_id
            elif isinstance(client_message_id, str) and client_message_id.strip():
                parsed_client_id = uuid.UUID(client_message_id.strip())

        with transaction.atomic():
            if parsed_client_id:
                existing = ConversationMessage.objects.filter(
                    conversation=conversation,
                    client_message_id=parsed_client_id,
                ).first()
                if existing:
                    return existing, False

            locked_conv = Conversation.objects.select_for_update().get(id=conversation.id)

            if locked_conv.status == ConversationStatus.ARCHIVED:
                raise ValidationError(
                    "Cannot append messages to an archived conversation.",
                    code="archived_conversation_locked",
                )

            if parsed_client_id:
                existing = ConversationMessage.objects.filter(
                    conversation=locked_conv,
                    client_message_id=parsed_client_id,
                ).first()
                if existing:
                    return existing, False

            current_sequence = locked_conv.next_message_sequence

            message = ConversationMessage.objects.create(
                organization=locked_conv.organization,
                conversation=locked_conv,
                sequence=current_sequence,
                role=role,
                author=author,
                content=content.strip(),
                content_format=content_format,
                client_message_id=parsed_client_id,
                metadata=safe_metadata,
            )

            locked_conv.next_message_sequence = current_sequence + 1
            locked_conv.last_message_at = timezone.now()
            locked_conv.save(update_fields=["next_message_sequence", "last_message_at", "updated_at"])

            return message, True

    @staticmethod
    def archive_conversation(conversation: Conversation, actor) -> Conversation:
        """Archive a conversation to prevent further message posting (idempotent)."""
        with transaction.atomic():
            locked_conv = Conversation.objects.select_for_update().get(id=conversation.id)
            if locked_conv.status != ConversationStatus.ARCHIVED:
                locked_conv.status = ConversationStatus.ARCHIVED
                locked_conv.updated_by = actor
                locked_conv.save(update_fields=["status", "updated_by", "updated_at"])
            return locked_conv
