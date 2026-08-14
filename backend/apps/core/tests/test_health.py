"""Tests for Core Health, Readiness, Middleware, and Exceptions."""
from django.test import SimpleTestCase, Client
from django.test import TestCase, Client
from django.urls import reverse
from rest_framework import status
from rest_framework.exceptions import ValidationError
from apps.core.exceptions import custom_exception_handler


class HealthCheckTests(TestCase):
    """Test suite verifying /health/live and /health/ready endpoints."""

    databases = {"default"}

    def setUp(self):
        self.client = Client()

    def test_health_live_endpoint(self):
        """Verify liveness probe returns HTTP 200 with alive status."""
        url = reverse("health_live")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data.get("status"), "alive")
        self.assertEqual(data.get("service"), "tersuite-backend")
        self.assertIn("timestamp", data)
        self.assertIn("version", data)

    def test_health_ready_endpoint(self):
        """Verify readiness probe returns service status breakdown."""
        url = reverse("health_ready")
        response = self.client.get(url)

        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_503_SERVICE_UNAVAILABLE])
        data = response.json()
        self.assertIn("status", data)
        self.assertIn("services", data)
        self.assertIn("database", data["services"])
        self.assertIn("redis", data["services"])
        self.assertIn("celery", data["services"])

    def test_request_id_middleware(self):
        """Verify X-Request-ID header is generated and attached to response."""
        url = reverse("health_live")
        response = self.client.get(url)

        self.assertTrue(response.has_header("X-Request-ID"))
        custom_id = "test-custom-trace-id-12345"
        response_custom = self.client.get(url, HTTP_X_REQUEST_ID=custom_id)
        self.assertEqual(response_custom.get("X-Request-ID"), custom_id)


class ExceptionHandlerTests(SimpleTestCase):
    """Test suite for uniform error response handling."""

    def test_validation_error_format(self):
        """Verify validation errors are wrapped into standard { error: ... } contract."""
        exc = ValidationError(detail={"email": ["This field is required."]})
        response = custom_exception_handler(exc, context={})

        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)
        self.assertEqual(response.data["error"]["code"], "invalid")
        self.assertIn("details", response.data["error"])
