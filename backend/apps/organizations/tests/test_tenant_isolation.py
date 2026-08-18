"""Tenant isolation and access control tests for organizations."""
import uuid
import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient
from apps.organizations.enums import OrganizationRole
from apps.organizations.models import Organization, OrganizationMembership
from apps.organizations.services import ensure_personal_organization

User = get_user_model()


@pytest.mark.django_db
class TestOrganizationTenantIsolation:
    """Test suite for organization boundaries and access enforcement."""

    def setup_method(self):
        self.client = APIClient()
        self.user_a = User.objects.create_user(email="alice@example.com", password="password123")
        self.user_b = User.objects.create_user(email="bob@example.com", password="password123")

        self.org_a = ensure_personal_organization(self.user_a)
        self.org_b = ensure_personal_organization(self.user_b)

    def test_user_cannot_access_unaffiliated_organization(self):
        self.client.force_authenticate(user=self.user_a)
        resp = self.client.get(f"/api/v1/organizations/{self.org_b.id}/")
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_user_cannot_list_members_of_unaffiliated_organization(self):
        self.client.force_authenticate(user=self.user_a)
        resp = self.client.get(f"/api/v1/organizations/{self.org_b.id}/members/")
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_user_cannot_mutate_unaffiliated_organization(self):
        self.client.force_authenticate(user=self.user_a)
        resp = self.client.patch(
            f"/api/v1/organizations/{self.org_b.id}/",
            {"name": "Hacked Name"},
            format="json",
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_mismatched_header_and_path_returns_404(self):
        self.client.force_authenticate(user=self.user_a)
        # Pass header for org_a but request org_b path
        resp = self.client.get(
            f"/api/v1/organizations/{self.org_b.id}/",
            HTTP_X_TERSUITE_ORGANIZATION_ID=str(self.org_a.id),
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND
