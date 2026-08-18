"""Tests for Control Center Knowledge Base and Projects endpoints."""
import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from apps.generations.enums import GenerationStatus
from apps.generations.models import Generation
from apps.organizations.services import ensure_personal_organization
from apps.projects.models import Project
from apps.projects.services import ProjectService

User = get_user_model()


@pytest.mark.django_db
class TestControlCenterKnowledgeAndProjectsAPI:
    """Test suite for /api/v1/control-center/knowledge/ and /api/v1/control-center/projects/."""

    @pytest.fixture(autouse=True)
    def setup_fixtures(self):
        self.client = APIClient()

        # Regular customer
        self.customer = User.objects.create_user(
            email="customer.kb@tersuite.com",
            password="CustomerPass123!",
            first_name="Customer",
            last_name="KB",
            is_staff=False,
        )
        self.org = ensure_personal_organization(self.customer)

        # Staff operator
        self.staff_user = User.objects.create_user(
            email="staff.kb@tersuite.com",
            password="StaffPass123!",
            first_name="Staff",
            last_name="Operator",
            is_staff=True,
        )

        # Seed projects
        self.active_project = ProjectService.create_project(
            organization=self.org,
            actor=self.customer,
            name="Active WooCommerce Plugin",
            slug="active-woo-plugin",
            plugin_slug="active-woo-plugin",
            wordpress_version="6.7",
            php_version="8.3",
            is_archived=False,
        )
        self.archived_project = ProjectService.create_project(
            organization=self.org,
            actor=self.customer,
            name="Archived Affiliate Tracker",
            slug="archived-affiliate-tracker",
            plugin_slug="archived-affiliate-tracker",
            is_archived=True,
        )

        # Seed a generation under active project
        Generation.objects.create(
            organization=self.org,
            project=self.active_project,
            created_by=self.customer,
            prompt="Build WooCommerce high performance extension.",
            status=GenerationStatus.BUILDING,
        )


    # 1. Anonymous Access (Expect 401)
    def test_anonymous_access_denied(self):
        """Anonymous requests to knowledge and project endpoints must receive 401."""
        endpoints = [
            "/api/v1/control-center/knowledge/",
            "/api/v1/control-center/knowledge/wp-sec-nonce-verification/",
            "/api/v1/control-center/projects/",
        ]
        for url in endpoints:
            resp = self.client.get(url)
            assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    # 2. Non-Staff Access (Expect 403)
    def test_non_staff_access_forbidden(self):
        """Non-staff authenticated requests must receive 403."""
        self.client.force_authenticate(user=self.customer)
        endpoints = [
            "/api/v1/control-center/knowledge/",
            "/api/v1/control-center/knowledge/wp-sec-nonce-verification/",
            "/api/v1/control-center/projects/",
        ]
        for url in endpoints:
            resp = self.client.get(url)
            assert resp.status_code == status.HTTP_403_FORBIDDEN

    # 3. Staff Knowledge List Endpoint
    def test_staff_knowledge_list_success(self):
        """Staff can list all knowledge units."""
        self.client.force_authenticate(user=self.staff_user)
        resp = self.client.get("/api/v1/control-center/knowledge/")
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert len(data) >= 11
        first_item = data[0]
        assert "id" in first_item
        assert "title" in first_item
        assert "category" in first_item
        assert "rules_count" in first_item
        assert "confidence" in first_item

    def test_staff_knowledge_list_filtering(self):
        """Staff can filter knowledge units by category and search term."""
        self.client.force_authenticate(user=self.staff_user)

        # Filter category
        resp_sec = self.client.get("/api/v1/control-center/knowledge/?category=SECURITY")
        assert resp_sec.status_code == status.HTTP_200_OK
        sec_data = resp_sec.json()
        assert len(sec_data) == 4
        for item in sec_data:
            assert item["category"] == "SECURITY"

        # Search term
        resp_search = self.client.get("/api/v1/control-center/knowledge/?search=nonce")
        assert resp_search.status_code == status.HTTP_200_OK
        search_data = resp_search.json()
        assert len(search_data) > 0
        assert search_data[0]["id"] == "wp-sec-nonce-verification"

    # 4. Staff Knowledge Detail Endpoint
    def test_staff_knowledge_detail_success(self):
        """Staff can fetch full details of a specific knowledge unit."""
        self.client.force_authenticate(user=self.staff_user)
        resp = self.client.get("/api/v1/control-center/knowledge/wp-sec-nonce-verification/")
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["id"] == "wp-sec-nonce-verification"
        assert len(data["rules"]) > 0
        assert len(data["anti_patterns"]) > 0
        assert len(data["patterns"]) > 0

    def test_staff_knowledge_detail_not_found(self):
        """Requesting non-existent knowledge unit returns 404."""
        self.client.force_authenticate(user=self.staff_user)
        resp = self.client.get("/api/v1/control-center/knowledge/invalid-unit-id-404/")
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    # 5. Staff Projects List Endpoint
    def test_staff_projects_list_success(self):
        """Staff can list all projects with pagination and generation count."""
        self.client.force_authenticate(user=self.staff_user)
        resp = self.client.get("/api/v1/control-center/projects/")
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert "results" in data
        assert data["pagination"]["count"] >= 2
        results = data["results"]
        active_proj = next(p for p in results if p["id"] == str(self.active_project.id))
        assert active_proj["name"] == "Active WooCommerce Plugin"
        assert active_proj["user"]["email"] == self.customer.email
        assert active_proj["generations_count"] == 1
        assert active_proj["is_archived"] is False

    def test_staff_projects_list_filtering(self):
        """Staff can filter projects by archive status and search term."""
        self.client.force_authenticate(user=self.staff_user)

        # Filter is_archived=false
        resp_active = self.client.get("/api/v1/control-center/projects/?is_archived=false")
        assert resp_active.status_code == status.HTTP_200_OK
        assert resp_active.json()["pagination"]["count"] == 1

        # Filter is_archived=true
        resp_arch = self.client.get("/api/v1/control-center/projects/?is_archived=true")
        assert resp_arch.status_code == status.HTTP_200_OK
        assert resp_arch.json()["pagination"]["count"] == 1

        # Search term
        resp_search = self.client.get("/api/v1/control-center/projects/?search=affiliate")
        assert resp_search.status_code == status.HTTP_200_OK
        assert resp_search.json()["pagination"]["count"] == 1
        assert resp_search.json()["results"][0]["name"] == "Archived Affiliate Tracker"

    # 6. Summary Endpoint includes Knowledge Units
    def test_summary_includes_knowledge_units(self):
        """Summary endpoint includes total and categorized knowledge units."""
        self.client.force_authenticate(user=self.staff_user)
        resp = self.client.get("/api/v1/control-center/summary/")
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert "knowledge_units" in data
        assert data["knowledge_units"]["total"] >= 11
        assert "SECURITY" in data["knowledge_units"]["categories"]
        assert "WOOCOMMERCE" in data["knowledge_units"]["categories"]
