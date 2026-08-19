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
