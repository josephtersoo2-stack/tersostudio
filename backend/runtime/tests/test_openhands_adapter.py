"""Unit tests for the OpenHands Agent Server adapter boundary (v1.42.1 protocol).

Verifies strict RemoteConversation protocol compliance, error propagation, and event normalization.
"""
import unittest
from unittest.mock import MagicMock, patch
import httpx
from apps.realtime.events import EventType
from runtime.exceptions import AdapterConnectionError
from runtime.adapters.openhands.config import OpenHandsServerConfig
from runtime.adapters.openhands.adapter import OpenHandsAgentRuntime
from runtime.interfaces.session import (
    ExecutionStatus,
    FailureCategory,
    SessionConfig,
    SessionStatus,
)


class OpenHandsAdapterTests(unittest.TestCase):
    """Test suite verifying OpenHands adapter protocol and error semantics."""

    def setUp(self):
        self.config = OpenHandsServerConfig(
            server_url="http://mock-openhands-server:8010",
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

    def test_headers_include_auth_token_and_sdk_version(self):
        """Verify headers contain authorization bearer, user agent, and content type."""
        headers = self.runtime._get_headers()
        self.assertEqual(headers["Authorization"], "Bearer test-api-key-xyz")
        self.assertEqual(headers["Content-Type"], "application/json")
        self.assertIn("OpenHands-SDK/1.42.1", headers["User-Agent"])

    @patch("httpx.Client.post")
    def test_create_session_success(self, mock_post):
        """Verify create_session makes POST /api/conversations and extracts conversation ID."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 201
        mock_response.json.return_value = {"conversation_id": "conv-remote-123"}
        mock_post.return_value = mock_response

        session = self.runtime.create_session(self.session_config)

        self.assertIsNotNone(session)
        self.assertEqual(session.status, SessionStatus.ACTIVE)
        self.assertEqual(session.remote_conversation_id, "conv-remote-123")

    @patch("httpx.Client.post")
    def test_create_session_fails_on_unreachable_server(self, mock_post):
        """Verify create_session raises AdapterConnectionError when server is unreachable."""
        mock_post.side_effect = httpx.ConnectError("Connection refused by host")

        with self.assertRaises(AdapterConnectionError) as ctx:
            self.runtime.create_session(self.session_config)

        self.assertIn("Cannot connect to OpenHands Agent Server", str(ctx.exception))

    @patch("httpx.Client.get")
    @patch("httpx.Client.post")
    def test_send_task_success_protocol_flow(self, mock_post, mock_get):
        """Verify send_task follows v1.42.1 RemoteConversation flow:

        1. POST /api/conversations (create session)
        2. POST /api/conversations/{id}/events (send user message)
        3. POST /api/conversations/{id}/run (trigger run)
        4. GET /api/conversations/{id} (inspect state)
        """
        # Session creation mock
        mock_create_resp = MagicMock(spec=httpx.Response)
        mock_create_resp.status_code = 201
        mock_create_resp.json.return_value = {"conversation_id": "conv-456"}

        # Message submit mock
        mock_msg_resp = MagicMock(spec=httpx.Response)
        mock_msg_resp.status_code = 200
        mock_msg_resp.json.return_value = {"status": "ok"}

        # Run trigger mock
        mock_run_resp = MagicMock(spec=httpx.Response)
        mock_run_resp.status_code = 200
        mock_run_resp.json.return_value = {"status": "running"}

        # State check mock
        mock_state_resp = MagicMock(spec=httpx.Response)
        mock_state_resp.status_code = 200
        mock_state_resp.json.return_value = {
            "output": "Generated WordPress plugin skeleton.",
            "token_usage": {"total_tokens": 500},
        }

        mock_post.side_effect = [mock_create_resp, mock_msg_resp, mock_run_resp]
        mock_get.return_value = mock_state_resp

        session = self.runtime.create_session(self.session_config)
        result = self.runtime.send_task(session.session_id, "Generate plugin skeleton.")

        self.assertTrue(result.success)
        self.assertEqual(result.execution_status, ExecutionStatus.SUCCESS)
        self.assertEqual(result.failure_category, FailureCategory.NONE)
        self.assertEqual(result.output, "Generated WordPress plugin skeleton.")

    @patch("httpx.Client.post")
    def test_send_task_reports_infrastructure_failure_on_network_error(self, mock_post):
        """Verify send_task reports INFRASTRUCTURE_UNAVAILABLE on connection error.

        Guarantees NO fake success is reported when execution fails.
        """
        mock_create_resp = MagicMock(spec=httpx.Response)
        mock_create_resp.status_code = 201
        mock_create_resp.json.return_value = {"conversation_id": "conv-456"}

        mock_post.side_effect = [
            mock_create_resp,
            httpx.ConnectError("Connection reset by peer"),
        ]

        session = self.runtime.create_session(self.session_config)
        result = self.runtime.send_task(session.session_id, "Generate plugin skeleton.")

        self.assertFalse(result.success)
        self.assertEqual(result.execution_status, ExecutionStatus.INFRASTRUCTURE_UNAVAILABLE)
        self.assertEqual(result.failure_category, FailureCategory.NETWORK_CONNECTION)
        self.assertTrue(result.retryable)
        self.assertIn("Infrastructure unavailable", result.error)

    @patch("httpx.Client.post")
    def test_cancel_execution_calls_interrupt_endpoint(self, mock_post):
        """Verify cancel_execution issues POST /api/conversations/{id}/interrupt."""
        mock_create_resp = MagicMock(spec=httpx.Response)
        mock_create_resp.status_code = 201
        mock_create_resp.json.return_value = {"conversation_id": "conv-interrupt-test"}

        mock_interrupt_resp = MagicMock(spec=httpx.Response)
        mock_interrupt_resp.status_code = 200

        mock_post.side_effect = [mock_create_resp, mock_interrupt_resp]

        session = self.runtime.create_session(self.session_config)
        cancelled = self.runtime.cancel_execution(session.session_id)

        self.assertTrue(cancelled)
        self.assertEqual(session.status, SessionStatus.CANCELLED)

    @patch("httpx.Client.post")
    def test_event_normalization_from_json_and_sdk(self, mock_post):
        """Verify translation of raw JSON and SDK event types into NormalizedEvent."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 201
        mock_response.json.return_value = {"conversation_id": "conv-789"}
        mock_post.return_value = mock_response

        session = self.runtime.create_session(self.session_config)

        # Test raw action event
        action_raw = {"type": "action", "tool": "terminal", "command": "php -l plugin.php"}
        norm_action = self.runtime._normalize_openhands_event(action_raw, session)
        self.assertEqual(norm_action.event_type, EventType.AGENT_TOOL_STARTED)

        # Test raw observation event
        obs_raw = {"type": "observation", "output": "No syntax errors detected."}
        norm_obs = self.runtime._normalize_openhands_event(obs_raw, session)
        self.assertEqual(norm_obs.event_type, EventType.AGENT_TOOL_FINISHED)

        # Test raw interrupt event
        interrupt_raw = {"type": "interrupt", "reason": "user_cancelled"}
        norm_interrupt = self.runtime._normalize_openhands_event(interrupt_raw, session)
        self.assertEqual(norm_interrupt.event_type, EventType.GENERATION_CANCELLED)
