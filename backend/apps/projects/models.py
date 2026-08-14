"""Projects data models for organizing WordPress plugin generations."""
import re
from django.conf import settings
from django.db import models
from django.utils.text import slugify
from apps.core.models import TimeStampedModel


class ProjectQuerySet(models.QuerySet):
    """Custom queryset providing helper filters for project ownership and lifecycle."""

    def for_user(self, user):
        """Filter projects owned by a specific user."""
        return self.filter(user=user)

    def active(self):
        """Filter non-archived projects."""
        return self.filter(is_archived=False)

    def archived(self):
        """Filter archived projects."""
        return self.filter(is_archived=True)


class Project(TimeStampedModel):
    """Represents a discrete WordPress plugin engineering project owned by a user."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="projects",
        db_index=True,
        help_text="User who owns this project.",
    )
    name = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Human-readable name of the WordPress project.",
    )
    slug = models.SlugField(
        max_length=255,
        help_text="URL-safe slug identifier for the project.",
    )
    description = models.TextField(
        blank=True,
        default="",
        help_text="Detailed description of the WordPress plugin requirements.",
    )
    plugin_slug = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="WordPress plugin folder/main-file slug (e.g. 'tersuite-affiliate').",
    )
    wordpress_version = models.CharField(
        max_length=20,
        default="6.7",
        help_text="Target WordPress core version.",
    )
    php_version = models.CharField(
        max_length=20,
        default="8.2",
        help_text="Target PHP runtime version.",
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Arbitrary project configuration, preferences, and tags.",
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
                fields=["user", "slug"],
                name="unique_user_project_slug",
            )
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.slug})"

    def save(self, *args, **kwargs):
        """Automatically generate slug and default plugin_slug if not set."""
        if not self.slug:
            base_slug = slugify(self.name) or "project"
            slug = base_slug
            counter = 1
            while Project.objects.filter(user=self.user, slug=slug).exclude(id=self.id).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug

        if not self.plugin_slug:
            clean_plugin_slug = re.sub(r"[^a-z0-9_-]", "-", self.name.lower()).strip("-")
            self.plugin_slug = clean_plugin_slug or "plugin"

        super().save(*args, **kwargs)
