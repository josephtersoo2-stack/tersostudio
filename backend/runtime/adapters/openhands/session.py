"""OpenHands Agent Session wrapper."""
from typing import List, Optional
from apps.realtime.events import NormalizedEvent
from runtime.interfaces.session import AgentSession, SessionConfig, SessionStatus, TaskResult


class OpenHandsAgentSession(AgentSession):
    """Session implementation binding a Tersuite session to an OpenHands remote conversation."""

    def __init__(
        self,
        session_id: str,
        conversation_id: str,
        config: SessionConfig,
    ):
        self._session_id = session_id
        self._conversation_id = conversation_id
        self._config = config
        self._status = SessionStatus.INITIALIZING
        self._events: List[NormalizedEvent] = []
        self._result: Optional[TaskResult] = None

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def conversation_id(self) -> str:
        """The underlying OpenHands conversation UUID."""
        return self._conversation_id

    @property
    def config(self) -> SessionConfig:
        return self._config

    @property
    def status(self) -> SessionStatus:
        return self._status

    def update_status(self, new_status: SessionStatus) -> None:
        self._status = new_status

    def add_event(self, event: NormalizedEvent) -> None:
        self._events.append(event)
