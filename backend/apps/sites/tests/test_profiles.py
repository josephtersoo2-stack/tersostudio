"""API tests for site profile snapshots."""
import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient
from apps.organizations.services import ensure_personal_organization
from apps.sites.models import WordPressSite

User = get_user_model()


@pytest.mark.django_db
class TestSiteProfilesAPI:
    """Test suite for snapshot creation and read-only inspection."""

    def setup_method(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email="dev@example.com", password="password123")
        self.org = ensure_personal_organization(self.user)
        self.site = WordPressSite.objects.create(
            organization=self.org,
            name="Testing Site",
            url="https://test.example.com/",
            created_by=self.user,
        )
        self.client.force_authenticate(user=self.user)

    def test_record_snapshot_via_site_action(self):
        payload = {
            "wordpress_version": "6.7",
            "php_version": "8.3",
            "multisite": False,
            "locale": "en_US",
            "timezone": "America/New_York",
            "active_theme": {"name": "Astra", "version": "4.5.0"},
            "active_plugins": [{"slug": "contact-form-7", "version": "5.9"}],
        }

        resp = self.client.post(f"/api/v1/sites/{self.site.id}/snapshots/", payload, format="json")
        assert resp.status_code == status.HTTP_201_CREATED
        data = resp.json()
        assert data["version"] == 1
        assert data["wordpress_version"] == "6.7"
        assert len(data["checksum_sha256"]) == 64

        list_resp = self.client.get(f"/api/v1/sites/{self.site.id}/snapshots/")
        assert list_resp.status_code == status.HTTP_200_OK
        assert len(list_resp.json()) == 1

    def test_snapshot_viewset_is_read_only(self):
        # Global snapshots endpoint supports GET
        resp = self.client.get("/api/v1/sites/snapshots/")
        assert resp.status_code == status.HTTP_200_OK

        # POST / PUT / PATCH / DELETE on snapshots viewset return 405 Method Not Allowed
        post_resp = self.client.post("/api/v1/sites/snapshots/", {"wordpress_version": "6.7"}, format="json")
        assert post_resp.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
