"""API tests for Conversation endpoints."""
import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient
from apps.conversations.models import Conversation
from apps.organizations.services import ensure_personal_organization
from apps.projects.services import ProjectService

User = get_user_model()


@pytest.mark.django_db
class TestConversationAPI:
    """Test suite for conversation REST endpoints."""

    def setup_method(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email="dev@example.com", password="password123")
        self.org = ensure_personal_organization(self.user)
        self.project = ProjectService.create_project(
            organization=self.org,
            actor=self.user,
            name="Plugin Project",
        )
        self.client.force_authenticate(user=self.user)

    def test_create_and_retrieve_conversation(self):
        payload = {
            "project_id": str(self.project.id),
            "title": "Architecture Discussions",
            "purpose": "PROJECT_PLANNING",
        }

        resp = self.client.post("/api/v1/conversations/", payload, format="json")
        assert resp.status_code == status.HTTP_201_CREATED
        data = resp.json()
        assert data["title"] == "Architecture Discussions"
        assert data["purpose"] == "PROJECT_PLANNING"
        assert data["project_id"] == str(self.project.id)

        conv_id = data["id"]
        get_resp = self.client.get(f"/api/v1/conversations/{conv_id}/")
        assert get_resp.status_code == status.HTTP_200_OK
        assert get_resp.json()["id"] == conv_id

    def test_archive_conversation_action(self):
        conv = Conversation.objects.create(
            organization=self.org,
            project=self.project,
            title="Old Chat",
            created_by=self.user,
        )

        resp = self.client.post(f"/api/v1/conversations/{conv.id}/archive/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["status"] == "ARCHIVED"
