"""Tests for client message idempotency."""
import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient
from apps.conversations.models import Conversation, ConversationMessage
from apps.organizations.services import ensure_personal_organization
from apps.projects.services import ProjectService

User = get_user_model()


@pytest.mark.django_db
class TestMessageIdempotency:
    """Test suite for client_message_id idempotency."""

    def setup_method(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email="dev@example.com", password="password123")
        self.org = ensure_personal_organization(self.user)
        self.project = ProjectService.create_project(
            organization=self.org,
            actor=self.user,
            name="Chat Project",
        )
        self.conv = Conversation.objects.create(
            organization=self.org,
            project=self.project,
            title="Idempotency Test Thread",
            created_by=self.user,
        )
        self.client.force_authenticate(user=self.user)

    def test_duplicate_client_message_id_returns_same_row_and_status_200(self):
        payload = {
            "content": "Deploy changes now.",
            "client_message_id": "client-msg-uuid-12345",
        }

        # First post -> 201 Created
        resp1 = self.client.post(f"/api/v1/conversations/{self.conv.id}/messages/", payload, format="json")
        assert resp1.status_code == status.HTTP_201_CREATED
        msg1_id = resp1.json()["id"]
        assert resp1.json()["sequence"] == 1

        # Second post with identical client_message_id -> 200 OK, same ID, sequence not incremented
        resp2 = self.client.post(f"/api/v1/conversations/{self.conv.id}/messages/", payload, format="json")
        assert resp2.status_code == status.HTTP_200_OK
        assert resp2.json()["id"] == msg1_id
        assert resp2.json()["sequence"] == 1

        # Database contains exactly 1 message
        assert ConversationMessage.objects.filter(conversation=self.conv).count() == 1

        # Next new message gets sequence 2
        resp3 = self.client.post(
            f"/api/v1/conversations/{self.conv.id}/messages/",
            {"content": "New message", "client_message_id": "client-msg-uuid-67890"},
            format="json",
        )
        assert resp3.status_code == status.HTTP_201_CREATED
        assert resp3.json()["sequence"] == 2
