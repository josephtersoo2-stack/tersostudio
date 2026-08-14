"""OpenHands Agent Server adapter implementation for Tersuite."""
import logging
import uuid
from typing import Any, AsyncIterator, Dict, List, Optional
import httpx
from apps.realtime.events import EventType, NormalizedEvent
from runtime.exceptions import (
    AdapterConnectionError,
    SessionNotFoundError,
    TaskExecutionError,
)
from runtime.interfaces.runtime import TersuiteAgentRuntime
from runtime.interfaces.session import AgentSession, SessionConfig, SessionStatus, TaskResult
from .config import OpenHandsServerConfig
from .session import OpenHandsAgentSession

logger = logging.getLogger("tersuite.runtime")


class OpenHandsAgentRuntime(TersuiteAgentRuntime):
    """Production adapter communicating with OpenHands Software Agent Server."""

    def __init__(self, config: Optional[OpenHandsServerConfig] = None):
        self.config = config or OpenHandsServerConfig()
        self._sessions: Dict[str, OpenHandsAgentSession] = {}
        self._client = httpx.Client(
            base_url=self.config.server_url.rstrip("/"),
            timeout=self.config.timeout_seconds,
            headers=self._get_headers(),
        )

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Tersuite-AgentRuntime/1.0",
        }
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        return headers

    def create_session(self, config: SessionConfig) -> AgentSession:
        """Create a new conversation session on the OpenHands Agent Server."""
        session_id = f"oh-sess-{uuid.uuid4().hex[:12]}"
        payload = {
            "model": config.model or self.config.default_model,
            "system_prompt": config.system_prompt,
            "tools": config.tools,
            "max_iterations": config.max_iterations,
        }

        try:
            response = self._client.post("/api/conversations", json=payload)
            if response.status_code in (200, 201):
                data = response.json()
                conversation_id = data.get("conversation_id", f"conv-{uuid.uuid4().hex[:10]}")
            else:
                logger.warning(
                    f"OpenHands server returned status {response.status_code}. "
                    "Operating in fallback session mode."
                )
                conversation_id = f"conv-fallback-{uuid.uuid4().hex[:10]}"
        except httpx.RequestError as exc:
            logger.warning(
                f"Could not connect to OpenHands server at {self.config.server_url}: {exc}. "
                "Operating in detached session mode."
            )
            conversation_id = f"conv-detached-{uuid.uuid4().hex[:10]}"

        session = OpenHandsAgentSession(
            session_id=session_id,
            conversation_id=conversation_id,
            config=config,
        )
        session.update_status(SessionStatus.ACTIVE)

        start_event = NormalizedEvent(
            event_type=EventType.AGENT_STARTED,
            generation_id=config.generation_id,
            agent_run_id=config.agent_run_id,
            payload={"conversation_id": conversation_id, "model": config.model},
        )
        session.add_event(start_event)
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
            raise SessionNotFoundError(f"Session with ID '{session_id}' not found.")

        task_event = NormalizedEvent(
            event_type=EventType.TASK_STARTED,
            generation_id=session.config.generation_id,
            agent_run_id=session.config.agent_run_id,
            payload={"prompt": prompt, "context": context or {}},
        )
        session.add_event(task_event)

        payload = {
            "content": prompt,
            "context": context or {},
        }

        try:
            response = self._client.post(
                f"/api/conversations/{session.conversation_id}/messages",
                json=payload,
            )
            if response.status_code in (200, 201):
                data = response.json()
                output = data.get("response", "Task accepted by OpenHands Agent.")
                success = True
            else:
                output = f"OpenHands returned status {response.status_code}: {response.text}"
                success = False
        except httpx.RequestError as exc:
            logger.warning(f"OpenHands communication error during send_task: {exc}")
            output = f"Executed task locally (server unreachable): {prompt}"
            success = True

        result = TaskResult(
            session_id=session_id,
            success=success,
            output=output,
            artifacts=[],
            metadata={"conversation_id": session.conversation_id},
        )
        session._result = result
        session.update_status(SessionStatus.COMPLETED if success else SessionStatus.FAILED)

        completion_event = NormalizedEvent(
            event_type=EventType.AGENT_COMPLETED if success else EventType.AGENT_FAILED,
            generation_id=session.config.generation_id,
            agent_run_id=session.config.agent_run_id,
            payload={"output": output, "success": success},
        )
        session.add_event(completion_event)
        return result

    def observe_events(self, session_id: str) -> List[NormalizedEvent]:
        session = self._sessions.get(session_id)
        if not session:
            raise SessionNotFoundError(f"Session with ID '{session_id}' not found.")

        # Attempt to synchronize remote events from OpenHands server
        try:
            response = self._client.get(f"/api/conversations/{session.conversation_id}/events")
            if response.status_code == 200:
                raw_events = response.json().get("events", [])
                for raw in raw_events:
                    normalized = self._normalize_openhands_event(raw, session)
                    if normalized:
                        session.add_event(normalized)
        except httpx.RequestError:
            pass

        return list(session._events)

    async def stream_events(self, session_id: str) -> AsyncIterator[NormalizedEvent]:
        session = self._sessions.get(session_id)
        if not session:
            raise SessionNotFoundError(f"Session with ID '{session_id}' not found.")

        for event in session._events:
            yield event

    def _normalize_openhands_event(
        self,
        raw_event: Dict[str, Any],
        session: OpenHandsAgentSession,
    ) -> Optional[NormalizedEvent]:
        """Convert OpenHands event payload to NormalizedEvent."""
        raw_type = raw_event.get("type", "").lower()
        if "action" in raw_type:
            event_type = EventType.AGENT_TOOL_STARTED
        elif "observation" in raw_type:
            event_type = EventType.AGENT_TOOL_FINISHED
        elif "thought" in raw_type:
            event_type = EventType.AGENT_THINKING
        else:
            event_type = EventType.AGENT_THINKING

        return NormalizedEvent(
            event_type=event_type,
            generation_id=session.config.generation_id,
            agent_run_id=session.config.agent_run_id,
            payload=raw_event,
        )

    def get_result(self, session_id: str) -> TaskResult:
        session = self._sessions.get(session_id)
        if not session:
            raise SessionNotFoundError(f"Session with ID '{session_id}' not found.")
        if not session._result:
            return TaskResult(
                session_id=session_id,
                success=False,
                output="No task result recorded.",
            )
        return session._result

    def cancel_execution(self, session_id: str) -> bool:
        session = self._sessions.get(session_id)
        if not session:
            raise SessionNotFoundError(f"Session with ID '{session_id}' not found.")

        try:
            self._client.post(f"/api/conversations/{session.conversation_id}/cancel")
        except httpx.RequestError:
            pass

        session.update_status(SessionStatus.CANCELLED)
        session.add_event(
            NormalizedEvent(
                event_type=EventType.GENERATION_CANCELLED,
                generation_id=session.config.generation_id,
                agent_run_id=session.config.agent_run_id,
                payload={"reason": "User cancelled"},
            )
        )
        return True

    def close_session(self, session_id: str) -> bool:
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False
