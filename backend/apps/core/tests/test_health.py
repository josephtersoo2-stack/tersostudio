"""Tests for Core Health, Readiness, Middleware, and Exceptions."""
from unittest.mock import MagicMock, patch

from django.test import Client, SimpleTestCase, TestCase
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
        """Verify liveness probe returns HTTP 200 with alive status without requiring external services."""
        url = reverse("health_live")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data.get("status"), "alive")
        self.assertEqual(data.get("service"), "tersuite-backend")
        self.assertIn("timestamp", data)
        self.assertIn("version", data)

    @patch("apps.core.views.connection.cursor")
    @patch("redis.from_url")
    @patch("config.celery.app.connection_for_read")
    def test_health_ready_all_healthy(self, mock_celery_conn, mock_redis_from_url, mock_cursor):
        """Verify readiness probe returns HTTP 200 when DB, Redis, and Celery are healthy."""
        # Mock DB
        mock_cursor.return_value.__enter__.return_value.fetchone.return_value = (1,)

        # Mock Redis
        mock_redis_client = MagicMock()
        mock_redis_client.ping.return_value = True
        mock_redis_from_url.return_value = mock_redis_client

        # Mock Celery
        mock_conn = MagicMock()
        mock_conn.transport.driver_type = "redis"
        mock_celery_conn.return_value.__enter__.return_value = mock_conn

        url = reverse("health_ready")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["status"], "ready")
        self.assertTrue(data["all_healthy"])
        self.assertEqual(data["services"]["database"]["status"], "healthy")
        self.assertEqual(data["services"]["redis"]["status"], "healthy")
        self.assertEqual(data["services"]["celery"]["status"], "healthy")

    @patch("apps.core.views.connection.cursor", side_effect=Exception("Database password=secret123 connection error"))
    @patch("redis.from_url")
    @patch("config.celery.app.connection_for_read")
    def test_health_ready_database_failure(self, mock_celery_conn, mock_redis_from_url, mock_cursor):
        """Verify readiness returns HTTP 503 on database failure without leaking exception details."""
        mock_redis_client = MagicMock()
        mock_redis_client.ping.return_value = True
        mock_redis_from_url.return_value = mock_redis_client

        mock_conn = MagicMock()
        mock_conn.transport.driver_type = "redis"
        mock_celery_conn.return_value.__enter__.return_value = mock_conn

        url = reverse("health_ready")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        data = response.json()
        self.assertEqual(data["status"], "degraded")
        self.assertFalse(data["all_healthy"])
        self.assertEqual(data["services"]["database"]["status"], "unhealthy")
        self.assertEqual(data["services"]["database"]["code"], "database_unavailable")
        # Ensure raw exception text, passwords, and URLs are never serialized
        resp_text = response.content.decode("utf-8")
        self.assertNotIn("secret123", resp_text)
        self.assertNotIn("password", resp_text)
        self.assertNotIn("Traceback", resp_text)

    @patch("apps.core.views.connection.cursor")
    @patch("redis.from_url", side_effect=Exception("Redis AUTH failed password=redis_secret"))
    @patch("config.celery.app.connection_for_read")
    def test_health_ready_redis_failure(self, mock_celery_conn, mock_redis_from_url, mock_cursor):
        """Verify readiness returns HTTP 503 on redis failure without leaking secrets."""
        mock_cursor.return_value.__enter__.return_value.fetchone.return_value = (1,)

        mock_conn = MagicMock()
        mock_conn.transport.driver_type = "redis"
        mock_celery_conn.return_value.__enter__.return_value = mock_conn

        url = reverse("health_ready")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        data = response.json()
        self.assertEqual(data["status"], "degraded")
        self.assertFalse(data["all_healthy"])
        self.assertEqual(data["services"]["redis"]["status"], "unhealthy")
        self.assertEqual(data["services"]["redis"]["code"], "redis_unavailable")
        resp_text = response.content.decode("utf-8")
        self.assertNotIn("redis_secret", resp_text)

    @patch("apps.core.views.connection.cursor")
    @patch("redis.from_url")
    @patch("config.celery.app.connection_for_read", side_effect=Exception("Broker broker_url=redis://pass@127.0.0.1:6379 failed"))
    def test_health_ready_celery_failure(self, mock_celery_conn, mock_redis_from_url, mock_cursor):
        """Verify readiness returns HTTP 503 on celery broker failure without leaking URLs or credentials."""
        mock_cursor.return_value.__enter__.return_value.fetchone.return_value = (1,)

        mock_redis_client = MagicMock()
        mock_redis_client.ping.return_value = True
        mock_redis_from_url.return_value = mock_redis_client

        url = reverse("health_ready")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        data = response.json()
        self.assertEqual(data["status"], "degraded")
        self.assertFalse(data["all_healthy"])
        self.assertEqual(data["services"]["celery"]["status"], "unhealthy")
        self.assertEqual(data["services"]["celery"]["code"], "celery_broker_unavailable")
        resp_text = response.content.decode("utf-8")
        self.assertNotIn("redis://pass@", resp_text)

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
