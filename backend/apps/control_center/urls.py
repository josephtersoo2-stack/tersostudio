"""URL configuration for Tersuite Control Center API."""
from django.urls import path

from .views import (
    ControlCenterAgentRunDetailView,
    ControlCenterAgentRunsListView,
    ControlCenterArtifactDownloadView,
    ControlCenterArtifactsListView,
    ControlCenterGenerationCancelView,
    ControlCenterGenerationDetailView,
    ControlCenterGenerationsListView,
    ControlCenterHealthView,
    ControlCenterKnowledgeDetailView,
    ControlCenterKnowledgeListView,
    ControlCenterProjectListView,
    ControlCenterStepRetryView,
    ControlCenterSummaryView,
)

urlpatterns = [
    # Summary
    path("summary/", ControlCenterSummaryView.as_view(), name="control-center-summary"),
    # Projects
    path("projects/", ControlCenterProjectListView.as_view(), name="control-center-projects"),
    # Knowledge Base
    path("knowledge/", ControlCenterKnowledgeListView.as_view(), name="control-center-knowledge-list"),
    path("knowledge/<str:unit_id>/", ControlCenterKnowledgeDetailView.as_view(), name="control-center-knowledge-detail"),
    # Generations
    path("generations/", ControlCenterGenerationsListView.as_view(), name="control-center-generations"),
    path("generations/<uuid:generation_id>/", ControlCenterGenerationDetailView.as_view(), name="control-center-generation-detail"),
    path("generations/<uuid:generation_id>/cancel/", ControlCenterGenerationCancelView.as_view(), name="control-center-generation-cancel"),
    # Steps
    path("steps/<uuid:step_id>/retry/", ControlCenterStepRetryView.as_view(), name="control-center-step-retry"),
    # Agent Runs
    path("runs/", ControlCenterAgentRunsListView.as_view(), name="control-center-runs"),
    path("runs/<uuid:run_id>/", ControlCenterAgentRunDetailView.as_view(), name="control-center-run-detail"),
    # Operational Health
    path("health/", ControlCenterHealthView.as_view(), name="control-center-health"),
    # Artifacts
    path("artifacts/", ControlCenterArtifactsListView.as_view(), name="control-center-artifacts"),
    path("artifacts/<uuid:artifact_id>/download/", ControlCenterArtifactDownloadView.as_view(), name="control-center-artifact-download"),
]
