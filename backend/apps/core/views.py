"""Health and readiness views for Tersuite AI Studio."""
import time
import logging
from django.utils import timezone
from django.db import connection
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status

logger = logging.getLogger("tersuite")


class HealthLiveView(APIView):
    """Liveness probe: verifies that the web process is running and responding."""

    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
        return Response(
            {
                "status": "alive",
                "timestamp": timezone.now().isoformat(),
                "service": "tersuite-backend",
                "version": "0.1.0",
            },
            status=status.HTTP_200_OK,
        )


class HealthReadyView(APIView):
    """Readiness probe: inspects Database, Redis, and Celery broker connectivity.

    Reports readiness without synchronously executing a blocking Celery task.
    Returns HTTP 200 if all required services are healthy, HTTP 503 otherwise.
    Never exposes raw exception strings, URLs, passwords, or secrets in responses.
    """

    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
        services = {}
        all_healthy = True

        # 1. Database Check
        db_start = time.time()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            db_duration = (time.time() - db_start) * 1000
            services["database"] = {
                "status": "healthy",
                "engine": connection.vendor,
                "latency_ms": round(db_duration, 2),
            }
        except Exception as exc:
            logger.error("Health check Database failure: %s", exc.__class__.__name__)
            services["database"] = {
                "status": "unhealthy",
                "code": "database_unavailable",
            }
            all_healthy = False

        # 2. Redis Check
        redis_start = time.time()
        try:
            import redis

            redis_client = redis.from_url(
                settings.REDIS_URL,
                socket_connect_timeout=2,
                socket_timeout=2,
            )
            redis_client.ping()
            redis_duration = (time.time() - redis_start) * 1000
            services["redis"] = {
                "status": "healthy",
                "latency_ms": round(redis_duration, 2),
            }
        except Exception as exc:
            logger.warning("Health check Redis failure: %s", exc.__class__.__name__)
            services["redis"] = {
                "status": "unhealthy",
                "code": "redis_unavailable",
            }
            all_healthy = False

        # 3. Celery Broker Connectivity Check (Non-blocking)
        try:
            from config.celery import app as celery_app

            with celery_app.connection_for_read() as conn:
                conn.connect()
                broker_transport = conn.transport.driver_type
            services["celery"] = {
                "status": "healthy",
                "broker": broker_transport,
            }
        except Exception as exc:
            logger.warning("Health check Celery broker failure: %s", exc.__class__.__name__)
            services["celery"] = {
                "status": "unhealthy",
                "code": "celery_broker_unavailable",
            }
            all_healthy = False

        response_status = status.HTTP_200_OK if all_healthy else status.HTTP_503_SERVICE_UNAVAILABLE

        return Response(
            {
                "status": "ready" if all_healthy else "degraded",
                "timestamp": timezone.now().isoformat(),
                "all_healthy": all_healthy,
                "services": services,
            },
            status=response_status,
        )
