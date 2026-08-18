"""URL routes for Organizations domain."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import OrganizationViewSet

router = DefaultRouter()
router.register("", OrganizationViewSet, basename="organization")

urlpatterns = [
    path("", include(router.urls)),
]
