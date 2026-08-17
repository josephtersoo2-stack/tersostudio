"""API tests for WordPress Sites endpoints."""
import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient
from apps.organizations.services import ensure_personal_organization
from apps.sites.models import WordPressSite

User = get_user_model()


@pytest.mark.django_db
class TestSiteAPI:
    """Test suite for site REST endpoints."""

    def setup_method(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email="siteadmin@example.com", password="password123")
        self.org = ensure_personal_organization(self.user)
        self.client.force_authenticate(user=self.user)

    def test_create_and_retrieve_site(self):
        payload = {
            "name": "Corporate Portal",
            "url": "https://PORTAL.EXAMPLE.COM:443/wp/",
            "environment": "PRODUCTION",
            "metadata": {"hosting": "aws"},
        }

        resp = self.client.post("/api/v1/sites/", payload, format="json")
        assert resp.status_code == status.HTTP_201_CREATED
        data = resp.json()
        assert data["name"] == "Corporate Portal"
        # URL normalized
        assert data["url"] == "https://portal.example.com/wp/"
        assert data["connection_status"] == "UNVERIFIED"

        site_id = data["id"]
        get_resp = self.client.get(f"/api/v1/sites/{site_id}/")
        assert get_resp.status_code == status.HTTP_200_OK
        assert get_resp.json()["id"] == site_id

    def test_cannot_forge_connected_status(self):
        payload = {
            "name": "Spoofed Site",
            "url": "https://example.com/",
            "connection_status": "CONNECTED",
        }

        resp = self.client.post("/api/v1/sites/", payload, format="json")
        assert resp.status_code == status.HTTP_201_CREATED
        # Read-only field ignores incoming CONNECTED and stays UNVERIFIED
        assert resp.json()["connection_status"] == "UNVERIFIED"
