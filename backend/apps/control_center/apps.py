"""Django application configuration for apps.control_center."""
from django.apps import AppConfig


class ControlCenterConfig(AppConfig):
    """App configuration for staff-only Control Center monitoring."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.control_center"
    verbose_name = "Tersuite Control Center"
