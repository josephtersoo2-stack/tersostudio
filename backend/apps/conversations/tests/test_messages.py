"""API tests for conversation messages."""
import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient
from apps.conversations.models import Conversation
from apps.generations.models import AgentRun, Generation
from apps.organizations.services import ensure_personal_organization
from apps.projects.services import ProjectService

User = get_user_model()


@pytest.mark.django_db
class TestConversationMessagesAPI:
    """Test suite for message creation, ordering, and agent decoupling."""

    def setup_method(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email="dev@example.com", password="password123")
        self.org = ensure_personal_organization(self.user)
        self.project = ProjectService.create_project(
            organization=self.org,
            actor=self.user,
            name="Plugin Project",
        )
        self.conv = Conversation.objects.create(
            organization=self.org,
            project=self.project,
            title="Chat Thread",
            created_by=self.user,
        )
        self.client.force_authenticate(user=self.user)

    def test_post_message_and_list_ordered(self):
        resp1 = self.client.post(
            f"/api/v1/conversations/{self.conv.id}/messages/",
            {"content": "First message"},
            format="json",
        )
        assert resp1.status_code == status.HTTP_201_CREATED
        assert resp1.json()["sequence"] == 1

        resp2 = self.client.post(
            f"/api/v1/conversations/{self.conv.id}/messages/",
            {"content": "Second message"},
            format="json",
        )
        assert resp2.status_code == status.HTTP_201_CREATED
        assert resp2.json()["sequence"] == 2

        list_resp = self.client.get(f"/api/v1/conversations/{self.conv.id}/messages/")
        assert list_resp.status_code == status.HTTP_200_OK
        data = list_resp.json()
        assert len(data) == 2
        assert data[0]["sequence"] == 1
        assert data[1]["sequence"] == 2

    def test_message_posting_does_not_invoke_agents_or_create_generations(self):
        # Initial counts
        gen_count_before = Generation.objects.count()
        run_count_before = AgentRun.objects.count()

        self.client.post(
            f"/api/v1/conversations/{self.conv.id}/messages/",
            {"content": "Generate a full plugin for me now!"},
            format="json",
        )

        assert Generation.objects.count() == gen_count_before
        assert AgentRun.objects.count() == run_count_before

    def test_messages_viewset_is_read_only(self):
        # Global messages endpoint supports GET
        resp = self.client.get("/api/v1/conversations/messages/")
        assert resp.status_code == status.HTTP_200_OK

        # POST / PUT / PATCH / DELETE on messages endpoint return 405 Method Not Allowed
        post_resp = self.client.post("/api/v1/conversations/messages/", {"content": "Direct"}, format="json")
        assert post_resp.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
