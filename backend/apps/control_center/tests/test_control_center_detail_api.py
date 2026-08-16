"""Tests for CC-02 operational detail, health, artifacts, and download endpoints."""
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
from apps.generations.storage import get_artifact_storage
from apps.projects.models import Project

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def staff_user(db):
    return User.objects.create_user(
        email="staff.detail.operator@tersuite.com",
        password="StaffPassword123!",
        first_name="Staff",
        last_name="Operator",
        is_staff=True,
    )


@pytest.fixture
def normal_user(db):
    return User.objects.create_user(
        email="customer.user@tersuite.com",
        password="CustomerPassword123!",
        first_name="Customer",
        last_name="User",
        is_staff=False,
    )


@pytest.fixture
def sample_operational_tree(db, normal_user):
    """Seed a rich operational tree with generation, step, run, workspace, and stored artifact."""
    project = Project.objects.create(
        user=normal_user,
        name="WooCommerce Enterprise Gateway",
        description="Payment gateway integration",
    )
    full_prompt = (
        "Build a custom WooCommerce payment gateway plugin supporting Stripe webhooks, "
        "refund workflows, and admin configuration tabs."
    )
    generation = Generation.objects.create(
        project=project,
        user=normal_user,
        prompt=full_prompt,
        status=GenerationStatus.BUILDING,
        current_step_number=1,
        total_steps=2,
        metadata={"target_php": "8.2", "wp_version": "6.5"},
    )
    workspace = Workspace.objects.create(
        generation=generation,
        workspace_path="/var/workspaces/woo_gw_01",
        storage_type="local",
        is_active=True,
        disk_usage_bytes=4096,
        metadata={"container_id": "docker_c_99"},
    )
    step_1 = GenerationStep.objects.create(
        generation=generation,
        step_number=1,
        name="Architecture & Webhook Handlers",
        agent_role="architect",
        status=StepStatus.COMPLETED,
        input_payload={"spec": "Stripe webhook endpoint design"},
        output_payload={"classes": ["WC_Gateway_Stripe_Custom", "Webhook_Listener"]},
    )
    run_1 = AgentRun.objects.create(
        step=step_1,
        run_number=1,
        runtime_type="openhands",
        model_name="openrouter/openai/gpt-4o-mini",
        status=AgentRunStatus.COMPLETED,
        session_id="oh-sess-detail-01",
        remote_conversation_id="conv-uuid-detail-01",
        prompt="Draft the class WC_Gateway_Stripe_Custom architecture and write tests.",
        output="Created class WC_Gateway_Stripe_Custom and verified webhook handler.",
        token_usage={"prompt_tokens": 1200, "completion_tokens": 450},
        error_details={},
    )

    # Save real physical artifact via storage singleton
    storage = get_artifact_storage()
    file_bytes = b"<?php\n// WooCommerce Gateway Plugin File\nclass WC_Gateway_Custom {}\n"
    storage_key, size_bytes, checksum = storage.save_artifact(
        generation_id=str(generation.id),
        artifact_id="art-001",
        filename="wc-gateway-custom.php",
        content=file_bytes,
    )

    artifact_1 = Artifact.objects.create(
        generation=generation,
        agent_run=run_1,
        name="wc-gateway-custom.php",
        file_path="/var/workspaces/woo_gw_01/wc-gateway-custom.php",
        artifact_type=ArtifactType.SOURCE_CODE,
        mime_type="text/x-php",
        size_bytes=size_bytes,
        checksum_sha256=checksum,
        storage_backend="local_filesystem",
        storage_key=storage_key,
        metadata={"lines_of_code": 3},
    )

    return {
        "project": project,
        "generation": generation,
        "workspace": workspace,
        "step_1": step_1,
        "run_1": run_1,
        "artifact_1": artifact_1,
        "raw_content": file_bytes,
    }


@pytest.mark.django_db
class TestCC02Permissions:
    """Validate that all CC-02 operational endpoints enforce staff authorization."""

    def test_anonymous_requests_rejected_with_401(self, api_client, sample_operational_tree):
        gen = sample_operational_tree["generation"]
        run = sample_operational_tree["run_1"]
        art = sample_operational_tree["artifact_1"]

        endpoints = [
            f"/api/v1/control-center/generations/{gen.id}/",
            f"/api/v1/control-center/runs/{run.id}/",
            "/api/v1/control-center/health/",
            "/api/v1/control-center/artifacts/",
            f"/api/v1/control-center/artifacts/{art.id}/download/",
        ]

        for endpoint in endpoints:
            resp = api_client.get(endpoint)
            assert resp.status_code == status.HTTP_401_UNAUTHORIZED, f"Expected 401 for {endpoint}"

    def test_non_staff_requests_rejected_with_403(
        self, api_client, normal_user, sample_operational_tree
    ):
        api_client.force_authenticate(user=normal_user)
        gen = sample_operational_tree["generation"]
        run = sample_operational_tree["run_1"]
        art = sample_operational_tree["artifact_1"]

        endpoints = [
            f"/api/v1/control-center/generations/{gen.id}/",
            f"/api/v1/control-center/runs/{run.id}/",
            "/api/v1/control-center/health/",
            "/api/v1/control-center/artifacts/",
            f"/api/v1/control-center/artifacts/{art.id}/download/",
        ]

        for endpoint in endpoints:
            resp = api_client.get(endpoint)
            assert resp.status_code == status.HTTP_403_FORBIDDEN, f"Expected 403 for {endpoint}"

    def test_staff_requests_granted_200(
        self, api_client, staff_user, sample_operational_tree
    ):
        api_client.force_authenticate(user=staff_user)
        gen = sample_operational_tree["generation"]
        run = sample_operational_tree["run_1"]
        art = sample_operational_tree["artifact_1"]

        assert api_client.get(f"/api/v1/control-center/generations/{gen.id}/").status_code == 200
        assert api_client.get(f"/api/v1/control-center/runs/{run.id}/").status_code == 200
        assert api_client.get("/api/v1/control-center/health/").status_code == 200
        assert api_client.get("/api/v1/control-center/artifacts/").status_code == 200
        assert api_client.get(f"/api/v1/control-center/artifacts/{art.id}/download/").status_code == 200


@pytest.mark.django_db
class TestGenerationDetailEndpoint:
    """Validate Generation Detail schema and full operational context."""

    def test_generation_detail_returns_expected_structure(
        self, api_client, staff_user, sample_operational_tree
    ):
        api_client.force_authenticate(user=staff_user)
        gen = sample_operational_tree["generation"]

        response = api_client.get(f"/api/v1/control-center/generations/{gen.id}/")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["id"] == str(gen.id)
        assert data["prompt"] == gen.prompt
        assert data["status"] == "BUILDING"
        assert data["current_step_number"] == 1
        assert data["total_steps"] == 2
        assert data["metadata"] == {"target_php": "8.2", "wp_version": "6.5"}

        # Project & User objects
        assert data["project"]["name"] == "WooCommerce Enterprise Gateway"
        assert data["user"]["email"] == "customer.user@tersuite.com"

        # Timestamps envelope
        assert "created_at" in data["timestamps"]
        assert "updated_at" in data["timestamps"]
        assert data["timestamps"]["completed_at"] is None

        # Steps & nested runs
        assert len(data["steps"]) == 1
        step_data = data["steps"][0]
        assert step_data["name"] == "Architecture & Webhook Handlers"
        assert step_data["status"] == "COMPLETED"
        assert len(step_data["runs"]) == 1
        assert step_data["runs"][0]["model_name"] == "openrouter/openai/gpt-4o-mini"

        # Workspace & Artifacts
        assert data["workspace"] is not None
        assert data["workspace"]["workspace_path"] == "/var/workspaces/woo_gw_01"
        assert len(data["artifacts"]) == 1
        assert data["artifacts"][0]["name"] == "wc-gateway-custom.php"

    def test_nonexistent_generation_returns_404(self, api_client, staff_user):
        api_client.force_authenticate(user=staff_user)
        response = api_client.get("/api/v1/control-center/generations/00000000-0000-0000-0000-000000000000/")
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestAgentRunDetailEndpoint:
    """Validate Agent Run Detail diagnostics and execution metadata."""

    def test_run_detail_returns_expected_diagnostics(
        self, api_client, staff_user, sample_operational_tree
    ):
        api_client.force_authenticate(user=staff_user)
        run = sample_operational_tree["run_1"]

        response = api_client.get(f"/api/v1/control-center/runs/{run.id}/")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["id"] == str(run.id)
        assert data["run_number"] == 1
        assert data["runtime_type"] == "openhands"
        assert data["model_name"] == "openrouter/openai/gpt-4o-mini"
        assert data["session_id"] == "oh-sess-detail-01"
        assert data["remote_conversation_id"] == "conv-uuid-detail-01"
        assert data["prompt"] == run.prompt
        assert data["output"] == run.output
        assert data["token_usage"] == {"prompt_tokens": 1200, "completion_tokens": 450}

        # Parent generation and step context
        assert "id" in data["generation"]
        assert data["generation"]["project_name"] == "WooCommerce Enterprise Gateway"
        assert data["step"]["name"] == "Architecture & Webhook Handlers"

    def test_nonexistent_run_returns_404(self, api_client, staff_user):
        api_client.force_authenticate(user=staff_user)
        response = api_client.get("/api/v1/control-center/runs/00000000-0000-0000-0000-000000000000/")
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestControlCenterHealthEndpoint:
    """Validate health inspection and secret omission."""

    def test_health_response_structure_and_no_secrets(self, api_client, staff_user):
        api_client.force_authenticate(user=staff_user)
        response = api_client.get("/api/v1/control-center/health/")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["status"] in ["ready", "degraded", "unhealthy"]
        assert "services" in data
        assert "database" in data["services"]
        assert "redis" in data["services"]
        assert "celery_broker" in data["services"]
        assert "openhands" in data["services"]
        assert "runtime" in data

        runtime = data["runtime"]
        assert "backend" in runtime
        assert "openrouter_configured" in runtime
        assert "openhands_api_key_configured" in runtime
        assert isinstance(runtime["openrouter_configured"], bool)
        assert isinstance(runtime["openhands_api_key_configured"], bool)

        # Confirm no credentials in serialized response
        content_str = str(data)
        assert "sk-or-v1" not in content_str
        assert "OPENROUTER_API_KEY" not in content_str
        assert "OPENHANDS_API_KEY" not in content_str
        assert "postgres://" not in content_str
        assert "redis://" not in content_str


@pytest.mark.django_db
class TestArtifactsListAndDownloadEndpoints:
    """Validate Artifact listing, filters, and safe authenticated file download."""

    def test_artifacts_list_pagination_and_filters(
        self, api_client, staff_user, sample_operational_tree
    ):
        api_client.force_authenticate(user=staff_user)
        gen = sample_operational_tree["generation"]

        # List all artifacts
        response = api_client.get("/api/v1/control-center/artifacts/")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["pagination"]["count"] == 1
        assert data["results"][0]["name"] == "wc-gateway-custom.php"
        assert data["results"][0]["project_name"] == "WooCommerce Enterprise Gateway"

        # Filter by generation_id
        resp_gen = api_client.get(f"/api/v1/control-center/artifacts/?generation_id={gen.id}")
        assert resp_gen.status_code == status.HTTP_200_OK
        assert resp_gen.json()["pagination"]["count"] == 1

        # Filter by artifact_type
        resp_type = api_client.get("/api/v1/control-center/artifacts/?artifact_type=source_code")
        assert resp_type.status_code == status.HTTP_200_OK
        assert resp_type.json()["pagination"]["count"] == 1

        # Search filter
        resp_search = api_client.get("/api/v1/control-center/artifacts/?search=wc-gateway")
        assert resp_search.status_code == status.HTTP_200_OK
        assert resp_search.json()["pagination"]["count"] == 1

    def test_artifact_download_happy_path(
        self, api_client, staff_user, sample_operational_tree
    ):
        api_client.force_authenticate(user=staff_user)
        art = sample_operational_tree["artifact_1"]
        raw_content = sample_operational_tree["raw_content"]

        response = api_client.get(f"/api/v1/control-center/artifacts/{art.id}/download/")
        assert response.status_code == status.HTTP_200_OK
        assert response.content == raw_content
        assert response.headers["Content-Disposition"] == 'attachment; filename="wc-gateway-custom.php"'
        assert response.headers["Content-Length"] == str(len(raw_content))

    def test_artifact_download_missing_file_returns_404(
        self, api_client, staff_user, sample_operational_tree
    ):
        api_client.force_authenticate(user=staff_user)
        gen = sample_operational_tree["generation"]

        # Create artifact pointing to non-existent storage key
        ghost_art = Artifact.objects.create(
            generation=gen,
            name="ghost-file.txt",
            file_path="/ghost.txt",
            artifact_type=ArtifactType.OTHER,
            storage_key="non_existent/ghost_file.txt",
        )

        response = api_client.get(f"/api/v1/control-center/artifacts/{ghost_art.id}/download/")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_non_staff_cannot_download_artifacts(
        self, api_client, normal_user, sample_operational_tree
    ):
        api_client.force_authenticate(user=normal_user)
        art = sample_operational_tree["artifact_1"]
        response = api_client.get(f"/api/v1/control-center/artifacts/{art.id}/download/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_artifact_download_nonexistent_artifact_returns_404(self, api_client, staff_user):
        api_client.force_authenticate(user=staff_user)
        response = api_client.get("/api/v1/control-center/artifacts/00000000-0000-0000-0000-000000000000/download/")
        assert response.status_code == status.HTTP_404_NOT_FOUND

