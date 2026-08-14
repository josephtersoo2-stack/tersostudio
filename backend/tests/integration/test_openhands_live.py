"""Live Smoke Test for OpenHands Agent Server integration.

This test connects to a REAL OpenHands Agent Server instance.
If the server is unavailable in the current test environment, the test is explicitly
marked as SKIPPED / NOT RUN rather than fabricated as a pass.
"""
import os
import unittest
import httpx
from runtime.adapters.openhands.config import OpenHandsServerConfig
from runtime.adapters.openhands.adapter import OpenHandsAgentRuntime
from runtime.interfaces.session import SessionConfig, SessionStatus


def is_openhands_server_available(server_url: str) -> bool:
    """Check if the remote OpenHands Agent Server is reachable."""
    try:
        response = httpx.get(f"{server_url.rstrip('/')}/docs", timeout=2.0)
        return response.status_code == 200
    except Exception:
        return False


class OpenHandsLiveSmokeTests(unittest.TestCase):
    """Smoke test suite executed against live OpenHands Agent Server."""

    def setUp(self):
        self.server_url = os.getenv("OPENHANDS_SERVER_URL", "http://localhost:8010")
        self.api_key = os.getenv("OPENHANDS_API_KEY", "")

        # Check live server connectivity before running
        if not is_openhands_server_available(self.server_url):
            self.skipTest(
                f"NOT RUN — OpenHands Agent Server unavailable at '{self.server_url}'. "
                "Launch the OpenHands Agent Server container/process to run live smoke tests."
            )

        self.config = OpenHandsServerConfig(
            server_url=self.server_url,
            api_key=self.api_key or None,
            timeout_seconds=60,
        )
        self.runtime = OpenHandsAgentRuntime(self.config)

    def test_live_openhands_roundtrip(self):
        """Execute real end-to-end conversation creation and task execution."""
        session_config = SessionConfig(
            generation_id="gen-smoke-001",
            agent_run_id="run-smoke-001",
            model="anthropic/claude-sonnet-4-5-20250929",
            system_prompt="You are an automated testing assistant. Output 'SMOKE_TEST_OK'.",
        )

        # 1. Create real session on OpenHands server
        session = self.runtime.create_session(session_config)
        self.assertIsNotNone(session.session_id)
        self.assertIsNotNone(session.remote_conversation_id)
        self.assertEqual(session.status, SessionStatus.ACTIVE)

        # 2. Dispatch task
        task_result = self.runtime.send_task(
            session_id=session.session_id,
            prompt="Respond with SMOKE_TEST_OK",
        )
        self.assertTrue(task_result.success)
        self.assertIn("SMOKE_TEST_OK", task_result.output)

        # 3. Retrieve historical events
        events = self.runtime.get_historical_events(session.session_id)
        self.assertTrue(len(events) >= 1)

        # 4. Clean up session
        self.runtime.close_session(session.session_id)
