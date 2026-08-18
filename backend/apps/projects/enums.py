"""Enums for Projects and Project-Site associations."""
from django.db import models


class ProjectSitePurpose(models.TextChoices):
    """Purpose of a site attachment to a project."""

    PRIMARY = "PRIMARY", "Primary Production Site"
    STAGING = "STAGING", "Staging Environment"
    DEVELOPMENT = "DEVELOPMENT", "Development Environment"
    TEST = "TEST", "Automated Testing Environment"
