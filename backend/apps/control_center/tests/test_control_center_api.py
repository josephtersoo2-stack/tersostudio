"""Tests for staff-only Control Center API endpoints."""
import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from apps.generations.enums import (
    AgentRunStatus,
    ArtifactType,
    GenerationStatus,
    StepStatus,
)
from apps.generations.models import (
    AgentRun,
    Artifact,
    Generation,
    GenerationStep,
    Workspace,
)
from apps.projects.models import Project

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def staff_user(db):
    return User.objects.create_user(
        email="staff.operator@tersuite.com",
        password="StaffPassword123!",
        first_name="Staff",
        last_name="Operator",
        is_staff=True,
    )


@pytest.fixture
def normal_user_a(db):
    return User.objects.create_user(
        email="customer.a@tersuite.com",
        password="CustomerPassword123!",
        first_name="Customer",
        last_name="Alpha",
        is_staff=False,
    )


@pytest.fixture
def normal_user_b(db):
    return User.objects.create_user(
        email="customer.b@tersuite.com",
        password="CustomerPassword123!",
        first_name="Customer",
        last_name="Beta",
        is_staff=False,
    )


@pytest.fixture
def seed_data(db, normal_user_a, normal_user_b):
    # Projects for Customer A & B
    project_a = Project.objects.create(
        user=normal_user_a,
        name="Alpha WooCommerce Plugin",
        description="Affiliate tracking module",
        is_archived=False,
    )
    project_b = Project.objects.create(
        user=normal_user_b,
        name="Beta Membership Addon",
        description="Subscription manager",
        is_archived=True,
    )

    # Generation 1 (Alpha user - BUILDING)
    long_prompt = "Build a WooCommerce affiliate plugin with high performance tracking " * 5
    gen_1 = Generation.objects.create(
        project=project_a,
        user=normal_user_a,
        prompt=long_prompt,
        status=GenerationStatus.BUILDING,
        current_step_number=1,
        total_steps=2,
    )
    workspace_1 = Workspace.objects.create(
        generation=gen_1,
        workspace_path="/var/workspaces/gen_1",
    )
    step_1 = GenerationStep.objects.create(
        generation=gen_1,
        step_number=1,
        name="Scaffold Architecture",
        agent_role="architect",
        status=StepStatus.COMPLETED,
    )
    step_2 = GenerationStep.objects.create(
        generation=gen_1,
        step_number=2,
        name="Implement Hooks",
        agent_role="coder",
        status=StepStatus.RUNNING,
    )
    run_1 = AgentRun.objects.create(
        step=step_1,
        run_number=1,
        runtime_type="openhands",
        model_name="openrouter/openai/gpt-4o-mini",
        status=AgentRunStatus.COMPLETED,
        session_id="oh-sess-001",
        remote_conversation_id="conv-uuid-001",
        prompt="Create initial directory structure and manifest.json " * 4,
        output="Created directories and verified manifest.json successfully. " * 6,
        token_usage={"prompt_tokens": 500, "completion_tokens": 120},
    )
    run_2 = AgentRun.objects.create(
        step=step_2,
        run_number=1,
        runtime_type="openhands",
        model_name="openrouter/anthropic/claude-3.5-sonnet",
        status=AgentRunStatus.RUNNING,
        session_id="oh-sess-002",
        remote_conversation_id="conv-uuid-002",
        prompt="Write action hooks for cart recalculation",
        output="",
    )
    artifact_1 = Artifact.objects.create(
        generation=gen_1,
        agent_run=run_1,
        name="manifest.json",
        artifact_type=ArtifactType.CONFIGURATION,
        file_path="/var/workspaces/gen_1/manifest.json",
        size_bytes=1024,
    )

    # Generation 2 (Beta user - FAILED)
    gen_2 = Generation.objects.create(
        project=project_b,
        user=normal_user_b,
        prompt="Build a membership gatekeeper plugin",
        status=GenerationStatus.FAILED,
        failure_category="TIMEOUT",
        error_message="Agent session timed out while querying database schema " * 4,
        current_step_number=1,
        total_steps=1,
    )
    step_b1 = GenerationStep.objects.create(
        generation=gen_2,
        step_number=1,
        name="Database Schema Creation",
        agent_role="architect",
        status=StepStatus.FAILED,
    )
    run_b1 = AgentRun.objects.create(
        step=step_b1,
        run_number=1,
        runtime_type="openhands",
        model_name="openrouter/openai/gpt-4o-mini",
        status=AgentRunStatus.FAILED,
        failure_category="TIMEOUT",
        prompt="Generate custom table migrations",
        output="Failed to complete migration script.",
    )

    return {
        "project_a": project_a,
        "project_b": project_b,
        "gen_1": gen_1,
        "gen_2": gen_2,
        "run_1": run_1,
        "run_2": run_2,
        "run_b1": run_b1,
        "artifact_1": artifact_1,
    }


@pytest.mark.django_db
class TestControlCenterPermissions:
    """Validate strict staff-only access control boundary."""

    def test_anonymous_user_cannot_access_summary(self, api_client):
        response = api_client.get("/api/v1/control-center/summary/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_anonymous_user_cannot_access_generations(self, api_client):
        response = api_client.get("/api/v1/control-center/generations/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_anonymous_user_cannot_access_runs(self, api_client):
        response = api_client.get("/api/v1/control-center/runs/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_authenticated_non_staff_cannot_access_summary(self, api_client, normal_user_a):
        api_client.force_authenticate(user=normal_user_a)
        response = api_client.get("/api/v1/control-center/summary/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_authenticated_non_staff_cannot_access_generations(self, api_client, normal_user_a):
        api_client.force_authenticate(user=normal_user_a)
        response = api_client.get("/api/v1/control-center/generations/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_authenticated_non_staff_cannot_access_runs(self, api_client, normal_user_a):
        api_client.force_authenticate(user=normal_user_a)
        response = api_client.get("/api/v1/control-center/runs/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_staff_user_can_access_summary(self, api_client, staff_user):
        api_client.force_authenticate(user=staff_user)
        response = api_client.get("/api/v1/control-center/summary/")
        assert response.status_code == status.HTTP_200_OK

    def test_staff_user_can_access_generations(self, api_client, staff_user):
        api_client.force_authenticate(user=staff_user)
        response = api_client.get("/api/v1/control-center/generations/")
        assert response.status_code == status.HTTP_200_OK

    def test_staff_user_can_access_runs(self, api_client, staff_user):
        api_client.force_authenticate(user=staff_user)
        response = api_client.get("/api/v1/control-center/runs/")
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestControlCenterSummaryEndpoint:
    """Validate summary metrics aggregation and security posture."""

    def test_summary_response_contains_required_keys_and_accurate_counts(
        self, api_client, staff_user, seed_data
    ):
        api_client.force_authenticate(user=staff_user)
        response = api_client.get("/api/v1/control-center/summary/")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert "projects" in data
        assert "generations" in data
        assert "agent_runs" in data
        assert "steps" in data
        assert "artifacts" in data
        assert "runtime" in data

        # Projects verification
        assert data["projects"]["total"] == 2
        assert data["projects"]["active"] == 1
        assert data["projects"]["archived"] == 1

        # Generations verification
        assert data["generations"]["total"] == 2
        assert data["generations"]["active"] == 1  # 1 BUILDING, 1 FAILED
        assert data["generations"]["building"] == 1
        assert data["generations"]["failed"] == 1

        # Agent Runs verification
        assert data["agent_runs"]["total"] == 3
        assert data["agent_runs"]["completed"] == 1
        assert data["agent_runs"]["running"] == 1
        assert data["agent_runs"]["failed"] == 1

        # Steps verification
        assert data["steps"]["total"] == 3
        assert data["steps"]["completed"] == 1
        assert data["steps"]["running"] == 1
        assert data["steps"]["failed"] == 1

        # Artifacts verification
        assert data["artifacts"]["total"] == 1
        assert data["artifacts"]["configuration"] == 1

    def test_summary_response_does_not_expose_secrets(self, api_client, staff_user, seed_data):
        api_client.force_authenticate(user=staff_user)
        response = api_client.get("/api/v1/control-center/summary/")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        runtime = data["runtime"]
        assert "openrouter_configured" in runtime
        assert "openhands_api_key_configured" in runtime
        assert isinstance(runtime["openrouter_configured"], bool)
        assert isinstance(runtime["openhands_api_key_configured"], bool)

        # Check raw text dump of response for forbidden substrings
        content_str = str(data)
        assert "sk-or-v1" not in content_str
        assert "OPENROUTER_API_KEY" not in content_str
        assert "OPENHANDS_API_KEY" not in content_str
        assert "OPENHANDS_AGENT_SERVER_API_KEY" not in content_str
        assert "SECRET_KEY" not in content_str
        assert "postgres://" not in content_str
        assert "redis://" not in content_str


@pytest.mark.django_db
class TestControlCenterGenerationsListEndpoint:
    """Validate generations listing, cross-tenant visibility, pagination, and filters."""

    def test_staff_can_view_cross_tenant_generations(
        self, api_client, staff_user, seed_data
    ):
        api_client.force_authenticate(user=staff_user)
        response = api_client.get("/api/v1/control-center/generations/")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["pagination"]["count"] == 2
        emails = [item["user_email"] for item in data["results"]]
        assert "customer.a@tersuite.com" in emails
        assert "customer.b@tersuite.com" in emails

    def test_generations_status_filter(self, api_client, staff_user, seed_data):
        api_client.force_authenticate(user=staff_user)

        response = api_client.get("/api/v1/control-center/generations/?status=BUILDING")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["pagination"]["count"] == 1
        assert data["results"][0]["status"] == "BUILDING"
        assert data["results"][0]["project_name"] == "Alpha WooCommerce Plugin"

        response_failed = api_client.get("/api/v1/control-center/generations/?status=FAILED")
        assert response_failed.status_code == status.HTTP_200_OK
        data_failed = response_failed.json()
        assert data_failed["pagination"]["count"] == 1
        assert data_failed["results"][0]["status"] == "FAILED"

    def test_generations_project_and_user_filters(self, api_client, staff_user, seed_data):
        api_client.force_authenticate(user=staff_user)
        project_a = seed_data["project_a"]

        response = api_client.get(f"/api/v1/control-center/generations/?project_id={project_a.id}")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["pagination"]["count"] == 1
        assert response.json()["results"][0]["project_id"] == str(project_a.id)

    def test_generations_search(self, api_client, staff_user, seed_data):
        api_client.force_authenticate(user=staff_user)

        # Search by prompt snippet
        response = api_client.get("/api/v1/control-center/generations/?search=membership")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["pagination"]["count"] == 1
        assert response.json()["results"][0]["project_name"] == "Beta Membership Addon"

        # Search by user email
        response_email = api_client.get("/api/v1/control-center/generations/?search=customer.a")
        assert response_email.status_code == status.HTTP_200_OK
        assert response_email.json()["pagination"]["count"] == 1

        # Search by failure category
        response_fail = api_client.get("/api/v1/control-center/generations/?search=TIMEOUT")
        assert response_fail.status_code == status.HTTP_200_OK
        assert response_fail.json()["pagination"]["count"] == 1

    def test_generations_preview_truncation(self, api_client, staff_user, seed_data):
        api_client.force_authenticate(user=staff_user)
        response = api_client.get("/api/v1/control-center/generations/")
        assert response.status_code == status.HTTP_200_OK

        results = response.json()["results"]
        for item in results:
            assert len(item["prompt_preview"]) <= 140
            assert len(item["error_message_preview"]) <= 140

        # Check that long prompt was truncated with "..."
        gen1_item = next(it for it in results if it["project_name"] == "Alpha WooCommerce Plugin")
        assert gen1_item["prompt_preview"].endswith("...")

    def test_generations_pagination_envelope(self, api_client, staff_user, seed_data):
        api_client.force_authenticate(user=staff_user)
        response = api_client.get("/api/v1/control-center/generations/?page=1&page_size=1")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["pagination"]["count"] == 2
        assert data["pagination"]["total_pages"] == 2
        assert data["pagination"]["current_page"] == 1
        assert data["pagination"]["page_size"] == 1
        assert len(data["results"]) == 1


@pytest.mark.django_db
class TestControlCenterAgentRunsListEndpoint:
    """Validate agent runs listing, filters, search, and preview bounds."""

    def test_staff_can_view_cross_tenant_runs(self, api_client, staff_user, seed_data):
        api_client.force_authenticate(user=staff_user)
        response = api_client.get("/api/v1/control-center/runs/")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["pagination"]["count"] == 3
        emails = [item["user_email"] for item in data["results"]]
        assert "customer.a@tersuite.com" in emails
        assert "customer.b@tersuite.com" in emails

    def test_runs_status_and_runtime_filters(self, api_client, staff_user, seed_data):
        api_client.force_authenticate(user=staff_user)

        response_running = api_client.get("/api/v1/control-center/runs/?status=RUNNING")
        assert response_running.status_code == status.HTTP_200_OK
        assert response_running.json()["pagination"]["count"] == 1
        assert response_running.json()["results"][0]["status"] == "RUNNING"

        response_openhands = api_client.get("/api/v1/control-center/runs/?runtime_type=openhands")
        assert response_openhands.status_code == status.HTTP_200_OK
        assert response_openhands.json()["pagination"]["count"] == 3

    def test_runs_model_and_failure_category_filters(self, api_client, staff_user, seed_data):
        api_client.force_authenticate(user=staff_user)

        response_claude = api_client.get("/api/v1/control-center/runs/?model=claude-3.5-sonnet")
        assert response_claude.status_code == status.HTTP_200_OK
        assert response_claude.json()["pagination"]["count"] == 1
        assert "claude-3.5-sonnet" in response_claude.json()["results"][0]["model_name"]

        response_timeout = api_client.get("/api/v1/control-center/runs/?failure_category=TIMEOUT")
        assert response_timeout.status_code == status.HTTP_200_OK
        assert response_timeout.json()["pagination"]["count"] == 1
        assert response_timeout.json()["results"][0]["failure_category"] == "TIMEOUT"

    def test_runs_search(self, api_client, staff_user, seed_data):
        api_client.force_authenticate(user=staff_user)

        # Search by session_id
        response = api_client.get("/api/v1/control-center/runs/?search=oh-sess-001")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["pagination"]["count"] == 1
        assert response.json()["results"][0]["session_id"] == "oh-sess-001"

        # Search by step name
        response_step = api_client.get("/api/v1/control-center/runs/?search=Database Schema")
        assert response_step.status_code == status.HTTP_200_OK
        assert response_step.json()["pagination"]["count"] == 1

    def test_runs_preview_truncations(self, api_client, staff_user, seed_data):
        api_client.force_authenticate(user=staff_user)
        response = api_client.get("/api/v1/control-center/runs/")
        assert response.status_code == status.HTTP_200_OK

        results = response.json()["results"]
        for item in results:
            assert len(item["prompt_preview"]) <= 140
            assert len(item["output_preview"]) <= 180

        run1_item = next(it for it in results if it["session_id"] == "oh-sess-001")
        assert run1_item["prompt_preview"].endswith("...")
        assert run1_item["output_preview"].endswith("...")
        assert run1_item["token_usage"] == {"prompt_tokens": 500, "completion_tokens": 120}
