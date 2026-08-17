"""Unit tests for the OpenHands Agent Server adapter boundary (Official SDK Path).

Verifies strict official SDK RemoteConversation lifecycle execution, error classification,
live event callback streaming, and event normalization with zero fallback to homemade REST layers.
"""
import unittest
from unittest.mock import MagicMock, patch
import httpx
from apps.realtime.events import EventType, NormalizedEvent
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
    """Test suite verifying OpenHands adapter official SDK lifecycle and error semantics."""

    def setUp(self):
        self.config = OpenHandsServerConfig(
            server_url="http://mock-openhands-server:8010",
            server_api_key="test-api-key-xyz",
            server_timeout_seconds=30,
        )
        self.runtime = OpenHandsAgentRuntime(self.config)
        self.session_config = SessionConfig(
            generation_id="gen-oh-001",
            agent_run_id="run-oh-002",
            model="anthropic/claude-sonnet-4-5-20250929",
            system_prompt="You are a WordPress engineering assistant.",
        )

    def test_config_secret_masking(self):
        """Verify OpenHandsServerConfig repr masks server_api_key and llm_api_key."""
        config = OpenHandsServerConfig(
            server_url="http://localhost:8010",
            server_api_key="secret-server-key-123",
            llm_api_key="sk-or-v1-secret-llm-key-456",
        )
        config_repr = repr(config)
        self.assertNotIn("secret-server-key-123", config_repr)
        self.assertNotIn("sk-or-v1-secret-llm-key-456", config_repr)
        self.assertIn("server_api_key='***'", config_repr)
        self.assertIn("llm_api_key='***'", config_repr)

    @patch("runtime.adapters.openhands.adapter.OpenHandsConversation")
    @patch("runtime.adapters.openhands.adapter.OpenHandsAgent")
    @patch("runtime.adapters.openhands.adapter.OpenHandsLLM")
    @patch("runtime.adapters.openhands.adapter.OpenHandsRemoteWorkspace")
    def test_credential_boundary_isolation(self, mock_ws_cls, mock_llm_cls, mock_agent_cls, mock_conv_cls):
        """Verify Agent Server API keys are never supplied to LLM, and LLM keys are never supplied to Workspace."""
        custom_config = OpenHandsServerConfig(
            server_url="http://mock-server:8010",
            server_api_key="server-only-token-abc",
            llm_api_key="llm-only-token-xyz",
            llm_default_model="openrouter/anthropic/claude-3.5-sonnet",
        )
        runtime = OpenHandsAgentRuntime(custom_config)
        session_cfg = SessionConfig(
            generation_id="gen-boundary-01",
            agent_run_id="run-boundary-01",
            model="openrouter/anthropic/claude-3.5-sonnet",
        )
        runtime.create_session(session_cfg)

        # 1. OpenHandsLLM receives ONLY llm_api_key
        mock_llm_cls.assert_called_once()
        llm_kwargs = mock_llm_cls.call_args[1]
        self.assertEqual(llm_kwargs["api_key"].get_secret_value(), "llm-only-token-xyz")
        self.assertNotEqual(llm_kwargs["api_key"].get_secret_value(), "server-only-token-abc")

        # 2. OpenHandsRemoteWorkspace receives ONLY server_api_key
        mock_ws_cls.assert_called_once()
        ws_kwargs = mock_ws_cls.call_args[1]
        self.assertEqual(ws_kwargs["api_key"], "server-only-token-abc")
        self.assertNotEqual(ws_kwargs["api_key"], "llm-only-token-xyz")

    def test_headers_include_auth_token_and_sdk_version(self):
        """Verify headers contain authorization bearer, user agent, and content type."""
        headers = self.runtime._get_headers()
        self.assertEqual(headers["Authorization"], "Bearer test-api-key-xyz")
        self.assertEqual(headers["Content-Type"], "application/json")
        self.assertIn("OpenHands-SDK/1.42.1", headers["User-Agent"])

    @patch("runtime.adapters.openhands.adapter.OpenHandsConversation")
    def test_create_session_success(self, mock_conv_cls):
        """Verify create_session initializes official OpenHands Conversation factory."""
        mock_conv = MagicMock()
        mock_conv.id = "conv-sdk-123"
        mock_conv_cls.return_value = mock_conv

        session = self.runtime.create_session(self.session_config)

        self.assertIsNotNone(session)
        self.assertEqual(session.status, SessionStatus.ACTIVE)
        self.assertEqual(session.remote_conversation_id, "conv-sdk-123")
        self.assertEqual(session.conversation_obj, mock_conv)

    @patch("runtime.adapters.openhands.adapter.OpenHandsConversation")
    def test_create_session_wires_live_event_callback(self, mock_conv_cls):
        """Verify create_session passes a callback to OpenHandsConversation and streams events."""
        mock_conv = MagicMock()
        mock_conv.id = "conv-sdk-stream"
        mock_conv_cls.return_value = mock_conv

        received_events = []
        self.session_config.on_event = lambda ev: received_events.append(ev)

        session = self.runtime.create_session(self.session_config)

        # Ensure callbacks parameter was passed to OpenHandsConversation
        self.assertTrue(mock_conv_cls.called)
        call_kwargs = mock_conv_cls.call_args[1]
        self.assertIn("callbacks", call_kwargs)
        callbacks = call_kwargs["callbacks"]
        self.assertIsInstance(callbacks, list)
        self.assertEqual(len(callbacks), 1)

        # Trigger the callback simulating live event from WebSocket
        raw_event = {"type": "action", "tool": "file_writer", "action": "create_file"}
        callbacks[0](raw_event)

        # Verify event was added to session and streamed to on_event callback
        self.assertEqual(len(session._events), 1)
        self.assertEqual(session._events[0].event_type, EventType.AGENT_TOOL_STARTED)
        self.assertEqual(len(received_events), 1)
        self.assertEqual(received_events[0].event_type, EventType.AGENT_TOOL_STARTED)
        self.assertEqual(received_events[0].generation_id, "gen-oh-001")
        self.assertEqual(received_events[0].agent_run_id, "run-oh-002")

    @patch("runtime.adapters.openhands.adapter.OpenHandsConversation")
    def test_create_session_fails_on_unreachable_server(self, mock_conv_cls):
        """Verify create_session raises AdapterConnectionError when server is unreachable."""
        mock_conv_cls.side_effect = httpx.ConnectError("Connection refused by host")

        with self.assertRaises(AdapterConnectionError) as ctx:
            self.runtime.create_session(self.session_config)

        self.assertIn("Cannot connect to OpenHands Agent Server", str(ctx.exception))

    @patch("runtime.adapters.openhands.adapter.OpenHandsConversation")
    def test_send_task_success_sdk_execution(self, mock_conv_cls):
        """Verify send_task delegates solely to conv.send_message() and conv.run()."""
        mock_conv = MagicMock()
        mock_conv.id = "conv-sdk-456"

        mock_event = MagicMock()
        mock_event.role = "assistant"
        mock_event.content = "Generated WordPress plugin skeleton."
        mock_event.output = None
        mock_event.model_dump.return_value = {
            "type": "message",
            "role": "assistant",
            "content": "Generated WordPress plugin skeleton.",
        }
        mock_conv.state.events = [mock_event]
        mock_conv.state.stats.model_dump.return_value = {"total_tokens": 420}

        mock_conv_cls.return_value = mock_conv

        session = self.runtime.create_session(self.session_config)
        result = self.runtime.send_task(session.session_id, "Generate plugin skeleton.")

        # Verify SDK methods called
        mock_conv.send_message.assert_called_once_with("Generate plugin skeleton.")
        mock_conv.run.assert_called_once()

        # Verify result extracted from SDK state
        self.assertTrue(result.success)
        self.assertEqual(result.execution_status, ExecutionStatus.SUCCESS)
        self.assertEqual(result.failure_category, FailureCategory.NONE)
        self.assertEqual(result.output, "Generated WordPress plugin skeleton.")
        self.assertEqual(result.token_usage, {"total_tokens": 420})

    @patch("runtime.adapters.openhands.adapter.OpenHandsConversation")
    def test_send_task_reports_model_error_on_sdk_failure(self, mock_conv_cls):
        """Verify send_task classifies litellm / model errors properly without REST fallback."""
        mock_conv = MagicMock()
        mock_conv.id = "conv-sdk-789"
        mock_conv.run.side_effect = Exception("LLMBadRequestError: litellm.BadRequestError: Provider NOT provided for model")
        mock_conv_cls.return_value = mock_conv

        session = self.runtime.create_session(self.session_config)
        result = self.runtime.send_task(session.session_id, "Execute task.")

        self.assertFalse(result.success)
        self.assertEqual(result.execution_status, ExecutionStatus.AGENT_FAILED)
        self.assertEqual(result.failure_category, FailureCategory.MODEL_ERROR)
        self.assertFalse(result.retryable)
        self.assertIn("litellm.BadRequestError", result.error)

    @patch("runtime.adapters.openhands.adapter.OpenHandsConversation")
    def test_send_task_reports_infrastructure_failure_on_network_error(self, mock_conv_cls):
        """Verify send_task reports INFRASTRUCTURE_UNAVAILABLE on connection loss."""
        mock_conv = MagicMock()
        mock_conv.id = "conv-sdk-net"
        mock_conv.run.side_effect = httpx.ConnectError("Connection reset by peer")
        mock_conv_cls.return_value = mock_conv

        session = self.runtime.create_session(self.session_config)
        result = self.runtime.send_task(session.session_id, "Execute task.")

        self.assertFalse(result.success)
        self.assertEqual(result.execution_status, ExecutionStatus.INFRASTRUCTURE_UNAVAILABLE)
        self.assertEqual(result.failure_category, FailureCategory.NETWORK_CONNECTION)
        self.assertTrue(result.retryable)
        self.assertIn("Infrastructure connection error", result.error)

    @patch("runtime.adapters.openhands.adapter.OpenHandsConversation")
    def test_send_task_reports_timeout_failure(self, mock_conv_cls):
        """Verify send_task classifies timeout errors properly."""
        mock_conv = MagicMock()
        mock_conv.id = "conv-sdk-timeout"
        mock_conv.run.side_effect = TimeoutError("Execution timed out after 300s")
        mock_conv_cls.return_value = mock_conv

        session = self.runtime.create_session(self.session_config)
        result = self.runtime.send_task(session.session_id, "Execute task.")

        self.assertFalse(result.success)
        self.assertEqual(result.execution_status, ExecutionStatus.TIMEOUT)
        self.assertEqual(result.failure_category, FailureCategory.TIMEOUT)
        self.assertTrue(result.retryable)

    @patch("runtime.adapters.openhands.adapter.OpenHandsConversation")
    def test_send_task_reports_tool_error(self, mock_conv_cls):
        """Verify send_task classifies tool execution failures properly."""
        mock_conv = MagicMock()
        mock_conv.id = "conv-sdk-tool"
        mock_conv.run.side_effect = Exception("ToolExecutionError: tool 'bash' failed with code 127")
        mock_conv_cls.return_value = mock_conv

        session = self.runtime.create_session(self.session_config)
        result = self.runtime.send_task(session.session_id, "Execute task.")

        self.assertFalse(result.success)
        self.assertEqual(result.execution_status, ExecutionStatus.AGENT_FAILED)
        self.assertEqual(result.failure_category, FailureCategory.TOOL_ERROR)
        self.assertFalse(result.retryable)

    @patch("runtime.adapters.openhands.adapter.OpenHandsConversation")
    def test_cancel_execution_calls_sdk_interrupt(self, mock_conv_cls):
        """Verify cancel_execution issues conv.interrupt() via official SDK."""
        mock_conv = MagicMock()
        mock_conv.id = "conv-sdk-interrupt"
        mock_conv_cls.return_value = mock_conv

        session = self.runtime.create_session(self.session_config)
        cancelled = self.runtime.cancel_execution(session.session_id)

        mock_conv.interrupt.assert_called_once()
        self.assertTrue(cancelled)
        self.assertEqual(session.status, SessionStatus.CANCELLED)

    @patch("runtime.adapters.openhands.adapter.OpenHandsConversation")
    def test_event_normalization_from_json_and_sdk(self, mock_conv_cls):
        """Verify translation of raw JSON and SDK event types into NormalizedEvent."""
        mock_conv = MagicMock()
        mock_conv.id = "conv-sdk-events"
        mock_conv_cls.return_value = mock_conv

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
