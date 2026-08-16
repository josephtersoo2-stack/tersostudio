"""Staff-only permission classes for Tersuite Control Center."""
from rest_framework.permissions import BasePermission


class IsStaffControlCenterUser(BasePermission):
    """Allows access only to authenticated staff or superuser accounts.

    Rules:
    - Anonymous users are rejected with 401 Unauthorized (via DRF authentication flow).
    - Authenticated non-staff users are rejected with 403 Forbidden.
    - Staff users and superusers have full read-only visibility across system records.
    """

    message = "Staff privileges are required to access the Tersuite Control Center."

    def has_permission(self, request, view) -> bool:
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        return bool(user.is_staff or user.is_superuser)
