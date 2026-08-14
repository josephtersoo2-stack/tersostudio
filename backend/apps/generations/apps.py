"""Django app configuration for generations."""
from django.apps import AppConfig


class GenerationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.generations"
    verbose_name = "Generations"
