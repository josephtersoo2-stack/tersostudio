"""Tests for WorkflowSchedulerService driving DAG execution, leases, claims, and verified completion."""
import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.accounts.models import User
from apps.generations.enums import GenerationStatus, StepStatus
from apps.generations.models import Generation, GenerationMilestone, GenerationStep
from apps.organizations.models import Organization
from apps.products.models import WordPressProduct
from apps.projects.models import Project
from apps.workflows.enums import (
    AttemptStatus,
    DependencyType,
    WorkflowRunStatus,
    WorkPackageStatus,
)
from apps.workflows.models import (
    OutboxEvent,
    WorkflowRun,
    WorkPackage,
    WorkPackageAttempt,
    WorkPackageDependency,
    WorkPackageLease,
)
from apps.workflows.services.graph import WorkflowGraphService
from apps.workflows.services.scheduler import WorkflowSchedulerService


@pytest.fixture
def workflow_setup(db):
    user = User.objects.create(email="worker@tersuite.com", password="Password123!")
    org = Organization.objects.create(name="Tersuite Lab", slug="tersuite-lab", created_by=user)
    prod = WordPressProduct.objects.create(organization=org, display_name="Plugin A", slug="plugin-a", created_by=user)
    proj = Project.objects.create(organization=org, product=prod, name="Proj A", slug="proj-a", created_by=user)
    gen = Generation.objects.create(organization=org, project=proj, prompt="Build WP plugin", status=GenerationStatus.BUILDING, created_by=user)
    milestone = GenerationMilestone.objects.create(generation=gen, name="Milestone 1", sequence=1)
    step1 = GenerationStep.objects.create(generation=gen, milestone=milestone, step_number=1, name="Step 1", agent_role="coder", status=StepStatus.PENDING)
    step2 = GenerationStep.objects.create(generation=gen, milestone=milestone, step_number=2, name="Step 2", agent_role="reviewer", status=StepStatus.PENDING)
    run = WorkflowRun.objects.create(organization=org, generation=gen, run_number=1, status=WorkflowRunStatus.PENDING, created_by=user)

    p1 = WorkPackage.objects.create(
        organization=org,
        workflow_run=run,
        generation_step=step1,
        key="pkg_1",
        name="Task 1",
        priority=100,
        status=WorkPackageStatus.PENDING,
        created_by=user,
    )
    p2 = WorkPackage.objects.create(
        organization=org,
        workflow_run=run,
        generation_step=step2,
        key="pkg_2",
        name="Task 2",
        priority=50,
        status=WorkPackageStatus.PENDING,
        created_by=user,
    )
    WorkflowGraphService.add_dependency(p1, p2, dependency_type=DependencyType.HARD)

    return org, user, gen, run, p1, p2, step1, step2


@pytest.mark.django_db
class TestWorkflowSchedulerService:
    """Test suite for DAG progression, worker claims, candidate completions, and verification."""

    def test_tick_advances_root_packages(self, workflow_setup):
        org, user, gen, run, p1, p2, s1, s2 = workflow_setup

        # Initial tick
        advanced = WorkflowSchedulerService.tick(workflow_run_id=run.id)
        assert advanced >= 1

        p1.refresh_from_db()
        p2.refresh_from_db()
        run.refresh_from_db()

        assert run.status == WorkflowRunStatus.RUNNING
        assert p1.status == WorkPackageStatus.READY
        assert p1.ready_at is not None
        assert p2.status == WorkPackageStatus.PENDING  # p2 depends on p1

    def test_claim_next_and_lease(self, workflow_setup):
        org, user, gen, run, p1, p2, s1, s2 = workflow_setup
        WorkflowSchedulerService.tick(workflow_run_id=run.id)

        # Worker claims next ready task
        claim_result = WorkflowSchedulerService.claim_next(worker_id="agent_coder_01", workflow_run_id=run.id)
        assert claim_result is not None
        claimed_pkg, attempt, lease = claim_result

        assert claimed_pkg.id == p1.id
        assert claimed_pkg.status == WorkPackageStatus.RUNNING
        assert claimed_pkg.attempt_count == 1
        assert attempt.attempt_number == 1
        assert attempt.worker_id == "agent_coder_01"
        assert attempt.status == AttemptStatus.RUNNING
        assert lease.worker_id == "agent_coder_01"
        assert not lease.is_expired()

        # Second claim when no other tasks ready returns None
        claim_result2 = WorkflowSchedulerService.claim_next(worker_id="agent_coder_02", workflow_run_id=run.id)
        assert claim_result2 is None

    def test_claim_blocked_for_canonical_non_runnable_states(self, workflow_setup):
        org, user, gen, run, p1, p2, s1, s2 = workflow_setup
        WorkflowSchedulerService.tick(workflow_run_id=run.id)

        for blocked_status in [
            GenerationStatus.PAUSED,
            GenerationStatus.CANCELLING,
            GenerationStatus.CANCELLED,
            GenerationStatus.FAILED,
            GenerationStatus.TIMED_OUT,
            GenerationStatus.BLOCKED,
            GenerationStatus.ACTIVE,
        ]:
            gen.status = blocked_status
            gen.save()
            claim = WorkflowSchedulerService.claim_next(worker_id="worker_01", workflow_run_id=run.id)
            assert claim is None, f"Claim should be blocked when generation is {blocked_status}"

    def test_token_attempt_binding_mismatch_rejected(self, workflow_setup):
        org, user, gen, run, p1, p2, s1, s2 = workflow_setup
        p1.status = WorkPackageStatus.READY
        p1.save()
        p2.status = WorkPackageStatus.READY
        p2.save()

        # Worker 1 claims p1
        pkg1, attempt1, lease1 = WorkflowSchedulerService.claim_next(worker_id="worker_1", workflow_run_id=run.id)
        # Worker 2 claims p2
        pkg2, attempt2, lease2 = WorkflowSchedulerService.claim_next(worker_id="worker_2", workflow_run_id=run.id)

        # Cross-pairing: lease1 token + attempt2 ID must fail
        with pytest.raises(ValidationError) as exc:
            WorkflowSchedulerService.record_candidate_complete(
                attempt_id=attempt2.id,
                lease_token=lease1.lease_token,
                result_payload={"files": ["evil.php"]},
            )
        assert exc.value.code == "lease_attempt_mismatch"

        # Verify state untouched
        lease1.refresh_from_db()
        lease2.refresh_from_db()
        assert lease1.released_at is None
        assert lease2.released_at is None
        pkg1.refresh_from_db()
        pkg2.refresh_from_db()
        assert pkg1.status == WorkPackageStatus.RUNNING
        assert pkg2.status == WorkPackageStatus.RUNNING

    def test_record_attempt_failure_retryable_vs_terminal(self, workflow_setup):
        org, user, gen, run, p1, p2, s1, s2 = workflow_setup
        WorkflowSchedulerService.tick(workflow_run_id=run.id)
        pkg, attempt, lease = WorkflowSchedulerService.claim_next(worker_id="worker_01", workflow_run_id=run.id)

        # 1. Retryable failure -> schedules RETRY_WAIT
        updated_pkg = WorkflowSchedulerService.record_attempt_failure(
            attempt_id=attempt.id,
            lease_token=lease.lease_token,
            failure_category="NETWORK_CONNECTION",
            error_details={"error": "Connection timeout"},
            retryable=True,
        )
        assert updated_pkg.status == WorkPackageStatus.RETRY_WAIT
        assert updated_pkg.next_attempt_at is not None

        # 2. Advance to READY and claim again
        updated_pkg.next_attempt_at = timezone.now() - timezone.timedelta(seconds=1)
        updated_pkg.save()
        WorkflowSchedulerService.tick(workflow_run_id=run.id)

        pkg_2, attempt_2, lease_2 = WorkflowSchedulerService.claim_next(worker_id="worker_01", workflow_run_id=run.id)
        assert attempt_2.attempt_number == 2

        # Non-retryable failure -> marks FAILED
        failed_pkg = WorkflowSchedulerService.record_attempt_failure(
            attempt_id=attempt_2.id,
            lease_token=lease_2.lease_token,
            failure_category="MODEL_ERROR",
            error_details={"error": "Fatal syntax error in prompt"},
            retryable=False,
        )
        assert failed_pkg.status == WorkPackageStatus.FAILED
        assert failed_pkg.failure_category == "MODEL_ERROR"

    def test_record_candidate_complete_does_not_mark_completed(self, workflow_setup):
        org, user, gen, run, p1, p2, s1, s2 = workflow_setup
        WorkflowSchedulerService.tick(workflow_run_id=run.id)
        pkg, attempt, lease = WorkflowSchedulerService.claim_next(worker_id="agent_coder_01", workflow_run_id=run.id)

        # Worker reports candidate complete
        result_payload = {"files": ["plugin.php"], "manifest": {"name": "Test"}}
        updated_pkg = WorkflowSchedulerService.record_candidate_complete(
            attempt_id=attempt.id,
            lease_token=lease.lease_token,
            result_payload=result_payload,
        )

        assert updated_pkg.status == WorkPackageStatus.CANDIDATE_COMPLETE
        assert updated_pkg.result_payload == result_payload

        # Lease must be released
        lease.refresh_from_db()
        assert lease.released_at is not None

        # p2 must still be PENDING because p1 is only CANDIDATE_COMPLETE, not COMPLETED
        WorkflowSchedulerService.tick(workflow_run_id=run.id)
        p2.refresh_from_db()
        assert p2.status == WorkPackageStatus.PENDING

    def test_mark_validated_complete_requires_candidate_complete(self, workflow_setup):
        org, user, gen, run, p1, p2, s1, s2 = workflow_setup
        WorkflowSchedulerService.tick(workflow_run_id=run.id)

        # Attempting validated completion on PENDING or READY package fails
        with pytest.raises(ValidationError) as exc:
            WorkflowSchedulerService.mark_validated_complete(
                work_package_id=p1.id,
                validation_evidence={"qa": "pass"},
            )
        assert exc.value.code == "invalid_package_state"

        # Claim and record candidate complete
        pkg, attempt, lease = WorkflowSchedulerService.claim_next(worker_id="agent_coder_01", workflow_run_id=run.id)
        WorkflowSchedulerService.record_candidate_complete(
            attempt_id=attempt.id,
            lease_token=lease.lease_token,
            result_payload={"files": ["plugin.php"]},
        )

        # Marking validated complete with valid proof
        evidence = {"qa_passed": True, "sandbox_activation": "PASS", "php_errors": 0}
        completed_pkg = WorkflowSchedulerService.mark_validated_complete(
            work_package_id=p1.id,
            validation_evidence=evidence,
        )
        assert completed_pkg.status == WorkPackageStatus.COMPLETED
        assert completed_pkg.completed_at is not None

        # Step 1 should be rolled up to COMPLETED
        s1.refresh_from_db()
        assert s1.status == StepStatus.COMPLETED

        # Next tick advances downstream package p2 to READY
        WorkflowSchedulerService.tick(workflow_run_id=run.id)
        p2.refresh_from_db()
        assert p2.status == WorkPackageStatus.READY

    def test_record_candidate_and_failure_expired_lease_rejected(self, workflow_setup):
        org, user, gen, run, p1, p2, s1, s2 = workflow_setup
        WorkflowSchedulerService.tick(workflow_run_id=run.id)
        pkg, attempt, lease = WorkflowSchedulerService.claim_next(worker_id="agent_coder_01", workflow_run_id=run.id)

        # Expire lease manually
        past_time = timezone.now() - timezone.timedelta(seconds=60)
        lease.expires_at = past_time
        lease.save(update_fields=["expires_at"])

        with pytest.raises(ValidationError) as exc:
            WorkflowSchedulerService.record_candidate_complete(
                attempt_id=attempt.id,
                lease_token=lease.lease_token,
                result_payload={"files": []},
            )
        assert exc.value.code == "lease_expired"

        with pytest.raises(ValidationError) as exc_fail:
            WorkflowSchedulerService.record_attempt_failure(
                attempt_id=attempt.id,
                lease_token=lease.lease_token,
                failure_category="TEST",
                error_details={"err": "fail"},
            )
        assert exc_fail.value.code == "lease_expired"

    def test_record_candidate_complete_during_cancellation_finalizes_generation(self, workflow_setup):
        org, user, gen, run, p1, p2, s1, s2 = workflow_setup
        WorkflowSchedulerService.tick(workflow_run_id=run.id)
        pkg, attempt, lease = WorkflowSchedulerService.claim_next(worker_id="agent_coder_01", workflow_run_id=run.id)

        # Transition generation and run to CANCELLING
        gen.status = GenerationStatus.CANCELLING
        gen.cancel_requested_at = timezone.now()
        gen.save()
        run.status = WorkflowRunStatus.CANCELLING
        run.save()

        # Worker calls candidate complete while cancelling
        updated_pkg = WorkflowSchedulerService.record_candidate_complete(
            attempt_id=attempt.id,
            lease_token=lease.lease_token,
            result_payload={"patch": "partial"},
        )

        assert updated_pkg.status == WorkPackageStatus.CANCELLED
        attempt.refresh_from_db()
        assert attempt.status == AttemptStatus.CANDIDATE_COMPLETE
        assert attempt.result_payload == {"patch": "partial"}

        # Assert generation and run finalized to CANCELLED
        gen.refresh_from_db()
        run.refresh_from_db()
        assert gen.status == GenerationStatus.CANCELLED
        assert run.status == WorkflowRunStatus.CANCELLED

    def test_mark_validated_complete_rejects_inconsistent_attempt_truth(self, workflow_setup):
        org, user, gen, run, p1, p2, s1, s2 = workflow_setup
        WorkflowSchedulerService.tick(workflow_run_id=run.id)
        pkg, attempt, lease = WorkflowSchedulerService.claim_next(worker_id="agent_coder_01", workflow_run_id=run.id)

        # Manually force package to CANDIDATE_COMPLETE while attempt is still RUNNING
        pkg.status = WorkPackageStatus.CANDIDATE_COMPLETE
        pkg.save(update_fields=["status"])

        with pytest.raises(ValidationError) as exc:
            WorkflowSchedulerService.mark_validated_complete(
                work_package_id=pkg.id,
                validation_evidence={"qa": "pass"},
            )
        assert exc.value.code == "invalid_attempt_state"

        # If attempt count differs from latest attempt number
        attempt.status = AttemptStatus.CANDIDATE_COMPLETE
        attempt.save(update_fields=["status"])
        pkg.attempt_count = 99
        pkg.save(update_fields=["attempt_count"])

        with pytest.raises(ValidationError) as exc_mismatch:
            WorkflowSchedulerService.mark_validated_complete(
                work_package_id=pkg.id,
                validation_evidence={"qa": "pass"},
            )
        assert exc_mismatch.value.code == "attempt_count_mismatch"
