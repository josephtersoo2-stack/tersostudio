"""Probe and verify Control Center CC-01 & CC-02 API endpoints and permission enforcement."""
import json
import os
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

import django
django.setup()

from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from apps.generations.enums import ArtifactType, GenerationStatus, StepStatus
from apps.generations.models import Artifact, Generation, GenerationStep, AgentRun
from apps.generations.storage import get_artifact_storage
from apps.projects.models import Project

User = get_user_model()


def main():
    print("==================================================")
    print("TERSUITE CONTROL CENTER (CC-02) API VERIFICATION")
    print("==================================================")

    client = APIClient()

    # Create/get customer and staff accounts
    customer_user, _ = User.objects.get_or_create(
        email="customer.probe@tersuite.com",
        defaults={"first_name": "Customer", "last_name": "Probe", "is_staff": False},
    )
    customer_user.is_staff = False
    customer_user.is_superuser = False
    customer_user.save()
    token_cust, _ = Token.objects.get_or_create(user=customer_user)

    staff_user, _ = User.objects.get_or_create(
        email="staff.operator@tersuite.com",
        defaults={"first_name": "Staff", "last_name": "Operator", "is_staff": True},
    )
    staff_user.is_staff = True
    staff_user.save()
    token_staff, _ = Token.objects.get_or_create(user=staff_user)

    # Ensure a sample generation, run, and real physical artifact exists for verification
    project, _ = Project.objects.get_or_create(
        user=customer_user,
        name="CC-02 Verification Project",
        defaults={"description": "End-to-end operational verification"},
    )
    generation, _ = Generation.objects.get_or_create(
        project=project,
        user=customer_user,
        prompt="Create a WordPress plugin that integrates Stripe checkout and dynamic webhook listeners.",
        defaults={
            "status": GenerationStatus.BUILDING,
            "current_step_number": 1,
            "total_steps": 2,
            "metadata": {"wp_version": "6.5", "php_target": "8.2"},
        },
    )
    step, _ = GenerationStep.objects.get_or_create(
        generation=generation,
        step_number=1,
        name="Architecture Blueprint & Class Scaffolding",
        defaults={
            "agent_role": "architect",
            "status": StepStatus.COMPLETED,
            "input_payload": {"spec": "Stripe Gateway"},
            "output_payload": {"classes": ["WC_Gateway_Stripe"]},
        },
    )
    run, _ = AgentRun.objects.get_or_create(
        step=step,
        run_number=1,
        defaults={
            "runtime_type": "openhands",
            "model_name": "openrouter/openai/gpt-4o-mini",
            "session_id": "oh-sess-probe-01",
            "remote_conversation_id": "conv-uuid-probe-01",
            "prompt": "Draft class WC_Gateway_Stripe and unit tests.",
            "output": "Class WC_Gateway_Stripe scaffolded and verified.",
            "token_usage": {"prompt_tokens": 650, "completion_tokens": 140},
        },
    )

    # Save real physical artifact
    storage = get_artifact_storage()
    file_bytes = b"<?php\n/**\n * Plugin Name: CC-02 Verification Gateway\n */\nclass WC_Gateway_Probe {}\n"
    storage_key, size_bytes, checksum = storage.save_artifact(
        generation_id=str(generation.id),
        artifact_id="art-probe-001",
        filename="cc02-gateway-probe.php",
        content=file_bytes,
    )
    artifact, _ = Artifact.objects.get_or_create(
        generation=generation,
        name="cc02-gateway-probe.php",
        defaults={
            "agent_run": run,
            "file_path": "/plugins/cc02-gateway-probe.php",
            "artifact_type": ArtifactType.SOURCE_CODE,
            "mime_type": "text/x-php",
            "size_bytes": size_bytes,
            "checksum_sha256": checksum,
            "storage_backend": "local_filesystem",
            "storage_key": storage_key,
        },
    )

    # 1. Anonymous Access Test (Expect 401)
    print("\n--- 1. Anonymous Access Test ---")
    endpoints = [
        f"/api/v1/control-center/generations/{generation.id}/",
        f"/api/v1/control-center/runs/{run.id}/",
        "/api/v1/control-center/health/",
        "/api/v1/control-center/artifacts/",
        f"/api/v1/control-center/artifacts/{artifact.id}/download/",
    ]
    for ep in endpoints:
        resp = client.get(ep)
        print(f"GET {ep[:45]}... -> HTTP {resp.status_code} (Expected 401)")
        assert resp.status_code == 401
    print("[PASS] All CC-02 endpoints strictly reject anonymous requests with 401 Unauthorized.")

    # 2. Non-Staff Access Test (Expect 403)
    print("\n--- 2. Non-Staff Authenticated Access Test ---")
    client.credentials(HTTP_AUTHORIZATION=f"Token {token_cust.key}")
    for ep in endpoints:
        resp = client.get(ep)
        print(f"GET {ep[:45]}... -> HTTP {resp.status_code} (Expected 403)")
        assert resp.status_code == 403
    print("[PASS] All CC-02 endpoints strictly reject authenticated non-staff requests with 403 Forbidden.")

    # 3. Staff Access Test (Expect 200)
    print("\n--- 3. Staff Authenticated Access Test ---")
    client.credentials(HTTP_AUTHORIZATION=f"Token {token_staff.key}")
    resp_gen = client.get(f"/api/v1/control-center/generations/{generation.id}/")
    resp_run = client.get(f"/api/v1/control-center/runs/{run.id}/")
    resp_health = client.get("/api/v1/control-center/health/")
    resp_arts = client.get("/api/v1/control-center/artifacts/")
    resp_dl = client.get(f"/api/v1/control-center/artifacts/{artifact.id}/download/")

    print(f"GET /generations/{generation.id}/ -> HTTP {resp_gen.status_code} (Expected 200)")
    print(f"GET /runs/{run.id}/        -> HTTP {resp_run.status_code} (Expected 200)")
    print(f"GET /health/                               -> HTTP {resp_health.status_code} (Expected 200)")
    print(f"GET /artifacts/                            -> HTTP {resp_arts.status_code} (Expected 200)")
    print(f"GET /artifacts/{artifact.id}/download/     -> HTTP {resp_dl.status_code} (Expected 200)")

    assert resp_gen.status_code == 200
    assert resp_run.status_code == 200
    assert resp_health.status_code == 200
    assert resp_arts.status_code == 200
    assert resp_dl.status_code == 200
    assert resp_dl.content == file_bytes
    print("[PASS] Staff requests succeeded with 200 OK and valid artifact content.")

    # Print Sample JSON
    print("\n==================================================")
    print("SAMPLE JSON: GET /api/v1/control-center/generations/<id>/")
    print("==================================================")
    print(json.dumps(resp_gen.json(), indent=2))

    print("\n==================================================")
    print("SAMPLE JSON: GET /api/v1/control-center/runs/<id>/")
    print("==================================================")
    print(json.dumps(resp_run.json(), indent=2))

    print("\n==================================================")
    print("SAMPLE JSON: GET /api/v1/control-center/health/")
    print("==================================================")
    print(json.dumps(resp_health.json(), indent=2))

    print("\n==================================================")
    print("SAMPLE JSON: GET /api/v1/control-center/artifacts/")
    print("==================================================")
    print(json.dumps(resp_arts.json(), indent=2))


if __name__ == "__main__":
    main()
