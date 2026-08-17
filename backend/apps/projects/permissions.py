"""Project ownership and tenant permissions."""
from apps.organizations.permissions import (
    HasOrganizationReadAccess,
    HasOrganizationWriteAccess,
)

__all__ = [
    "HasOrganizationReadAccess",
    "HasOrganizationWriteAccess",
]
