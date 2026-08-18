"""Models for Organizations and Organization Memberships."""
from django.conf import settings
from django.db import models
from apps.core.models import TimeStampedModel
from apps.core.validators import validate_safe_json_object
from .enums import OrganizationRole


class Organization(TimeStampedModel):
    """Represents a tenant organization owning projects, products, sites, and workflows."""

    name = models.CharField(
        max_length=255,
        help_text="Human-readable name of the organization.",
    )
    slug = models.SlugField(
        max_length=255,
        unique=True,
        help_text="Unique URL-safe identifier for the organization.",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="organizations_created",
        help_text="User who created this organization.",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="organizations_updated",
        help_text="User who last updated this organization.",
    )
    is_personal = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Designates whether this is a user's default personal workspace.",
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Designates whether this organization is active or soft-archived.",
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        validators=[validate_safe_json_object],
        help_text="Safe JSON metadata and configuration preferences.",
    )

    class Meta:
        verbose_name = "Organization"
        verbose_name_plural = "Organizations"
        ordering = ["name", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["created_by"],
                condition=models.Q(is_personal=True, created_by__isnull=False),
                name="unique_personal_organization_per_user",
            )
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.slug})"


class OrganizationMembership(TimeStampedModel):
    """Binds a user to an organization with a specific tenant role."""

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="memberships",
        db_index=True,
        help_text="Organization for this membership.",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="organization_memberships",
        db_index=True,
        help_text="User belonging to the organization.",
    )
    role = models.CharField(
        max_length=20,
        choices=OrganizationRole.choices,
        default=OrganizationRole.MEMBER,
        db_index=True,
        help_text="Role and permission tier within the organization.",
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Designates whether this membership is active.",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="organization_memberships_created",
        help_text="User who granted or added this membership.",
    )

    class Meta:
        verbose_name = "Organization Membership"
        verbose_name_plural = "Organization Memberships"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "user"],
                name="unique_organization_user_membership",
            )
        ]
        indexes = [
            models.Index(fields=["user", "is_active"]),
            models.Index(fields=["organization", "role", "is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.user.email} - {self.organization.slug} ({self.role})"
