"""URL routes for WordPress Sites domain."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import SiteProfileSnapshotViewSet, WordPressSiteViewSet

router = DefaultRouter()
router.register("snapshots", SiteProfileSnapshotViewSet, basename="site-snapshot")
router.register("", WordPressSiteViewSet, basename="site")

urlpatterns = [
    path("", include(router.urls)),
]
