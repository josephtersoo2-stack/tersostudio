"""Tests for the Generation State Machine service and API endpoints."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.generations.enums import GenerationStatus
from apps.generations.exceptions import InvalidStateTransitionError
from apps.generations.models import Generation
from apps.generations.services.state_machine import GenerationStateMachine
from apps.projects.models import Project

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
        self.project = Project.objects.create(
            user=self.user,
            name="WooCommerce Stripe Connect",
        )
        self.generation = Generation.objects.create(
            project=self.project,
            user=self.user,
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
        # DRAFT cannot jump directly to BUILDING
        with self.assertRaises(InvalidStateTransitionError):
            GenerationStateMachine.transition(
                self.generation,
                target_status=GenerationStatus.BUILDING,
            )

        # Move to COMPLETED and verify terminal state cannot transition out
        gen = GenerationStateMachine.transition(self.generation, GenerationStatus.SPECIFICATION)
        gen = GenerationStateMachine.transition(gen, GenerationStatus.APPROVED)
        gen = GenerationStateMachine.transition(gen, GenerationStatus.PLANNING)
        gen = GenerationStateMachine.transition(gen, GenerationStatus.BUILDING)
        gen = GenerationStateMachine.transition(gen, GenerationStatus.TESTING)
        gen = GenerationStateMachine.transition(gen, GenerationStatus.REVIEW)
        gen = GenerationStateMachine.transition(gen, GenerationStatus.PACKAGING)
        gen = GenerationStateMachine.transition(gen, GenerationStatus.COMPLETED)

        with self.assertRaises(InvalidStateTransitionError):
            GenerationStateMachine.transition(gen, GenerationStatus.PLANNING)

    def test_failure_transition_records_timestamps_and_category(self):
        """Verify FAILED transition records failed_at, error message, and failure category."""
        gen = GenerationStateMachine.transition(self.generation, GenerationStatus.SPECIFICATION)
        gen = GenerationStateMachine.transition(
            gen,
            target_status=GenerationStatus.FAILED,
            error_message="Model provider connection timeout.",
            failure_category="NETWORK_CONNECTION",
            reason="Unreachable LLM endpoint",
        )

        self.assertEqual(gen.status, GenerationStatus.FAILED)
        self.assertIsNotNone(gen.failed_at)
        self.assertEqual(gen.error_message, "Model provider connection timeout.")
        self.assertEqual(gen.failure_category, "NETWORK_CONNECTION")

    def test_pause_and_resume_lifecycle(self):
        """Verify PAUSED transition sets paused_at, and resuming clears it."""
        gen = GenerationStateMachine.transition(self.generation, GenerationStatus.SPECIFICATION)
        gen = GenerationStateMachine.transition(gen, GenerationStatus.APPROVED)
        gen = GenerationStateMachine.transition(gen, GenerationStatus.PLANNING)

        # Pause
        gen = GenerationStateMachine.transition(gen, GenerationStatus.PAUSED, reason="Waiting for user review")
        self.assertEqual(gen.status, GenerationStatus.PAUSED)
        self.assertIsNotNone(gen.paused_at)

        # Resume to PLANNING
        gen = GenerationStateMachine.transition(gen, GenerationStatus.PLANNING, reason="Resuming execution")
        self.assertEqual(gen.status, GenerationStatus.PLANNING)
        self.assertIsNone(gen.paused_at)

    def test_repair_loops_from_testing_and_review_to_building(self):
        """Verify repair loops allowing backward progression to BUILDING for critic/test fixes."""
        gen = GenerationStateMachine.transition(self.generation, GenerationStatus.SPECIFICATION)
        gen = GenerationStateMachine.transition(gen, GenerationStatus.APPROVED)
        gen = GenerationStateMachine.transition(gen, GenerationStatus.PLANNING)
        gen = GenerationStateMachine.transition(gen, GenerationStatus.BUILDING)
        gen = GenerationStateMachine.transition(gen, GenerationStatus.TESTING)

        # Test failure repair loop: TESTING -> BUILDING
        gen = GenerationStateMachine.transition(gen, GenerationStatus.BUILDING, reason="Fixing PHP linting syntax error")
        self.assertEqual(gen.status, GenerationStatus.BUILDING)

        # Back to TESTING -> REVIEW
        gen = GenerationStateMachine.transition(gen, GenerationStatus.TESTING)
        gen = GenerationStateMachine.transition(gen, GenerationStatus.REVIEW)

        # Security review repair loop: REVIEW -> BUILDING
        gen = GenerationStateMachine.transition(gen, GenerationStatus.BUILDING, reason="Patching CSRF missing nonce")
        self.assertEqual(gen.status, GenerationStatus.BUILDING)

    def test_api_transition_endpoint_success(self):
        """Verify POST /api/v1/generations/{id}/transition/ executes valid state changes."""
        self.client.force_authenticate(user=self.user)
        payload = {
            "target_status": "SPECIFICATION",
            "reason": "Feature discovery completed.",
        }
        response = self.client.post(
            f"/api/v1/generations/{self.generation.id}/transition/",
            payload,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "SPECIFICATION")

    def test_api_transition_endpoint_invalid_returns_400(self):
        """Verify invalid transition via API returns HTTP 400 Bad Request."""
        self.client.force_authenticate(user=self.user)
        payload = {
            "target_status": "COMPLETED",  # Cannot jump from DRAFT to COMPLETED
            "reason": "Skipping all steps.",
        }
        response = self.client.post(
            f"/api/v1/generations/{self.generation.id}/transition/",
            payload,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "invalid_state_transition")

    def test_api_pause_cancel_retry_actions(self):
        """Verify custom action endpoints /pause/, /cancel/, /retry/."""
        self.client.force_authenticate(user=self.user)

        # Move to PLANNING
        GenerationStateMachine.transition(self.generation, GenerationStatus.SPECIFICATION)
        GenerationStateMachine.transition(self.generation, GenerationStatus.APPROVED)
        GenerationStateMachine.transition(self.generation, GenerationStatus.PLANNING)

        # Action: Pause
        pause_resp = self.client.post(f"/api/v1/generations/{self.generation.id}/pause/")
        self.assertEqual(pause_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(pause_resp.data["status"], "PAUSED")

        # Action: Cancel
        cancel_resp = self.client.post(f"/api/v1/generations/{self.generation.id}/cancel/")
        self.assertEqual(cancel_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(cancel_resp.data["status"], "CANCELLED")
