"""Models for WordPress Products and Plugin Targets."""
import re
from django.core.exceptions import ValidationError
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
        max_length=190,
        help_text="URL-safe slug for the product, unique within the organization.",
    )
    version = models.CharField(
        max_length=30,
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
        indexes = [
            models.Index(
                fields=["organization", "kind", "is_archived"],
                name="products_wo_organiz_381fa2_idx",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "slug"],
                name="unique_org_product_slug",
            )
        ]

    def clean(self) -> None:
        super().clean()
        if self.kind != ProductKind.PLUGIN:
            raise ValidationError(
                "Only 'PLUGIN' product targets are supported in this milestone.",
                code="unsupported_product_kind",
            )

    def __str__(self) -> str:
        return f"{self.display_name} ({self.kind} - {self.slug})"


class PluginTarget(TimeStampedModel):
    """Specific technical target metadata for WordPress plugins."""

    product = models.OneToOneField(
        WordPressProduct,
        on_delete=models.CASCADE,
        related_name="plugin_target",
        help_text="Parent WordPress product target.",
    )
    plugin_slug = models.SlugField(
        max_length=100,
        help_text="WordPress plugin folder/main-file slug (e.g. 'tersuite-affiliate').",
    )
    text_domain = models.SlugField(
        max_length=100,
        help_text="WordPress gettext localization text-domain.",
    )
    namespace_prefix = models.CharField(
        max_length=100,
        help_text="PHP PSR-4 namespace prefix.",
    )
    main_file = models.CharField(
        max_length=150,
        help_text="Relative path to plugin entrypoint file (e.g. 'tersuite-affiliate.php').",
    )

    class Meta:
        verbose_name = "Plugin Target"
        verbose_name_plural = "Plugin Targets"
        ordering = ["-created_at"]

    def clean(self) -> None:
        super().clean()
        if hasattr(self, "product") and self.product:
            if self.plugin_slug != self.product.slug:
                raise ValidationError("Plugin slug must match product slug.", code="plugin_slug_mismatch")
        if self.text_domain != self.plugin_slug:
            raise ValidationError("Text domain must match plugin slug.", code="text_domain_mismatch")
        if not re.match(r"^[A-Za-z][A-Za-z0-9_]*$", self.namespace_prefix or ""):
            raise ValidationError(
                "Namespace prefix must be a valid PHP identifier matching ^[A-Za-z][A-Za-z0-9_]*$.",
                code="invalid_namespace_prefix",
            )
        if (
            not self.main_file
            or "/" in self.main_file
            or "\\" in self.main_file
            or not self.main_file.endswith(".php")
            or len(self.main_file) <= 4
        ):
            raise ValidationError(
                "Main file must be a simple filename ending with .php without directory separators.",
                code="invalid_main_file",
            )

    def __str__(self) -> str:
        return f"{self.plugin_slug} ({self.namespace_prefix})"
