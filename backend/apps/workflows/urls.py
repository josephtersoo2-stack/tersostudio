"""URL routing for Workflows inspection endpoints."""
from rest_framework.routers import DefaultRouter
from .views import (
    WorkflowRunViewSet,
    WorkPackageViewSet,
    WorkPackageAttemptViewSet,
)

router = DefaultRouter()
router.register(r"workflow-runs", WorkflowRunViewSet, basename="workflow-run")
router.register(r"work-packages", WorkPackageViewSet, basename="work-package")
router.register(r"work-package-attempts", WorkPackageAttemptViewSet, basename="work-package-attempt")

urlpatterns = router.urls
