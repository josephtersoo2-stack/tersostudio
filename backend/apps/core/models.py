"""Core base models for Tersuite AI Studio."""
import uuid
from django.db import models


class UUIDModel(models.Model):
    """Abstract base model that uses a UUIDv4 primary key."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique identifier (UUIDv4)",
    )

    class Meta:
        abstract = True


class TimeStampedModel(UUIDModel):
    """Abstract model providing self-updating created_at and updated_at timestamps."""

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
        abstract = True
        ordering = ["-created_at"]


class OrganizationOwnedModel(TimeStampedModel):
    """Abstract model for resources owned by a tenant organization with audit attribution."""

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.PROTECT,
        related_name="%(app_label)s_%(class)s_records",
        db_index=True,
        help_text="Tenant organization that owns this resource.",
    )
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(app_label)s_%(class)s_created",
        help_text="User who created this resource.",
    )
    updated_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(app_label)s_%(class)s_updated",
        help_text="User who last updated this resource.",
    )

    class Meta:
        abstract = True
        ordering = ["-created_at"]
