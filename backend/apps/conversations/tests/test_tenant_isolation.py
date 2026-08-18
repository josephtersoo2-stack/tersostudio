"""Tenant isolation tests for Conversations and Messages."""
import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient
from apps.conversations.models import Conversation
from apps.organizations.services import ensure_personal_organization
from apps.projects.services import ProjectService

User = get_user_model()


@pytest.mark.django_db
class TestConversationsTenantIsolation:
    """Test suite for conversation tenant boundaries."""

    def setup_method(self):
        self.client = APIClient()
        self.user_a = User.objects.create_user(email="alice@example.com", password="password123")
        self.user_b = User.objects.create_user(email="bob@example.com", password="password123")

        self.org_a = ensure_personal_organization(self.user_a)
        self.org_b = ensure_personal_organization(self.user_b)

        self.proj_a = ProjectService.create_project(
            organization=self.org_a,
            actor=self.user_a,
            name="Alice Project",
        )

        self.conv_a = Conversation.objects.create(
            organization=self.org_a,
            project=self.proj_a,
            title="Alice Conversation",
            created_by=self.user_a,
        )

    def test_cross_tenant_conversation_access_returns_404(self):
        self.client.force_authenticate(user=self.user_b)
        resp = self.client.get(f"/api/v1/conversations/{self.conv_a.id}/")
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_cross_tenant_message_posting_returns_404(self):
        self.client.force_authenticate(user=self.user_b)
        resp = self.client.post(
            f"/api/v1/conversations/{self.conv_a.id}/messages/",
            {"content": "Intrusion attempt"},
            format="json",
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND
