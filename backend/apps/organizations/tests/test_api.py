"""API tests for Organization CRUD and membership endpoints."""
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
class TestOrganizationAPI:
    """Test suite for organization REST endpoints."""

    def setup_method(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email="owner@example.com", password="password123")
        self.org = ensure_personal_organization(self.user)
        self.client.force_authenticate(user=self.user)

    def test_list_organizations(self):
        resp = self.client.get("/api/v1/organizations/")
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert len(data) == 1
        assert data[0]["id"] == str(self.org.id)

    def test_create_organization(self):
        payload = {"name": "Engineering Team", "metadata": {"tier": "enterprise"}}
        resp = self.client.post("/api/v1/organizations/", payload, format="json")
        assert resp.status_code == status.HTTP_201_CREATED
        data = resp.json()
        assert data["name"] == "Engineering Team"
        assert data["is_personal"] is False
        assert data["slug"] == "engineering-team"

        # Owner membership auto-created
        created_org = Organization.objects.get(id=data["id"])
        mem = OrganizationMembership.objects.get(organization=created_org, user=self.user)
        assert mem.role == OrganizationRole.OWNER

    def test_retrieve_organization(self):
        resp = self.client.get(f"/api/v1/organizations/{self.org.id}/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["id"] == str(self.org.id)

    def test_update_organization(self):
        resp = self.client.patch(
            f"/api/v1/organizations/{self.org.id}/",
            {"name": "Updated Org Name"},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["name"] == "Updated Org Name"

    def test_add_and_list_members(self):
        other_user = User.objects.create_user(email="developer@example.com", password="password123")

        resp = self.client.post(
            f"/api/v1/organizations/{self.org.id}/members/",
            {"email": "developer@example.com", "role": "MEMBER"},
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.json()["email"] == "developer@example.com"
        assert resp.json()["role"] == "MEMBER"

        list_resp = self.client.get(f"/api/v1/organizations/{self.org.id}/members/")
        assert list_resp.status_code == status.HTTP_200_OK
        assert len(list_resp.json()) == 2

    def test_change_role_and_remove_member(self):
        other_user = User.objects.create_user(email="developer@example.com", password="password123")
        membership = OrganizationMembership.objects.create(
            organization=self.org,
            user=other_user,
            role=OrganizationRole.MEMBER,
            is_active=True,
        )

        patch_resp = self.client.patch(
            f"/api/v1/organizations/{self.org.id}/members/{membership.id}/",
            {"role": "ADMIN"},
            format="json",
        )
        assert patch_resp.status_code == status.HTTP_200_OK
        assert patch_resp.json()["role"] == "ADMIN"

        del_resp = self.client.delete(f"/api/v1/organizations/{self.org.id}/members/{membership.id}/")
        assert del_resp.status_code == status.HTTP_204_NO_CONTENT

        membership.refresh_from_db()
        assert membership.is_active is False
