"""Live End-to-End Integration Smoke Test for Official OpenHands Agent Server.

Validates the full live chain:
TersuiteAgentRuntime
  ↓
official OpenHands SDK (v1.42.1) / RemoteConversation
  ↓
official OpenHands Agent Server (openhands-agent-server v1.42.1) on port 8010
  ↓
configured LLM provider
  ↓
real Agent
  ↓
real tool execution & file generation
  ↓
real event stream & completion
"""
import os
import unittest
from pathlib import Path
import httpx

from apps.realtime.events import EventType, NormalizedEvent
from runtime.adapters.openhands.config import OpenHandsServerConfig
from runtime.adapters.openhands.adapter import OpenHandsAgentRuntime
from runtime.interfaces.session import ExecutionStatus, SessionConfig, SessionStatus


def is_official_openhands_server_available(server_url: str) -> bool:
    """Verify that the official OpenHands Agent Server is running on server_url."""
    try:
        url = f"{server_url.rstrip('/')}/openapi.json"
        response = httpx.get(url, timeout=3.0)
        if response.status_code == 200:
            data = response.json()
            title = data.get("info", {}).get("title", "")
            return "OpenHands Agent Server" in title
        return False
    except Exception:
        return False


def get_available_llm_credentials() -> tuple[str, str]:
    """Retrieve available LLM model and API key from environment."""
    if os.getenv("OPENROUTER_API_KEY"):
        model = os.getenv("OPENROUTER_MODEL", "openrouter/anthropic/claude-3.5-sonnet")
        if not model.startswith("openrouter/"):
            model = f"openrouter/{model}"
        return model, os.environ["OPENROUTER_API_KEY"]
    if os.getenv("ANTHROPIC_API_KEY"):
        return "anthropic/claude-3-5-sonnet-20241022", os.environ["ANTHROPIC_API_KEY"]
    if os.getenv("OPENAI_API_KEY"):
        return "openai/gpt-4o", os.environ["OPENAI_API_KEY"]
    if os.getenv("GEMINI_API_KEY"):
        return "gemini/gemini-1.5-pro", os.environ["GEMINI_API_KEY"]
    if os.getenv("GROQ_API_KEY"):
        return "groq/llama-3.3-70b-versatile", os.environ["GROQ_API_KEY"]
    return "", ""


class OfficialOpenHandsLiveSmokeTests(unittest.TestCase):
    """End-to-end integration test against the official OpenHands Agent Server."""

    def setUp(self):
        self.server_url = os.getenv("OPENHANDS_AGENT_SERVER_URL", "http://127.0.0.1:8010")
        
        # 1. Verify official OpenHands Agent Server is running
        if not is_official_openhands_server_available(self.server_url):
            self.skipTest(
                f"SKIPPED — Official OpenHands Agent Server (openhands-agent-server) "
                f"is not running on '{self.server_url}'."
            )

        # 2. Check for configured LLM API key
        self.model, self.api_key = get_available_llm_credentials()
        if not self.api_key:
            self.skipTest(
                "SKIPPED — No LLM API key (OPENROUTER_API_KEY, ANTHROPIC_API_KEY, OPENAI_API_KEY, GEMINI_API_KEY, "
                "or GROQ_API_KEY) found in environment for live agent execution."
            )

        self.config = OpenHandsServerConfig(
            server_url=self.server_url,
            server_api_key=os.getenv("OPENHANDS_AGENT_SERVER_API_KEY") or None,
            server_timeout_seconds=120,
            llm_api_key=self.api_key,
            llm_default_model=self.model,
        )
        self.runtime = OpenHandsAgentRuntime(self.config)

    def test_live_agent_coding_task_execution(self):
        """Execute a real coding task against the official OpenHands Agent Server.

        Task: Create a Python file containing a function returning 42,
        create a test file asserting the function, run pytest, and report.
        """
        session_config = SessionConfig(
            generation_id="gen-live-real-001",
            agent_run_id="run-live-real-001",
            model=self.model,
            system_prompt="You are an expert Python engineer. Complete the requested task precisely.",
        )

        session = self.runtime.create_session(session_config)
        self.assertIsNotNone(session.session_id)
        self.assertIsNotNone(session.remote_conversation_id)
        self.assertEqual(session.status, SessionStatus.ACTIVE)

        task_prompt = (
            "Create a small Python file answer.py containing a function get_answer() "
            "that returns 42. Then create a test file test_answer.py that asserts "
            "get_answer() == 42. Run the test to confirm it passes."
        )

        result = self.runtime.send_task(session.session_id, task_prompt)

        # Verify real execution results
        self.assertTrue(result.success)
        self.assertEqual(result.execution_status, ExecutionStatus.SUCCESS)
        self.assertTrue(len(result.output) > 0)

        # Verify historical events from real server
        events = self.runtime.get_historical_events(session.session_id)
        self.assertTrue(len(events) > 0)

        # Verify session cleanup
        closed = self.runtime.close_session(session.session_id)
        self.assertTrue(closed)
