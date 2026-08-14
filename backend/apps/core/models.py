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
