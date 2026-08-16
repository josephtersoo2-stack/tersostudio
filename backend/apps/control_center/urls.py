"""URL configuration for Tersuite Control Center API."""
from django.urls import path

from .views import (
    ControlCenterAgentRunsListView,
    ControlCenterGenerationsListView,
    ControlCenterSummaryView,
)

urlpatterns = [
    path("summary/", ControlCenterSummaryView.as_view(), name="control-center-summary"),
    path("generations/", ControlCenterGenerationsListView.as_view(), name="control-center-generations"),
    path("runs/", ControlCenterAgentRunsListView.as_view(), name="control-center-runs"),
]
