"""Custom exception handler normalizing DRF error responses."""
import logging
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger("tersuite")


def extract_error_code(exc) -> str:
    """Extract a stable error code from DRF or Django exceptions."""
    if hasattr(exc, "get_codes"):
        try:
            codes = exc.get_codes()
            if isinstance(codes, str):
                return codes
            if isinstance(codes, list) and codes and isinstance(codes[0], str):
                return codes[0]
            if isinstance(codes, dict) and codes:
                first_val = next(iter(codes.values()))
                if isinstance(first_val, str):
                    return first_val
                if isinstance(first_val, list) and first_val and isinstance(first_val[0], str):
                    return first_val[0]
                if isinstance(first_val, dict) and first_val:
                    nested_val = next(iter(first_val.values()))
                    if isinstance(nested_val, list) and nested_val and isinstance(nested_val[0], str):
                        return nested_val[0]
                    if isinstance(nested_val, str):
                        return nested_val
        except Exception:
            pass

    if hasattr(exc, "code") and exc.code:
        return str(exc.code)

    if hasattr(exc, "default_code") and exc.default_code:
        return str(exc.default_code)

    return "error"


def custom_exception_handler(exc, context):
    """Normalize all DRF exceptions into a standard JSON contract."""
    response = exception_handler(exc, context)

    if response is not None:
        error_code = extract_error_code(exc)
        error_message = "An error occurred during request processing."

        if isinstance(response.data, dict):
            if "detail" in response.data:
                error_message = str(response.data["detail"])
            elif response.data:
                first_val = next(iter(response.data.values()))
                if isinstance(first_val, list) and first_val:
                    error_message = str(first_val[0])
                elif isinstance(first_val, str):
                    error_message = str(first_val)
            details = response.data
        elif isinstance(response.data, list):
            if response.data:
                error_message = str(response.data[0])
            details = {"errors": response.data}
        else:
            details = {"detail": str(response.data)}

        # If error_code was extracted as 'invalid', check if there's a more specific code in details
        if error_code == "invalid" and isinstance(details, dict):
            for k, v in details.items():
                if hasattr(v, "code") and v.code:
                    error_code = str(v.code)
                    break
                if isinstance(v, list) and v and hasattr(v[0], "code") and v[0].code:
                    error_code = str(v[0].code)
                    break

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
