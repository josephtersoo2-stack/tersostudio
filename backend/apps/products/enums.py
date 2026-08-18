"""Enums and constants for WordPress Product Targets."""
from django.db import models


class ProductKind(models.TextChoices):
    """Supported WordPress product types."""

    PLUGIN = "PLUGIN", "WordPress Plugin"
    THEME = "THEME", "WordPress Theme"


B2_WRITABLE_PRODUCT_KINDS = frozenset([ProductKind.PLUGIN])
