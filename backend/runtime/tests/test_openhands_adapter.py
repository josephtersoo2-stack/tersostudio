"""Unit tests for the OpenHands Agent Server adapter boundary."""
import unittest
from unittest.mock import MagicMock, patch
import httpx
from apps.realtime.events import EventType
from runtime.adapters.openhands.config import OpenHandsServerConfig
from runtime.adapters.openhands.adapter import OpenHandsAgentRuntime
from runtime.interfaces.session import SessionConfig, SessionStatus


class OpenHandsAdapterTests(unittest.TestCase):
    """Test suite verifying OpenHands adapter boundary logic and event normalization."""

    def setUp(self):
        self.config = OpenHandsServerConfig(
            server_url="http://mock-openhands-server:8000",
            api_key="test-api-key-xyz",
            timeout_seconds=30,
        )
        self.runtime = OpenHandsAgentRuntime(self.config)
        self.session_config = SessionConfig(
            generation_id="gen-oh-001",
            agent_run_id="run-oh-002",
            model="anthropic/claude-sonnet-4-5-20250929",
            system_prompt="You are a WordPress engineering assistant.",
        )

    def test_headers_include_auth_token(self):
        """Verify headers contain authorization bearer and user agent."""
        headers = self.runtime._get_headers()
        self.assertEqual(headers["Authorization"], "Bearer test-api-key-xyz")
        self.assertEqual(headers["Content-Type"], "application/json")
        self.assertIn("Tersuite", headers["User-Agent"])

    @patch("httpx.Client.post")
    def test_create_session_success(self, mock_post):
        """Verify create_session makes correct REST call and extracts conversation ID."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 201
        mock_response.json.return_value = {"conversation_id": "conv-remote-123"}
        mock_post.return_value = mock_response

        session = self.runtime.create_session(self.session_config)

        self.assertIsNotNone(session)
        self.assertEqual(session.status, SessionStatus.ACTIVE)
        self.assertEqual(session.conversation_id, "conv-remote-123")

    @patch("httpx.Client.post")
    def test_send_task_success(self, mock_post):
        """Verify send_task dispatches message to OpenHands server and normalizes response."""
        # 1. Mock create session
        mock_create_resp = MagicMock(spec=httpx.Response)
        mock_create_resp.status_code = 201
        mock_create_resp.json.return_value = {"conversation_id": "conv-456"}

        # 2. Mock send task message
        mock_task_resp = MagicMock(spec=httpx.Response)
        mock_task_resp.status_code = 200
        mock_task_resp.json.return_value = {"response": "Generated WordPress plugin skeleton."}

        mock_post.side_effect = [mock_create_resp, mock_task_resp]

        session = self.runtime.create_session(self.session_config)
        result = self.runtime.send_task(session.session_id, "Generate plugin skeleton.")

        self.assertTrue(result.success)
        self.assertEqual(result.output, "Generated WordPress plugin skeleton.")

    def test_event_normalization(self):
        """Verify translation of raw OpenHands event types into NormalizedEvent."""
        session = self.runtime.create_session(self.session_config)

        # Test action event
        action_raw = {"type": "agent_action", "tool": "terminal", "command": "php -l plugin.php"}
        norm_action = self.runtime._normalize_openhands_event(action_raw, session)
        self.assertEqual(norm_action.event_type, EventType.AGENT_TOOL_STARTED)

        # Test observation event
        obs_raw = {"type": "agent_observation", "output": "No syntax errors detected."}
        norm_obs = self.runtime._normalize_openhands_event(obs_raw, session)
        self.assertEqual(norm_obs.event_type, EventType.AGENT_TOOL_FINISHED)

        # Test thought event
        thought_raw = {"type": "thought", "text": "Next, verifying database table creation."}
        norm_thought = self.runtime._normalize_openhands_event(thought_raw, session)
        self.assertEqual(norm_thought.event_type, EventType.AGENT_THINKING)
