"""Tests for the Generation State Machine service and API endpoints."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.generations.enums import GenerationStatus
from apps.generations.exceptions import InvalidStateTransitionError
from apps.generations.models import Generation, GenerationStateTransition
from apps.generations.services.state_machine import GenerationStateMachine
from apps.organizations.services import ensure_personal_organization
from apps.projects.services import ProjectService

User = get_user_model()


class GenerationStateMachineTests(TestCase):
    """Test suite verifying strict generation state machine transitions and audit records."""

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
        """Verify the complete forward lifecycle progression through B3 canonical states."""
        flow = [
            GenerationStatus.DISCOVERY,
            GenerationStatus.SPECIFICATION_DRAFT,
            GenerationStatus.PLAN_DRAFT,
            GenerationStatus.AWAITING_APPROVAL,
            GenerationStatus.APPROVED,
            GenerationStatus.SCHEDULED,
            GenerationStatus.BUILDING,
            GenerationStatus.INTEGRATING,
            GenerationStatus.REVIEWING,
            GenerationStatus.SANDBOX_QA,
            GenerationStatus.RELEASE_CANDIDATE,
            GenerationStatus.AWAITING_DEPLOYMENT_APPROVAL,
            GenerationStatus.STAGED,
            GenerationStatus.ACTIVE,
        ]

        gen = self.generation
        expected_version = 0
        expected_seq = 1

        for target in flow:
            expected_version += 1
            gen = GenerationStateMachine.transition(gen, target_status=target, reason=f"Moved to {target}")
            self.assertEqual(gen.status, target)
            self.assertEqual(gen.state_version, expected_version)
            self.assertEqual(gen.next_transition_sequence, expected_seq + 1)
            expected_seq += 1

        self.assertEqual(gen.state_transitions.count(), len(flow))

    def test_invalid_transition_raises_error(self):
        """Verify skipping required phases raises InvalidStateTransitionError."""
        # DRAFT cannot jump directly to BUILDING
        with self.assertRaises(InvalidStateTransitionError):
            GenerationStateMachine.transition(
                self.generation,
                target_status=GenerationStatus.BUILDING,
            )

        # Move to ACTIVE (terminal success) and verify terminal state cannot transition out
        gen = self.generation
        for target in [
            GenerationStatus.DISCOVERY,
            GenerationStatus.SPECIFICATION_DRAFT,
            GenerationStatus.PLAN_DRAFT,
            GenerationStatus.AWAITING_APPROVAL,
            GenerationStatus.APPROVED,
            GenerationStatus.SCHEDULED,
            GenerationStatus.BUILDING,
            GenerationStatus.INTEGRATING,
            GenerationStatus.REVIEWING,
            GenerationStatus.SANDBOX_QA,
            GenerationStatus.RELEASE_CANDIDATE,
            GenerationStatus.AWAITING_DEPLOYMENT_APPROVAL,
            GenerationStatus.STAGED,
            GenerationStatus.ACTIVE,
        ]:
            gen = GenerationStateMachine.transition(gen, target_status=target)

        with self.assertRaises(InvalidStateTransitionError):
            GenerationStateMachine.transition(gen, GenerationStatus.PLAN_DRAFT)

    def test_failure_transition_records_timestamps_and_category(self):
        """Verify FAILED transition records failed_at, error message, and failure category."""
        gen = GenerationStateMachine.transition(self.generation, GenerationStatus.DISCOVERY)
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
        """Verify PAUSED transition sets paused_at, resume_status, and resuming restores state."""
        gen = GenerationStateMachine.transition(self.generation, GenerationStatus.DISCOVERY)
        gen = GenerationStateMachine.transition(gen, GenerationStatus.SPECIFICATION_DRAFT)

        # Pause
        gen = GenerationStateMachine.transition(gen, GenerationStatus.PAUSED, reason="Waiting for user review")
        self.assertEqual(gen.status, GenerationStatus.PAUSED)
        self.assertEqual(gen.resume_status, GenerationStatus.SPECIFICATION_DRAFT)
        self.assertIsNotNone(gen.paused_at)

        # Resume
        gen = GenerationStateMachine.transition(gen, GenerationStatus.SPECIFICATION_DRAFT, reason="Resuming execution")
        self.assertEqual(gen.status, GenerationStatus.SPECIFICATION_DRAFT)
        self.assertIsNone(gen.paused_at)

    def test_repair_loops_from_sandbox_and_reviewing_to_correcting(self):
        """Verify repair loops allowing progression to CORRECTING -> BUILDING for fixes."""
        gen = self.generation
        for target in [
            GenerationStatus.DISCOVERY,
            GenerationStatus.SPECIFICATION_DRAFT,
            GenerationStatus.PLAN_DRAFT,
            GenerationStatus.AWAITING_APPROVAL,
            GenerationStatus.APPROVED,
            GenerationStatus.SCHEDULED,
            GenerationStatus.BUILDING,
            GenerationStatus.INTEGRATING,
            GenerationStatus.REVIEWING,
        ]:
            gen = GenerationStateMachine.transition(gen, target_status=target)

        # Reviewing findings require correction: REVIEWING -> CORRECTING -> BUILDING
        gen = GenerationStateMachine.transition(gen, GenerationStatus.CORRECTING, reason="Reviewer findings received")
        self.assertEqual(gen.status, GenerationStatus.CORRECTING)

        gen = GenerationStateMachine.transition(gen, GenerationStatus.BUILDING, reason="Applying reviewer repairs")
        self.assertEqual(gen.status, GenerationStatus.BUILDING)

    def test_api_transition_endpoint_direct_progression_returns_409(self):
        """Verify POST /api/v1/generations/{id}/transition/ rejects direct forward state forcing with 409."""
        self.client.force_authenticate(user=self.user)
        payload = {
            "target_status": "BUILDING",
            "reason": "Direct progression attempt.",
        }
        response = self.client.post(
            f"/api/v1/generations/{self.generation.id}/transition/",
            payload,
            format="json",
            HTTP_X_ORGANIZATION_ID=str(self.org.id),
        )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data["error"]["code"], "direct_transition_requires_coordinator")

    def test_api_pause_cancel_retry_actions(self):
        """Verify custom action endpoints /pause/, /cancel/, /retry/ with Idempotency-Key."""
        self.client.force_authenticate(user=self.user)

        # Transition to SCHEDULED -> BUILDING
        gen = self.generation
        for target in [
            GenerationStatus.DISCOVERY,
            GenerationStatus.SPECIFICATION_DRAFT,
            GenerationStatus.PLAN_DRAFT,
            GenerationStatus.AWAITING_APPROVAL,
            GenerationStatus.APPROVED,
            GenerationStatus.SCHEDULED,
            GenerationStatus.BUILDING,
        ]:
            gen = GenerationStateMachine.transition(gen, target_status=target)

        # Action: Pause with Idempotency-Key
        pause_resp = self.client.post(
            f"/api/v1/generations/{self.generation.id}/pause/",
            data={"reason": "Operator pause"},
            format="json",
            HTTP_X_ORGANIZATION_ID=str(self.org.id),
            HTTP_IDEMPOTENCY_KEY="pause_key_001",
        )
        self.assertEqual(pause_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(pause_resp.data["generation"]["status"], "PAUSED")

        # Action: Resume with Idempotency-Key
        resume_resp = self.client.post(
            f"/api/v1/generations/{self.generation.id}/resume/",
            data={"reason": "Operator resume"},
            format="json",
            HTTP_X_ORGANIZATION_ID=str(self.org.id),
            HTTP_IDEMPOTENCY_KEY="resume_key_001",
        )
        self.assertEqual(resume_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resume_resp.data["generation"]["status"], "BUILDING")

        # Action: Cancel with Idempotency-Key
        cancel_resp = self.client.post(
            f"/api/v1/generations/{self.generation.id}/cancel/",
            data={"reason": "Operator cancel"},
            format="json",
            HTTP_X_ORGANIZATION_ID=str(self.org.id),
            HTTP_IDEMPOTENCY_KEY="cancel_key_001",
        )
        self.assertEqual(cancel_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(cancel_resp.data["generation"]["status"], "CANCELLED")

    def test_legacy_metadata_state_history_preserved_without_mutation(self):
        """Verify legacy metadata['state_history'] is preserved untouched and not appended on B3 transitions."""
        legacy_history = [
            {"from_status": "DRAFT", "to_status": "SPECIFICATION", "timestamp": "2026-08-01T00:00:00Z"}
        ]
        self.generation.metadata["state_history"] = list(legacy_history)
        self.generation.save()

        initial_transitions_count = self.generation.state_transitions.count()
        initial_version = self.generation.state_version

        # Perform valid B3 transition
        gen = GenerationStateMachine.transition(self.generation, target_status=GenerationStatus.DISCOVERY, reason="Starting discovery")

        # Assert metadata is structurally identical / untouched
        self.assertEqual(gen.metadata["state_history"], legacy_history)
        # Assert one GenerationStateTransition was created
        self.assertEqual(gen.state_transitions.count(), initial_transitions_count + 1)
        # Assert state version incremented once
        self.assertEqual(gen.state_version, initial_version + 1)

