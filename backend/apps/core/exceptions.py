"""Custom exception handler normalizing DRF error responses."""
import logging
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger("tersuite")


def custom_exception_handler(exc, context):
    """Normalize all DRF exceptions into a standard JSON contract."""
    response = exception_handler(exc, context)

    if response is not None:
        error_code = getattr(exc, "default_code", "error")
        error_message = "An error occurred during request processing."

        if isinstance(response.data, dict):
            if "detail" in response.data:
                error_message = str(response.data["detail"])
            details = response.data
        elif isinstance(response.data, list):
            details = {"errors": response.data}
        else:
            details = {"detail": str(response.data)}

        response.data = {
            "error": {
                "code": str(error_code),
                "message": error_message,
                "status_code": response.status_code,
                "details": details,
            }
        }
    else:
        # Unhandled server errors (500)
        logger.exception(f"Unhandled server exception: {exc}")
        response = Response(
            {
                "error": {
                    "code": "internal_server_error",
                    "message": "An unexpected server error occurred.",
                    "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                    "details": {},
                }
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return response
