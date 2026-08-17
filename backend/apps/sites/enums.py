"""Enums for WordPress Sites and Profile Snapshots."""
from django.db import models


class SiteEnvironment(models.TextChoices):
    """Environment types for WordPress sites."""

    PRODUCTION = "PRODUCTION", "Production"
    STAGING = "STAGING", "Staging"
    DEVELOPMENT = "DEVELOPMENT", "Development"
    LOCAL = "LOCAL", "Local"


class SiteConnectionStatus(models.TextChoices):
    """Pairing/connection status of the WordPress site."""

    UNVERIFIED = "UNVERIFIED", "Unverified"
    CONNECTED = "CONNECTED", "Connected"
    DISCONNECTED = "DISCONNECTED", "Disconnected"
    ERROR = "ERROR", "Error"


class SiteProfileSource(models.TextChoices):
    """Origin source of the profile snapshot data."""

    MANUAL = "MANUAL", "Manual Entry"
    WORDPRESS_CLIENT = "WORDPRESS_CLIENT", "WordPress Client Plugin"
