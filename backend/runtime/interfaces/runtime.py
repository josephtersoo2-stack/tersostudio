"""Abstract runtime interface defining Tersuite's decoupled agent contract."""
from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, List, Optional
from apps.realtime.events import NormalizedEvent
from .session import AgentSession, SessionConfig, TaskResult


class TersuiteAgentRuntime(ABC):
    """Abstract Base Class for all Tersuite Agent Execution Adapters.

    Decouples Tersuite Django applications from OpenHands internals and other
    agent execution engines.

    Phase 1 Scope Note:
    In Phase 1, runtime session state is managed in-memory within the adapter boundary.
    Durable ORM persistence for generations and agent runs is part of Phase 2.
    """

    @abstractmethod
    def create_session(self, config: SessionConfig) -> AgentSession:
        """Instantiate a new agent execution session.

        Raises AdapterConnectionError if the underlying agent server is unreachable.
        """
        pass

    @abstractmethod
    def get_session(self, session_id: str) -> Optional[AgentSession]:
        """Retrieve an active session by its Tersuite session ID."""
        pass

    @abstractmethod
    def send_task(
        self,
        session_id: str,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> TaskResult:
        """Send a prompt/task to the active agent session and execute it.

        Must return a structured TaskResult with accurate success/failure telemetry.
        Must NOT fabricate success if the agent server is unreachable.
        """
        pass

    @abstractmethod
    def get_historical_events(self, session_id: str) -> List[NormalizedEvent]:
        """Retrieve recorded historical events from the session log or server."""
        pass

    @abstractmethod
    def observe_events(self, session_id: str) -> List[NormalizedEvent]:
        """Retrieve all currently known events for a session (alias for historical log)."""
        pass

    @abstractmethod
    async def subscribe_events(self, session_id: str) -> AsyncIterator[NormalizedEvent]:
        """Asynchronously stream live events as they occur."""
        pass

    @abstractmethod
    def get_result(self, session_id: str) -> TaskResult:
        """Retrieve the latest task result and artifacts for the session."""
        pass

    @abstractmethod
    def cancel_execution(self, session_id: str) -> bool:
        """Cancel an in-flight agent task execution."""
        pass

    @abstractmethod
    def close_session(self, session_id: str) -> bool:
        """Clean up and close an agent session."""
        pass
