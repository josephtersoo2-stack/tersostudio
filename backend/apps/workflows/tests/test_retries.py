"""Tests for WorkflowRetryService exponential backoff and eligibility rules."""
import pytest
from apps.accounts.models import User
from apps.generations.enums import GenerationStatus
from apps.generations.models import Generation, GenerationMilestone, GenerationStep
from apps.organizations.models import Organization
from apps.products.models import WordPressProduct
from apps.projects.models import Project
from apps.workflows.enums import WorkflowRunStatus, WorkPackageStatus
from apps.workflows.models import WorkflowRun, WorkPackage, WorkPackageAttempt
from apps.workflows.services.retries import WorkflowRetryService


@pytest.mark.django_db
class TestWorkflowRetryService:
    """Test suite for deterministic retry calculations and eligibility."""

    def test_calculate_retry_delay_exponential_growth(self):
        # Base 30s, max 900s
        assert WorkflowRetryService.calculate_retry_delay(attempt_number=1, base_seconds=30, max_seconds=900) == 30
        assert WorkflowRetryService.calculate_retry_delay(attempt_number=2, base_seconds=30, max_seconds=900) == 60
        assert WorkflowRetryService.calculate_retry_delay(attempt_number=3, base_seconds=30, max_seconds=900) == 120
        assert WorkflowRetryService.calculate_retry_delay(attempt_number=4, base_seconds=30, max_seconds=900) == 240
        assert WorkflowRetryService.calculate_retry_delay(attempt_number=5, base_seconds=30, max_seconds=900) == 480
        assert WorkflowRetryService.calculate_retry_delay(attempt_number=6, base_seconds=30, max_seconds=900) == 900  # Capped at max 900

    def test_should_retry_respects_max_attempts(self, db):
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
            max_attempts=3,
            attempt_count=2,
            created_by=user,
        )
        attempt = WorkPackageAttempt.objects.create(work_package=pkg, attempt_number=2, worker_id="w1", retryable=True)
        assert WorkflowRetryService.should_retry(pkg, attempt) is True

        pkg.attempt_count = 3
        assert WorkflowRetryService.should_retry(pkg, attempt) is False

        # Non-retryable attempt
        pkg.attempt_count = 1
        attempt.retryable = False
        assert WorkflowRetryService.should_retry(pkg, attempt) is False

    def test_package_retry_base_seconds_honored(self, db):
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
            key="pkg_custom_base",
            name="Custom Base Task",
            retry_base_seconds=45,
            attempt_count=2,
            created_by=user,
        )
        initial_version = pkg.state_version
        from django.utils import timezone
        now = timezone.now()
        updated_pkg = WorkflowRetryService.schedule_retry(pkg, now=now)

        # Expected delay = min(45 * 2 ** (2 - 1), 900) = 90 seconds
        expected_next = now + timezone.timedelta(seconds=90)
        assert abs((updated_pkg.next_attempt_at - expected_next).total_seconds()) < 1
        assert updated_pkg.status == WorkPackageStatus.RETRY_WAIT

        # Assert state_version persisted atomically
        pkg.refresh_from_db()
        assert pkg.state_version == initial_version + 1
        assert pkg.status == WorkPackageStatus.RETRY_WAIT

    def test_automatic_retry_blocked_in_non_runnable_states(self, db):
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
            key="pkg_states",
            name="State Test Task",
            created_by=user,
        )
        attempt = WorkPackageAttempt.objects.create(work_package=pkg, attempt_number=1, worker_id="w1", retryable=True)

        for non_runnable in [
            GenerationStatus.BLOCKED,
            GenerationStatus.PAUSED,
            GenerationStatus.CANCELLING,
            GenerationStatus.CANCELLED,
            GenerationStatus.FAILED,
            GenerationStatus.ACTIVE,
        ]:
            gen.status = non_runnable
            assert WorkflowRetryService.should_retry(pkg, attempt, manual_mode=False) is False

    def test_manual_retry_policy_allows_blocked_failed_timed_out(self, db):
        user = User.objects.create(email="worker@tersuite.com", password="Password123!")
        org = Organization.objects.create(name="Tersuite Lab", slug="tersuite-lab", created_by=user)
        prod = WordPressProduct.objects.create(organization=org, display_name="Plugin A", slug="plugin-a", created_by=user)
        proj = Project.objects.create(organization=org, product=prod, name="Proj A", slug="proj-a", created_by=user)
        gen = Generation.objects.create(organization=org, project=proj, prompt="Build WP plugin", status=GenerationStatus.BLOCKED, created_by=user)
        milestone = GenerationMilestone.objects.create(generation=gen, name="Milestone 1", sequence=1)
        step = GenerationStep.objects.create(generation=gen, milestone=milestone, step_number=1, name="Step 1", agent_role="coder")
        run = WorkflowRun.objects.create(organization=org, generation=gen, run_number=1, status=WorkflowRunStatus.RUNNING, created_by=user)

        pkg = WorkPackage.objects.create(
            organization=org,
            workflow_run=run,
            generation_step=step,
            key="pkg_manual",
            name="Manual Task",
            created_by=user,
        )
        attempt = WorkPackageAttempt.objects.create(work_package=pkg, attempt_number=1, worker_id="w1", retryable=True)

        # BLOCKED -> allowed in manual mode
        assert WorkflowRetryService.should_retry(pkg, attempt, manual_mode=True) is True

        # FAILED -> allowed in manual mode
        gen.status = GenerationStatus.FAILED
        assert WorkflowRetryService.should_retry(pkg, attempt, manual_mode=True) is True

        # TIMED_OUT -> allowed in manual mode
        gen.status = GenerationStatus.TIMED_OUT
        assert WorkflowRetryService.should_retry(pkg, attempt, manual_mode=True) is True

        # ACTIVE -> rejected in manual mode
        gen.status = GenerationStatus.ACTIVE
        assert WorkflowRetryService.should_retry(pkg, attempt, manual_mode=True) is False
