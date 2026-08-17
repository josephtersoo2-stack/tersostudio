"""Tests for Project-Site associations and attachment actions."""
import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient
from apps.organizations.services import ensure_personal_organization
from apps.projects.services import ProjectService
from apps.sites.models import WordPressSite

User = get_user_model()


@pytest.mark.django_db
class TestProjectSitesAPI:
    """Test suite for project site linking."""

    def setup_method(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email="admin@example.com", password="password123")
        self.org = ensure_personal_organization(self.user)
        self.project = ProjectService.create_project(
            organization=self.org,
            actor=self.user,
            name="E-Commerce Extension",
        )
        self.site = WordPressSite.objects.create(
            organization=self.org,
            name="Staging Store",
            url="https://staging.store.example.com/",
            created_by=self.user,
        )
        self.client.force_authenticate(user=self.user)

    def test_attach_site_to_project(self):
        payload = {
            "site_id": str(self.site.id),
            "purpose": "STAGING",
        }
        resp = self.client.post(f"/api/v1/projects/{self.project.id}/sites/", payload, format="json")
        assert resp.status_code == status.HTTP_201_CREATED
        data = resp.json()
        assert data["project_id"] == str(self.project.id)
        assert data["site_id"] == str(self.site.id)
        assert data["purpose"] == "STAGING"

        list_resp = self.client.get(f"/api/v1/projects/{self.project.id}/sites/")
        assert list_resp.status_code == status.HTTP_200_OK
        assert len(list_resp.json()) == 1

    def test_detach_site_from_project(self):
        ProjectService.add_site_to_project(
            project=self.project,
            site=self.site,
            actor=self.user,
            purpose="DEVELOPMENT",
        )

        del_resp = self.client.delete(f"/api/v1/projects/{self.project.id}/sites/{self.site.id}/")
        assert del_resp.status_code == status.HTTP_204_NO_CONTENT

        list_resp = self.client.get(f"/api/v1/projects/{self.project.id}/sites/")
        assert list_resp.status_code == status.HTTP_200_OK
        assert len(list_resp.json()) == 0

    def test_cross_tenant_site_attachment_rejected(self):
        other_user = User.objects.create_user(email="other@example.com", password="password123")
        other_org = ensure_personal_organization(other_user)
        foreign_site = WordPressSite.objects.create(
            organization=other_org,
            name="Foreign Site",
            url="https://foreign.example.com/",
            created_by=other_user,
        )

        payload = {"site_id": str(foreign_site.id)}
        resp = self.client.post(f"/api/v1/projects/{self.project.id}/sites/", payload, format="json")
        assert resp.status_code == status.HTTP_404_NOT_FOUND
