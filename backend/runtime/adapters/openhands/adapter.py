"""OpenHands Agent Server adapter implementation for Tersuite.

Strictly follows the OpenHands Agent Server REST contract and rejects any
fake-success fallbacks.
"""
import logging
import uuid
from typing import Any, AsyncIterator, Dict, List, Optional
import httpx
from apps.realtime.events import EventType, NormalizedEvent
from runtime.exceptions import (
    AdapterConnectionError,
    SessionNotFoundError,
    TaskExecutionError,
    TimeoutExecutionError,
)
from runtime.interfaces.runtime import TersuiteAgentRuntime
from runtime.interfaces.session import (
    AgentSession,
    ExecutionStatus,
    FailureCategory,
    SessionConfig,
    SessionStatus,
    TaskResult,
)
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
        """Create a new conversation session on the OpenHands Agent Server.

        Raises AdapterConnectionError if the remote server cannot be reached.
        Never generates synthetic conversation IDs when remote creation fails.
        """
        session_id = f"oh-sess-{uuid.uuid4().hex[:12]}"
        payload = {
            "model": config.model or self.config.default_model,
            "system_prompt": config.system_prompt,
            "tools": config.tools,
            "max_iterations": config.max_iterations,
        }

        try:
            response = self._client.post("/api/conversations", json=payload)
            if response.status_code not in (200, 201):
                err_msg = (
                    f"OpenHands Agent Server failed to create conversation: "
                    f"HTTP {response.status_code} - {response.text}"
                )
                logger.error(err_msg)
                raise AdapterConnectionError(err_msg, details={"status_code": response.status_code})

            data = response.json()
            conversation_id = data.get("conversation_id")
            if not conversation_id:
                raise AdapterConnectionError(
                    "OpenHands Agent Server response missing 'conversation_id'",
                    details={"response": data},
                )

        except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError) as exc:
            err_msg = f"Cannot connect to OpenHands Agent Server at {self.config.server_url}: {exc}"
            logger.error(err_msg)
            raise AdapterConnectionError(err_msg, details={"error": str(exc)})

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
        """Dispatch task to OpenHands conversation.

        Returns real failure states upon server error. Never fabricates success.
        """
        session = self._sessions.get(session_id)
        if not session:
            raise SessionNotFoundError(f"Session with ID '{session_id}' not found.")

        if not session.remote_conversation_id:
            return TaskResult(
                session_id=session_id,
                success=False,
                execution_status=ExecutionStatus.INFRASTRUCTURE_UNAVAILABLE,
                failure_category=FailureCategory.NETWORK_CONNECTION,
                error="Session has no active OpenHands conversation ID.",
                retryable=True,
            )

        task_event = NormalizedEvent(
            event_type=EventType.TASK_STARTED,
            generation_id=session.config.generation_id,
            agent_run_id=session.config.agent_run_id,
            payload={"prompt": prompt, "context": context or {}},
        )
        session.add_event(task_event)
        session.update_status(SessionStatus.RUNNING)

        payload = {
            "content": prompt,
            "context": context or {},
        }

        try:
            response = self._client.post(
                f"/api/conversations/{session.remote_conversation_id}/messages",
                json=payload,
            )

            if response.status_code in (200, 201):
                data = response.json()
                output = data.get("response", "")
                token_usage = data.get("token_usage", {})
                artifacts = data.get("artifacts", [])

                result = TaskResult(
                    session_id=session_id,
                    success=True,
                    execution_status=ExecutionStatus.SUCCESS,
                    failure_category=FailureCategory.NONE,
                    output=output,
                    artifacts=artifacts,
                    token_usage=token_usage,
                    metadata={"conversation_id": session.remote_conversation_id},
                )
                session.update_status(SessionStatus.COMPLETED)
                session.add_event(
                    NormalizedEvent(
                        event_type=EventType.AGENT_COMPLETED,
                        generation_id=session.config.generation_id,
                        agent_run_id=session.config.agent_run_id,
                        payload={"output": output, "success": True},
                    )
                )
            else:
                err_msg = f"OpenHands returned HTTP {response.status_code}: {response.text}"
                result = TaskResult(
                    session_id=session_id,
                    success=False,
                    execution_status=ExecutionStatus.AGENT_FAILED,
                    failure_category=FailureCategory.MODEL_ERROR,
                    error=err_msg,
                    retryable=False,
                )
                session.update_status(SessionStatus.FAILED)
                session.add_event(
                    NormalizedEvent(
                        event_type=EventType.AGENT_FAILED,
                        generation_id=session.config.generation_id,
                        agent_run_id=session.config.agent_run_id,
                        payload={"error": err_msg, "success": False},
                    )
                )

        except (httpx.ConnectError, httpx.NetworkError) as exc:
            err_msg = f"Infrastructure unavailable: could not contact OpenHands server: {exc}"
            logger.error(err_msg)
            result = TaskResult(
                session_id=session_id,
                success=False,
                execution_status=ExecutionStatus.INFRASTRUCTURE_UNAVAILABLE,
                failure_category=FailureCategory.NETWORK_CONNECTION,
                error=err_msg,
                retryable=True,
            )
            session.update_status(SessionStatus.FAILED)
            session.add_event(
                NormalizedEvent(
                    event_type=EventType.SYSTEM_ERROR,
                    generation_id=session.config.generation_id,
                    agent_run_id=session.config.agent_run_id,
                    payload={"error": err_msg, "retryable": True},
                )
            )
        except httpx.TimeoutException as exc:
            err_msg = f"Execution timed out communicating with OpenHands server: {exc}"
            logger.error(err_msg)
            result = TaskResult(
                session_id=session_id,
                success=False,
                execution_status=ExecutionStatus.TIMEOUT,
                failure_category=FailureCategory.TIMEOUT,
                error=err_msg,
                retryable=True,
            )
            session.update_status(SessionStatus.FAILED)

        session._result = result
        return result

    def get_historical_events(self, session_id: str) -> List[NormalizedEvent]:
        """Fetch historical events from session log and sync with server if available."""
        session = self._sessions.get(session_id)
        if not session:
            raise SessionNotFoundError(f"Session with ID '{session_id}' not found.")

        if session.remote_conversation_id:
            try:
                response = self._client.get(
                    f"/api/conversations/{session.remote_conversation_id}/events"
                )
                if response.status_code == 200:
                    raw_events = response.json().get("events", [])
                    for raw in raw_events:
                        normalized = self._normalize_openhands_event(raw, session)
                        if normalized:
                            session.add_event(normalized)
            except httpx.RequestError as exc:
                logger.warning(f"Could not synchronize remote events from OpenHands: {exc}")

        return list(session._events)

    def observe_events(self, session_id: str) -> List[NormalizedEvent]:
        """Alias for get_historical_events."""
        return self.get_historical_events(session_id)

    async def subscribe_events(self, session_id: str) -> AsyncIterator[NormalizedEvent]:
        """Asynchronously stream events for the active session."""
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
                execution_status=ExecutionStatus.PENDING,
                output="No task result recorded.",
            )
        return session._result

    def cancel_execution(self, session_id: str) -> bool:
        session = self._sessions.get(session_id)
        if not session:
            raise SessionNotFoundError(f"Session with ID '{session_id}' not found.")

        if session.remote_conversation_id:
            try:
                self._client.post(
                    f"/api/conversations/{session.remote_conversation_id}/cancel"
                )
            except httpx.RequestError as exc:
                logger.warning(f"Failed to send remote cancellation to OpenHands: {exc}")

        session.update_status(SessionStatus.CANCELLED)
        session.add_event(
            NormalizedEvent(
                event_type=EventType.GENERATION_CANCELLED,
                generation_id=session.config.generation_id,
                agent_run_id=session.config.agent_run_id,
                payload={"reason": "User cancelled execution."},
            )
        )
        return True

    def close_session(self, session_id: str) -> bool:
        session = self._sessions.get(session_id)
        if session and session.remote_conversation_id:
            try:
                self._client.post(
                    f"/api/conversations/{session.remote_conversation_id}/close"
                )
            except httpx.RequestError:
                pass

        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False
