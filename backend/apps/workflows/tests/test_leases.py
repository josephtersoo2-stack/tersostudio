"""Tests for WorkflowLeaseService heartbeat, renewal, and stale lease reaping."""
from datetime import timedelta
import uuid
import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.accounts.models import User
from apps.generations.enums import GenerationStatus
from apps.generations.models import Generation, GenerationMilestone, GenerationStep
from apps.organizations.models import Organization
from apps.products.models import WordPressProduct
from apps.projects.models import Project
from apps.workflows.enums import (
    AttemptStatus,
    LeaseReleaseReason,
    WorkflowRunStatus,
    WorkPackageStatus,
)
from apps.workflows.models import (
    WorkflowRun,
    WorkPackage,
    WorkPackageAttempt,
    WorkPackageLease,
)
from apps.workflows.services.leases import WorkflowLeaseService


@pytest.fixture
def lease_setup(db):
    user = User.objects.create(email="worker@tersuite.com", password="Password123!")
    org = Organization.objects.create(name="Tersuite Lab", slug="tersuite-lab", created_by=user)
    prod = WordPressProduct.objects.create(organization=org, display_name="Plugin A", slug="plugin-a", created_by=user)
    proj = Project.objects.create(organization=org, product=prod, name="Proj A", slug="proj-a", created_by=user)
    gen = Generation.objects.create(organization=org, project=proj, prompt="Build WP plugin", status=GenerationStatus.BUILDING, created_by=user)
    milestone = GenerationMilestone.objects.create(generation=gen, name="Milestone 1", sequence=1)
    step = GenerationStep.objects.create(generation=gen, milestone=milestone, step_number=1, name="Step 1", agent_role="coder")
    run = WorkflowRun.objects.create(organization=org, generation=gen, run_number=1, status=WorkflowRunStatus.RUNNING, created_by=user)
    pkg = WorkPackage.objects.create(
        organization=org,
        workflow_run=run,
        generation_step=step,
        key="pkg_1",
        name="Task 1",
        status=WorkPackageStatus.RUNNING,
        max_attempts=3,
        attempt_count=1,
        timeout_seconds=60,
        retry_base_seconds=10,
        created_by=user,
    )
    attempt = WorkPackageAttempt.objects.create(
        work_package=pkg,
        attempt_number=1,
        status=AttemptStatus.RUNNING,
        worker_id="worker_01",
        started_at=timezone.now(),
    )
    return org, user, gen, run, pkg, attempt


@pytest.mark.django_db
class TestWorkflowLeaseService:
    """Test suite for lease lifecycle, heartbeat, and reaper operations."""

    def test_acquire_and_heartbeat_lease(self, lease_setup):
        org, user, gen, run, pkg, attempt = lease_setup
        now = attempt.started_at

        lease = WorkflowLeaseService.acquire_lease(
            work_package=pkg,
            attempt=attempt,
            worker_id="worker_01",
            duration_seconds=30,
            now=now,
        )
        assert lease.worker_id == "worker_01"
        assert lease.expires_at == now + timedelta(seconds=30)

        # Heartbeat extension
        heartbeat_time = now + timedelta(seconds=20)
        extended_lease = WorkflowLeaseService.heartbeat(
            lease_token=lease.lease_token,
            attempt_id=attempt.id,
            duration_seconds=30,
            now=heartbeat_time,
        )
        assert extended_lease.expires_at == heartbeat_time + timedelta(seconds=30)
        assert extended_lease.heartbeat_at == heartbeat_time

    def test_heartbeat_capped_by_package_execution_deadline(self, lease_setup):
        org, user, gen, run, pkg, attempt = lease_setup
        now = attempt.started_at
        pkg.timeout_seconds = 35
        pkg.save()

        lease = WorkflowLeaseService.acquire_lease(
            work_package=pkg,
            attempt=attempt,
            worker_id="worker_01",
            duration_seconds=20,
            now=now,
        )

        # Heartbeat at T+15s with duration 30s. Would be T+45s, but effective expires_at must cap at T+35s (deadline)
        heartbeat_time = now + timedelta(seconds=15)
        extended_lease = WorkflowLeaseService.heartbeat(
            lease_token=lease.lease_token,
            attempt_id=attempt.id,
            duration_seconds=30,
            now=heartbeat_time,
        )
        assert extended_lease.expires_at == now + timedelta(seconds=35)

    def test_heartbeat_fails_on_expired_lease(self, lease_setup):
        org, user, gen, run, pkg, attempt = lease_setup
        now = attempt.started_at

        lease = WorkflowLeaseService.acquire_lease(
            work_package=pkg,
            attempt=attempt,
            worker_id="worker_01",
            duration_seconds=30,
            now=now,
        )

        future_time = now + timedelta(seconds=40)
        with pytest.raises(ValidationError) as exc:
            WorkflowLeaseService.heartbeat(
                lease_token=lease.lease_token,
                attempt_id=attempt.id,
                now=future_time,
            )
        assert exc.value.code == "lease_expired"

    def test_reap_expired_leases_and_schedule_retry(self, lease_setup):
        org, user, gen, run, pkg, attempt = lease_setup
        now = attempt.started_at
        initial_version = pkg.state_version

        lease = WorkflowLeaseService.acquire_lease(
            work_package=pkg,
            attempt=attempt,
            worker_id="worker_01",
            duration_seconds=30,
            now=now,
        )

        # Reap leases at T+40s
        reap_time = now + timedelta(seconds=40)
        reaped_count = WorkflowLeaseService.reap_expired_leases(now=reap_time)
        assert reaped_count == 1

        lease.refresh_from_db()
        attempt.refresh_from_db()
        pkg.refresh_from_db()

        assert lease.released_at is not None
        assert lease.release_reason == LeaseReleaseReason.EXPIRED
        assert attempt.status == AttemptStatus.TIMED_OUT
        # Since attempt 1 < max_attempts 3, package is scheduled for retry
        assert pkg.status == WorkPackageStatus.RETRY_WAIT
        assert pkg.next_attempt_at is not None
        # Assert state_version delta is exactly +1
        assert pkg.state_version == initial_version + 1
        assert pkg.attempt_count == 1

    def test_reap_expired_leases_cancellation_and_terminal_branches(self, lease_setup):
        org, user, gen, run, pkg, attempt = lease_setup
        now = attempt.started_at

        # 1. Test terminal exhaustion (max_attempts = 1)
        pkg.max_attempts = 1
        pkg.attempt_count = 1
        pkg.save(update_fields=["max_attempts", "attempt_count"])
        initial_version = pkg.state_version

        lease = WorkflowLeaseService.acquire_lease(
            work_package=pkg,
            attempt=attempt,
            worker_id="worker_01",
            duration_seconds=30,
            now=now,
        )

        reap_time = now + timedelta(seconds=40)
        reaped = WorkflowLeaseService.reap_expired_leases(now=reap_time)
        assert reaped == 1

        pkg.refresh_from_db()
        attempt.refresh_from_db()
        assert pkg.status == WorkPackageStatus.TIMED_OUT
        assert pkg.state_version == initial_version + 1
        assert attempt.status == AttemptStatus.TIMED_OUT

    def test_release_lease_triggers_cancellation_finalization(self, lease_setup):
        org, user, gen, run, pkg, attempt = lease_setup
        now = attempt.started_at

        lease = WorkflowLeaseService.acquire_lease(
            work_package=pkg,
            attempt=attempt,
            worker_id="worker_01",
            duration_seconds=30,
            now=now,
        )

        # Set generation to CANCELLING
        gen.status = GenerationStatus.CANCELLING
        gen.cancel_requested_at = now
        gen.save()
        run.status = WorkflowRunStatus.CANCELLING
        run.save()

        # Releasing the lease cooperatively finalizes cancellation deterministically
        WorkflowLeaseService.release_lease(lease.lease_token, now=now)

        gen.refresh_from_db()
        run.refresh_from_db()
        pkg.refresh_from_db()
        attempt.refresh_from_db()

        assert gen.status == GenerationStatus.CANCELLED
        assert run.status == WorkflowRunStatus.CANCELLED
        assert pkg.status == WorkPackageStatus.CANCELLED
        assert attempt.status == AttemptStatus.CANCELLED

    def test_cancellation_generation_wide_quiescence_check(self, lease_setup):
        org, user, gen, run, pkg, attempt = lease_setup
        now = attempt.started_at

        # Acquire a lease on run 1
        lease1 = WorkflowLeaseService.acquire_lease(
            work_package=pkg,
            attempt=attempt,
            worker_id="worker_01",
            duration_seconds=30,
            now=now,
        )

        # Set generation to CANCELLING
        gen.status = GenerationStatus.CANCELLING
        gen.cancel_requested_at = now
        gen.save()

        # Attempting finalization while lease1 is active returns False
        from apps.workflows.services.cancellation import WorkflowCancellationService
        finalized = WorkflowCancellationService.finalize_if_quiescent(gen.id)
        assert finalized is False
        gen.refresh_from_db()
        assert gen.status == GenerationStatus.CANCELLING

        # Release lease1
        WorkflowLeaseService.release_lease(lease1.lease_token, now=now)
        gen.refresh_from_db()
        assert gen.status == GenerationStatus.CANCELLED

        # Repeated finalizer call is idempotent
        assert WorkflowCancellationService.finalize_if_quiescent(gen.id) is False
