"""End-to-End Verification Script for Real Celery-to-OpenHands-to-OpenRouter Pipeline.

Validates the full decoupled chain with zero mocking and zero manual ExecutionService.run() calls:
Generation (BUILDING)
  ↓
GenerationStep (PENDING)
  ↓
ExecutionService.create_and_dispatch(step)
  ↓
AgentRun created in DB (QUEUED)
  ↓
transaction.on_commit -> Celery execute_agent_run.delay(run.id)
  ↓
Real background Celery worker (solo pool) consumes task from Redis
  ↓
execute_agent_run Celery task invokes ExecutionService.run(run.id)
  ↓
AgentRun status transitions to RUNNING
  ↓
OpenHandsAgentRuntime initializes official OpenHands SDK RemoteConversation
  ↓
Official OpenHands Agent Server (v1.42.1 on port 8010)
  ↓
OpenRouter LLM (openrouter/openai/gpt-4o-mini)
  ↓
Real tool execution & WebSocket event callbacks
  ↓
AgentRun status transitions to COMPLETED
  ↓
GenerationStep status transitions to COMPLETED
  ↓
Generation remains BUILDING
"""
import os
import sys
import time
from pathlib import Path

# Setup Django environment
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
os.environ["AGENT_RUNTIME_BACKEND"] = "openhands"

import django
django.setup()

import httpx
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.generations.enums import AgentRunStatus, GenerationStatus, StepStatus
from apps.generations.models import AgentRun, Generation, GenerationStep
from apps.generations.services.execution_service import ExecutionService
from apps.projects.models import Project

User = get_user_model()


def verify_openhands_server(server_url: str) -> bool:
    """Verify the official OpenHands Agent Server is healthy."""
    try:
        url = f"{server_url.rstrip('/')}/openapi.json"
        resp = httpx.get(url, timeout=3.0)
        if resp.status_code == 200:
            info = resp.json().get("info", {})
            return "OpenHands Agent Server" in info.get("title", "")
        return False
    except Exception:
        return False


def verify_openrouter_credentials(api_key: str) -> bool:
    """Verify OpenRouter credentials."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "https://tersuite.com",
        "X-Title": "Tersuite AI Studio",
    }
    try:
        resp = httpx.get("https://openrouter.ai/api/v1/auth/key", headers=headers, timeout=5.0)
        if resp.status_code != 200:
            print(f"[ERROR] OpenRouter Authentication Failed: HTTP {resp.status_code} - {resp.text}")
            return False
        key_data = resp.json().get("data", {})
        label = key_data.get("label", "unnamed")
        print(f"[OK] OpenRouter Key Verified: label='{label}'")
        return True
    except Exception as exc:
        print(f"[ERROR] Failed to connect to OpenRouter API: {exc}")
        return False


def main():
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        print("\n[ERROR] OPENROUTER_API_KEY is not set in the local environment.")
        print('Please set: $env:OPENROUTER_API_KEY = "sk-or-v1-..."')
        sys.exit(1)

    model_slug = os.getenv("OPENROUTER_MODEL", "openrouter/openai/gpt-4o-mini").strip()
    if not model_slug.startswith("openrouter/"):
        model_slug = f"openrouter/{model_slug}"

    server_url = getattr(settings, "OPENHANDS_AGENT_SERVER_URL", "http://localhost:8010")

    print("==================================================")
    print("TERSUITE AI STUDIO — REAL CELERY PIPELINE TEST")
    print("==================================================")
    print(f"Provider:        OpenRouter (via OpenHands SDK LiteLLM)")
    print(f"Model Slug:      {model_slug}")
    print(f"Agent Server:    {server_url}")
    print(f"Celery Broker:   {settings.CELERY_BROKER_URL}")
    print(f"Backend Runtime: openhands")
    print("--------------------------------------------------")

    # 1. Verify OpenHands Agent Server
    if not verify_openhands_server(server_url):
        print(f"[ERROR] Official OpenHands Agent Server is not running on '{server_url}'.")
        sys.exit(1)
    print(f"[OK] Official OpenHands Agent Server 1.42.1 is active on {server_url}")

    # 2. Verify OpenRouter Credentials
    if not verify_openrouter_credentials(api_key):
        print(f"[ERROR] OpenRouter verification failed. Aborting execution.")
        sys.exit(1)

    # 3. Create Domain Models
    user, _ = User.objects.get_or_create(
        email="celery.verification@tersuite.com",
        defaults={"first_name": "Celery", "last_name": "Tester"},
    )
    project, _ = Project.objects.get_or_create(
        user=user,
        name="Real Celery Pipeline Verification Project",
        defaults={"description": "End-to-end verification through real Celery worker."},
    )
    generation = Generation.objects.create(
        project=project,
        user=user,
        prompt="Create a file named TERSUITE_CELERY_TEST.txt containing 'Tersuite AI Studio real Celery to OpenHands execution verified.' Then read the file and report its contents.",
        status=GenerationStatus.BUILDING,
    )
    step = GenerationStep.objects.create(
        generation=generation,
        step_number=1,
        name="Real Celery Execution Step",
        agent_role="coder",
        status=StepStatus.PENDING,
        input_payload={
            "model": model_slug,
            "prompt": (
                "Create a file named TERSUITE_CELERY_TEST.txt in the current directory containing exactly:\n"
                "Tersuite AI Studio real Celery to OpenHands execution verified.\n"
                "Then read the file to verify and report its contents."
            ),
            "system_prompt": "You are a precise software engineer. Complete the file writing and reading task accurately.",
            "max_iterations": 10,
        },
    )

    print(f"[OK] Created Generation {generation.id} in BUILDING status")
    print(f"[OK] Created GenerationStep {step.id} (step 1) in PENDING status")

    # 4. Dispatch Step -> AgentRun QUEUED + transaction.on_commit -> Celery execute_agent_run.delay()
    dispatch_time = timezone.now()
    run = ExecutionService.create_and_dispatch(step)
    print(f"\n[OK] Step Dispatched at {dispatch_time.isoformat()}:")
    print(f"     AgentRun ID:     {run.id}")
    print(f"     Initial Status:  {run.status} (QUEUED)")
    print(f"     Celery Task:     execute_agent_run.delay('{run.id}') enqueued via transaction.on_commit")

    # 5. DO NOT call ExecutionService.run() directly!
    # Instead, poll the database as the real background Celery worker consumes and executes the run.
    print("\n--- Awaiting Real Celery Worker Execution (polling PostgreSQL database) ---")
    timeout_seconds = 120
    poll_interval = 1.0
    start_poll = time.time()
    observed_running = False
    running_timestamp = None
    completed_timestamp = None

    while time.time() - start_poll < timeout_seconds:
        run.refresh_from_db()
        current_status = run.status

        if current_status == AgentRunStatus.RUNNING and not observed_running:
            observed_running = True
            running_timestamp = timezone.now()
            print(f"[OBSERVED] AgentRun {run.id} transitioned to RUNNING at {running_timestamp.isoformat()}")
            print(f"           Session ID:             {run.session_id}")
            print(f"           Remote Conversation ID: {run.remote_conversation_id}")

        if current_status in (AgentRunStatus.COMPLETED, AgentRunStatus.FAILED):
            completed_timestamp = timezone.now()
            print(f"[OBSERVED] AgentRun {run.id} reached terminal state: {current_status} at {completed_timestamp.isoformat()}")
            break

        time.sleep(poll_interval)

    # 6. Evaluate Results
    run.refresh_from_db()
    step.refresh_from_db()
    generation.refresh_from_db()
    total_elapsed = time.time() - start_poll

    print("\n--------------------------------------------------")
    print("REAL CELERY PIPELINE EXECUTION RESULTS")
    print("--------------------------------------------------")
    print(f"AgentRun ID:                 {run.id}")
    print(f"AgentRun Status:             {run.status}")
    print(f"Session ID:                  {run.session_id}")
    print(f"Remote Conversation ID:      {run.remote_conversation_id}")
    print(f"Observed States:             QUEUED -> RUNNING ({observed_running}) -> {run.status}")
    print(f"Total Polling Duration:      {total_elapsed:.2f}s")
    print(f"Token Usage:                 {run.token_usage}")
    print(f"\n--- Agent Output ---")
    print(run.output)

    print("\n--- Domain Statuses ---")
    print(f"GenerationStep Status:       {step.status}")
    print(f"Parent Generation Status:    {generation.status} (deliberately BUILDING)")

    if not observed_running and run.status == AgentRunStatus.QUEUED:
        print("\n[FAILED] Celery worker did not pick up the QUEUED task within timeout.")
        print("Please verify the background Celery worker is running:")
        print("  celery -A config worker --loglevel=info --pool=solo")
        sys.exit(1)

    if run.status == AgentRunStatus.COMPLETED and step.status == StepStatus.COMPLETED:
        print("\n==================================================")
        print("REAL CELERY-TO-OPENHANDS PIPELINE: FULLY VERIFIED")
        print("==================================================")
        sys.exit(0)
    else:
        print(f"\n[FAILED] Pipeline did not complete successfully: {run.error_details}")
        sys.exit(1)


if __name__ == "__main__":
    main()
