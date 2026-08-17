"""Services for managing conversations and deterministic message appending."""
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
        client_message_id: str | None = None,
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

        safe_metadata = metadata or {}
        validate_safe_json_object(safe_metadata)

        clean_client_id = (client_message_id or "").strip()

        with transaction.atomic():
            # Check idempotency before locking
            if clean_client_id:
                existing = ConversationMessage.objects.filter(
                    conversation=conversation,
                    client_message_id=clean_client_id,
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
            if clean_client_id:
                existing = ConversationMessage.objects.filter(
                    conversation=locked_conv,
                    client_message_id=clean_client_id,
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
                client_message_id=clean_client_id,
                metadata=safe_metadata,
            )

            locked_conv.next_message_sequence = current_sequence + 1
            locked_conv.last_message_at = timezone.now()
            locked_conv.save(update_fields=["next_message_sequence", "last_message_at", "updated_at"])

            return message, True

    @staticmethod
    def archive_conversation(conversation: Conversation, actor) -> Conversation:
        """Archive a conversation to prevent further message posting."""
        with transaction.atomic():
            conversation.status = ConversationStatus.ARCHIVED
            conversation.updated_by = actor
            conversation.save(update_fields=["status", "updated_by", "updated_at"])
            return conversation
