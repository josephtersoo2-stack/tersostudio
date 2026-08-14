"""Abstract runtime interface defining Tersuite's decoupled agent contract."""
from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, List, Optional
from apps.realtime.events import NormalizedEvent
from .session import AgentSession, SessionConfig, TaskResult


class TersuiteAgentRuntime(ABC):
    """Abstract Base Class for all Tersuite Agent Execution Adapters.

    Decouples Tersuite business logic from OpenHands and other agent execution engines.
    """

    @abstractmethod
    def create_session(self, config: SessionConfig) -> AgentSession:
        """Instantiate a new agent execution session."""
        pass

    @abstractmethod
    def get_session(self, session_id: str) -> Optional[AgentSession]:
        """Retrieve an active session by its ID."""
        pass

    @abstractmethod
    def send_task(
        self,
        session_id: str,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> TaskResult:
        """Send a prompt/task to the active agent session and await or trigger execution."""
        pass

    @abstractmethod
    def observe_events(self, session_id: str) -> List[NormalizedEvent]:
        """Retrieve all recorded normalized events for a session."""
        pass

    @abstractmethod
    async def stream_events(self, session_id: str) -> AsyncIterator[NormalizedEvent]:
        """Asynchronously stream normalized events in real time."""
        pass

    @abstractmethod
    def get_result(self, session_id: str) -> TaskResult:
        """Retrieve the final outcome and artifacts of the session."""
        pass

    @abstractmethod
    def cancel_execution(self, session_id: str) -> bool:
        """Cancel an in-flight agent task execution."""
        pass

    @abstractmethod
    def close_session(self, session_id: str) -> bool:
        """Clean up and close an agent session."""
        pass
