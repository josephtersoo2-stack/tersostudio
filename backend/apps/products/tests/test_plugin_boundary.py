"""Tests ensuring THEME creation is rejected and plugin boundaries are enforced."""
import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient
from apps.organizations.services import ensure_personal_organization

User = get_user_model()


@pytest.mark.django_db
class TestProductBoundary:
    """Test suite for product kind boundaries."""

    def setup_method(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email="dev@example.com", password="password123")
        self.org = ensure_personal_organization(self.user)
        self.client.force_authenticate(user=self.user)

    def test_theme_product_creation_rejected(self):
        payload = {
            "kind": "THEME",
            "display_name": "Tersuite Block Theme",
        }
        resp = self.client.post("/api/v1/products/", payload, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        err = resp.json()["error"]
        assert err["code"] == "invalid" or "unsupported_product_kind" in str(err)
