"""Tests ensuring THEME creation is rejected and plugin boundaries are enforced."""
import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.test import APIClient
from apps.organizations.services import ensure_personal_organization
from apps.products.models import WordPressProduct

User = get_user_model()


@pytest.mark.django_db
class TestProductBoundary:
    """Test suite for product kind boundaries."""

    def setup_method(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email="dev@example.com", password="password123")
        self.org = ensure_personal_organization(self.user)
        self.client.force_authenticate(user=self.user)

    def test_direct_products_post_rejected_method_not_allowed(self):
        """Verify POST /api/v1/products/ returns 405 Method Not Allowed."""
        resp = self.client.post("/api/v1/products/", {"display_name": "New"}, format="json")
        assert resp.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_theme_product_creation_rejected_in_model_and_project_api(self):
        """Verify THEME creation is rejected with unsupported_product_kind."""
        # 1. Model-level validation
        prod = WordPressProduct(
            organization=self.org,
            kind="THEME",
            display_name="Tersuite Block Theme",
            slug="tersuite-block-theme",
        )
        with pytest.raises(ValidationError) as excinfo:
            prod.clean()
        assert excinfo.value.code == "unsupported_product_kind"

        # 2. Project API level validation
        payload = {
            "name": "Theme Project",
            "product": {
                "kind": "THEME",
                "display_name": "Tersuite Block Theme",
            },
        }
        resp = self.client.post("/api/v1/projects/", payload, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        err = resp.json()["error"]
        assert "unsupported_product_kind" in str(err) or "Only PLUGIN products" in str(err)
