"""URL routing for Core health endpoints."""
from django.urls import path
from .views import HealthLiveView, HealthReadyView

urlpatterns = [
    path("live/", HealthLiveView.as_view(), name="health_live"),
    path("ready/", HealthReadyView.as_view(), name="health_ready"),
    path("", HealthReadyView.as_view(), name="health_default"),
]
