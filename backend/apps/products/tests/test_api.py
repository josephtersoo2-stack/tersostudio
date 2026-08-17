"""API tests for WordPress Products."""
import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient
from apps.organizations.services import ensure_personal_organization
from apps.products.models import WordPressProduct

User = get_user_model()


@pytest.mark.django_db
class TestProductAPI:
    """Test suite for product endpoints."""

    def setup_method(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email="developer@example.com", password="password123")
        self.org = ensure_personal_organization(self.user)
        self.client.force_authenticate(user=self.user)

    def test_create_and_retrieve_plugin_product(self):
        payload = {
            "display_name": "LMS Course Engine",
            "version": "1.0.0",
            "wordpress_version": "6.7",
            "php_version": "8.2",
            "plugin_target": {
                "plugin_slug": "lms-course-engine",
                "text_domain": "lms-course-engine",
                "namespace_prefix": "LMSCourseEngine",
                "main_file": "lms-course-engine.php",
            },
        }

        resp = self.client.post("/api/v1/products/", payload, format="json")
        assert resp.status_code == status.HTTP_201_CREATED
        data = resp.json()
        assert data["display_name"] == "LMS Course Engine"
        assert data["slug"] == "lms-course-engine"
        assert data["plugin_target"]["namespace_prefix"] == "LMSCourseEngine"

        get_resp = self.client.get(f"/api/v1/products/{data['id']}/")
        assert get_resp.status_code == status.HTTP_200_OK
        assert get_resp.json()["id"] == data["id"]

    def test_list_products_tenant_isolated(self):
        # Create a product in org
        self.client.post("/api/v1/products/", {"display_name": "Org 1 Product"}, format="json")

        # Other user & org
        other_user = User.objects.create_user(email="other@example.com", password="password123")
        other_org = ensure_personal_organization(other_user)

        list_resp = self.client.get("/api/v1/products/")
        assert list_resp.status_code == status.HTTP_200_OK
        results = list_resp.json().get("results", list_resp.json())
        assert len(results) == 1

        # Other client sees nothing in their org
        other_client = APIClient()
        other_client.force_authenticate(user=other_user)
        other_list = other_client.get("/api/v1/products/")
        assert other_list.status_code == status.HTTP_200_OK
        other_results = other_list.json().get("results", other_list.json())
        assert len(other_results) == 0
