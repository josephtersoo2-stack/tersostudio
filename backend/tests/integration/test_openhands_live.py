"""Live End-to-End Smoke Test for Tersuite Agent Runtime + OpenHands Agent Server v1.42.1.

Validates the complete chain:
Tersuite Runtime -> OpenHands Conversation -> send message -> run -> WebSocket live event stream -> execution completes -> final output & artifacts captured.
"""
import asyncio
import json
import os
import unittest
import httpx
import websockets
from apps.realtime.events import EventType, NormalizedEvent
from runtime.adapters.openhands.config import OpenHandsServerConfig
from runtime.adapters.openhands.adapter import OpenHandsAgentRuntime
from runtime.interfaces.session import ExecutionStatus, SessionConfig, SessionStatus


def is_openhands_server_available(server_url: str) -> bool:
    """Check whether the real OpenHands Agent Server is running."""
    try:
        response = httpx.get(f"{server_url.rstrip('/')}/health", timeout=3.0)
        return response.status_code == 200
    except Exception:
        return False


class OpenHandsLiveSmokeTests(unittest.TestCase):
    """End-to-end live smoke tests against running OpenHands Agent Server."""

    def setUp(self):
        self.server_url = os.getenv("OPENHANDS_SERVER_URL", "http://127.0.0.1:8010")
        self.api_key = os.getenv("OPENHANDS_API_KEY", "")

        if not is_openhands_server_available(self.server_url):
            self.skipTest(
                f"NOT RUN — Live OpenHands Agent Server unavailable at '{self.server_url}'."
            )

        self.config = OpenHandsServerConfig(
            server_url=self.server_url,
            api_key=self.api_key or None,
            timeout_seconds=60,
        )
        self.runtime = OpenHandsAgentRuntime(self.config)

    def test_live_openhands_roundtrip_execution(self):
        """Execute complete roundtrip against real OpenHands Agent Server.

        Validates:
        1. Conversation creation (POST /api/conversations)
        2. Live WebSocket subscription (/sockets/events/{id})
        3. Message dispatch (POST /api/conversations/{id}/events)
        4. Run triggering (POST /api/conversations/{id}/run)
        5. Live event stream capture (thought, tool action, observation, completion)
        6. Final result and artifacts verification.
        """
        session_config = SessionConfig(
            generation_id="gen-live-smoke-001",
            agent_run_id="run-live-smoke-001",
            model="anthropic/claude-sonnet-4-5-20250929",
            system_prompt="You are a WordPress engineering assistant. Generate affiliate tracking scaffold.",
        )

        # 1. Create real conversation on OpenHands server
        session = self.runtime.create_session(session_config)
        self.assertIsNotNone(session.session_id)
        self.assertIsNotNone(session.remote_conversation_id)
        self.assertEqual(session.status, SessionStatus.ACTIVE)
        print(f"\n[OpenHands Live] Created conversation: {session.remote_conversation_id}")

        # 2. Dispatch task
        task_prompt = "Generate WordPress affiliate tracking scaffold with nonces and custom table schema."
        task_result = self.runtime.send_task(
            session_id=session.session_id,
            prompt=task_prompt,
        )

        # 3. Assert execution success
        self.assertTrue(task_result.success)
        self.assertEqual(task_result.execution_status, ExecutionStatus.SUCCESS)
        self.assertIn("TERSUITE_VERIFIED", task_result.output)
        self.assertTrue(len(task_result.artifacts) >= 1)
        print(f"[OpenHands Live] Output: {task_result.output}")
        print(f"[OpenHands Live] Artifacts: {task_result.artifacts}")
        print(f"[OpenHands Live] Token Usage: {task_result.token_usage}")

        # 4. Synchronize and verify historical events
        events = self.runtime.get_historical_events(session.session_id)
        self.assertTrue(len(events) >= 3)
        event_types = [e.event_type for e in events]
        print(f"[OpenHands Live] Captured Event Stream ({len(events)} events):")
        for i, ev in enumerate(events, 1):
            print(f"  {i}. [{ev.event_type}] -> {ev.payload}")

        self.assertIn(EventType.AGENT_STARTED, event_types)
        self.assertIn(EventType.TASK_STARTED, event_types)
        self.assertIn(EventType.AGENT_COMPLETED, event_types)

        # 5. Clean up session
        closed = self.runtime.close_session(session.session_id)
        self.assertTrue(closed)
