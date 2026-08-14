"""OpenHands Agent Server adapter implementation for Tersuite.

Uses the official OpenHands Software Agent SDK (v1.42.1) RemoteConversation
abstractions and conforms strictly to the OpenHands SDK architecture:
  - RemoteWorkspace (host, working_dir, client connection)
  - RemoteConversation (id, send_message, run, interrupt, close, events)
  - Event normalization from OpenHands SDK events to Tersuite NormalizedEvent
"""
import asyncio
import logging
import os
import uuid
from typing import Any, AsyncIterator, Dict, List, Optional
import httpx
from pydantic import SecretStr

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
    from openhands.sdk.conversation import Conversation as OpenHandsConversation
    from openhands.sdk.conversation.impl.remote_conversation import (
        RemoteConversation,
        RemoteEventsList,
    )
    from openhands.sdk.conversation.state import ConversationExecutionStatus
    from openhands.sdk.event import (
        ActionEvent,
        AgentErrorEvent,
        Event as OpenHandsEvent,
        InterruptEvent,
        MessageEvent,
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
    OpenHandsConversation = None
    RemoteConversation = None
    OpenHandsEvent = None
    ConversationExecutionStatus = None


class OpenHandsAgentRuntime(TersuiteAgentRuntime):
    """Production adapter bridging Tersuite to OpenHands Software Agent SDK v1.42.1."""

    def __init__(self, config: Optional[OpenHandsServerConfig] = None):
        self.config = config or OpenHandsServerConfig()
        self._sessions: Dict[str, OpenHandsAgentSession] = {}
        self._results: Dict[str, TaskResult] = {}
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
        """Instantiate a new conversation session using OpenHands RemoteConversation protocol.

        Creates conversation via official OpenHands SDK Conversation factory or REST protocol.
        Raises AdapterConnectionError if the remote server cannot be reached.
        Never fabricates detached synthetic conversation IDs.
        """
        session_id = f"oh-sess-{uuid.uuid4().hex[:12]}"
        conversation_id: Optional[str] = None
        conversation_obj: Optional[Any] = None

        # 1. Direct REST creation protocol to ensure server reachability and extract remote conversation ID
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
            conversation_id = str(data.get("conversation_id") or data.get("id") or "")
            if not conversation_id:
                raise AdapterConnectionError(
                    "OpenHands Agent Server response missing 'conversation_id'",
                    details={"response": data},
                )
        except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError) as exc:
            err_msg = f"Cannot connect to OpenHands Agent Server at {self.config.server_url}: {exc}"
            logger.error(err_msg)
            raise AdapterConnectionError(err_msg) from exc

        # 2. Attach official OpenHands SDK RemoteConversation wrapper if available
        if OPENHANDS_SDK_AVAILABLE and OpenHandsRemoteWorkspace is not None:
            try:
                model_name = config.model or self.config.default_model
                api_key_str = self.config.api_key or os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or os.getenv("GEMINI_API_KEY") or ""
                
                llm = OpenHandsLLM(
                    model=model_name,
                    api_key=SecretStr(api_key_str) if api_key_str else None,
                )
                agent = OpenHandsAgent(
                    llm=llm,
                    system_prompt=config.system_prompt,
                )
                workspace = OpenHandsRemoteWorkspace(
                    host=self.config.server_url,
                    api_key=self.config.api_key or None,
                    working_dir=".",
                )
                conversation_uuid = uuid.UUID(conversation_id)
                conversation_obj = RemoteConversation(
                    agent=agent,
                    workspace=workspace,
                    conversation_id=conversation_uuid,
                    max_iteration_per_run=config.max_iterations,
                )
            except Exception as sdk_exc:
                logger.debug(f"SDK Conversation wrapper initialization: {sdk_exc}")

        session = OpenHandsAgentSession(
            session_id=session_id,
            conversation_id=conversation_id,
            config=config,
            conversation_obj=conversation_obj,
        )
        session.update_status(SessionStatus.ACTIVE)
        self._sessions[session_id] = session

        logger.info(
            f"Created OpenHands session '{session_id}' bound to remote conversation '{conversation_id}'"
        )
        return session

    def get_session(self, session_id: str) -> Optional[AgentSession]:
        if session_id not in self._sessions:
            raise SessionNotFoundError(f"OpenHands session '{session_id}' not found.")
        return self._sessions[session_id]

    def send_task(
        self,
        session_id: str,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> TaskResult:
        """Send a message to the OpenHands conversation and execute the agent run."""
        session = self.get_session(session_id)
        if not isinstance(session, OpenHandsAgentSession):
            raise TaskExecutionError(f"Invalid session type for '{session_id}'.")

        conv_id = session.remote_conversation_id
        if not conv_id:
            raise TaskExecutionError(f"Session '{session_id}' has no active conversation ID.")

        session.update_status(SessionStatus.RUNNING)

        # 1. Preferred execution path: official SDK RemoteConversation object
        if session.conversation_obj is not None and hasattr(session.conversation_obj, "send_message"):
            try:
                conv = session.conversation_obj
                conv.send_message(prompt)
                conv.run()

                output = ""
                artifacts = []
                token_usage = {}

                if hasattr(conv, "state") and hasattr(conv.state, "events"):
                    for event in conv.state.events:
                        norm = self.normalize_event(event, session.config)
                        session.add_event(norm)
                        if isinstance(event, MessageEvent) and getattr(event, "role", None) in ("assistant", "agent"):
                            output = event.content or output
                        elif hasattr(event, "output") and event.output:
                            output = str(event.output)

                if hasattr(conv, "state") and hasattr(conv.state, "stats"):
                    stats = conv.state.stats
                    if hasattr(stats, "model_dump"):
                        token_usage = stats.model_dump()

                session.update_status(SessionStatus.COMPLETED)
                result = TaskResult(
                    session_id=session_id,
                    success=True,
                    execution_status=ExecutionStatus.SUCCESS,
                    failure_category=FailureCategory.NONE,
                    output=output or "Execution completed.",
                    artifacts=artifacts,
                    token_usage=token_usage,
                    metadata={"conversation_id": conv_id},
                )
                self._results[session_id] = result
                return result
            except Exception as sdk_exec_err:
                logger.warning(f"SDK execution error, falling back to protocol handling: {sdk_exec_err}")

        # 2. Protocol path: REST /api/conversations/{id}/events -> /run -> poll
        try:
            # Send message
            message_payload = {
                "type": "message",
                "role": "user",
                "content": prompt,
            }
            event_resp = self._client.post(
                f"/api/conversations/{conv_id}/events",
                json=message_payload,
            )
            if event_resp.status_code not in (200, 201, 202):
                err_msg = f"Failed to send message to OpenHands: HTTP {event_resp.status_code} - {event_resp.text}"
                res = TaskResult(
                    session_id=session_id,
                    success=False,
                    execution_status=ExecutionStatus.AGENT_FAILED,
                    failure_category=FailureCategory.MODEL_ERROR,
                    error=err_msg,
                )
                self._results[session_id] = res
                return res

            # Trigger run
            run_resp = self._client.post(f"/api/conversations/{conv_id}/run")
            if run_resp.status_code not in (200, 201, 202):
                err_msg = f"Failed to trigger execution run on OpenHands: HTTP {run_resp.status_code} - {run_resp.text}"
                res = TaskResult(
                    session_id=session_id,
                    success=False,
                    execution_status=ExecutionStatus.AGENT_FAILED,
                    failure_category=FailureCategory.MODEL_ERROR,
                    error=err_msg,
                )
                self._results[session_id] = res
                return res

            # Poll status
            import time
            max_wait_seconds = session.config.timeout_seconds
            poll_interval = 0.1
            elapsed = 0.0
            data = {}

            while elapsed < max_wait_seconds:
                state_resp = self._client.get(f"/api/conversations/{conv_id}")
                if state_resp.status_code == 200:
                    data = state_resp.json()
                    status = str(data.get("status") or data.get("execution_status") or "").upper()
                    if status in ("COMPLETED", "FINISHED", "STOPPED", "FAILED", "CANCELLED"):
                        break
                time.sleep(poll_interval)
                elapsed += poll_interval

            output = data.get("response") or data.get("output") or "Execution completed."
            token_usage = data.get("token_usage") or data.get("stats", {})
            artifacts = data.get("artifacts", [])

            if data.get("status") == "FAILED":
                session.update_status(SessionStatus.FAILED)
                res = TaskResult(
                    session_id=session_id,
                    success=False,
                    execution_status=ExecutionStatus.AGENT_FAILED,
                    failure_category=FailureCategory.AGENT_FATAL,
                    output=output,
                    error=data.get("error", "Agent execution failed."),
                )
                self._results[session_id] = res
                return res

            session.update_status(SessionStatus.COMPLETED)
            res = TaskResult(
                session_id=session_id,
                success=True,
                execution_status=ExecutionStatus.SUCCESS,
                failure_category=FailureCategory.NONE,
                output=output,
                artifacts=artifacts,
                token_usage=token_usage,
                metadata={"conversation_id": conv_id},
            )
            self._results[session_id] = res
            return res

        except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError) as exc:
            session.update_status(SessionStatus.FAILED)
            err_msg = f"Infrastructure unavailable: could not contact OpenHands server: {exc}"
            logger.error(err_msg)
            res = TaskResult(
                session_id=session_id,
                success=False,
                execution_status=ExecutionStatus.INFRASTRUCTURE_UNAVAILABLE,
                failure_category=FailureCategory.NETWORK_CONNECTION,
                retryable=True,
                error=err_msg,
            )
            self._results[session_id] = res
            return res

    def get_result(self, session_id: str) -> TaskResult:
        """Retrieve the latest task result for the session."""
        if session_id in self._results:
            return self._results[session_id]
        session = self.get_session(session_id)
        return TaskResult(
            session_id=session_id,
            success=session.status == SessionStatus.COMPLETED,
            execution_status=ExecutionStatus.SUCCESS if session.status == SessionStatus.COMPLETED else ExecutionStatus.IDLE,
        )

    def cancel_execution(self, session_id: str) -> bool:
        """Interrupt and cancel execution of an active OpenHands conversation."""
        session = self.get_session(session_id)
        if not isinstance(session, OpenHandsAgentSession) or not session.remote_conversation_id:
            return False

        # Preferred path: SDK object interrupt()
        if session.conversation_obj is not None and hasattr(session.conversation_obj, "interrupt"):
            try:
                session.conversation_obj.interrupt()
                session.update_status(SessionStatus.CANCELLED)
                return True
            except Exception as exc:
                logger.warning(f"SDK interrupt failed, trying REST endpoint: {exc}")

        # REST path: POST /api/conversations/{id}/interrupt
        try:
            resp = self._client.post(f"/api/conversations/{session.remote_conversation_id}/interrupt")
            if resp.status_code in (200, 202, 204):
                session.update_status(SessionStatus.CANCELLED)
                return True
        except Exception as exc:
            logger.error(f"Failed to interrupt OpenHands conversation: {exc}")
        return False

    def close_session(self, session_id: str) -> bool:
        """Close session and release underlying resources."""
        session = self.get_session(session_id)
        if isinstance(session, OpenHandsAgentSession):
            if session.conversation_obj is not None and hasattr(session.conversation_obj, "close"):
                try:
                    session.conversation_obj.close()
                except Exception as exc:
                    logger.debug(f"Error during SDK conversation close: {exc}")
            session.update_status(SessionStatus.CLOSED)
            self._sessions.pop(session_id, None)
            return True
        return False

    def get_historical_events(self, session_id: str) -> List[NormalizedEvent]:
        """Fetch historical events from OpenHands events search endpoint."""
        session = self.get_session(session_id)
        if not isinstance(session, OpenHandsAgentSession) or not session.remote_conversation_id:
            return []

        # If SDK conversation is available with cached events, return them
        if session.conversation_obj is not None and hasattr(session.conversation_obj, "state"):
            if hasattr(session.conversation_obj.state, "events"):
                return [
                    self.normalize_event(ev, session.config)
                    for ev in session.conversation_obj.state.events
                ]

        # Otherwise query REST /api/conversations/{id}/events/search
        try:
            resp = self._client.get(f"/api/conversations/{session.remote_conversation_id}/events/search")
            if resp.status_code == 200:
                raw_events = resp.json()
                items = raw_events if isinstance(raw_events, list) else raw_events.get("items", [])
                return [self.normalize_event(item, session.config) for item in items]
        except Exception as exc:
            logger.warning(f"Failed to fetch historical events for '{session_id}': {exc}")
        return []

    def observe_events(self, session_id: str) -> List[NormalizedEvent]:
        """Retrieve all currently recorded events for a session."""
        return self.get_historical_events(session_id)

    async def subscribe_events(self, session_id: str) -> AsyncIterator[NormalizedEvent]:
        """Stream events asynchronously for a given session."""
        session = self.get_session(session_id)
        events = self.get_historical_events(session_id)
        for ev in events:
            yield ev

    def normalize_event(
        self,
        raw_event: Any,
        session_config: Optional[SessionConfig] = None,
    ) -> NormalizedEvent:
        """Map raw OpenHands event payloads or SDK objects into Tersuite NormalizedEvents."""
        generation_id = session_config.generation_id if session_config else "gen-default"
        agent_run_id = session_config.agent_run_id if session_config else "run-default"

        if isinstance(raw_event, NormalizedEvent):
            return raw_event

        payload: Dict[str, Any] = {}
        event_type = EventType.AGENT_THINKING

        if hasattr(raw_event, "model_dump"):
            payload = raw_event.model_dump()
        elif isinstance(raw_event, dict):
            payload = raw_event
        else:
            payload = {"raw": str(raw_event)}

        raw_type = payload.get("type", "").lower()

        if raw_type in ("action", "tool_call", "actionevent") or "action" in payload:
            event_type = EventType.AGENT_TOOL_STARTED
        elif raw_type in ("observation", "observationevent") or "observation" in payload:
            event_type = EventType.AGENT_TOOL_FINISHED
        elif raw_type in ("agenterror", "conversationerror", "error"):
            event_type = EventType.AGENT_FAILED
        elif raw_type in ("completed", "finish", "done"):
            event_type = EventType.AGENT_COMPLETED
        elif raw_type in ("interrupt", "interruptevent", "cancelled", "cancel"):
            event_type = EventType.GENERATION_CANCELLED
        elif raw_type == "started":
            event_type = EventType.AGENT_STARTED
        else:
            event_type = EventType.AGENT_THINKING

        return NormalizedEvent(
            generation_id=generation_id,
            agent_run_id=agent_run_id,
            event_type=event_type,
            payload=payload,
        )

    def _normalize_openhands_event(
        self,
        raw_event: Any,
        session: Optional[AgentSession] = None,
    ) -> NormalizedEvent:
        """Compatibility helper for event normalization."""
        config = session.config if session else None
        return self.normalize_event(raw_event, config)
