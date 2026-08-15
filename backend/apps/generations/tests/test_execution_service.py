"""Tests for the ExecutionService and Celery task execution."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.generations.enums import AgentRunStatus, GenerationStatus, StepStatus
from apps.generations.exceptions import StepNotExecutableError
from apps.generations.models import AgentRun, Generation, GenerationStep, Workspace
from apps.generations.services.execution_service import ExecutionService
from apps.projects.models import Project

User = get_user_model()


class ExecutionServiceTests(TestCase):
    """Test suite for ExecutionService and associated execution logic."""

    databases = {"default"}

    def setUp(self):
        self.user = User.objects.create_user(
            email="lead.developer@tersuite.com",
            password="StrongPassword123!",
        )
        self.project = Project.objects.create(
            user=self.user,
            name="Test Project",
            description="Testing execution pipeline.",
        )
        self.generation = Generation.objects.create(
            project=self.project,
            user=self.user,
            prompt="Generate a custom user role manager plugin.",
            status=GenerationStatus.DRAFT,
        )
        self.step = GenerationStep.objects.create(
            generation=self.generation,
            step_number=1,
            name="Architecture Design",
            agent_role="architect",
            status=StepStatus.PENDING,
            input_payload={"prompt": "Design user roles schema."},
        )

    def test_create_and_dispatch_not_building_raises_error(self):
        """Verify create_and_dispatch raises error if generation is not in BUILDING state."""
        self.assertEqual(self.generation.status, GenerationStatus.DRAFT)
        with self.assertRaises(StepNotExecutableError):
            ExecutionService.create_and_dispatch(self.step)

    def test_create_and_dispatch_wrong_step_status_raises_error(self):
        """Verify create_and_dispatch raises error if step is already RUNNING/COMPLETED."""
        self.generation.status = GenerationStatus.BUILDING
        self.generation.save()

        self.step.status = StepStatus.COMPLETED
        self.step.save()

        with self.assertRaises(StepNotExecutableError):
            ExecutionService.create_and_dispatch(self.step)

    def test_create_and_dispatch_success(self):
        """Verify create_and_dispatch successfully enqueues step execution."""
        self.generation.status = GenerationStatus.BUILDING
        self.generation.save()

        run = ExecutionService.create_and_dispatch(self.step)

        self.assertEqual(run.status, AgentRunStatus.QUEUED)
        self.assertEqual(run.step, self.step)
        self.assertEqual(run.run_number, 1)

        self.step.refresh_from_db()
        self.assertEqual(self.step.status, StepStatus.RUNNING)
        self.assertIsNotNone(self.step.started_at)

    def test_run_skips_non_queued_agent_run(self):
        """Verify run skips execution if AgentRun is not in QUEUED state."""
        self.generation.status = GenerationStatus.BUILDING
        self.generation.save()

        run = AgentRun.objects.create(
            step=self.step,
            run_number=1,
            status=AgentRunStatus.RUNNING,
            prompt="Prompt",
        )

        result_run = ExecutionService.run(str(run.id))
        self.assertEqual(result_run.status, AgentRunStatus.RUNNING)

    def test_run_success_flow(self):
        """Verify execution flow completes successfully with mock adapter."""
        self.generation.status = GenerationStatus.BUILDING
        self.generation.save()

        run = AgentRun.objects.create(
            step=self.step,
            run_number=1,
            status=AgentRunStatus.QUEUED,
            prompt="Prompt",
        )

        result_run = ExecutionService.run(str(run.id))

        self.assertEqual(result_run.status, AgentRunStatus.COMPLETED)
        self.assertIsNotNone(result_run.completed_at)
        self.assertIn("successfully in mock environment", result_run.output)

        self.step.refresh_from_db()
        self.assertEqual(self.step.status, StepStatus.COMPLETED)

        # Confirm success does NOT automatically advance the parent generation
        self.generation.refresh_from_db()
        self.assertEqual(self.generation.status, GenerationStatus.BUILDING)

    def test_run_failure_flow_propagates(self):
        """Verify execution failure propagates to FAILED state for both step and generation."""
        self.generation.status = GenerationStatus.BUILDING
        self.generation.save()

        run = AgentRun.objects.create(
            step=self.step,
            run_number=1,
            status=AgentRunStatus.QUEUED,
            prompt="Prompt",
        )

        # Force mock adapter to fail by supplying a failure instruction in the prompt
        run.prompt = "FORCE_MOCK_FAILURE: Simulated LLM timeout."
        run.save()

        result_run = ExecutionService.run(str(run.id))

        self.assertEqual(result_run.status, AgentRunStatus.FAILED)
        self.assertEqual(result_run.failure_category, "TIMEOUT")
        self.assertTrue(result_run.error_details.get("simulated"))

        self.step.refresh_from_db()
        self.assertEqual(self.step.status, StepStatus.FAILED)
        self.assertEqual(self.step.error_message, "Simulated LLM timeout.")

        # Confirm failure propagates up to Generation
        self.generation.refresh_from_db()
        self.assertEqual(self.generation.status, GenerationStatus.FAILED)
        self.assertIn("Step 1 (Architecture Design) failed.", self.generation.metadata.get("state_history")[-1].get("reason", ""))
