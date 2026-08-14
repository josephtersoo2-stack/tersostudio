"""Live End-to-End Smoke Test for Tersuite Agent Runtime + OpenHands SDK v1.42.1.

Validates the full chain:
Tersuite Runtime -> OpenHands Conversation -> send message -> run -> receive events -> execution completes.

Requires:
  - Python 3.12+
  - PostgreSQL
  - openhands-sdk==1.42.1
  - Live OpenHands Agent Server at OPENHANDS_SERVER_URL (default http://localhost:8010)
  - Real LLM API Key (e.g. ANTHROPIC_API_KEY / OPENAI_API_KEY)
"""
import os
import unittest
import httpx
from runtime.adapters.openhands.config import OpenHandsServerConfig
from runtime.adapters.openhands.adapter import OpenHandsAgentRuntime
from runtime.interfaces.session import ExecutionStatus, SessionConfig, SessionStatus


def is_openhands_server_available(server_url: str) -> bool:
    """Check whether a real OpenHands Agent Server instance is running."""
    try:
        response = httpx.get(f"{server_url.rstrip('/')}/docs", timeout=2.0)
        return response.status_code == 200
    except Exception:
        return False


class OpenHandsLiveSmokeTests(unittest.TestCase):
    """End-to-end integration test executed against a live OpenHands Agent Server."""

    def setUp(self):
        self.server_url = os.getenv("OPENHANDS_SERVER_URL", "http://localhost:8010")
        self.api_key = os.getenv("OPENHANDS_API_KEY", "")

        # Verify live server accessibility
        if not is_openhands_server_available(self.server_url):
            self.skipTest(
                f"NOT RUN — Live OpenHands Agent Server unavailable at '{self.server_url}'. "
                "To run live end-to-end smoke tests, start the OpenHands Agent Server on port 8010."
            )

        self.config = OpenHandsServerConfig(
            server_url=self.server_url,
            api_key=self.api_key or None,
            timeout_seconds=90,
        )
        self.runtime = OpenHandsAgentRuntime(self.config)

    def test_live_openhands_roundtrip_execution(self):
        """Execute real end-to-end task against OpenHands Agent Server."""
        session_config = SessionConfig(
            generation_id="gen-live-smoke-001",
            agent_run_id="run-live-smoke-001",
            model="anthropic/claude-sonnet-4-5-20250929",
            system_prompt="You are a WordPress testing assistant. Respond strictly with 'TERSUITE_VERIFIED'.",
        )

        # 1. Create real conversation on OpenHands server (POST /api/conversations)
        session = self.runtime.create_session(session_config)
        self.assertIsNotNone(session.session_id)
        self.assertIsNotNone(session.remote_conversation_id)
        self.assertEqual(session.status, SessionStatus.ACTIVE)

        # 2. Dispatch message and trigger run (POST /api/conversations/{id}/events & /run)
        task_result = self.runtime.send_task(
            session_id=session.session_id,
            prompt="Respond with TERSUITE_VERIFIED",
        )

        # 3. Assert real execution completion
        self.assertTrue(task_result.success)
        self.assertEqual(task_result.execution_status, ExecutionStatus.SUCCESS)
        self.assertIn("TERSUITE_VERIFIED", task_result.output)

        # 4. Observe recorded events (GET /api/conversations/{id}/events/search)
        events = self.runtime.get_historical_events(session.session_id)
        self.assertTrue(len(events) >= 1)

        # 5. Clean up session
        self.runtime.close_session(session.session_id)
