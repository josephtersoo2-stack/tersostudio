"""Core request logging and correlation ID middleware."""
import logging
import time
import uuid

logger = logging.getLogger("tersuite")


class RequestLoggingMiddleware:
    """Middleware to assign correlation IDs and log incoming HTTP requests."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Retrieve incoming X-Request-ID or generate new UUID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.request_id = request_id

        start_time = time.time()
        response = self.get_response(request)
        duration = time.time() - start_time

        # Attach request ID to response header
        response["X-Request-ID"] = request_id

        # Skip noisy logging on live health probe
        if request.path != "/api/v1/health/live/":
            logger.info(
                f"{request.method} {request.path} {response.status_code} "
                f"({duration:.3f}s) [req_id={request_id}]"
            )

        return response
