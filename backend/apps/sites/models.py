"""Data models for WordPress Sites and Site Profile Snapshots."""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from apps.core.models import OrganizationOwnedModel, TimeStampedModel
from apps.core.validators import (
    find_forbidden_json_key,
    normalize_wordpress_url,
    validate_safe_json_object,
)
from .enums import SiteConnectionStatus, SiteEnvironment, SiteProfileSource


class WordPressSite(OrganizationOwnedModel):
    """Represents a remote or local WordPress site metadata entity."""

    name = models.CharField(
        max_length=255,
        help_text="Human-readable label for the WordPress site.",
    )
    url = models.URLField(
        max_length=2048,
        help_text="Canonical normalized WordPress site root URL.",
    )
    environment = models.CharField(
        max_length=20,
        choices=SiteEnvironment.choices,
        default=SiteEnvironment.PRODUCTION,
        db_index=True,
        help_text="Environment deployment classification.",
    )
    connection_status = models.CharField(
        max_length=20,
        choices=SiteConnectionStatus.choices,
        default=SiteConnectionStatus.UNVERIFIED,
        db_index=True,
        help_text="Verified pairing state with the WordPress site.",
    )
    next_profile_version = models.PositiveIntegerField(
        default=1,
        help_text="Monotonically increasing sequence version for snapshots.",
    )
    last_profiled_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of the most recent profile snapshot capture.",
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        validators=[validate_safe_json_object],
        help_text="Arbitrary safe JSON metadata (strictly no credentials).",
    )
    is_archived = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Whether this site is soft-archived.",
    )

    class Meta:
        verbose_name = "WordPress Site"
        verbose_name_plural = "WordPress Sites"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["organization", "environment", "is_archived"],
                name="sites_wordp_organiz_6f2e82_idx",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "url"],
                name="unique_org_site_url",
            )
        ]

    def clean(self) -> None:
        super().clean()
        if self.url:
            self.url = normalize_wordpress_url(self.url)

    def __str__(self) -> str:
        return f"{self.name} ({self.url})"


class SiteProfileSnapshot(TimeStampedModel):
    """Immutable point-in-time environment snapshot of a WordPress site."""

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.PROTECT,
        related_name="site_profile_snapshots",
        db_index=True,
        help_text="Tenant organization owning the snapshot.",
    )
    site = models.ForeignKey(
        WordPressSite,
        on_delete=models.CASCADE,
        related_name="profile_snapshots",
        db_index=True,
        help_text="WordPress site described by this snapshot.",
    )
    version = models.PositiveIntegerField(
        help_text="Sequential version number for this site's snapshots.",
    )
    source = models.CharField(
        max_length=20,
        choices=SiteProfileSource.choices,
        default=SiteProfileSource.MANUAL,
        db_index=True,
        help_text="Origin source of snapshot capture.",
    )
    wordpress_version = models.CharField(
        max_length=20,
        blank=True,
        default="",
        help_text="Detected WordPress core version.",
    )
    php_version = models.CharField(
        max_length=20,
        blank=True,
        default="",
        help_text="Detected PHP runtime version.",
    )
    multisite = models.BooleanField(
        default=False,
        help_text="Whether WordPress multisite network is enabled.",
    )
    locale = models.CharField(
        max_length=32,
        default="en_US",
        help_text="WordPress site locale setting.",
    )
    timezone = models.CharField(
        max_length=64,
        default="UTC",
        help_text="WordPress configured timezone.",
    )
    active_theme = models.JSONField(
        default=dict,
        blank=True,
        validators=[validate_safe_json_object],
        help_text="Active theme name, version, and template metadata.",
    )
    active_plugins = models.JSONField(
        default=list,
        blank=True,
        help_text="List of active plugins with versions and slugs.",
    )
    server = models.JSONField(
        default=dict,
        blank=True,
        validators=[validate_safe_json_object],
        help_text="Web server, database software, and OS metadata.",
    )
    capabilities = models.JSONField(
        default=dict,
        blank=True,
        validators=[validate_safe_json_object],
        help_text="Supported WordPress REST endpoints and extension APIs.",
    )
    health = models.JSONField(
        default=dict,
        blank=True,
        validators=[validate_safe_json_object],
        help_text="Site Health status metrics and diagnostics.",
    )
    checksum_sha256 = models.CharField(
        max_length=64,
        blank=True,
        default="",
        help_text="SHA-256 integrity hash of the snapshot content.",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="site_profile_snapshots_created",
        help_text="User who initiated or recorded this snapshot.",
    )

    class Meta:
        verbose_name = "Site Profile Snapshot"
        verbose_name_plural = "Site Profile Snapshots"
        ordering = ["-version"]
        constraints = [
            models.UniqueConstraint(
                fields=["site", "version"],
                name="unique_site_profile_version",
            )
        ]
        indexes = [
            models.Index(fields=["organization", "-created_at"], name="sites_sitep_organiz_a43e81_idx"),
        ]

    def clean(self) -> None:
        super().clean()
        if self.site and self.organization_id != self.site.organization_id:
            raise ValidationError(
                "Snapshot organization must match site organization.",
                code="organization_mismatch",
            )
        if self.active_plugins:
            forbidden = find_forbidden_json_key(self.active_plugins)
            if forbidden:
                raise ValidationError(
                    f"Forbidden secret key '{forbidden}' detected in active_plugins.",
                    code="forbidden_secret_key",
                )

    def __str__(self) -> str:
        return f"{self.site.name} - Snapshot v{self.version}"
