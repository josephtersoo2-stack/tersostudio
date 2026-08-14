"""Contract compliance tests for Tersuite Agent Runtime abstractions."""
import unittest
from runtime.interfaces.runtime import TersuiteAgentRuntime
from runtime.interfaces.session import AgentSession, SessionConfig, SessionStatus
from runtime.adapters.mock_adapter import MockAgentRuntime, MockAgentSession
from runtime.adapters.openhands.adapter import OpenHandsAgentRuntime
from runtime.adapters.openhands.session import OpenHandsAgentSession


class RuntimeContractTests(unittest.TestCase):
    """Verify that all adapters correctly implement the required abstract interfaces."""

    def test_mock_adapter_implements_runtime_interface(self):
        """Verify MockAgentRuntime is a subclass and instance of TersuiteAgentRuntime."""
        runtime = MockAgentRuntime()
        self.assertIsInstance(runtime, TersuiteAgentRuntime)

    def test_openhands_adapter_implements_runtime_interface(self):
        """Verify OpenHandsAgentRuntime is a subclass and instance of TersuiteAgentRuntime."""
        runtime = OpenHandsAgentRuntime()
        self.assertIsInstance(runtime, TersuiteAgentRuntime)

    def test_mock_session_implements_session_interface(self):
        """Verify MockAgentSession is a subclass of AgentSession."""
        config = SessionConfig(generation_id="gen-1", agent_run_id="run-1")
        session = MockAgentSession(session_id="s-1", config=config)
        self.assertIsInstance(session, AgentSession)
        self.assertEqual(session.status, SessionStatus.INITIALIZING)
        self.assertIsNotNone(session.remote_conversation_id)

    def test_openhands_session_implements_session_interface(self):
        """Verify OpenHandsAgentSession is a subclass of AgentSession."""
        config = SessionConfig(generation_id="gen-1", agent_run_id="run-1")
        session = OpenHandsAgentSession(session_id="s-1", conversation_id="conv-123", config=config)
        self.assertIsInstance(session, AgentSession)
        self.assertEqual(session.remote_conversation_id, "conv-123")
