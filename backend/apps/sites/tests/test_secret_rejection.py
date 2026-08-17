"""Tests verifying rejection of secret keys in site and snapshot payloads."""
import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient
from apps.organizations.services import ensure_personal_organization
from apps.sites.models import WordPressSite

User = get_user_model()


@pytest.mark.django_db
class TestSecretRejection:
    """Test suite for secret rejection in Sites."""

    def setup_method(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email="dev@example.com", password="password123")
        self.org = ensure_personal_organization(self.user)
        self.site = WordPressSite.objects.create(
            organization=self.org,
            name="Secure Site",
            url="https://sec.example.com/",
            created_by=self.user,
        )
        self.client.force_authenticate(user=self.user)

    def test_site_metadata_rejects_credentials(self):
        payload = {
            "name": "Leaky Site",
            "url": "https://leaky.example.com/",
            "metadata": {"api_key": "secret-value"},
        }
        resp = self.client.post("/api/v1/sites/", payload, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        err = resp.json()["error"]
        assert "api_key" in str(err)
        # Secret value must not be echoed
        assert "secret-value" not in str(err)

    def test_snapshot_rejects_credentials(self):
        payload = {
            "wordpress_version": "6.7",
            "server": {"database_url": "postgres://user:pass@localhost:5432/db"},
        }
        resp = self.client.post(f"/api/v1/sites/{self.site.id}/snapshots/", payload, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        err = resp.json()["error"]
        assert "database_url" in str(err)
        assert "postgres://" not in str(err)
