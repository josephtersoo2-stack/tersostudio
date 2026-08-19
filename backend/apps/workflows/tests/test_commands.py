"""Tests for WorkflowCommandService idempotent control commands (PAUSE, RESUME, CANCEL, RETRY)."""
import uuid
import pytest
from django.core.exceptions import ValidationError

from apps.accounts.models import User
from apps.generations.enums import GenerationStatus
from apps.generations.models import Generation
from apps.organizations.models import Organization
from apps.products.models import WordPressProduct
from apps.projects.models import Project
from apps.workflows.enums import CommandType, WorkflowRunStatus
from apps.workflows.models import WorkflowCommand, WorkflowRun
from apps.workflows.services.commands import WorkflowCommandService


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
    run = WorkflowRun.objects.create(
        organization=org,
        generation=gen,
        run_number=1,
        status=WorkflowRunStatus.RUNNING,
        created_by=user,
    )
    return org, user, gen, run


@pytest.mark.django_db
class TestWorkflowCommandService:
    """Test suite for idempotent control commands."""

    def test_pause_and_idempotent_replay(self, command_setup):
        org, user, gen, run = command_setup
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
        org, user, gen, run = command_setup
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
        org, user, gen, run = command_setup
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
        assert res["status"] == GenerationStatus.BUILDING
        gen.refresh_from_db()
        assert gen.status == GenerationStatus.BUILDING
