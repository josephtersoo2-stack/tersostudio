"""Tests for WorkflowSchedulerService driving DAG execution, leases, claims, and verified completion."""
import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.accounts.models import User
from apps.generations.enums import GenerationStatus, StepStatus
from apps.generations.models import Generation, GenerationStep
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
    WorkPackageDependency,
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
    step1 = GenerationStep.objects.create(generation=gen, step_number=1, name="Step 1", agent_role="coder", status=StepStatus.PENDING)
    step2 = GenerationStep.objects.create(generation=gen, step_number=2, name="Step 2", agent_role="reviewer", status=StepStatus.PENDING)
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

    def test_mark_validated_complete_advances_dag(self, workflow_setup):
        org, user, gen, run, p1, p2, s1, s2 = workflow_setup
        WorkflowSchedulerService.tick(workflow_run_id=run.id)
        pkg, attempt, lease = WorkflowSchedulerService.claim_next(worker_id="agent_coder_01", workflow_run_id=run.id)
        WorkflowSchedulerService.record_candidate_complete(
            attempt_id=attempt.id,
            lease_token=lease.lease_token,
            result_payload={"files": ["plugin.php"]},
        )

        # Attempting validated completion without structured evidence fails
        with pytest.raises(ValidationError):
            WorkflowSchedulerService.mark_validated_complete(work_package_id=p1.id, validation_evidence={})

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
