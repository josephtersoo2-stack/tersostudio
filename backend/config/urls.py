"""Root URL Configuration for Tersuite AI Studio."""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    # API v1 versioning
    path("api/v1/health/", include("apps.core.urls")),
    path("api/v1/auth/", include("apps.accounts.urls")),
    path("api/v1/organizations/", include("apps.organizations.urls")),
    path("api/v1/products/", include("apps.products.urls")),
    path("api/v1/sites/", include("apps.sites.urls")),
    path("api/v1/projects/", include("apps.projects.urls")),
    path("api/v1/conversations/", include("apps.conversations.urls")),
    path("api/v1/control-center/", include("apps.control_center.urls")),
    path("api/v1/", include("apps.generations.urls")),
    path("api/v1/", include("apps.workflows.urls")),
]
