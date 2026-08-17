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

    def test_compose_and_env_mock_backend_default(self):
        """Verify default Compose and .env.example configuration uses mock backend and forces no Agent Server."""
        import os
        from pathlib import Path

        base_dir = Path(__file__).resolve().parent.parent.parent
        compose_path = base_dir / "docker-compose.yml"
        env_example_path = base_dir / ".env.example"

        self.assertTrue(compose_path.exists(), "docker-compose.yml must exist")
        self.assertTrue(env_example_path.exists(), ".env.example must exist")

        compose_content = compose_path.read_text(encoding="utf-8")
        env_content = env_example_path.read_text(encoding="utf-8")

        # 1. Assert mock backend is set in both
        self.assertIn("AGENT_RUNTIME_BACKEND=mock", compose_content)
        self.assertIn("AGENT_RUNTIME_BACKEND=mock", env_content)

        # 2. Assert docker-compose.yml does not force openhands backend or localhost agent server lines
        self.assertNotIn("AGENT_RUNTIME_BACKEND=openhands", compose_content)
        self.assertNotIn("OPENHANDS_AGENT_SERVER_URL=http://localhost:8010", compose_content)

