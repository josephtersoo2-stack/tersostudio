"""Models for WordPress Products and Plugin Targets."""
from django.db import models
from apps.core.models import OrganizationOwnedModel, TimeStampedModel
from apps.core.validators import validate_safe_json_object
from .enums import ProductKind


class WordPressProduct(OrganizationOwnedModel):
    """Represents an organization-owned WordPress product target (e.g. Plugin)."""

    kind = models.CharField(
        max_length=20,
        choices=ProductKind.choices,
        default=ProductKind.PLUGIN,
        db_index=True,
        help_text="Product target category (PLUGIN, THEME).",
    )
    display_name = models.CharField(
        max_length=255,
        help_text="Human-readable product name.",
    )
    slug = models.SlugField(
        max_length=255,
        help_text="URL-safe slug for the product, unique within the organization.",
    )
    version = models.CharField(
        max_length=50,
        default="0.1.0",
        help_text="Current product semantic version.",
    )
    wordpress_version = models.CharField(
        max_length=20,
        default="6.7",
        help_text="Target WordPress core compatibility version.",
    )
    php_version = models.CharField(
        max_length=20,
        default="8.2",
        help_text="Target PHP runtime compatibility version.",
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        validators=[validate_safe_json_object],
        help_text="Arbitrary safe JSON configuration and preferences.",
    )
    is_archived = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Whether this product is archived.",
    )

    class Meta:
        verbose_name = "WordPress Product"
        verbose_name_plural = "WordPress Products"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "slug"],
                name="unique_org_product_slug",
            )
        ]

    def __str__(self) -> str:
        return f"{self.display_name} ({self.kind} - {self.slug})"


class PluginTarget(models.Model):
    """Specific technical target metadata for WordPress plugins."""

    product = models.OneToOneField(
        WordPressProduct,
        on_delete=models.CASCADE,
        related_name="plugin_target",
        primary_key=True,
        help_text="Parent WordPress product target.",
    )
    plugin_slug = models.CharField(
        max_length=100,
        help_text="WordPress plugin folder/main-file slug (e.g. 'tersuite-affiliate').",
    )
    text_domain = models.CharField(
        max_length=100,
        help_text="WordPress gettext localization text-domain.",
    )
    namespace_prefix = models.CharField(
        max_length=100,
        help_text="PHP PSR-4 namespace prefix.",
    )
    main_file = models.CharField(
        max_length=255,
        help_text="Relative path to plugin entrypoint file (e.g. 'tersuite-affiliate.php').",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="Timestamp when record was created",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp when record was last updated",
    )

    class Meta:
        verbose_name = "Plugin Target"
        verbose_name_plural = "Plugin Targets"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.plugin_slug} ({self.namespace_prefix})"
