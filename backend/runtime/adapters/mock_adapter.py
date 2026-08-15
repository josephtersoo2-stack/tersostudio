"""Mock Agent Runtime adapter for deterministic testing and offline local development."""
import asyncio
import uuid
from typing import Any, AsyncIterator, Dict, List, Optional
from apps.realtime.events import EventType, NormalizedEvent
from runtime.exceptions import SessionNotFoundError
from runtime.interfaces.runtime import TersuiteAgentRuntime
from runtime.interfaces.session import (
    AgentSession,
    ExecutionStatus,
    FailureCategory,
    SessionConfig,
    SessionStatus,
    TaskResult,
)


class MockAgentSession(AgentSession):
    """In-memory agent session implementation for testing."""

    def __init__(self, session_id: str, config: SessionConfig):
        self._session_id = session_id
        self._conversation_id = f"mock-conv-{uuid.uuid4().hex[:8]}"
        self._config = config
        self._status = SessionStatus.INITIALIZING
        self._events: List[NormalizedEvent] = []
        self._result: Optional[TaskResult] = None

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def remote_conversation_id(self) -> Optional[str]:
        return self._conversation_id

    @property
    def config(self) -> SessionConfig:
        return self._config

    @property
    def status(self) -> SessionStatus:
        return self._status

    def update_status(self, new_status: SessionStatus) -> None:
        self._status = new_status

    def record_event(self, event_type: str, payload: Dict[str, Any] = None) -> NormalizedEvent:
        event = NormalizedEvent(
            event_type=event_type,
            generation_id=self._config.generation_id,
            agent_run_id=self._config.agent_run_id,
            payload=payload or {},
        )
        self._events.append(event)
        return event


class MockAgentRuntime(TersuiteAgentRuntime):
    """Deterministic Mock Runtime fulfilling the TersuiteAgentRuntime interface."""

    def __init__(self):
        self._sessions: Dict[str, MockAgentSession] = {}

    def create_session(self, config: SessionConfig) -> AgentSession:
        session_id = f"mock-session-{uuid.uuid4().hex[:10]}"
        session = MockAgentSession(session_id=session_id, config=config)
        session.update_status(SessionStatus.ACTIVE)
        session.record_event(
            EventType.AGENT_STARTED,
            {"model": config.model, "system_prompt": config.system_prompt[:50]},
        )
        self._sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> Optional[AgentSession]:
        return self._sessions.get(session_id)

    def send_task(
        self,
        session_id: str,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> TaskResult:
        session = self._sessions.get(session_id)
        if not session:
            raise SessionNotFoundError(f"Session with ID '{session_id}' was not found.")

        # Simulate execution steps
        session.update_status(SessionStatus.RUNNING)
        if prompt.startswith("FORCE_MOCK_FAILURE:"):
            error_msg = prompt.replace("FORCE_MOCK_FAILURE:", "").strip()
            result = TaskResult(
                session_id=session_id,
                success=False,
                execution_status=ExecutionStatus.TIMEOUT,
                failure_category=FailureCategory.TIMEOUT,
                output=f"Simulated execution failure: {error_msg}",
                error=error_msg,
                error_details={"simulated": True},
            )
            session._result = result
            session.update_status(SessionStatus.FAILED)
            return result

        session.record_event(
            EventType.TASK_STARTED,
            {"prompt": prompt, "context": context or {}},
        )
        session.record_event(
            EventType.AGENT_THINKING,
            {"thought": f"Executing task: {prompt}"},
        )
        session.record_event(
            EventType.AGENT_TOOL_STARTED,
            {"tool": "file_writer", "action": "create_scaffold"},
        )
        session.record_event(
            EventType.AGENT_TOOL_FINISHED,
            {"tool": "file_writer", "output": "Created project files successfully"},
        )
        session.record_event(
            EventType.AGENT_COMPLETED,
            {"summary": "Task completed successfully."},
        )

        result = TaskResult(
            session_id=session_id,
            success=True,
            execution_status=ExecutionStatus.SUCCESS,
            failure_category=FailureCategory.NONE,
            output=f"Executed task: '{prompt}' successfully in mock environment.",
            artifacts=["scaffold.zip", "manifest.json"],
            token_usage={"prompt_tokens": 120, "completion_tokens": 340, "total_tokens": 460},
            metadata={"adapter": "mock", "iterations": 3},
        )
        session._result = result
        session.update_status(SessionStatus.COMPLETED)
        return result

    def get_historical_events(self, session_id: str) -> List[NormalizedEvent]:
        session = self._sessions.get(session_id)
        if not session:
            raise SessionNotFoundError(f"Session with ID '{session_id}' was not found.")
        return list(session._events)

    def observe_events(self, session_id: str) -> List[NormalizedEvent]:
        return self.get_historical_events(session_id)

    async def subscribe_events(self, session_id: str) -> AsyncIterator[NormalizedEvent]:
        session = self._sessions.get(session_id)
        if not session:
            raise SessionNotFoundError(f"Session with ID '{session_id}' was not found.")
        for event in session._events:
            await asyncio.sleep(0.01)
            yield event

    def get_result(self, session_id: str) -> TaskResult:
        session = self._sessions.get(session_id)
        if not session:
            raise SessionNotFoundError(f"Session with ID '{session_id}' was not found.")
        if not session._result:
            return TaskResult(
                session_id=session_id,
                success=False,
                execution_status=ExecutionStatus.PENDING,
                output="Execution still in progress or no result produced.",
            )
        return session._result

    def cancel_execution(self, session_id: str) -> bool:
        session = self._sessions.get(session_id)
        if not session:
            raise SessionNotFoundError(f"Session with ID '{session_id}' was not found.")
        session.update_status(SessionStatus.CANCELLED)
        session.record_event(
            EventType.GENERATION_CANCELLED,
            {"reason": "User requested cancellation"},
        )
        return True

    def close_session(self, session_id: str) -> bool:
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False
