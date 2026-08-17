"""Reusable validators for safety, URL normalization, and JSON secrets filtering."""
import json
import re
from urllib.parse import urlparse, urlunparse
from django.core.exceptions import ValidationError

FORBIDDEN_SECRET_KEYS = frozenset(
    [
        "password",
        "passwd",
        "pwd",
        "secret",
        "token",
        "access_token",
        "refresh_token",
        "api_key",
        "apikey",
        "private_key",
        "client_secret",
        "authorization",
        "cookie",
        "set_cookie",
        "database_url",
        "db_password",
        "wp_salts",
        "application_password",
    ]
)


def normalize_json_key(key: str) -> str:
    """Normalize a JSON object key by lowercasing and replacing spaces/hyphens with underscores."""
    if not isinstance(key, str):
        key = str(key)
    return re.sub(r"[\s\-]+", "_", key.strip().lower())


def find_forbidden_json_key(value) -> str | None:
    """Recursively inspect dictionaries and lists to find any forbidden secret key.

    Returns the first matching forbidden normalized key name, or None if safe.
    Never exposes or returns key values.
    """
    if isinstance(value, dict):
        for k, v in value.items():
            norm_k = normalize_json_key(str(k))
            if norm_k in FORBIDDEN_SECRET_KEYS:
                return norm_k
            nested = find_forbidden_json_key(v)
            if nested:
                return nested
    elif isinstance(value, (list, tuple, set)):
        for item in value:
            nested = find_forbidden_json_key(item)
            if nested:
                return nested
    return None


def validate_safe_json_object(value, max_bytes: int = 32768) -> None:
    """Ensure a JSON field value is a safe dictionary and does not exceed byte limits or contain forbidden keys."""
    if value is None:
        return

    if not isinstance(value, dict):
        raise ValidationError("Metadata must be a valid JSON object/dictionary.")

    forbidden_key = find_forbidden_json_key(value)
    if forbidden_key:
        raise ValidationError(
            f"Forbidden secret key '{forbidden_key}' detected in metadata payload. Credentials must not be stored in metadata."
        )

    try:
        serialized = json.dumps(value, sort_keys=True, separators=(",", ":"))
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"Metadata is not valid serializable JSON: {exc}") from exc

    byte_len = len(serialized.encode("utf-8"))
    if byte_len > max_bytes:
        raise ValidationError(
            f"Metadata payload size ({byte_len} bytes) exceeds the maximum allowed limit of {max_bytes} bytes."
        )


def normalize_wordpress_url(url: str) -> str:
    """Validate and normalize a WordPress site URL according to B2 specifications.

    Rules:
    - Must be absolute http or https
    - Rejects credentials (user/password)
    - Lowercases host
    - Strips default ports (80 for http, 443 for https)
    - Strips fragments
    - Normalizes empty path to '/'
    - Rejects non-empty query strings for site identity URLs
    """
    if not url or not isinstance(url, str):
        raise ValidationError("A valid site URL string is required.")

    url_clean = url.strip()
    parsed = urlparse(url_clean)

    if parsed.scheme.lower() not in ("http", "https"):
        raise ValidationError(f"URL scheme '{parsed.scheme}' is not supported. Must be 'http' or 'https'.")

    if not parsed.netloc:
        raise ValidationError("URL must contain a valid hostname.")

    if parsed.username or parsed.password:
        raise ValidationError("URLs containing embedded username or password credentials are strictly prohibited.")

    if parsed.query:
        raise ValidationError("Site URLs must not contain query parameters.")

    if parsed.fragment:
        # Fragments are stripped per specification
        pass

    scheme = parsed.scheme.lower()
    hostname = parsed.hostname.lower() if parsed.hostname else ""
    if not hostname:
        raise ValidationError("URL contains an invalid hostname.")

    port = parsed.port
    if (scheme == "http" and port == 80) or (scheme == "https" and port == 443):
        netloc = hostname
    elif port:
        netloc = f"{hostname}:{port}"
    else:
        netloc = hostname

    path = parsed.path or "/"
    if not path.startswith("/"):
        path = "/" + path

    # Clean double slashes in path
    path = re.sub(r"/{2,}", "/", path)

    # Reconstruct normalized URL with empty params, query, and fragment
    normalized = urlunparse((scheme, netloc, path, "", "", ""))
    return normalized
