"""Tests for the Generations domain (models, steps, agent runs, and CRUD APIs)."""
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.generations.enums import AgentRunStatus, ArtifactType, GenerationStatus, StepStatus
from apps.generations.models import AgentRun, Artifact, Generation, GenerationMilestone, GenerationStep, Workspace
from apps.organizations.services import ensure_personal_organization
from apps.projects.services import ProjectService

User = get_user_model()


class GenerationDomainTests(TestCase):
    """Test suite for Generations, GenerationSteps, and AgentRuns."""

    databases = {"default"}

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="lead.architect@tersuite.com",
            password="StrongPassword123!",
        )
        self.org = ensure_personal_organization(self.user)
        self.project = ProjectService.create_project(
            organization=self.org,
            actor=self.user,
            name="WordPress Membership Matrix",
            description="Content restriction and membership levels.",
        )
        self.generation = Generation.objects.create(
            organization=self.org,
            project=self.project,
            created_by=self.user,
            prompt="Build a full membership plugin with content locking shortcodes.",
            status=GenerationStatus.DRAFT,
        )
        self.milestone = GenerationMilestone.objects.create(
            generation=self.generation,
            name="Core Milestone",
            sequence=1,
        )

    def test_create_generation_api_creates_workspace_automatically(self):
        """Verify POST /api/generations/ automatically initializes an isolated Workspace."""
        self.client.force_authenticate(user=self.user)
        payload = {
            "project_id": str(self.project.id),
            "prompt": "Create an appointment booking plugin with Google Calendar integration.",
            "metadata": {"preferred_php": "8.3"},
        }
        response = self.client.post(
            "/api/v1/generations/",
            payload,
            format="json",
            HTTP_X_ORGANIZATION_ID=str(self.org.id),
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        gen_id = response.data["id"]
        generation = Generation.objects.get(id=gen_id)

        self.assertEqual(generation.prompt, payload["prompt"])
        self.assertEqual(generation.status, GenerationStatus.DRAFT)
        self.assertIsNotNone(generation.workspace)
        self.assertTrue(generation.workspace.is_active)
        self.assertIn(str(gen_id), generation.workspace.workspace_path)

    def test_generation_steps_sequence_and_unique_constraint(self):
        """Verify steps are properly sequenced and constrained by step_number."""
        step1 = GenerationStep.objects.create(
            generation=self.generation,
            milestone=self.milestone,
            step_number=1,
            name="Feature Discovery & Spec",
            agent_role="feature_discovery",
            status=StepStatus.COMPLETED,
        )
        step2 = GenerationStep.objects.create(
            generation=self.generation,
            milestone=self.milestone,
            step_number=2,
            name="Architecture Blueprint",
            agent_role="architect",
            status=StepStatus.PENDING,
        )

        steps = self.generation.steps.all()
        self.assertEqual(list(steps), [step1, step2])

        # Test duplicate step_number raises IntegrityError
        from django.db.utils import IntegrityError
        with self.assertRaises(IntegrityError):
            GenerationStep.objects.create(
                generation=self.generation,
                milestone=self.milestone,
                step_number=1,
                name="Duplicate Step 1",
                agent_role="coder",
            )

    def test_multiple_agent_runs_for_single_step(self):
        """Verify a single GenerationStep supports multiple execution attempts (AgentRuns)."""
        step = GenerationStep.objects.create(
            generation=self.generation,
            milestone=self.milestone,
            step_number=1,
            name="Code Generation",
            agent_role="coder",
            status=StepStatus.RUNNING,
        )

        # Attempt 1: Failed run
        run1 = AgentRun.objects.create(
            step=step,
            run_number=1,
            runtime_type="openhands",
            session_id="oh-sess-001",
            remote_conversation_id="3fa85f64-5717-4562-b3fc-2c963f66afa6",
            status=AgentRunStatus.FAILED,
            model_name="anthropic/claude-sonnet-4-5-20250929",
            prompt="Generate custom post type registration.",
            failure_category="MODEL_ERROR",
            error_details={"exception": "Rate limit exceeded"},
        )

        # Attempt 2: Successful retry run
        run2 = AgentRun.objects.create(
            step=step,
            run_number=2,
            runtime_type="openhands",
            session_id="oh-sess-002",
            remote_conversation_id="7ba95f64-5717-4562-b3fc-2c963f66afa7",
            status=AgentRunStatus.COMPLETED,
            model_name="anthropic/claude-sonnet-4-5-20250929",
            prompt="Generate custom post type registration.",
            output="<?php register_post_type('membership_level', ...);",
            token_usage={"total_tokens": 1250},
        )

        runs = step.runs.all()
        self.assertEqual(len(runs), 2)
        self.assertEqual(runs[0], run1)
        self.assertEqual(runs[1], run2)
        self.assertEqual(runs[0].session_id, "oh-sess-001")
        self.assertEqual(runs[1].session_id, "oh-sess-002")

    def test_generation_detail_serializer_structure(self):
        """Verify detail view returns nested steps, workspace, and artifacts."""
        Workspace.objects.create(
            generation=self.generation,
            workspace_path=f"workspaces/{self.generation.id}",
        )
        step = GenerationStep.objects.create(
            generation=self.generation,
            milestone=self.milestone,
            step_number=1,
            name="Architecture",
            agent_role="architect",
        )
        AgentRun.objects.create(
            step=step,
            run_number=1,
            session_id="oh-sess-test",
            status=AgentRunStatus.COMPLETED,
            prompt="Design database schema.",
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            f"/api/v1/generations/{self.generation.id}/",
            HTTP_X_ORGANIZATION_ID=str(self.org.id),
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], str(self.generation.id))
        self.assertIn("steps", response.data)
        self.assertEqual(len(response.data["steps"]), 1)
        self.assertEqual(len(response.data["steps"][0]["runs"]), 1)
        self.assertIsNotNone(response.data["workspace"])
        self.assertIn("artifacts", response.data)

    def test_generation_cannot_be_deleted_via_api(self):
        """Verify public API disallows destructive DELETE on Generation records (HTTP 405)."""
        self.client.force_authenticate(user=self.user)
        response = self.client.delete(
            f"/api/v1/generations/{self.generation.id}/",
            HTTP_X_ORGANIZATION_ID=str(self.org.id),
        )

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertTrue(Generation.objects.filter(id=self.generation.id).exists())

    def test_generation_ownership_cannot_diverge_from_project_owner(self):
        """Verify Generation organization is strictly derived from / matched to Project organization."""
        other_user = User.objects.create_user(
            email="impostor@tersuite.com",
            password="StrongPassword123!",
        )
        other_org = ensure_personal_organization(other_user)

        # Attempt creating generation setting organization to other_org on project owned by self.org
        gen = Generation(
            organization=other_org,
            project=self.project,
            created_by=other_user,
            prompt="Attempting to hijack ownership.",
        )
        with self.assertRaises((ValidationError, ValueError)):
            gen.save()

    def test_generation_steps_are_read_only_via_api(self):
        """Verify clients cannot create, update, or delete GenerationSteps via public API."""
        step = GenerationStep.objects.create(
            generation=self.generation,
            milestone=self.milestone,
            step_number=1,
            name="Architecture",
            agent_role="architect",
        )

        self.client.force_authenticate(user=self.user)

        # POST
        post_resp = self.client.post(
            "/api/v1/steps/",
            {"name": "Fabricated Step"},
            format="json",
            HTTP_X_ORGANIZATION_ID=str(self.org.id),
        )
        self.assertEqual(post_resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        # PATCH
        patch_resp = self.client.patch(
            f"/api/v1/steps/{step.id}/",
            {"name": "Tampered"},
            format="json",
            HTTP_X_ORGANIZATION_ID=str(self.org.id),
        )
        self.assertEqual(patch_resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        # DELETE
        del_resp = self.client.delete(
            f"/api/v1/steps/{step.id}/",
            HTTP_X_ORGANIZATION_ID=str(self.org.id),
        )
        self.assertEqual(del_resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_agent_runs_are_read_only_via_api(self):
        """Verify clients cannot create, update, or delete AgentRuns via public API."""
        step = GenerationStep.objects.create(
            generation=self.generation,
            milestone=self.milestone,
            step_number=1,
            name="Architecture",
            agent_role="architect",
        )
        run = AgentRun.objects.create(
            step=step,
            run_number=1,
            prompt="Run prompt",
        )

        self.client.force_authenticate(user=self.user)

        # POST
        post_resp = self.client.post(
            "/api/v1/runs/",
            {"prompt": "Fabricated Run"},
            format="json",
            HTTP_X_ORGANIZATION_ID=str(self.org.id),
        )
        self.assertEqual(post_resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        # PATCH
        patch_resp = self.client.patch(
            f"/api/v1/runs/{run.id}/",
            {"output": "Fake output"},
            format="json",
            HTTP_X_ORGANIZATION_ID=str(self.org.id),
        )
        self.assertEqual(patch_resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        # DELETE
        del_resp = self.client.delete(
            f"/api/v1/runs/{run.id}/",
            HTTP_X_ORGANIZATION_ID=str(self.org.id),
        )
        self.assertEqual(del_resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_workspaces_and_artifacts_are_read_only_via_api(self):
        """Verify clients cannot POST, PATCH, or DELETE Workspaces and Artifacts."""
        workspace = Workspace.objects.create(
            generation=self.generation,
            workspace_path=f"workspaces/{self.generation.id}",
        )
        artifact = Artifact.objects.create(
            generation=self.generation,
            name="plugin.php",
            file_path="plugin.php",
            artifact_type=ArtifactType.SOURCE_CODE,
            storage_key="test-key",
        )

        self.client.force_authenticate(user=self.user)

        # Workspace mutations disallowed
        self.assertEqual(
            self.client.post(
                "/api/v1/workspaces/",
                {},
                HTTP_X_ORGANIZATION_ID=str(self.org.id),
            ).status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )
        self.assertEqual(
            self.client.patch(
                f"/api/v1/workspaces/{workspace.id}/",
                {},
                HTTP_X_ORGANIZATION_ID=str(self.org.id),
            ).status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )
        self.assertEqual(
            self.client.delete(
                f"/api/v1/workspaces/{workspace.id}/",
                HTTP_X_ORGANIZATION_ID=str(self.org.id),
            ).status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )

        # Artifact mutations disallowed
        self.assertEqual(
            self.client.post(
                "/api/v1/artifacts/",
                {},
                HTTP_X_ORGANIZATION_ID=str(self.org.id),
            ).status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )
        self.assertEqual(
            self.client.patch(
                f"/api/v1/artifacts/{artifact.id}/",
                {},
                HTTP_X_ORGANIZATION_ID=str(self.org.id),
            ).status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )
        self.assertEqual(
            self.client.delete(
                f"/api/v1/artifacts/{artifact.id}/",
                HTTP_X_ORGANIZATION_ID=str(self.org.id),
            ).status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def test_generation_step_missing_milestone_rejected(self):
        """Verify GenerationStep without milestone is rejected and never auto-creates milestones."""
        initial_milestone_count = GenerationMilestone.objects.filter(generation=self.generation).count()
        step = GenerationStep(
            generation=self.generation,
            step_number=99,
            name="Orphan Step",
            agent_role="architect",
        )
        with self.assertRaises(ValidationError):
            step.save()
        # Assert no milestone was fabricated
        self.assertEqual(
            GenerationMilestone.objects.filter(generation=self.generation).count(),
            initial_milestone_count,
        )

    def test_generation_step_cross_generation_milestone_rejected(self):
        """Verify GenerationStep cannot reference a milestone belonging to another generation."""
        other_gen = Generation.objects.create(
            organization=self.org,
            project=self.project,
            created_by=self.user,
            prompt="Other gen",
            status=GenerationStatus.DRAFT,
        )
        other_milestone = GenerationMilestone.objects.create(
            generation=other_gen,
            name="Other Milestone",
            sequence=1,
        )
        step = GenerationStep(
            generation=self.generation,
            milestone=other_milestone,
            step_number=99,
            name="Cross Gen Step",
            agent_role="architect",
        )
        with self.assertRaises(ValidationError):
            step.save()
