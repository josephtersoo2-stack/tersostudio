"""Tests for the Generations domain (models, steps, agent runs, and CRUD APIs)."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.generations.enums import AgentRunStatus, ArtifactType, GenerationStatus, StepStatus
from apps.generations.models import AgentRun, Artifact, Generation, GenerationStep, Workspace
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

    def test_create_generation_api_creates_workspace_automatically(self):
        """Verify POST /api/generations/ automatically initializes an isolated Workspace."""
        self.client.force_authenticate(user=self.user)
        payload = {
            "project_id": str(self.project.id),
            "prompt": "Create an appointment booking plugin with Google Calendar integration.",
            "metadata": {"preferred_php": "8.3"},
        }
        response = self.client.post("/api/v1/generations/", payload, format="json")

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
            step_number=1,
            name="Feature Discovery & Spec",
            agent_role="feature_discovery",
            status=StepStatus.COMPLETED,
        )
        step2 = GenerationStep.objects.create(
            generation=self.generation,
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
                step_number=1,
                name="Duplicate Step 1",
                agent_role="coder",
            )

    def test_multiple_agent_runs_for_single_step(self):
        """Verify a single GenerationStep supports multiple execution attempts (AgentRuns)."""
        step = GenerationStep.objects.create(
            generation=self.generation,
            step_number=1,
            name="Code Generation",
            agent_role="coder",
            status=StepStatus.RUNNING,
        )

        # Attempt 1: Failed run
        run1 = AgentRun.objects.create(
            step=step,
            run_number=1,
            prompt="Generate initial PHP code.",
            status=AgentRunStatus.FAILED,
            failure_category="MODEL_ERROR",
        )

        # Attempt 2: Successful retry run
        run2 = AgentRun.objects.create(
            step=step,
            run_number=2,
            prompt="Retry generating PHP code with repaired prompts.",
            status=AgentRunStatus.COMPLETED,
            output="Generated complete working code.",
        )

        runs = step.runs.all()
        self.assertEqual(len(runs), 2)
        self.assertEqual(runs[0], run1)
        self.assertEqual(runs[1], run2)
        self.assertEqual(runs[1].run_number, 2)

    def test_generation_detail_api_nested_representation(self):
        """Verify GET /api/v1/generations/{id}/ returns fully nested steps, workspace, and artifacts."""
        step = GenerationStep.objects.create(
            generation=self.generation,
            step_number=1,
            name="Specification",
            agent_role="feature_discovery",
            status=StepStatus.COMPLETED,
        )
        AgentRun.objects.create(
            step=step,
            run_number=1,
            status=AgentRunStatus.COMPLETED,
            output="Completed specification.",
        )
        Workspace.objects.create(
            generation=self.generation,
            workspace_path=f"workspaces/{self.generation.id}",
        )
        Artifact.objects.create(
            generation=self.generation,
            name="spec.md",
            file_path="docs/spec.md",
            artifact_type=ArtifactType.DOCUMENTATION,
            storage_key=f"artifacts/{self.generation.id}/spec.md",
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.get(f"/api/v1/generations/{self.generation.id}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertEqual(data["id"], str(self.generation.id))
        self.assertEqual(len(data["steps"]), 1)
        self.assertEqual(len(data["steps"][0]["runs"]), 1)
        self.assertIsNotNone(data["workspace"])
        self.assertEqual(len(data["artifacts"]), 1)
        self.assertEqual(data["artifacts"][0]["name"], "spec.md")

    def test_delete_generation_returns_405_method_not_allowed(self):
        """Verify DELETE /api/v1/generations/{id}/ is disallowed (durable retention)."""
        self.client.force_authenticate(user=self.user)
        response = self.client.delete(f"/api/v1/generations/{self.generation.id}/")
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
