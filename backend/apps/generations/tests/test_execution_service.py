"""Tests for the ExecutionService and Celery task execution."""
from unittest.mock import MagicMock, patch
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.generations.enums import AgentRunStatus, GenerationStatus, StepStatus
from apps.generations.exceptions import StepNotExecutableError
from apps.generations.models import AgentRun, Generation, GenerationStep
from apps.generations.services.execution_service import ExecutionService
from apps.organizations.services import ensure_personal_organization
from apps.projects.services import ProjectService
from apps.realtime.events import EventType
from runtime.interfaces.session import FailureCategory, TaskResult

User = get_user_model()


class ExecutionServiceTests(TestCase):
    """Test suite for ExecutionService and associated execution logic."""

    databases = {"default"}

    def setUp(self):
        self.user = User.objects.create_user(
            email="lead.developer@tersuite.com",
            password="StrongPassword123!",
        )
        self.org = ensure_personal_organization(self.user)
        self.project = ProjectService.create_project(
            organization=self.org,
            actor=self.user,
            name="Test Project",
            description="Testing execution pipeline.",
        )
        self.generation = Generation.objects.create(
            organization=self.org,
            project=self.project,
            created_by=self.user,
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

    @patch("apps.generations.tasks.execute_agent_run.delay")
    def test_create_and_dispatch_success(self, mock_task_delay):
        """Verify create_and_dispatch creates QUEUED AgentRun and queues Celery task."""
        self.generation.status = GenerationStatus.BUILDING
        self.generation.save()

        with self.captureOnCommitCallbacks(execute=True):
            agent_run = ExecutionService.create_and_dispatch(self.step)


        self.assertIsNotNone(agent_run)
        self.assertEqual(agent_run.status, AgentRunStatus.QUEUED)
        self.assertEqual(agent_run.run_number, 1)
        self.assertEqual(agent_run.step, self.step)

        # Verify step marked RUNNING
        self.step.refresh_from_db()
        self.assertEqual(self.step.status, StepStatus.RUNNING)
        self.assertIsNotNone(self.step.started_at)

        # Verify task queued
        mock_task_delay.assert_called_once_with(str(agent_run.id))

    @patch("apps.generations.services.execution_service.GenerationEventPublisher")
    @patch("apps.generations.services.execution_service._build_runtime")
    def test_execute_agent_run_success_flow(self, mock_build_runtime, mock_publisher_cls):
        """Verify execute_agent_run executes runtime and marks run/step COMPLETED on success."""
        self.generation.status = GenerationStatus.BUILDING
        self.generation.save()

        agent_run = AgentRun.objects.create(
            step=self.step,
            run_number=1,
            status=AgentRunStatus.QUEUED,
            prompt="Generate PHP code.",
        )

        mock_publisher = MagicMock()
        mock_publisher_cls.return_value = mock_publisher

        mock_session = MagicMock()
        mock_session.session_id = "test-session-123"
        mock_session.remote_conversation_id = "remote-conv-456"

        mock_runtime = MagicMock()
        mock_runtime.create_session.return_value = mock_session
        mock_runtime.send_task.return_value = TaskResult(
            session_id="test-session-123",
            success=True,
            output="Generated plugin code successfully.",
            token_usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        )
        mock_build_runtime.return_value = mock_runtime

        result = ExecutionService.execute_agent_run(str(agent_run.id))

        self.assertEqual(result.status, AgentRunStatus.COMPLETED)
        agent_run.refresh_from_db()
        self.assertEqual(agent_run.status, AgentRunStatus.COMPLETED)
        self.assertEqual(agent_run.output, "Generated plugin code successfully.")
        self.assertEqual(agent_run.session_id, "test-session-123")
        self.assertEqual(agent_run.remote_conversation_id, "remote-conv-456")
        self.assertIsNotNone(agent_run.completed_at)

        # Verify step marked COMPLETED
        self.step.refresh_from_db()
        self.assertEqual(self.step.status, StepStatus.COMPLETED)
        self.assertIsNotNone(self.step.completed_at)

        # Verify realtime events published
        self.assertTrue(mock_publisher.publish.called)

    @patch("apps.generations.services.execution_service.GenerationEventPublisher")
    @patch("apps.generations.services.execution_service._build_runtime")
    def test_execute_agent_run_failure_flow(self, mock_build_runtime, mock_publisher_cls):
        """Verify execute_agent_run handles execution failure, sets failure_category and transitions generation to FAILED."""
        self.generation.status = GenerationStatus.BUILDING
        self.generation.save()

        agent_run = AgentRun.objects.create(
            step=self.step,
            run_number=1,
            status=AgentRunStatus.QUEUED,
            prompt="Generate PHP code.",
        )

        mock_publisher = MagicMock()
        mock_publisher_cls.return_value = mock_publisher

        mock_session = MagicMock()
        mock_session.session_id = "test-session-123"
        mock_session.remote_conversation_id = "remote-conv-456"

        mock_runtime = MagicMock()
        mock_runtime.create_session.return_value = mock_session
        mock_runtime.send_task.return_value = TaskResult(
            session_id="test-session-123",
            success=False,
            failure_category=FailureCategory.NETWORK_CONNECTION,
            error="OpenHands server connection refused.",
            retryable=True,
            error_details={"error": "OpenHands server connection refused."},
        )
        mock_build_runtime.return_value = mock_runtime

        result = ExecutionService.execute_agent_run(str(agent_run.id))

        self.assertEqual(result.status, AgentRunStatus.FAILED)
        agent_run.refresh_from_db()
        self.assertEqual(agent_run.status, AgentRunStatus.FAILED)
        self.assertEqual(agent_run.failure_category, "NETWORK_CONNECTION")

        # Verify step marked FAILED
        self.step.refresh_from_db()
        self.assertEqual(self.step.status, StepStatus.FAILED)

        # Verify generation transitioned to FAILED
        self.generation.refresh_from_db()
        self.assertEqual(self.generation.status, GenerationStatus.FAILED)
        self.assertEqual(self.generation.failure_category, "NETWORK_CONNECTION")
