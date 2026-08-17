"""Enums and role definitions for Organization tenancy."""
from django.db import models


class OrganizationRole(models.TextChoices):
    """Roles for users within an Organization."""

    OWNER = "OWNER", "Owner"
    ADMIN = "ADMIN", "Admin"
    MEMBER = "MEMBER", "Member"
    VIEWER = "VIEWER", "Viewer"


WRITE_ROLES = frozenset(
    [
        OrganizationRole.OWNER,
        OrganizationRole.ADMIN,
        OrganizationRole.MEMBER,
    ]
)

MEMBER_MANAGER_ROLES = frozenset(
    [
        OrganizationRole.OWNER,
        OrganizationRole.ADMIN,
    ]
)

OWNER_ONLY_ROLES = frozenset([OrganizationRole.OWNER])
