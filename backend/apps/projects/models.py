"""Projects data models for organizing WordPress plugin generations."""
from django.conf import settings
from django.db import models
from django.utils.text import slugify

from apps.core.models import OrganizationOwnedModel, TimeStampedModel
from apps.core.validators import validate_safe_json_object
from .enums import ProjectSitePurpose


class ProjectQuerySet(models.QuerySet):
    """Custom queryset providing helper filters for project organization and lifecycle."""

    def for_organization(self, organization):
        """Filter projects owned by a specific tenant organization."""
        return self.filter(organization=organization)

    def active(self):
        """Filter non-archived projects."""
        return self.filter(is_archived=False)

    def archived(self):
        """Filter archived projects."""
        return self.filter(is_archived=True)


class Project(OrganizationOwnedModel):
    """Represents a discrete WordPress plugin engineering project owned by an organization."""

    name = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Human-readable name of the WordPress project.",
    )
    slug = models.SlugField(
        max_length=255,
        help_text="URL-safe slug identifier for the project, unique within the organization.",
    )
    description = models.TextField(
        blank=True,
        default="",
        help_text="Detailed description of the WordPress plugin requirements.",
    )
    product = models.OneToOneField(
        "products.WordPressProduct",
        on_delete=models.PROTECT,
        related_name="project",
        help_text="Underlying WordPress product target for this project.",
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        validators=[validate_safe_json_object],
        help_text="Arbitrary safe project configuration, preferences, and tags.",
    )
    is_archived = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Soft-deletion/archival flag for the project.",
    )

    objects = ProjectQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Project"
        verbose_name_plural = "Projects"
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "slug"],
                name="unique_org_project_slug",
            )
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.slug})"

    @property
    def user(self):
        """Backward compatibility alias for created_by."""
        return self.created_by

    @property
    def plugin_slug(self) -> str:
        """Backward compatibility alias sourced from product plugin target."""
        if hasattr(self, "product") and self.product and hasattr(self.product, "plugin_target"):
            return self.product.plugin_target.plugin_slug
        return ""

    @property
    def wordpress_version(self) -> str:
        """Backward compatibility alias sourced from product."""
        if hasattr(self, "product") and self.product:
            return self.product.wordpress_version
        return "6.7"

    @property
    def php_version(self) -> str:
        """Backward compatibility alias sourced from product."""
        if hasattr(self, "product") and self.product:
            return self.product.php_version
        return "8.2"

    def save(self, *args, **kwargs):
        """Automatically generate organization-scoped slug if not set."""
        if not self.slug:
            base_slug = slugify(self.name) or "project"
            slug = base_slug
            counter = 1
            while Project.objects.filter(organization=self.organization, slug=slug).exclude(id=self.id).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug

        super().save(*args, **kwargs)



class ProjectSite(TimeStampedModel):
    """Associates a WordPress site with a project for staging, development, or testing."""

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="project_sites",
        db_index=True,
        help_text="Tenant organization owning this association.",
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="project_sites",
        db_index=True,
        help_text="Project linked to the site.",
    )
    site = models.ForeignKey(
        "sites.WordPressSite",
        on_delete=models.CASCADE,
        related_name="project_associations",
        db_index=True,
        help_text="WordPress site attached to the project.",
    )
    purpose = models.CharField(
        max_length=20,
        choices=ProjectSitePurpose.choices,
        default=ProjectSitePurpose.DEVELOPMENT,
        help_text="Role or environment purpose of this site attachment.",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="project_sites_created",
        help_text="User who created this site association.",
    )

    class Meta:
        verbose_name = "Project Site"
        verbose_name_plural = "Project Sites"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["project", "site"],
                name="unique_project_site_link",
            )
        ]
        indexes = [
            models.Index(fields=["organization", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.project.name} <-> {self.site.name} ({self.purpose})"
