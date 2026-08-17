"""Tenant isolation tests for WordPress Sites and Snapshots."""
import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient
from apps.organizations.services import ensure_personal_organization
from apps.sites.models import WordPressSite

User = get_user_model()


@pytest.mark.django_db
class TestSitesTenantIsolation:
    """Test suite for site tenant boundaries."""

    def setup_method(self):
        self.client = APIClient()
        self.user_a = User.objects.create_user(email="alice@example.com", password="password123")
        self.user_b = User.objects.create_user(email="bob@example.com", password="password123")

        self.org_a = ensure_personal_organization(self.user_a)
        self.org_b = ensure_personal_organization(self.user_b)

        self.site_a = WordPressSite.objects.create(
            organization=self.org_a,
            name="Alice Site",
            url="https://alice.example.com/",
            created_by=self.user_a,
        )

    def test_cross_tenant_site_access_returns_404(self):
        self.client.force_authenticate(user=self.user_b)
        resp = self.client.get(f"/api/v1/sites/{self.site_a.id}/")
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_cross_tenant_snapshot_access_returns_404(self):
        self.client.force_authenticate(user=self.user_b)
        resp = self.client.get(f"/api/v1/sites/{self.site_a.id}/snapshots/")
        assert resp.status_code == status.HTTP_404_NOT_FOUND
