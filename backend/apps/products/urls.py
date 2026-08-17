"""URL routes for Products domain."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import WordPressProductViewSet

router = DefaultRouter()
router.register("", WordPressProductViewSet, basename="product")

urlpatterns = [
    path("", include(router.urls)),
]
