"""Tests for staff-only Control Center operational action mutation endpoints."""
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.generations.enums import (
    AgentRunStatus,
    GenerationStatus,
    StepStatus,
)
from apps.generations.models import AgentRun, Generation, GenerationMilestone, GenerationStep
from apps.organizations.services import ensure_personal_organization
from apps.projects.models import Project
from apps.projects.services import ProjectService

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def staff_user(db):
    return User.objects.create_user(
        email="ops_lead@tersuite.com",
        password="StaffPassword123!",
        is_staff=True,
    )


@pytest.fixture
def non_staff_user(db):
    return User.objects.create_user(
        email="regular_user@tersuite.com",
        password="RegularPassword123!",
        is_staff=False,
    )


@pytest.fixture
def sample_project(db, non_staff_user):
    org = ensure_personal_organization(non_staff_user)
    return ProjectService.create_project(
        organization=org,
        actor=non_staff_user,
        name="Operational Actions Project",
        description="Testing CC-03 operational mutation controls",
    )


@pytest.fixture
def active_generation(db, sample_project, non_staff_user):
    gen = Generation.objects.create(
        organization=sample_project.organization,
        project=sample_project,
        created_by=non_staff_user,
        prompt="Build WooCommerce high-throughput webhook sync plugin",
        status=GenerationStatus.BUILDING,
        current_step_number=1,
        total_steps=2,
    )
    milestone = GenerationMilestone.objects.create(
        generation=gen,
        name="Scaffolding & Coding",
        sequence=1,
    )
    step1 = GenerationStep.objects.create(
        generation=gen,
        milestone=milestone,
        step_number=1,
        name="Architecture Scaffolding",
        agent_role="architect",
        status=StepStatus.RUNNING,
        started_at=timezone.now(),
    )
    step2 = GenerationStep.objects.create(
        generation=gen,
        milestone=milestone,
        step_number=2,
        name="Code Implementation",
        agent_role="coder",
        status=StepStatus.PENDING,
    )
    run1 = AgentRun.objects.create(
        step=step1,
        run_number=1,
        runtime_type="mock",
        status=AgentRunStatus.RUNNING,
        prompt="Scaffold architecture files.",
        started_at=timezone.now(),
    )
    return gen, step1, step2, run1


@pytest.mark.django_db
class TestControlCenterGenerationCancel:
    """Tests for POST /api/v1/control-center/generations/<id>/cancel/."""

    def test_cancel_generation_anonymous_unauthorized(self, api_client, active_generation):
        gen, _, _, _ = active_generation
        url = f"/api/v1/control-center/generations/{gen.id}/cancel/"
        response = api_client.post(url, {"reason": "Test cancel"})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_cancel_generation_non_staff_forbidden(self, api_client, non_staff_user, active_generation):
        gen, _, _, _ = active_generation
        api_client.force_authenticate(user=non_staff_user)
        url = f"/api/v1/control-center/generations/{gen.id}/cancel/"
        response = api_client.post(url, {"reason": "Test cancel"})
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_cancel_generation_staff_happy_path(self, api_client, staff_user, active_generation):
        gen, step1, step2, run1 = active_generation
        api_client.force_authenticate(user=staff_user)

        url = f"/api/v1/control-center/generations/{gen.id}/cancel/"
        response = api_client.post(url, {"reason": "Manual operator intervention."})

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == str(gen.id)
        assert data["status"] == GenerationStatus.CANCELLED
        assert data["timestamps"]["cancelled_at"] is not None

        # Verify DB state
        gen.refresh_from_db()
        step1.refresh_from_db()
        step2.refresh_from_db()
        run1.refresh_from_db()

        assert gen.status == GenerationStatus.CANCELLED
        assert gen.cancelled_at is not None
        assert step1.status == StepStatus.CANCELLED
        assert step1.completed_at is not None
        assert step2.status == StepStatus.CANCELLED
        assert run1.status == AgentRunStatus.CANCELLED
        assert run1.completed_at is not None

    def test_cancel_generation_rejection_on_completed_generation(self, api_client, staff_user, sample_project, non_staff_user):
        gen = Generation.objects.create(
            organization=sample_project.organization,
            project=sample_project,
            created_by=non_staff_user,
            prompt="Completed plugin",
            status=GenerationStatus.ACTIVE,
            completed_at=timezone.now(),
        )
        api_client.force_authenticate(user=staff_user)

        url = f"/api/v1/control-center/generations/{gen.id}/cancel/"
        response = api_client.post(url, {"reason": "Try cancel completed"})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert data["error"] == "cannot_cancel"
        assert "ACTIVE" in data["detail"]

    def test_cancel_generation_rejection_on_already_cancelled_generation(self, api_client, staff_user, sample_project, non_staff_user):
        gen = Generation.objects.create(
            organization=sample_project.organization,
            project=sample_project,
            created_by=non_staff_user,
            prompt="Cancelled plugin",
            status=GenerationStatus.CANCELLED,
            cancelled_at=timezone.now(),
        )

        api_client.force_authenticate(user=staff_user)

        url = f"/api/v1/control-center/generations/{gen.id}/cancel/"
        response = api_client.post(url, {"reason": "Try cancel again"})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert data["error"] == "cannot_cancel"

    def test_cancel_generation_404_on_missing_uuid(self, api_client, staff_user):
        import uuid
        api_client.force_authenticate(user=staff_user)
        url = f"/api/v1/control-center/generations/{uuid.uuid4()}/cancel/"
        response = api_client.post(url, {})
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestControlCenterStepRetry:
    """Tests for POST /api/v1/control-center/steps/<id>/retry/."""

    def test_retry_step_anonymous_unauthorized(self, api_client, active_generation):
        _, step1, _, _ = active_generation
        url = f"/api/v1/control-center/steps/{step1.id}/retry/"
        response = api_client.post(url, {})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_retry_step_non_staff_forbidden(self, api_client, non_staff_user, active_generation):
        _, step1, _, _ = active_generation
        api_client.force_authenticate(user=non_staff_user)
        url = f"/api/v1/control-center/steps/{step1.id}/retry/"
        response = api_client.post(url, {})
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_retry_step_staff_happy_path_on_failed_step(self, api_client, staff_user, sample_project, non_staff_user):
        gen = Generation.objects.create(
            organization=sample_project.organization,
            project=sample_project,
            created_by=non_staff_user,
            prompt="Plugin with a failed step",
            status=GenerationStatus.FAILED,
            failed_at=timezone.now(),
            error_message="Agent syntax crash",
        )
        milestone = GenerationMilestone.objects.create(
            generation=gen,
            name="Schema",
            sequence=1,
        )
        step = GenerationStep.objects.create(
            generation=gen,
            milestone=milestone,
            step_number=1,
            name="Schema Generation",
            agent_role="architect",
            status=StepStatus.FAILED,
            error_message="Agent syntax crash",
            started_at=timezone.now(),
            completed_at=timezone.now(),
        )
        run1 = AgentRun.objects.create(
            step=step,
            run_number=1,
            runtime_type="mock",
            status=AgentRunStatus.FAILED,
            prompt="Generate schema",
            failure_category="SYNTAX_ERROR",
        )

        api_client.force_authenticate(user=staff_user)
        url = f"/api/v1/control-center/steps/{step.id}/retry/"
        response = api_client.post(url, {})

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "step" in data
        assert "run" in data
        assert data["generation_id"] == str(gen.id)
        assert data["generation_status"] == GenerationStatus.BUILDING

        assert data["step"]["id"] == str(step.id)
        assert data["step"]["status"] == StepStatus.RUNNING
        assert data["step"]["error_message"] == ""

        assert data["run"]["run_number"] == 2
        assert data["run"]["status"] == AgentRunStatus.QUEUED

        # Verify DB updates
        gen.refresh_from_db()
        step.refresh_from_db()
        assert gen.status == GenerationStatus.BUILDING
        assert step.status == StepStatus.RUNNING
        assert step.runs.count() == 2

    def test_retry_step_rejection_on_cancelled_generation(self, api_client, staff_user, sample_project, non_staff_user):
        gen = Generation.objects.create(
            organization=sample_project.organization,
            project=sample_project,
            created_by=non_staff_user,
            prompt="Cancelled plugin generation",
            status=GenerationStatus.CANCELLED,
            cancelled_at=timezone.now(),
        )
        milestone = GenerationMilestone.objects.create(
            generation=gen,
            name="Scaffolding",
            sequence=1,
        )
        step = GenerationStep.objects.create(
            generation=gen,
            milestone=milestone,
            step_number=1,
            name="Scaffolding",
            agent_role="architect",
            status=StepStatus.CANCELLED,
            completed_at=timezone.now(),
        )

        api_client.force_authenticate(user=staff_user)
        url = f"/api/v1/control-center/steps/{step.id}/retry/"
        response = api_client.post(url, {})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert data["error"] == "cannot_retry"
        assert "CANCELLED" in data["detail"]

    def test_retry_step_rejection_on_completed_step(self, api_client, staff_user, sample_project, non_staff_user):
        gen = Generation.objects.create(
            organization=sample_project.organization,
            project=sample_project,
            created_by=non_staff_user,
            prompt="Plugin generation",
            status=GenerationStatus.BUILDING,
        )
        milestone = GenerationMilestone.objects.create(
            generation=gen,
            name="Milestone",
            sequence=1,
        )
        step = GenerationStep.objects.create(
            generation=gen,
            milestone=milestone,
            step_number=1,
            name="Completed Step",
            agent_role="architect",
            status=StepStatus.COMPLETED,
            completed_at=timezone.now(),
        )

        api_client.force_authenticate(user=staff_user)
        url = f"/api/v1/control-center/steps/{step.id}/retry/"
        response = api_client.post(url, {})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert data["error"] == "cannot_retry"
        assert "COMPLETED" in data["detail"]

    def test_retry_step_rejection_on_running_step(self, api_client, staff_user, sample_project, non_staff_user):
        gen = Generation.objects.create(
            organization=sample_project.organization,
            project=sample_project,
            created_by=non_staff_user,
            prompt="Plugin generation",
            status=GenerationStatus.BUILDING,
        )
        milestone = GenerationMilestone.objects.create(
            generation=gen,
            name="Milestone",
            sequence=1,
        )
        step = GenerationStep.objects.create(
            generation=gen,
            milestone=milestone,
            step_number=1,
            name="In Flight Step",
            agent_role="coder",
            status=StepStatus.RUNNING,
            started_at=timezone.now(),
        )

        api_client.force_authenticate(user=staff_user)
        url = f"/api/v1/control-center/steps/{step.id}/retry/"
        response = api_client.post(url, {})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert data["error"] == "cannot_retry"
        assert "RUNNING" in data["detail"]

    def test_retry_step_rejection_on_completed_generation(self, api_client, staff_user, sample_project, non_staff_user):
        gen = Generation.objects.create(
            organization=sample_project.organization,
            project=sample_project,
            created_by=non_staff_user,
            prompt="Done plugin",
            status=GenerationStatus.ACTIVE,
            completed_at=timezone.now(),
        )
        milestone = GenerationMilestone.objects.create(
            generation=gen,
            name="Milestone",
            sequence=1,
        )
        step = GenerationStep.objects.create(
            generation=gen,
            milestone=milestone,
            step_number=1,
            name="Failed Step On Done Generation",
            agent_role="security",
            status=StepStatus.FAILED,
        )

        api_client.force_authenticate(user=staff_user)
        url = f"/api/v1/control-center/steps/{step.id}/retry/"
        response = api_client.post(url, {})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert data["error"] == "cannot_retry"
        assert "ACTIVE" in data["detail"]
