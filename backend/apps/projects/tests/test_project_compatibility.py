"""Compatibility tests ensuring legacy project field aliases behave as single source of truth."""
import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient
from apps.organizations.services import ensure_personal_organization
from apps.projects.services import ProjectService

User = get_user_model()


@pytest.mark.django_db
class TestProjectCompatibility:
    """Test suite for legacy aliases and contract compatibility."""

    def setup_method(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email="dev@example.com", password="password123")
        self.org = ensure_personal_organization(self.user)
        self.client.force_authenticate(user=self.user)

    def test_legacy_read_aliases_sourced_from_product(self):
        project = ProjectService.create_project(
            organization=self.org,
            actor=self.user,
            name="Affiliate Tracker",
            product_payload={
                "plugin_slug": "affiliate-tracker-pro",
                "wordpress_version": "6.6",
                "php_version": "8.1",
            },
        )

        resp = self.client.get(f"/api/v1/projects/{project.id}/")
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()

        # Legacy aliases
        assert data["user_id"] == str(self.user.id)
        assert data["plugin_slug"] == "affiliate-tracker-pro"
        assert data["wordpress_version"] == "6.6"
        assert data["php_version"] == "8.1"
        assert data["product"]["plugin_target"]["plugin_slug"] == "affiliate-tracker-pro"
