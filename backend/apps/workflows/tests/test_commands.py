"""Tests for WorkflowCommandService idempotent control commands (PAUSE, RESUME, CANCEL, RETRY)."""
from datetime import timedelta
import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.accounts.models import User
from apps.generations.enums import GenerationStatus
from apps.generations.models import Generation, GenerationMilestone, GenerationStep
from apps.organizations.models import Organization
from apps.products.models import WordPressProduct
from apps.projects.models import Project
from apps.workflows.enums import AttemptStatus, CommandType, WorkflowRunStatus, WorkPackageStatus
from apps.workflows.models import (
    WorkflowCommand,
    WorkflowRun,
    WorkPackage,
    WorkPackageAttempt,
    WorkPackageLease,
)
from apps.workflows.services.commands import WorkflowCommandService
from apps.workflows.services.leases import WorkflowLeaseService


@pytest.fixture
def command_setup(db):
    user = User.objects.create(email="operator@tersuite.com", password="Password123!")
    org = Organization.objects.create(name="Tersuite Lab", slug="tersuite-lab", created_by=user)
    prod = WordPressProduct.objects.create(organization=org, display_name="Plugin A", slug="plugin-a", created_by=user)
    proj = Project.objects.create(organization=org, product=prod, name="Proj A", slug="proj-a", created_by=user)
    gen = Generation.objects.create(
        organization=org,
        project=proj,
        prompt="Build WP plugin",
        status=GenerationStatus.BUILDING,
        created_by=user,
    )
    milestone = GenerationMilestone.objects.create(generation=gen, name="Milestone 1", sequence=1)
    step = GenerationStep.objects.create(generation=gen, milestone=milestone, step_number=1, name="Step 1", agent_role="coder")
    run = WorkflowRun.objects.create(
        organization=org,
        generation=gen,
        run_number=1,
        status=WorkflowRunStatus.RUNNING,
        created_by=user,
    )
    return org, user, gen, run, milestone, step


@pytest.mark.django_db
class TestWorkflowCommandService:
    """Test suite for idempotent control commands."""

    def test_pause_and_idempotent_replay(self, command_setup):
        org, user, gen, run, milestone, step = command_setup
        idempotency_key = "idemp_pause_001"

        # 1. First execution
        res1 = WorkflowCommandService.execute_command(
            generation=gen,
            command_type=CommandType.PAUSE,
            idempotency_key=idempotency_key,
            payload={"reason": "Operator pause"},
            actor=user,
        )
        assert res1["idempotent_replay"] is False
        assert res1["status"] == GenerationStatus.PAUSED

        gen.refresh_from_db()
        run.refresh_from_db()
        assert gen.status == GenerationStatus.PAUSED
        assert run.status == WorkflowRunStatus.PAUSED

        # 2. Idempotent replay with same key and payload
        res2 = WorkflowCommandService.execute_command(
            generation=gen,
            command_type=CommandType.PAUSE,
            idempotency_key=idempotency_key,
            payload={"reason": "Operator pause"},
            actor=user,
        )
        assert res2["idempotent_replay"] is True
        assert res2["command_id"] == res1["command_id"]

    def test_idempotency_key_conflict_with_different_payload(self, command_setup):
        org, user, gen, run, milestone, step = command_setup
        idempotency_key = "idemp_pause_002"

        # First execution
        WorkflowCommandService.execute_command(
            generation=gen,
            command_type=CommandType.PAUSE,
            idempotency_key=idempotency_key,
            payload={"reason": "Original reason"},
            actor=user,
        )

        # Same key with different payload must fail with conflict
        with pytest.raises(ValidationError) as exc:
            WorkflowCommandService.execute_command(
                generation=gen,
                command_type=CommandType.PAUSE,
                idempotency_key=idempotency_key,
                payload={"reason": "Different reason"},
                actor=user,
            )
        assert exc.value.code == "idempotency_key_conflict"

    def test_resume_command(self, command_setup):
        org, user, gen, run, milestone, step = command_setup
        # Pause first
        WorkflowCommandService.execute_command(
            generation=gen,
            command_type=CommandType.PAUSE,
            idempotency_key="idemp_p1",
            actor=user,
        )
        gen.refresh_from_db()
        assert gen.status == GenerationStatus.PAUSED

        # Resume
        res = WorkflowCommandService.execute_command(
            generation=gen,
            command_type=CommandType.RESUME,
            idempotency_key="idemp_r1",
            actor=user,
        )
        gen.refresh_from_db()
        run.refresh_from_db()
        assert gen.status == GenerationStatus.BUILDING
        assert run.status == WorkflowRunStatus.RUNNING

    def test_cancel_with_no_active_lease_finalizes_to_cancelled(self, command_setup):
        org, user, gen, run, milestone, step = command_setup
        pkg = WorkPackage.objects.create(
            organization=org,
            workflow_run=run,
            generation_step=step,
            key="pkg_1",
            name="Task 1",
            status=WorkPackageStatus.READY,
            created_by=user,
        )

        res = WorkflowCommandService.execute_command(
            generation=gen,
            command_type=CommandType.CANCEL,
            idempotency_key="idemp_c1",
            actor=user,
        )
        gen.refresh_from_db()
        run.refresh_from_db()
        pkg.refresh_from_db()

        assert gen.status == GenerationStatus.CANCELLED
        assert run.status == WorkflowRunStatus.CANCELLED
        assert pkg.status == WorkPackageStatus.CANCELLED

        # Verify transition records show both CANCELLING and CANCELLED
        statuses = list(gen.state_transitions.values_list("to_status", flat=True))
        assert "CANCELLING" in statuses
        assert "CANCELLED" in statuses

    def test_cancel_with_active_lease_stays_cancelling_until_reap(self, command_setup):
        org, user, gen, run, milestone, step = command_setup
        pkg = WorkPackage.objects.create(
            organization=org,
            workflow_run=run,
            generation_step=step,
            key="pkg_1",
            name="Task 1",
            status=WorkPackageStatus.RUNNING,
            created_by=user,
        )
        now = timezone.now()
        attempt = WorkPackageAttempt.objects.create(
            work_package=pkg,
            attempt_number=1,
            status=AttemptStatus.RUNNING,
            worker_id="worker_01",
            started_at=now,
        )
        lease = WorkflowLeaseService.acquire_lease(
            work_package=pkg,
            attempt=attempt,
            worker_id="worker_01",
            duration_seconds=30,
            now=now,
        )

        # Cancel command executed while lease is active
        WorkflowCommandService.execute_command(
            generation=gen,
            command_type=CommandType.CANCEL,
            idempotency_key="idemp_c2",
            actor=user,
        )
        gen.refresh_from_db()
        run.refresh_from_db()
        pkg.refresh_from_db()

        assert gen.status == GenerationStatus.CANCELLING
        assert run.status == WorkflowRunStatus.CANCELLING
        assert pkg.cancel_requested_at is not None

        # Lease expires and is reaped
        reap_time = now + timedelta(seconds=40)
        reaped = WorkflowLeaseService.reap_expired_leases(now=reap_time)
        assert reaped == 1

        gen.refresh_from_db()
        run.refresh_from_db()
        pkg.refresh_from_db()

        assert gen.status == GenerationStatus.CANCELLED
        assert run.status == WorkflowRunStatus.CANCELLED
        assert pkg.status == WorkPackageStatus.CANCELLED

    def test_retry_command_eligibility_and_exhaustion(self, command_setup):
        org, user, gen, run, milestone, step = command_setup
        gen.status = GenerationStatus.FAILED
        gen.save()
        run.status = WorkflowRunStatus.FAILED
        run.save()

        # 1. Package with non-retryable attempt fails retry
        pkg_non_retryable = WorkPackage.objects.create(
            organization=org,
            workflow_run=run,
            generation_step=step,
            key="pkg_fatal",
            name="Fatal Task",
            status=WorkPackageStatus.FAILED,
            max_attempts=3,
            attempt_count=1,
            created_by=user,
        )
        WorkPackageAttempt.objects.create(
            work_package=pkg_non_retryable,
            attempt_number=1,
            status=AttemptStatus.FAILED,
            retryable=False,
            worker_id="worker_01",
        )

        with pytest.raises(ValidationError) as exc:
            WorkflowCommandService.execute_command(
                generation=gen,
                command_type=CommandType.RETRY,
                idempotency_key="idemp_ret_01",
                actor=user,
            )
        assert exc.value.code == "retry_not_available"

        # 2. Add retryable package -> retry succeeds and schedules RETRY_WAIT
        pkg_retryable = WorkPackage.objects.create(
            organization=org,
            workflow_run=run,
            generation_step=step,
            key="pkg_retryable",
            name="Retryable Task",
            status=WorkPackageStatus.FAILED,
            max_attempts=3,
            attempt_count=1,
            created_by=user,
        )
        WorkPackageAttempt.objects.create(
            work_package=pkg_retryable,
            attempt_number=1,
            status=AttemptStatus.FAILED,
            retryable=True,
            worker_id="worker_01",
        )

        res = WorkflowCommandService.execute_command(
            generation=gen,
            command_type=CommandType.RETRY,
            idempotency_key="idemp_ret_02",
            actor=user,
        )
        gen.refresh_from_db()
        run.refresh_from_db()
        pkg_retryable.refresh_from_db()

        assert gen.status == GenerationStatus.SCHEDULED
        assert run.status == WorkflowRunStatus.RUNNING
        assert pkg_retryable.status == WorkPackageStatus.RETRY_WAIT
        assert pkg_retryable.next_attempt_at is not None
