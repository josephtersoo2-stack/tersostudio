"""Tests for Workflows read-only REST API endpoints, tenant isolation, and permissions."""
import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.generations.enums import GenerationStatus
from apps.generations.models import Generation
from apps.organizations.models import Organization, OrganizationMembership
from apps.products.models import WordPressProduct
from apps.projects.models import Project
from apps.workflows.enums import WorkflowRunStatus, WorkPackageStatus
from apps.workflows.models import WorkflowRun, WorkPackage, WorkPackageAttempt


@pytest.fixture
def multi_tenant_api_setup(db):
    # Tenant 1
    u1 = User.objects.create(email="user1@tenant1.com", password="Password123!")
    org1 = Organization.objects.create(name="Tenant 1", slug="tenant-1", created_by=u1)
    OrganizationMembership.objects.create(organization=org1, user=u1, role="OWNER", is_active=True)
    prod1 = WordPressProduct.objects.create(organization=org1, display_name="Prod 1", slug="prod-1", created_by=u1)
    proj1 = Project.objects.create(organization=org1, product=prod1, name="Proj 1", slug="proj-1", created_by=u1)
    gen1 = Generation.objects.create(organization=org1, project=proj1, prompt="Gen 1", status=GenerationStatus.BUILDING, created_by=u1)
    run1 = WorkflowRun.objects.create(organization=org1, generation=gen1, run_number=1, status=WorkflowRunStatus.RUNNING, created_by=u1)
    pkg1 = WorkPackage.objects.create(organization=org1, workflow_run=run1, key="pkg_1", name="Task 1", created_by=u1)
    att1 = WorkPackageAttempt.objects.create(work_package=pkg1, attempt_number=1, worker_id="w1")

    # Tenant 2
    u2 = User.objects.create(email="user2@tenant2.com", password="Password123!")
    org2 = Organization.objects.create(name="Tenant 2", slug="tenant-2", created_by=u2)
    OrganizationMembership.objects.create(organization=org2, user=u2, role="OWNER", is_active=True)
    prod2 = WordPressProduct.objects.create(organization=org2, display_name="Prod 2", slug="prod-2", created_by=u2)
    proj2 = Project.objects.create(organization=org2, product=prod2, name="Proj 2", slug="proj-2", created_by=u2)
    gen2 = Generation.objects.create(organization=org2, project=proj2, prompt="Gen 2", status=GenerationStatus.BUILDING, created_by=u2)
    run2 = WorkflowRun.objects.create(organization=org2, generation=gen2, run_number=1, status=WorkflowRunStatus.RUNNING, created_by=u2)
    pkg2 = WorkPackage.objects.create(organization=org2, workflow_run=run2, key="pkg_2", name="Task 2", created_by=u2)
    att2 = WorkPackageAttempt.objects.create(work_package=pkg2, attempt_number=1, worker_id="w2")

    return u1, org1, run1, pkg1, att1, u2, org2, run2, pkg2, att2


@pytest.mark.django_db
class TestWorkflowInspectionAPI:
    """Test suite for Workflow inspection endpoints and tenant isolation."""

    def test_workflow_runs_tenant_isolated(self, multi_tenant_api_setup):
        u1, org1, run1, pkg1, att1, u2, org2, run2, pkg2, att2 = multi_tenant_api_setup
        client = APIClient()
        client.force_authenticate(user=u1)

        # Tenant 1 lists workflow runs
        response = client.get("/api/v1/workflow-runs/", HTTP_X_ORGANIZATION_ID=str(org1.id))
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        ids = [item["id"] for item in data["results"]] if "results" in data else [item["id"] for item in data]
        assert str(run1.id) in ids
        assert str(run2.id) not in ids

    def test_work_packages_tenant_isolated(self, multi_tenant_api_setup):
        u1, org1, run1, pkg1, att1, u2, org2, run2, pkg2, att2 = multi_tenant_api_setup
        client = APIClient()
        client.force_authenticate(user=u1)

        response = client.get("/api/v1/work-packages/", HTTP_X_ORGANIZATION_ID=str(org1.id))
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        ids = [item["id"] for item in data["results"]] if "results" in data else [item["id"] for item in data]
        assert str(pkg1.id) in ids
        assert str(pkg2.id) not in ids

    def test_mutation_methods_disallowed(self, multi_tenant_api_setup):
        u1, org1, run1, pkg1, att1, u2, org2, run2, pkg2, att2 = multi_tenant_api_setup
        client = APIClient()
        client.force_authenticate(user=u1)

        # POST /api/v1/workflow-runs/ should be 405 Method Not Allowed
        resp = client.post("/api/v1/workflow-runs/", {"run_number": 2}, HTTP_X_ORGANIZATION_ID=str(org1.id))
        assert resp.status_code in [status.HTTP_405_METHOD_NOT_ALLOWED, status.HTTP_403_FORBIDDEN]
