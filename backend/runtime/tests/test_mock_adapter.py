"""Lifecycle and execution tests for the MockAgentRuntime adapter."""
import unittest
from apps.realtime.events import EventType
from runtime.adapters.mock_adapter import MockAgentRuntime
from runtime.interfaces.session import ExecutionStatus, SessionConfig, SessionStatus
from runtime.exceptions import SessionNotFoundError


class MockAdapterLifecycleTests(unittest.TestCase):
    """Test suite verifying mock runtime operations."""

    def setUp(self):
        self.runtime = MockAgentRuntime()
        self.config = SessionConfig(
            generation_id="gen-lifecycle-101",
            agent_run_id="run-lifecycle-202",
            model="anthropic/claude-sonnet-4-5-20250929",
            system_prompt="You are a WordPress expert.",
        )

    def test_full_execution_lifecycle(self):
        """Verify session creation, task execution, event recording, and completion."""
        # 1. Create session
        session = self.runtime.create_session(self.config)
        self.assertIsNotNone(session)
        self.assertEqual(session.status, SessionStatus.ACTIVE)

        # 2. Verify initial event
        events = self.runtime.observe_events(session.session_id)
        self.assertTrue(len(events) >= 1)
        self.assertEqual(events[0].event_type, EventType.AGENT_STARTED)

        # 3. Send Task
        prompt = "Create a simple WordPress settings page."
        result = self.runtime.send_task(session.session_id, prompt)

        self.assertTrue(result.success)
        self.assertEqual(result.execution_status, ExecutionStatus.SUCCESS)
        self.assertIn("Create a simple WordPress settings page", result.output)
        self.assertEqual(session.status, SessionStatus.COMPLETED)

        # 4. Verify recorded events
        historical_events = self.runtime.get_historical_events(session.session_id)
        event_types = [e.event_type for e in historical_events]
        self.assertIn(EventType.TASK_STARTED, event_types)
        self.assertIn(EventType.AGENT_THINKING, event_types)
        self.assertIn(EventType.AGENT_TOOL_STARTED, event_types)
        self.assertIn(EventType.AGENT_TOOL_FINISHED, event_types)
        self.assertIn(EventType.AGENT_COMPLETED, event_types)

        # 5. Retrieve result
        fetched_result = self.runtime.get_result(session.session_id)
        self.assertEqual(fetched_result.session_id, session.session_id)
        self.assertTrue(fetched_result.success)

        # 6. Close session
        closed = self.runtime.close_session(session.session_id)
        self.assertTrue(closed)
        self.assertIsNone(self.runtime.get_session(session.session_id))

    def test_cancel_execution(self):
        """Verify session cancellation updates status and logs cancellation event."""
        session = self.runtime.create_session(self.config)
        cancelled = self.runtime.cancel_execution(session.session_id)

        self.assertTrue(cancelled)
        self.assertEqual(session.status, SessionStatus.CANCELLED)

        events = self.runtime.observe_events(session.session_id)
        self.assertTrue(any(e.event_type == EventType.GENERATION_CANCELLED for e in events))

    def test_nonexistent_session_raises_error(self):
        """Verify operating on unknown session ID raises SessionNotFoundError."""
        with self.assertRaises(SessionNotFoundError):
            self.runtime.send_task("nonexistent-session-id", "test prompt")
