"""Tests for the ExecutionService and Celery task execution."""
from unittest.mock import MagicMock, patch
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.generations.enums import AgentRunStatus, GenerationStatus, StepStatus
from apps.generations.exceptions import StepNotExecutableError
from apps.generations.models import AgentRun, Generation, GenerationStep
from apps.generations.services.execution_service import ExecutionService
from apps.projects.models import Project
from apps.realtime.events import EventType
from runtime.exceptions import AdapterConnectionError, TimeoutExecutionError

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

    def test_run_success_flow_and_live_event_streaming(self):
        """Verify execution flow completes successfully with mock adapter and streams intermediate events."""
        self.generation.status = GenerationStatus.BUILDING
        self.generation.save()

        run = AgentRun.objects.create(
            step=self.step,
            run_number=1,
            status=AgentRunStatus.QUEUED,
            prompt="Prompt",
        )

        published_events = []
        with patch("apps.realtime.event_publisher.GenerationEventPublisher.publish", side_effect=published_events.append):
            result_run = ExecutionService.run(str(run.id))

        self.assertEqual(result_run.status, AgentRunStatus.COMPLETED)
        self.assertIsNotNone(result_run.completed_at)
        self.assertIn("successfully in mock environment", result_run.output)

        self.step.refresh_from_db()
        self.assertEqual(self.step.status, StepStatus.COMPLETED)

        # Confirm success does NOT automatically advance the parent generation
        self.generation.refresh_from_db()
        self.assertEqual(self.generation.status, GenerationStatus.BUILDING)

        # Verify live event streaming occurred during execution
        event_types = [e.event_type for e in published_events]
        self.assertIn(EventType.AGENT_STARTED, event_types)
        self.assertIn(EventType.AGENT_THINKING, event_types)
        self.assertIn(EventType.AGENT_TOOL_STARTED, event_types)
        self.assertIn(EventType.AGENT_TOOL_FINISHED, event_types)
        self.assertIn(EventType.AGENT_COMPLETED, event_types)
        self.assertIn(EventType.GENERATION_STEP_COMPLETED, event_types)

        # Verify all streamed events have correct generation_id and agent_run_id
        for ev in published_events:
            self.assertEqual(ev.generation_id, str(self.generation.id))
            self.assertEqual(ev.agent_run_id, str(run.id))

    def test_run_failure_classification_timeout(self):
        """Verify timeout execution failure properly records TIMEOUT category and retryable=True."""
        self.generation.status = GenerationStatus.BUILDING
        self.generation.save()

        run = AgentRun.objects.create(
            step=self.step,
            run_number=1,
            status=AgentRunStatus.QUEUED,
            prompt="FORCE_MOCK_FAILURE:TIMEOUT:Execution exceeded 300 seconds",
        )

        result_run = ExecutionService.run(str(run.id))

        self.assertEqual(result_run.status, AgentRunStatus.FAILED)
        self.assertEqual(result_run.failure_category, "TIMEOUT")
        self.assertTrue(result_run.error_details.get("retryable"))
        self.assertEqual(result_run.error_details.get("error"), "Execution exceeded 300 seconds")

        self.step.refresh_from_db()
        self.assertEqual(self.step.status, StepStatus.FAILED)
        self.assertEqual(self.step.error_message, "Execution exceeded 300 seconds")

        self.generation.refresh_from_db()
        self.assertEqual(self.generation.status, GenerationStatus.FAILED)
        self.assertEqual(self.generation.metadata.get("state_history")[-1].get("failure_category"), "TIMEOUT")

    def test_run_failure_classification_network(self):
        """Verify network execution failure properly records NETWORK_CONNECTION category and retryable=True."""
        self.generation.status = GenerationStatus.BUILDING
        self.generation.save()

        run = AgentRun.objects.create(
            step=self.step,
            run_number=1,
            status=AgentRunStatus.QUEUED,
            prompt="FORCE_MOCK_FAILURE:NETWORK:Connection refused by host",
        )

        result_run = ExecutionService.run(str(run.id))

        self.assertEqual(result_run.status, AgentRunStatus.FAILED)
        self.assertEqual(result_run.failure_category, "NETWORK_CONNECTION")
        self.assertTrue(result_run.error_details.get("retryable"))

        self.step.refresh_from_db()
        self.assertEqual(self.step.status, StepStatus.FAILED)

        self.generation.refresh_from_db()
        self.assertEqual(self.generation.status, GenerationStatus.FAILED)
        self.assertEqual(self.generation.metadata.get("state_history")[-1].get("failure_category"), "NETWORK_CONNECTION")

    def test_run_failure_classification_model_error(self):
        """Verify model error failure properly records MODEL_ERROR category and retryable=False."""
        self.generation.status = GenerationStatus.BUILDING
        self.generation.save()

        run = AgentRun.objects.create(
            step=self.step,
            run_number=1,
            status=AgentRunStatus.QUEUED,
            prompt="FORCE_MOCK_FAILURE:MODEL:Invalid model parameter or context length exceeded",
        )

        result_run = ExecutionService.run(str(run.id))

        self.assertEqual(result_run.status, AgentRunStatus.FAILED)
        self.assertEqual(result_run.failure_category, "MODEL_ERROR")
        self.assertFalse(result_run.error_details.get("retryable"))

        self.step.refresh_from_db()
        self.assertEqual(self.step.status, StepStatus.FAILED)

        self.generation.refresh_from_db()
        self.assertEqual(self.generation.status, GenerationStatus.FAILED)

    def test_run_failure_classification_tool_error(self):
        """Verify tool error failure properly records TOOL_ERROR category."""
        self.generation.status = GenerationStatus.BUILDING
        self.generation.save()

        run = AgentRun.objects.create(
            step=self.step,
            run_number=1,
            status=AgentRunStatus.QUEUED,
            prompt="FORCE_MOCK_FAILURE:TOOL:Command 'git' failed with exit status 1",
        )

        result_run = ExecutionService.run(str(run.id))

        self.assertEqual(result_run.status, AgentRunStatus.FAILED)
        self.assertEqual(result_run.failure_category, "TOOL_ERROR")
        self.assertFalse(result_run.error_details.get("retryable"))

    def test_run_runtime_exception_during_create_session(self):
        """Verify runtime error during create_session is classified properly as NETWORK_CONNECTION."""
        self.generation.status = GenerationStatus.BUILDING
        self.generation.save()

        run = AgentRun.objects.create(
            step=self.step,
            run_number=1,
            status=AgentRunStatus.QUEUED,
            prompt="Regular prompt",
        )

        with patch("runtime.adapters.mock_adapter.MockAgentRuntime.create_session", side_effect=AdapterConnectionError("Server offline")):
            result_run = ExecutionService.run(str(run.id))

        self.assertEqual(result_run.status, AgentRunStatus.FAILED)
        self.assertEqual(result_run.failure_category, "NETWORK_CONNECTION")
        self.assertTrue(result_run.error_details.get("retryable"))

        self.step.refresh_from_db()
        self.assertEqual(self.step.status, StepStatus.FAILED)

        self.generation.refresh_from_db()
        self.assertEqual(self.generation.status, GenerationStatus.FAILED)
