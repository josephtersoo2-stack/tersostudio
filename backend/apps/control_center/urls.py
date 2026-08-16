"""URL configuration for Tersuite Control Center API."""
from django.urls import path

from .views import (
    ControlCenterAgentRunDetailView,
    ControlCenterAgentRunsListView,
    ControlCenterArtifactDownloadView,
    ControlCenterArtifactsListView,
    ControlCenterGenerationDetailView,
    ControlCenterGenerationsListView,
    ControlCenterHealthView,
    ControlCenterSummaryView,
)

urlpatterns = [
    # Summary
    path("summary/", ControlCenterSummaryView.as_view(), name="control-center-summary"),
    # Generations
    path("generations/", ControlCenterGenerationsListView.as_view(), name="control-center-generations"),
    path("generations/<uuid:generation_id>/", ControlCenterGenerationDetailView.as_view(), name="control-center-generation-detail"),
    # Agent Runs
    path("runs/", ControlCenterAgentRunsListView.as_view(), name="control-center-runs"),
    path("runs/<uuid:run_id>/", ControlCenterAgentRunDetailView.as_view(), name="control-center-run-detail"),
    # Operational Health
    path("health/", ControlCenterHealthView.as_view(), name="control-center-health"),
    # Artifacts
    path("artifacts/", ControlCenterArtifactsListView.as_view(), name="control-center-artifacts"),
    path("artifacts/<uuid:artifact_id>/download/", ControlCenterArtifactDownloadView.as_view(), name="control-center-artifact-download"),
]
