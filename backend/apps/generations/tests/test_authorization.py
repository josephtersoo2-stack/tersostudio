"""Tests verifying strict multi-tenant authorization across Projects, Generations, Steps, and Artifacts."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.generations.enums import ArtifactType, GenerationStatus, StepStatus
from apps.generations.models import AgentRun, Artifact, Generation, GenerationStep, Workspace
from apps.organizations.services import ensure_personal_organization
from apps.projects.services import ProjectService

User = get_user_model()


class MultiTenantAuthorizationTests(TestCase):
    """Test suite ensuring absolute data isolation between different authenticated users."""

    databases = {"default"}

    def setUp(self):
        self.client = APIClient()

        # User A (Resource Owner)
        self.user_a = User.objects.create_user(
            email="tenant.a@tersuite.com",
            password="Password123!",
        )
        self.org_a = ensure_personal_organization(self.user_a)

        self.project_a = ProjectService.create_project(
            organization=self.org_a,
            actor=self.user_a,
            name="Tenant A Secret Plugin",
        )
        self.generation_a = Generation.objects.create(
            organization=self.org_a,
            project=self.project_a,
            created_by=self.user_a,
            prompt="Build private custom plugin for Tenant A.",
            status=GenerationStatus.DRAFT,
        )
        self.step_a = GenerationStep.objects.create(
            generation=self.generation_a,
            step_number=1,
            name="Architecture A",
            agent_role="architect",
            status=StepStatus.PENDING,
        )
        self.run_a = AgentRun.objects.create(
            step=self.step_a,
            run_number=1,
            prompt="Private prompt for Tenant A",
        )
        self.workspace_a = Workspace.objects.create(
            generation=self.generation_a,
            workspace_path=f"workspaces/{self.generation_a.id}",
        )
        self.artifact_a = Artifact.objects.create(
            generation=self.generation_a,
            name="private-code.php",
            file_path="private-code.php",
            artifact_type=ArtifactType.SOURCE_CODE,
            storage_key=f"artifacts/{self.generation_a.id}/private-code.php",
        )

        # User B (Attacker / Other Tenant)
        self.user_b = User.objects.create_user(
            email="tenant.b@tersuite.com",
            password="Password123!",
        )
        self.org_b = ensure_personal_organization(self.user_b)

    def test_user_b_cannot_access_user_a_project(self):
        """Verify User B cannot retrieve or modify User A's project."""
        self.client.force_authenticate(user=self.user_b)

        # Retrieve
        resp = self.client.get(f"/api/v1/projects/{self.project_a.id}/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

        # Update
        resp = self.client.patch(
            f"/api/v1/projects/{self.project_a.id}/",
            {"name": "Hacked Name"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

        # Delete
        resp = self.client.delete(f"/api/v1/projects/{self.project_a.id}/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_b_cannot_create_generation_for_user_a_project(self):
        """Verify User B cannot create a generation linked to User A's project."""
        self.client.force_authenticate(user=self.user_b)
        payload = {
            "project_id": str(self.project_a.id),
            "prompt": "Unauthorized generation attempt.",
        }
        resp = self.client.post("/api/v1/generations/", payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        error_details = resp.data.get("error", {}).get("details", resp.data)
        self.assertIn("project_id", error_details)

    def test_user_b_cannot_access_user_a_generation(self):
        """Verify User B cannot retrieve or list User A's generation."""
        self.client.force_authenticate(user=self.user_b)

        # List
        resp = self.client.get("/api/v1/generations/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        results = resp.data.get("results", resp.data)
        self.assertEqual(len(results), 0)

        # Retrieve
        resp = self.client.get(f"/api/v1/generations/{self.generation_a.id}/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_b_cannot_transition_user_a_generation(self):
        """Verify User B cannot trigger state transitions on User A's generation."""
        self.client.force_authenticate(user=self.user_b)
        payload = {"target_status": "SPECIFICATION"}
        resp = self.client.post(
            f"/api/v1/generations/{self.generation_a.id}/transition/",
            payload,
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_b_cannot_access_user_a_steps_and_runs(self):
        """Verify User B cannot view steps or agent runs belonging to User A."""
        self.client.force_authenticate(user=self.user_b)

        # Step
        resp = self.client.get(f"/api/v1/steps/{self.step_a.id}/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

        # Run
        resp = self.client.get(f"/api/v1/runs/{self.run_a.id}/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_b_cannot_download_user_a_artifacts(self):
        """Verify User B cannot download or inspect User A's artifact."""
        self.client.force_authenticate(user=self.user_b)

        # Retrieve metadata
        resp = self.client.get(f"/api/v1/artifacts/{self.artifact_a.id}/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

        # Download
        resp = self.client.get(f"/api/v1/artifacts/{self.artifact_a.id}/download/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_b_cannot_access_user_a_workspace(self):
        """Verify User B cannot inspect User A's workspace."""
        self.client.force_authenticate(user=self.user_b)

        # Via Generation sub-endpoint
        resp = self.client.get(f"/api/v1/generations/{self.generation_a.id}/workspace/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

        # Via Workspace direct endpoint
        resp = self.client.get(f"/api/v1/workspaces/{self.workspace_a.id}/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
