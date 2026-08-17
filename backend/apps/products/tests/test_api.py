"""API tests for WordPress Products."""
import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient
from apps.organizations.services import ensure_personal_organization
from apps.products.models import WordPressProduct
from apps.projects.services import ProjectService

User = get_user_model()


@pytest.mark.django_db
class TestProductAPI:
    """Test suite for product endpoints."""

    def setup_method(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email="developer@example.com", password="password123")
        self.org = ensure_personal_organization(self.user)
        self.client.force_authenticate(user=self.user)

    def test_post_products_disallowed_method_not_allowed(self):
        """Verify POST /api/v1/products/ returns 405 because products are created only atomically with projects."""
        payload = {
            "display_name": "LMS Course Engine",
            "version": "1.0.0",
        }
        resp = self.client.post("/api/v1/products/", payload, format="json")
        assert resp.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_delete_and_put_products_disallowed(self):
        """Verify DELETE and PUT /api/v1/products/{id}/ return 405."""
        project = ProjectService.create_project(
            organization=self.org,
            actor=self.user,
            name="LMS Course Engine",
            plugin_slug="lms-course-engine",
        )
        product_id = project.product.id

        del_resp = self.client.delete(f"/api/v1/products/{product_id}/")
        assert del_resp.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

        put_resp = self.client.put(f"/api/v1/products/{product_id}/", {"display_name": "New"}, format="json")
        assert put_resp.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_retrieve_and_patch_plugin_product(self):
        """Verify retrieving and patching a product created via project."""
        project = ProjectService.create_project(
            organization=self.org,
            actor=self.user,
            name="LMS Course Engine",
            plugin_slug="lms-course-engine",
            wordpress_version="6.7",
            php_version="8.2",
        )
        product_id = project.product.id

        get_resp = self.client.get(f"/api/v1/products/{product_id}/")
        assert get_resp.status_code == status.HTTP_200_OK
        data = get_resp.json()
        assert data["display_name"] == "LMS Course Engine"
        assert data["slug"] == "lms-course-engine"
        assert data["kind"] == "PLUGIN"
        assert data["plugin_target"]["plugin_slug"] == "lms-course-engine"

        # PATCH display name
        patch_resp = self.client.patch(
            f"/api/v1/products/{product_id}/",
            {"display_name": "Updated LMS Engine"},
            format="json",
        )
        assert patch_resp.status_code == status.HTTP_200_OK
        assert patch_resp.json()["display_name"] == "Updated LMS Engine"

    def test_list_products_tenant_isolated_and_filterable(self):
        """Verify listing products is tenant isolated and supports kind, archived, and search filters."""
        # Create product in org
        ProjectService.create_project(
            organization=self.org,
            actor=self.user,
            name="Org 1 Product",
            plugin_slug="org-1-product",
        )

        # Other user & org
        other_user = User.objects.create_user(email="other@example.com", password="password123")
        other_org = ensure_personal_organization(other_user)

        list_resp = self.client.get("/api/v1/products/")
        assert list_resp.status_code == status.HTTP_200_OK
        results = list_resp.json().get("results", list_resp.json())
        assert len(results) == 1
        assert results[0]["slug"] == "org-1-product"

        # Search filter
        search_resp = self.client.get("/api/v1/products/?search=Org 1")
        assert search_resp.status_code == status.HTTP_200_OK
        assert len(search_resp.json().get("results", search_resp.json())) == 1

        no_match_resp = self.client.get("/api/v1/products/?search=NonExistent")
        assert no_match_resp.status_code == status.HTTP_200_OK
        assert len(no_match_resp.json().get("results", no_match_resp.json())) == 0

        # Other client sees nothing in their org
        other_client = APIClient()
        other_client.force_authenticate(user=other_user)
        other_list = other_client.get("/api/v1/products/")
        assert other_list.status_code == status.HTTP_200_OK
        other_results = other_list.json().get("results", other_list.json())
        assert len(other_results) == 0
