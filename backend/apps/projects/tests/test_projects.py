"""Tests for the Projects app (CRUD, validation, and multi-tenant isolation)."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.projects.models import Project

User = get_user_model()


class ProjectModelAndAPITests(TestCase):
    """Test suite for Project model logic and REST API endpoints."""

    databases = {"default"}

    def setUp(self):
        self.client = APIClient()
        self.user1 = User.objects.create_user(
            email="developer1@tersuite.com",
            password="StrongPassword123!",
            first_name="Dev",
            last_name="One",
        )
        self.user2 = User.objects.create_user(
            email="developer2@tersuite.com",
            password="StrongPassword123!",
            first_name="Dev",
            last_name="Two",
        )
        self.project1 = Project.objects.create(
            user=self.user1,
            name="WooCommerce Affiliate Pro",
            description="Enterprise affiliate management plugin.",
            wordpress_version="6.7",
            php_version="8.3",
        )

    def test_project_model_auto_generates_slug_and_plugin_slug(self):
        """Verify model auto-generates slug and plugin_slug on save."""
        self.assertEqual(self.project1.slug, "woocommerce-affiliate-pro")
        self.assertEqual(self.project1.plugin_slug, "woocommerce-affiliate-pro")

    def test_project_duplicate_slug_auto_increments(self):
        """Verify duplicate names for the same user receive unique incremented slugs."""
        project2 = Project.objects.create(
            user=self.user1,
            name="WooCommerce Affiliate Pro",
        )
        self.assertEqual(project2.slug, "woocommerce-affiliate-pro-1")

    def test_list_projects_scoped_to_authenticated_user(self):
        """Verify user only sees their own projects."""
        Project.objects.create(user=self.user2, name="Other User Project")

        self.client.force_authenticate(user=self.user1)
        response = self.client.get("/api/v1/projects/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", response.data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], str(self.project1.id))

    def test_create_project_authenticated_success(self):
        """Verify authenticated user can create a new project."""
        self.client.force_authenticate(user=self.user1)
        payload = {
            "name": "LMS Course Engine",
            "description": "Learning management system for WordPress.",
            "wordpress_version": "6.7",
            "php_version": "8.2",
        }
        response = self.client.post("/api/v1/projects/", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "LMS Course Engine")
        self.assertEqual(response.data["user_id"], str(self.user1.id))
        self.assertEqual(response.data["slug"], "lms-course-engine")

    def test_retrieve_project_details(self):
        """Verify retrieving single project details."""
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(f"/api/v1/projects/{self.project1.id}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], str(self.project1.id))
        self.assertEqual(response.data["name"], "WooCommerce Affiliate Pro")

    def test_update_project(self):
        """Verify updating project description and metadata."""
        self.client.force_authenticate(user=self.user1)
        response = self.client.patch(
            f"/api/v1/projects/{self.project1.id}/",
            {"description": "Updated description with multi-tier commissions."},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.project1.refresh_from_db()
        self.assertEqual(self.project1.description, "Updated description with multi-tier commissions.")

    def test_archive_and_unarchive_project_actions(self):
        """Verify archive and unarchive custom actions."""
        self.client.force_authenticate(user=self.user1)

        # Archive
        archive_resp = self.client.post(f"/api/v1/projects/{self.project1.id}/archive/")
        self.assertEqual(archive_resp.status_code, status.HTTP_200_OK)
        self.project1.refresh_from_db()
        self.assertTrue(self.project1.is_archived)

        # Filter by active
        active_resp = self.client.get("/api/v1/projects/?archived=false")
        active_results = active_resp.data.get("results", active_resp.data)
        self.assertEqual(len(active_results), 0)

        # Filter by archived
        archived_resp = self.client.get("/api/v1/projects/?archived=true")
        archived_results = archived_resp.data.get("results", archived_resp.data)
        self.assertEqual(len(archived_results), 1)

        # Unarchive
        unarchive_resp = self.client.post(f"/api/v1/projects/{self.project1.id}/unarchive/")
        self.assertEqual(unarchive_resp.status_code, status.HTTP_200_OK)
        self.project1.refresh_from_db()
        self.assertFalse(self.project1.is_archived)

    def test_unauthenticated_request_denied(self):
        """Verify unauthenticated requests return 401."""
        response = self.client.get("/api/v1/projects/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
