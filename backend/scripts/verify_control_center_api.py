"""Probe and verify Control Center CC-01, CC-02, and CC-03 API endpoints and mutation enforcement."""
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
    print("TERSUITE CONTROL CENTER (CC-03) API VERIFICATION")
    print("==================================================")

    client = APIClient()

    # Create/get customer and staff accounts
    customer_user, _ = User.objects.get_or_create(
        email="customer.actions@tersuite.com",
        defaults={"first_name": "Customer", "last_name": "Actions", "is_staff": False},
    )
    customer_user.is_staff = False
    customer_user.is_superuser = False
    customer_user.save()
    token_cust, _ = Token.objects.get_or_create(user=customer_user)

    staff_user, _ = User.objects.get_or_create(
        email="staff.actions@tersuite.com",
        defaults={"first_name": "Staff", "last_name": "Operator", "is_staff": True},
    )
    staff_user.is_staff = True
    staff_user.save()
    token_staff, _ = Token.objects.get_or_create(user=staff_user)

    # 1. Ensure a live active generation for cancellation and retry verification
    project, _ = Project.objects.get_or_create(
        user=customer_user,
        name="CC-03 Operational Actions Project",
        defaults={"description": "End-to-end mutation testing"},
    )
    generation = Generation.objects.create(
        project=project,
        user=customer_user,
        prompt="Create a WordPress plugin that integrates high-frequency stock price webhooks.",
        status=GenerationStatus.BUILDING,
        current_step_number=1,
        total_steps=2,
        metadata={"wp_version": "6.6", "php_target": "8.3"},
    )
    step1 = GenerationStep.objects.create(
        generation=generation,
        step_number=1,
        name="Webhook Architecture & Database Schema",
        agent_role="architect",
        status=StepStatus.RUNNING,
        input_payload={"spec": "Stock Webhooks"},
    )
    step2 = GenerationStep.objects.create(
        generation=generation,
        step_number=2,
        name="REST Handler & Poller Implementation",
        agent_role="coder",
        status=StepStatus.PENDING,
    )
    run1 = AgentRun.objects.create(
        step=step1,
        run_number=1,
        runtime_type="mock",
        status="RUNNING",
        prompt="Scaffold tables for stock ticker webhooks.",
    )

    # Save a sample artifact
    storage = get_artifact_storage()
    file_bytes = b"<?php\n/**\n * Plugin Name: CC-03 Webhook Plugin\n */\n"
    storage_key, size_bytes, checksum = storage.save_artifact(
        generation_id=str(generation.id),
        artifact_id="art-cc03-001",
        filename="cc03-webhook.php",
        content=file_bytes,
    )
    Artifact.objects.create(
        generation=generation,
        agent_run=run1,
        name="cc03-webhook.php",
        file_path="/plugins/cc03-webhook.php",
        artifact_type=ArtifactType.SOURCE_CODE,
        mime_type="text/x-php",
        size_bytes=size_bytes,
        checksum_sha256=checksum,
        storage_backend="local_filesystem",
        storage_key=storage_key,
    )

    # 1. Anonymous Access Test on Mutations (Expect 401)
    print("\n--- 1. Anonymous Access Test on Mutation Endpoints ---")
    cancel_url = f"/api/v1/control-center/generations/{generation.id}/cancel/"
    retry_url = f"/api/v1/control-center/steps/{step1.id}/retry/"

    resp_cancel_anon = client.post(cancel_url, {"reason": "Unauthorized test"})
    resp_retry_anon = client.post(retry_url, {})
    print(f"POST {cancel_url[:45]}... -> HTTP {resp_cancel_anon.status_code} (Expected 401)")
    print(f"POST {retry_url[:45]}... -> HTTP {resp_retry_anon.status_code} (Expected 401)")
    assert resp_cancel_anon.status_code == 401
    assert resp_retry_anon.status_code == 401
    print("[PASS] Mutation endpoints reject anonymous access with 401 Unauthorized.")

    # 2. Non-Staff Access Test on Mutations (Expect 403)
    print("\n--- 2. Non-Staff Authenticated Access Test ---")
    client.credentials(HTTP_AUTHORIZATION=f"Token {token_cust.key}")
    resp_cancel_cust = client.post(cancel_url, {"reason": "Non-staff test"})
    resp_retry_cust = client.post(retry_url, {})
    print(f"POST {cancel_url[:45]}... -> HTTP {resp_cancel_cust.status_code} (Expected 403)")
    print(f"POST {retry_url[:45]}... -> HTTP {resp_retry_cust.status_code} (Expected 403)")
    assert resp_cancel_cust.status_code == 403
    assert resp_retry_cust.status_code == 403
    print("[PASS] Mutation endpoints reject non-staff users with 403 Forbidden.")

    # 3. Staff Cancel Generation Mutation Test (Expect 200)
    print("\n--- 3. Staff Cancel Generation Mutation Test ---")
    client.credentials(HTTP_AUTHORIZATION=f"Token {token_staff.key}")
    resp_cancel = client.post(cancel_url, {"reason": "Operator halted task for config adjustment."})
    print(f"POST {cancel_url} -> HTTP {resp_cancel.status_code} (Expected 200)")
    assert resp_cancel.status_code == 200
    cancel_data = resp_cancel.json()
    assert cancel_data["status"] == GenerationStatus.CANCELLED
    assert cancel_data["timestamps"]["cancelled_at"] is not None
    print("[PASS] Generation successfully transitioned to CANCELLED.")

    # 4. Duplicate Cancel Rejection (Expect 400)
    print("\n--- 4. Duplicate Cancel Rejection Test ---")
    resp_cancel_dup = client.post(cancel_url, {"reason": "Try cancel again"})
    print(f"POST {cancel_url} -> HTTP {resp_cancel_dup.status_code} (Expected 400)")
    assert resp_cancel_dup.status_code == 400
    assert resp_cancel_dup.json()["error"] == "cannot_cancel"
    print("[PASS] Duplicate cancellation properly rejected with 400 Bad Request.")

    # 5. Staff Retry Step Mutation Test on Cancelled Step (Expect 200)
    print("\n--- 5. Staff Retry Step Mutation Test ---")
    resp_retry = client.post(retry_url, {})
    print(f"POST {retry_url} -> HTTP {resp_retry.status_code} (Expected 200)")
    assert resp_retry.status_code == 200
    retry_data = resp_retry.json()
    assert retry_data["generation_status"] == GenerationStatus.BUILDING
    assert retry_data["step"]["status"] == StepStatus.RUNNING
    assert retry_data["run"]["run_number"] == 2
    assert retry_data["run"]["status"] == "QUEUED"
    print("[PASS] Step successfully retried, parent generation resumed BUILDING, AgentRun #2 created.")

    # Print Sample Mutation JSON
    print("\n==================================================")
    print("SAMPLE JSON: POST /api/v1/control-center/generations/<id>/cancel/")
    print("==================================================")
    print(json.dumps(cancel_data, indent=2))

    print("\n==================================================")
    print("SAMPLE JSON: POST /api/v1/control-center/steps/<id>/retry/")
    print("==================================================")
    print(json.dumps(retry_data, indent=2))


if __name__ == "__main__":
    main()
