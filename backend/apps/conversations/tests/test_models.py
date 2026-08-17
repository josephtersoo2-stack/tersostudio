"""Tests for Conversation and ConversationMessage models."""
import pytest
from django.contrib.auth import get_user_model
from apps.conversations.enums import ConversationStatus, MessageRole
from apps.conversations.models import Conversation, ConversationMessage
from apps.conversations.services import ConversationMessageService
from apps.organizations.services import ensure_personal_organization
from apps.projects.services import ProjectService

User = get_user_model()


@pytest.mark.django_db
class TestConversationModels:
    """Test suite for conversation model logic."""

    def setup_method(self):
        self.user = User.objects.create_user(email="dev@example.com", password="password123")
        self.org = ensure_personal_organization(self.user)
        self.project = ProjectService.create_project(
            organization=self.org,
            actor=self.user,
            name="Chat Project",
        )

    def test_create_conversation(self):
        conv = Conversation.objects.create(
            organization=self.org,
            project=self.project,
            title="Discovery Session 1",
            created_by=self.user,
            updated_by=self.user,
        )

        assert conv.status == ConversationStatus.ACTIVE
        assert conv.next_message_sequence == 1
        assert conv.last_message_at is None

    def test_append_message_advances_sequence(self):
        conv = Conversation.objects.create(
            organization=self.org,
            project=self.project,
            title="Discovery Session",
            created_by=self.user,
        )

        msg1, created1 = ConversationMessageService.append_user_message(
            conversation=conv,
            author=self.user,
            content="I need a WooCommerce multi-vendor affiliate plugin.",
        )

        assert created1 is True
        assert msg1.sequence == 1
        assert msg1.role == MessageRole.USER
        assert msg1.author == self.user

        conv.refresh_from_db()
        assert conv.next_message_sequence == 2
        assert conv.last_message_at is not None

        msg2, created2 = ConversationMessageService.append_user_message(
            conversation=conv,
            author=self.user,
            content="It should support 3 commission tiers.",
        )
        assert created2 is True
        assert msg2.sequence == 2
