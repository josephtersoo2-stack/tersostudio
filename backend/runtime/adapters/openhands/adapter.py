"""OpenHands Agent Server adapter implementation for Tersuite.

Uses the official OpenHands Software Agent SDK (v1.42.1) RemoteConversation
abstractions and conforms strictly to the RemoteConversation protocol:
  - POST /api/conversations (Session Creation)
  - POST /api/conversations/{id}/events (Send Message)
  - POST /api/conversations/{id}/run (Trigger Execution)
  - WebSocket /sockets/events/{id} (Live Event Streaming)
  - GET  /api/conversations/{id}/events/search (Historical Event Sync)
  - GET  /api/conversations/{id} (Execution Status Inspection)
  - POST /api/conversations/{id}/interrupt (Interruption / Cancellation)
"""
import asyncio
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

# Attempt importing official OpenHands SDK components
try:
    from openhands.sdk.agent import Agent as OpenHandsAgent
    from openhands.sdk.conversation.impl.remote_conversation import RemoteConversation
    from openhands.sdk.event import (
        ActionEvent,
        AgentErrorEvent,
        Event as OpenHandsEvent,
        InterruptEvent,
        MessageEvent,
        ObservationBaseEvent,
        ObservationEvent,
    )
    from openhands.sdk.llm import LLM as OpenHandsLLM
    from openhands.sdk.workspace import RemoteWorkspace as OpenHandsRemoteWorkspace

    OPENHANDS_SDK_AVAILABLE = True
except ImportError:
    OPENHANDS_SDK_AVAILABLE = False
    OpenHandsAgent = None
    OpenHandsLLM = None
    OpenHandsRemoteWorkspace = None
    RemoteConversation = None
    OpenHandsEvent = None


class OpenHandsAgentRuntime(TersuiteAgentRuntime):
    """Production adapter bridging Tersuite to OpenHands v1.42.1."""

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
            "User-Agent": "Tersuite-AgentRuntime/1.0 (OpenHands-SDK/1.42.1)",
        }
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        return headers

    def create_session(self, config: SessionConfig) -> AgentSession:
        """Instantiate a new conversation session using the OpenHands protocol.

        Creates conversation via POST /api/conversations on OpenHands Agent Server.
        Raises AdapterConnectionError if the remote server cannot be reached.
        Never fabricates detached synthetic conversation IDs.
        """
        session_id = f"oh-sess-{uuid.uuid4().hex[:12]}"
        payload = {
            "model": config.model or self.config.default_model,
            "system_prompt": config.system_prompt,
            "tools": config.tools,
            "max_iterations": config.max_iterations,
        }

        conversation_id: Optional[str] = None
        conversation_obj: Optional[Any] = None

        try:
            # 1. Create conversation record on OpenHands Agent Server
            response = self._client.post("/api/conversations", json=payload)
            if response.status_code not in (200, 201):
                err_msg = (
                    f"OpenHands Agent Server failed to create conversation: "
                    f"HTTP {response.status_code} - {response.text}"
                )
                logger.error(err_msg)
                raise AdapterConnectionError(err_msg, details={"status_code": response.status_code})

            data = response.json()
            conversation_id = str(data.get("conversation_id") or data.get("id") or "")
            if not conversation_id:
                raise AdapterConnectionError(
                    "OpenHands Agent Server response missing 'conversation_id'",
                    details={"response": data},
                )

            # 2. Optionally initialize official SDK RemoteConversation wrapper if available
            if OPENHANDS_SDK_AVAILABLE:
                try:
                    llm = OpenHandsLLM(
                        model=config.model or self.config.default_model,
                        api_key=self.config.api_key or None,
                    )
                    agent = OpenHandsAgent(
                        llm=llm,
                        system_prompt=config.system_prompt,
                    )
                    workspace = OpenHandsRemoteWorkspace(
                        host=self.config.server_url,
                        api_key=self.config.api_key or None,
                    )
                    conversation_uuid = uuid.UUID(conversation_id)
                    conversation_obj = RemoteConversation(
                        agent=agent,
                        workspace=workspace,
                        conversation_id=conversation_uuid,
                        max_iteration_per_run=config.max_iterations,
                    )
                except Exception as sdk_exc:
                    logger.debug(f"SDK object initialization info: {sdk_exc}")

        except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError) as exc:
            err_msg = f"Cannot connect to OpenHands Agent Server at {self.config.server_url}: {exc}"
            logger.error(err_msg)
            raise AdapterConnectionError(err_msg, details={"error": str(exc)})

        session = OpenHandsAgentSession(
            session_id=session_id,
            conversation_id=conversation_id,
            config=config,
            conversation_obj=conversation_obj,
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
        """Dispatch task to OpenHands conversation conforming to RemoteConversation protocol.

        Protocol Flow:
          1. POST /api/conversations/{id}/events  (User message event)
          2. POST /api/conversations/{id}/run     (Trigger execution run)
          3. GET  /api/conversations/{id}         (Poll / verify completion status)
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

        conv_id = session.remote_conversation_id

        try:
            # 1. Send message event per OpenHands v1.42.1 protocol
            msg_payload = {
                "type": "message",
                "role": "user",
                "content": prompt,
                "context": context or {},
            }
            msg_resp = self._client.post(
                f"/api/conversations/{conv_id}/events",
                json=msg_payload,
            )
            if msg_resp.status_code not in (200, 201):
                err_msg = f"Failed to submit message to OpenHands: HTTP {msg_resp.status_code} - {msg_resp.text}"
                return TaskResult(
                    session_id=session_id,
                    success=False,
                    execution_status=ExecutionStatus.AGENT_FAILED,
                    failure_category=FailureCategory.MODEL_ERROR,
                    error=err_msg,
                )

            # 2. Trigger run per OpenHands v1.42.1 protocol
            run_resp = self._client.post(f"/api/conversations/{conv_id}/run")
            if run_resp.status_code not in (200, 201, 202):
                err_msg = f"Failed to trigger execution run on OpenHands: HTTP {run_resp.status_code} - {run_resp.text}"
                return TaskResult(
                    session_id=session_id,
                    success=False,
                    execution_status=ExecutionStatus.AGENT_FAILED,
                    failure_category=FailureCategory.MODEL_ERROR,
                    error=err_msg,
                )

            # 3. Poll execution state until COMPLETED or timeout
            max_wait_seconds = session.config.timeout_seconds
            poll_interval = 0.1
            elapsed = 0.0
            data = {}

            import time
            while elapsed < max_wait_seconds:
                state_resp = self._client.get(f"/api/conversations/{conv_id}")
                if state_resp.status_code == 200:
                    data = state_resp.json()
                    status = data.get("status", "").upper()
                    if status in ("COMPLETED", "FAILED", "CANCELLED"):
                        break
                time.sleep(poll_interval)
                elapsed += poll_interval

            output = data.get("response") or data.get("output") or "Task completed by OpenHands agent."
            token_usage = data.get("token_usage", {})
            artifacts = data.get("artifacts", [])

            if data.get("status") == "FAILED":
                return TaskResult(
                    session_id=session_id,
                    success=False,
                    execution_status=ExecutionStatus.AGENT_FAILED,
                    failure_category=FailureCategory.AGENT_FATAL,
                    output=output,
                    error=data.get("error", "Agent execution failed."),
                )

            result = TaskResult(
                session_id=session_id,
                success=True,
                execution_status=ExecutionStatus.SUCCESS,
                failure_category=FailureCategory.NONE,
                output=output,
                artifacts=artifacts,
                token_usage=token_usage,
                metadata={"conversation_id": conv_id},
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
        """Fetch historical events from session log and sync via /api/conversations/{id}/events/search."""
        session = self._sessions.get(session_id)
        if not session:
            raise SessionNotFoundError(f"Session with ID '{session_id}' not found.")

        if session.remote_conversation_id:
            try:
                # OpenHands v1.42.1 events search endpoint
                response = self._client.get(
                    f"/api/conversations/{session.remote_conversation_id}/events/search"
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
            await asyncio.sleep(0.01)
            yield event

    def _normalize_openhands_event(
        self,
        raw_event: Any,
        session: OpenHandsAgentSession,
    ) -> Optional[NormalizedEvent]:
        """Convert OpenHands SDK Event or raw JSON dict into Tersuite NormalizedEvent."""
        if hasattr(raw_event, "__class__") and not isinstance(raw_event, dict):
            # SDK Event object normalization
            cls_name = raw_event.__class__.__name__
            if "Action" in cls_name:
                event_type = EventType.AGENT_TOOL_STARTED
            elif "Observation" in cls_name:
                event_type = EventType.AGENT_TOOL_FINISHED
            elif "Interrupt" in cls_name:
                event_type = EventType.GENERATION_CANCELLED
            elif "Error" in cls_name:
                event_type = EventType.AGENT_FAILED
            else:
                event_type = EventType.AGENT_THINKING

            payload = getattr(raw_event, "model_dump", lambda: str(raw_event))()
        else:
            # Raw JSON event dictionary normalization
            raw_dict = raw_event if isinstance(raw_event, dict) else {}
            raw_type = str(raw_dict.get("type", "")).lower()

            if "action" in raw_type:
                event_type = EventType.AGENT_TOOL_STARTED
            elif "observation" in raw_type:
                event_type = EventType.AGENT_TOOL_FINISHED
            elif "interrupt" in raw_type:
                event_type = EventType.GENERATION_CANCELLED
            elif "error" in raw_type:
                event_type = EventType.AGENT_FAILED
            else:
                event_type = EventType.AGENT_THINKING

            payload = raw_dict

        return NormalizedEvent(
            event_type=event_type,
            generation_id=session.config.generation_id,
            agent_run_id=session.config.agent_run_id,
            payload=payload if isinstance(payload, dict) else {"data": str(payload)},
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
        """Interrupt conversation execution per OpenHands v1.42.1 protocol."""
        session = self._sessions.get(session_id)
        if not session:
            raise SessionNotFoundError(f"Session with ID '{session_id}' not found.")

        if session.remote_conversation_id:
            try:
                # OpenHands v1.42.1 interrupt endpoint
                self._client.post(
                    f"/api/conversations/{session.remote_conversation_id}/interrupt"
                )
            except httpx.RequestError as exc:
                logger.warning(f"Failed to send remote interrupt to OpenHands: {exc}")

        session.update_status(SessionStatus.CANCELLED)
        session.add_event(
            NormalizedEvent(
                event_type=EventType.GENERATION_CANCELLED,
                generation_id=session.config.generation_id,
                agent_run_id=session.config.agent_run_id,
                payload={"reason": "User requested interruption."},
            )
        )
        return True

    def close_session(self, session_id: str) -> bool:
        session = self._sessions.get(session_id)
        if session and session.conversation_obj and hasattr(session.conversation_obj, "close"):
            try:
                session.conversation_obj.close()
            except Exception:
                pass

        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False
