"""URL routing for the Generations domain."""
from rest_framework.routers import DefaultRouter
from .views import (
    AgentRunViewSet,
    ArtifactViewSet,
    GenerationStepViewSet,
    GenerationViewSet,
    WorkspaceViewSet,
)

router = DefaultRouter()
router.register(r"generations", GenerationViewSet, basename="generation")
router.register(r"steps", GenerationStepViewSet, basename="step")
router.register(r"runs", AgentRunViewSet, basename="run")
router.register(r"workspaces", WorkspaceViewSet, basename="workspace")
router.register(r"artifacts", ArtifactViewSet, basename="artifact")

urlpatterns = router.urls
