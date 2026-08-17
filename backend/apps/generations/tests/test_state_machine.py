"""Tests for the Generation State Machine service and API endpoints."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.generations.enums import GenerationStatus
from apps.generations.exceptions import InvalidStateTransitionError
from apps.generations.models import Generation
from apps.generations.services.state_machine import GenerationStateMachine
from apps.organizations.services import ensure_personal_organization
from apps.projects.services import ProjectService

User = get_user_model()


class GenerationStateMachineTests(TestCase):
    """Test suite verifying strict generation state machine transitions and milestones."""

    databases = {"default"}

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="qa.lead@tersuite.com",
            password="StrongPassword123!",
        )
        self.org = ensure_personal_organization(self.user)
        self.project = ProjectService.create_project(
            organization=self.org,
            actor=self.user,
            name="WooCommerce Stripe Connect",
        )
        self.generation = Generation.objects.create(
            organization=self.org,
            project=self.project,
            created_by=self.user,
            prompt="Build Stripe Connect gateway for marketplace vendor split payments.",
            status=GenerationStatus.DRAFT,
        )

    def test_full_forward_lifecycle_progression(self):
        """Verify the complete forward lifecycle progression from DRAFT to COMPLETED."""
        flow = [
            GenerationStatus.SPECIFICATION,
            GenerationStatus.APPROVED,
            GenerationStatus.PLANNING,
            GenerationStatus.BUILDING,
            GenerationStatus.TESTING,
            GenerationStatus.REVIEW,
            GenerationStatus.PACKAGING,
            GenerationStatus.COMPLETED,
        ]

        gen = self.generation
        for target in flow:
            gen = GenerationStateMachine.transition(gen, target_status=target, reason=f"Moved to {target}")
            self.assertEqual(gen.status, target)

        self.assertIsNotNone(gen.completed_at)
        self.assertEqual(len(gen.metadata["state_history"]), len(flow))

    def test_invalid_transition_raises_error(self):
        """Verify skipping required phases raises InvalidStateTransitionError."""
        with self.assertRaises(InvalidStateTransitionError):
            GenerationStateMachine.transition(
                self.generation,
                target_status=GenerationStatus.PACKAGING,
                reason="Invalid jump",
            )

    def test_failure_transition_records_failure_fields(self):
        """Verify transitioning to FAILED records error message and failure category."""
        # Move to BUILDING first
        gen = GenerationStateMachine.transition(self.generation, GenerationStatus.SPECIFICATION)
        gen = GenerationStateMachine.transition(gen, GenerationStatus.APPROVED)
        gen = GenerationStateMachine.transition(gen, GenerationStatus.PLANNING)
        gen = GenerationStateMachine.transition(gen, GenerationStatus.BUILDING)

        # Fail from BUILDING
        failed_gen = GenerationStateMachine.transition(
            gen,
            target_status=GenerationStatus.FAILED,
            reason="LLM Provider 500 error",
            error_message="Connection timed out after 3 retries.",
            failure_category="MODEL_ERROR",
        )

        self.assertEqual(failed_gen.status, GenerationStatus.FAILED)
        self.assertEqual(failed_gen.failure_category, "MODEL_ERROR")
        self.assertEqual(failed_gen.error_message, "Connection timed out after 3 retries.")
        self.assertIsNotNone(failed_gen.failed_at)

    def test_retry_from_failed_transitions_to_retrying_then_building(self):
        """Verify retrying a failed generation resets failure states and returns to BUILDING."""
        # Setup failed generation
        gen = GenerationStateMachine.transition(self.generation, GenerationStatus.SPECIFICATION)
        gen = GenerationStateMachine.transition(gen, GenerationStatus.APPROVED)
        gen = GenerationStateMachine.transition(gen, GenerationStatus.PLANNING)
        gen = GenerationStateMachine.transition(gen, GenerationStatus.BUILDING)
        gen = GenerationStateMachine.transition(
            gen,
            target_status=GenerationStatus.FAILED,
            reason="Tool error",
            failure_category="TOOL_ERROR",
        )

        # Retry transition
        retrying_gen = GenerationStateMachine.transition(gen, target_status=GenerationStatus.RETRYING)
        self.assertEqual(retrying_gen.status, GenerationStatus.RETRYING)

        # Transition back to BUILDING
        resumed_gen = GenerationStateMachine.transition(retrying_gen, target_status=GenerationStatus.BUILDING)
        self.assertEqual(resumed_gen.status, GenerationStatus.BUILDING)
        self.assertEqual(resumed_gen.failure_category, "")
        self.assertIsNone(resumed_gen.failed_at)

    def test_cancellation_from_active_state(self):
        """Verify cancelling from BUILDING transitions to CANCELLED and records cancelled_at."""
        gen = GenerationStateMachine.transition(self.generation, GenerationStatus.SPECIFICATION)
        gen = GenerationStateMachine.transition(gen, GenerationStatus.APPROVED)
        gen = GenerationStateMachine.transition(gen, GenerationStatus.PLANNING)
        gen = GenerationStateMachine.transition(gen, GenerationStatus.BUILDING)

        cancelled_gen = GenerationStateMachine.transition(
            gen,
            target_status=GenerationStatus.CANCELLED,
            reason="User stopped generation.",
        )

        self.assertEqual(cancelled_gen.status, GenerationStatus.CANCELLED)
        self.assertIsNotNone(cancelled_gen.cancelled_at)

    def test_pause_and_resume_cycle(self):
        """Verify pausing from BUILDING and resuming back to BUILDING."""
        gen = GenerationStateMachine.transition(self.generation, GenerationStatus.SPECIFICATION)
        gen = GenerationStateMachine.transition(gen, GenerationStatus.APPROVED)
        gen = GenerationStateMachine.transition(gen, GenerationStatus.PLANNING)
        gen = GenerationStateMachine.transition(gen, GenerationStatus.BUILDING)

        paused_gen = GenerationStateMachine.transition(gen, target_status=GenerationStatus.PAUSED)
        self.assertEqual(paused_gen.status, GenerationStatus.PAUSED)
        self.assertIsNotNone(paused_gen.paused_at)

        resumed_gen = GenerationStateMachine.transition(paused_gen, target_status=GenerationStatus.BUILDING)
        self.assertEqual(resumed_gen.status, GenerationStatus.BUILDING)
        self.assertIsNone(resumed_gen.paused_at)
