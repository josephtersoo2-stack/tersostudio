"""OpenHands Agent Session wrapper binding Tersuite sessions to OpenHands conversations."""
from typing import Any, List, Optional
from apps.realtime.events import NormalizedEvent
from runtime.interfaces.session import AgentSession, SessionConfig, SessionStatus, TaskResult


class OpenHandsAgentSession(AgentSession):
    """Session implementation binding a Tersuite session to an OpenHands RemoteConversation."""

    def __init__(
        self,
        session_id: str,
        conversation_id: Optional[str],
        config: SessionConfig,
        conversation_obj: Optional[Any] = None,
    ):
        self._session_id = session_id
        self._conversation_id = conversation_id
        self._config = config
        self._conversation_obj = conversation_obj
        self._status = SessionStatus.INITIALIZING
        self._events: List[NormalizedEvent] = []
        self._result: Optional[TaskResult] = None

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def remote_conversation_id(self) -> Optional[str]:
        """The underlying OpenHands conversation identifier (UUID string), or None if initialization failed."""
        return self._conversation_id

    @property
    def config(self) -> SessionConfig:
        return self._config

    @property
    def status(self) -> SessionStatus:
        return self._status

    @property
    def conversation_obj(self) -> Optional[Any]:
        """The underlying OpenHands SDK RemoteConversation object, if initialized."""
        return self._conversation_obj

    def update_status(self, new_status: SessionStatus) -> None:
        self._status = new_status

    def add_event(self, event: NormalizedEvent) -> None:
        self._events.append(event)
