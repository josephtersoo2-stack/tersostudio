"""Services for managing WordPress Sites and Profile Snapshots."""
import hashlib
import json
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.core.validators import find_forbidden_json_key, validate_safe_json_object
from .enums import SiteProfileSource
from .models import SiteProfileSnapshot, WordPressSite


def compute_snapshot_checksum(payload: dict) -> str:
    """Compute deterministic SHA-256 checksum over snapshot payload."""
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def create_site_profile_snapshot(
    site: WordPressSite,
    actor,
    payload: dict | None = None,
    source: str = SiteProfileSource.MANUAL,
    sections: dict | None = None,
) -> SiteProfileSnapshot:
    """Create an immutable site profile snapshot and advance site profile version."""
    data = payload if payload is not None else (sections or {})
    if not isinstance(data, dict):
        raise ValidationError("Snapshot payload must be a JSON dictionary.", code="invalid_payload")

    forbidden_key = find_forbidden_json_key(data)
    if forbidden_key:
        raise ValidationError(
            f"Forbidden secret key '{forbidden_key}' detected in snapshot payload. Credentials cannot be stored.",
            code="forbidden_secret_key",
        )

    # Validate individual metadata sections
    active_theme = data.get("active_theme", {})
    server = data.get("server", {})
    capabilities = data.get("capabilities", {})
    health = data.get("health", {})
    active_plugins = data.get("active_plugins", [])

    if not isinstance(active_plugins, list):
        raise ValidationError("active_plugins must be a JSON list.", code="invalid_plugins_list")

    validate_safe_json_object(active_theme)
    validate_safe_json_object(server)
    validate_safe_json_object(capabilities)
    validate_safe_json_object(health)

    checksum = compute_snapshot_checksum(
        {
            "wordpress_version": data.get("wordpress_version", ""),
            "php_version": data.get("php_version", ""),
            "multisite": data.get("multisite", False),
            "locale": data.get("locale", "en_US"),
            "timezone": data.get("timezone", "UTC"),
            "active_theme": active_theme,
            "active_plugins": active_plugins,
            "server": server,
            "capabilities": capabilities,
            "health": health,
        }
    )

    with transaction.atomic():
        locked_site = WordPressSite.objects.select_for_update().get(id=site.id)
        current_version = locked_site.next_profile_version

        snapshot = SiteProfileSnapshot.objects.create(
            organization=locked_site.organization,
            site=locked_site,
            version=current_version,
            source=source,
            wordpress_version=str(data.get("wordpress_version", ""))[:50],
            php_version=str(data.get("php_version", ""))[:50],
            multisite=bool(data.get("multisite", False)),
            locale=str(data.get("locale", "en_US"))[:50],
            timezone=str(data.get("timezone", "UTC"))[:100],
            active_theme=active_theme,
            active_plugins=active_plugins,
            server=server,
            capabilities=capabilities,
            health=health,
            checksum_sha256=checksum,
            created_by=actor,
        )


        locked_site.next_profile_version = current_version + 1
        locked_site.last_profiled_at = timezone.now()
        locked_site.save(update_fields=["next_profile_version", "last_profiled_at", "updated_at"])

        return snapshot
