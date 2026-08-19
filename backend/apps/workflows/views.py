"""Read-only, tenant-isolated ViewSets for Workflow inspection."""
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from apps.organizations.context import OrganizationContextMixin
from .models import WorkflowRun, WorkPackage, WorkPackageAttempt
from .permissions import IsWorkflowReadOnly
from .serializers import (
    WorkflowRunSerializer,
    WorkPackageSerializer,
    WorkPackageAttemptSerializer,
)


class WorkflowRunViewSet(OrganizationContextMixin, viewsets.ReadOnlyModelViewSet):
    """List and retrieve workflow runs for the active organization."""

    permission_classes = [IsAuthenticated, IsWorkflowReadOnly]
    serializer_class = WorkflowRunSerializer

    def get_queryset(self):
        org = self.get_organization()
        return WorkflowRun.objects.filter(organization=org).select_related("generation").prefetch_related("packages")


class WorkPackageViewSet(OrganizationContextMixin, viewsets.ReadOnlyModelViewSet):
    """List and retrieve work packages for the active organization."""

    permission_classes = [IsAuthenticated, IsWorkflowReadOnly]
    serializer_class = WorkPackageSerializer

    def get_queryset(self):
        org = self.get_organization()
        return WorkPackage.objects.filter(organization=org).select_related("workflow_run", "generation_step")


class WorkPackageAttemptViewSet(OrganizationContextMixin, viewsets.ReadOnlyModelViewSet):
    """List and retrieve work package execution attempts for the active organization."""

    permission_classes = [IsAuthenticated, IsWorkflowReadOnly]
    serializer_class = WorkPackageAttemptSerializer

    def get_queryset(self):
        org = self.get_organization()
        return WorkPackageAttempt.objects.filter(work_package__organization=org).select_related("work_package")
