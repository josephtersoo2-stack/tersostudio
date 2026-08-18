"""OpenHands Agent Server adapter implementation for Tersuite.

Uses the official OpenHands Software Agent SDK (v1.42.1) RemoteConversation
as its sole execution path:
  - RemoteWorkspace: Sandboxed workspace connection to OpenHands Agent Server
  - Conversation / RemoteConversation: Lifecycle management (creation, send_message, run, interrupt, close)
  - Live Event Streaming: Real-time event subscription callback via WebSocket during execution
  - Events & Stats: Direct extraction and normalization from OpenHands state
  - Strict Failure Classification: Rich error categorization without homemade fallback retries
"""
import logging
import os
import uuid
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple

import httpx
from pydantic import SecretStr

from apps.realtime.events import EventType, NormalizedEvent
from runtime.exceptions import (
    AdapterConnectionError,
    SessionNotFoundError,
    TaskExecutionError,
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

# Import official OpenHands SDK components
try:
    from openhands.sdk.agent import Agent as OpenHandsAgent
    from openhands.sdk.conversation import Conversation as OpenHandsConversation
    from openhands.sdk.conversation.exceptions import (
        ConversationRunError,
        WebSocketConnectionError,
    )
    from openhands.sdk.conversation.impl.remote_conversation import (
        RemoteConversation,
    )
    from openhands.sdk.conversation.state import ConversationExecutionStatus
    from openhands.sdk.event import Event as OpenHandsEvent
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
    ConversationRunError = Exception
    WebSocketConnectionError = Exception


def _resolve_llm_credentials(
    model_name: str,
    configured_key: Optional[SecretStr],
    configured_base_url: Optional[str],
) -> Tuple[Optional[SecretStr], Optional[str]]:
    """Select only the credential matching the model prefix.

    openrouter/ -> OPENROUTER_API_KEY and OPENROUTER_BASE_URL
    anthropic/  -> ANTHROPIC_API_KEY
    openai/     -> OPENAI_API_KEY
    gemini/     -> GEMINI_API_KEY
    groq/       -> GROQ_API_KEY

    For an unknown provider prefix, pass no explicit provider key and do not borrow another provider's key.
    Never use the Agent Server key.
    """
    if model_name.startswith("openrouter/"):
        env_val = os.getenv("OPENROUTER_API_KEY")
        key = configured_key if configured_key is not None else (SecretStr(env_val) if env_val else None)
        base_url = configured_base_url or os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        return key, base_url
    elif model_name.startswith("anthropic/"):
        env_val = os.getenv("ANTHROPIC_API_KEY")
        key = configured_key if configured_key is not None else (SecretStr(env_val) if env_val else None)
        return key, configured_base_url
    elif model_name.startswith("openai/"):
        env_val = os.getenv("OPENAI_API_KEY")
        key = configured_key if configured_key is not None else (SecretStr(env_val) if env_val else None)
        return key, configured_base_url
    elif model_name.startswith("gemini/"):
        env_val = os.getenv("GEMINI_API_KEY")
        key = configured_key if configured_key is not None else (SecretStr(env_val) if env_val else None)
        return key, configured_base_url
    elif model_name.startswith("groq/"):
        env_val = os.getenv("GROQ_API_KEY")
        key = configured_key if configured_key is not None else (SecretStr(env_val) if env_val else None)
        return key, configured_base_url
    else:
        return None, configured_base_url


class OpenHandsAgentRuntime(TersuiteAgentRuntime):
    """Production adapter bridging Tersuite to OpenHands Software Agent SDK v1.42.1.

    The official OpenHands SDK RemoteConversation is the sole execution path.
    """

    def __init__(self, config: Optional[OpenHandsServerConfig] = None):
        self.config = config or OpenHandsServerConfig()
        self._sessions: Dict[str, OpenHandsAgentSession] = {}
        self._results: Dict[str, TaskResult] = {}

    def create_session(self, config: SessionConfig) -> AgentSession:
        """Instantiate a new conversation session using official OpenHands SDK RemoteConversation.

        Creates conversation via official OpenHands SDK Conversation factory.
        Wires real-time WebSocket event callbacks to enable live event streaming.
        Raises AdapterConnectionError if the remote server cannot be reached.
        Never fabricates detached synthetic conversation IDs.
        """
        session_id = f"oh-sess-{uuid.uuid4().hex[:12]}"
        conversation_id: Optional[str] = None
        conversation_obj: Optional[Any] = None

        if not OPENHANDS_SDK_AVAILABLE:
            raise AdapterConnectionError(
                "OpenHands Software Agent SDK is not installed in the environment."
            )

        session = OpenHandsAgentSession(
            session_id=session_id,
            conversation_id=None,
            config=config,
            conversation_obj=None,
        )

        def live_event_callback(raw_event: Any) -> None:
            """Callback invoked synchronously by OpenHands SDK WebSocket client on incoming events."""
            try:
                norm_event = self.normalize_event(raw_event, config)
                session.add_event(norm_event)
                if config.on_event:
                    config.on_event(norm_event)
            except Exception as ev_err:
                logger.warning(
                    "Error normalizing or forwarding live OpenHands event: %s",
                    ev_err,
                    exc_info=True,
                )

        try:
            model_name = config.model or self.config.llm_default_model
            llm_key, base_url = _resolve_llm_credentials(
                model_name=model_name,
                configured_key=self.config.llm_api_key,
                configured_base_url=self.config.llm_base_url,
            )

            llm_kwargs: Dict[str, Any] = {
                "model": model_name,
                "api_key": llm_key,
            }
            if base_url:
                llm_kwargs["base_url"] = base_url

            llm = OpenHandsLLM(**llm_kwargs)
            agent = OpenHandsAgent(
                llm=llm,
                system_prompt=config.system_prompt,
            )
            server_key_unwrapped = (
                self.config.server_api_key.get_secret_value()
                if self.config.server_api_key
                else None
            )
            workspace = OpenHandsRemoteWorkspace(
                host=self.config.server_url,
                api_key=server_key_unwrapped,
                working_dir=".",
                read_timeout=self.config.server_timeout_seconds,
            )

            conversation_obj = OpenHandsConversation(
                agent=agent,
                workspace=workspace,
                max_iteration_per_run=config.max_iterations,
                visualizer=None,
                callbacks=[live_event_callback],
            )

            if hasattr(conversation_obj, "id"):
                conversation_id = str(conversation_obj.id)
            elif hasattr(conversation_obj, "conversation_id"):
                conversation_id = str(conversation_obj.conversation_id)

        except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError, WebSocketConnectionError) as exc:
            err_msg = f"Cannot connect to OpenHands Agent Server at {self.config.server_url}: {exc}"
            logger.error(err_msg)
            raise AdapterConnectionError(err_msg, details={"server_url": self.config.server_url}) from exc
        except Exception as exc:
            err_msg = f"Failed to instantiate OpenHands RemoteConversation: {exc}"
            logger.error(err_msg)
            raise AdapterConnectionError(err_msg) from exc

        session._conversation_id = conversation_id
        session._conversation_obj = conversation_obj
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
        """Send a message to the OpenHands conversation and execute the agent run via SDK.

        If execution fails, accurately classifies the failure category and retryability.
        Never falls back to a handwritten REST retry.
        """
        session = self.get_session(session_id)
        if not isinstance(session, OpenHandsAgentSession):
            raise TaskExecutionError(f"Invalid session type for '{session_id}'.")

        conv = session.conversation_obj
        if conv is None or not hasattr(conv, "send_message"):
            err_msg = f"Session '{session_id}' has no valid OpenHands SDK Conversation instance."
            session.update_status(SessionStatus.FAILED)
            res = TaskResult(
                session_id=session_id,
                success=False,
                execution_status=ExecutionStatus.AGENT_FAILED,
                failure_category=FailureCategory.AGENT_FATAL,
                error=err_msg,
            )
            self._results[session_id] = res
            return res

        session.update_status(SessionStatus.RUNNING)

        try:
            # 1. Send user message via official SDK
            conv.send_message(prompt)

            # 2. Trigger run and wait for completion via official SDK (events stream live via callbacks)
            conv.run()

            # 3. Extract output and stats from official SDK state
            output = ""
            artifacts = []
            token_usage = {}

            if hasattr(conv, "state") and hasattr(conv.state, "events"):
                for event in conv.state.events:
                    if hasattr(event, "role") and getattr(event, "role", None) in ("assistant", "agent"):
                        content = getattr(event, "content", None)
                        if isinstance(content, str) and content:
                            output = content
                    elif hasattr(event, "output"):
                        out_val = getattr(event, "output", None)
                        if isinstance(out_val, str) and out_val:
                            output = out_val

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
                metadata={"conversation_id": session.remote_conversation_id},
            )
            self._results[session_id] = result
            return result

        except (httpx.ConnectError, httpx.NetworkError, WebSocketConnectionError) as net_err:
            session.update_status(SessionStatus.FAILED)
            err_msg = f"Infrastructure connection error during OpenHands execution: {net_err}"
            logger.error(err_msg)
            res = TaskResult(
                session_id=session_id,
                success=False,
                execution_status=ExecutionStatus.INFRASTRUCTURE_UNAVAILABLE,
                failure_category=FailureCategory.NETWORK_CONNECTION,
                retryable=True,
                error=err_msg,
                error_details={"exception": str(net_err), "type": type(net_err).__name__, "retryable": True},
            )
            self._results[session_id] = res
            return res

        except (TimeoutError, httpx.TimeoutException) as timeout_err:
            session.update_status(SessionStatus.FAILED)
            err_msg = f"Execution timed out on OpenHands Agent Server: {timeout_err}"
            logger.error(err_msg)
            res = TaskResult(
                session_id=session_id,
                success=False,
                execution_status=ExecutionStatus.TIMEOUT,
                failure_category=FailureCategory.TIMEOUT,
                retryable=True,
                error=err_msg,
                error_details={"exception": str(timeout_err), "type": type(timeout_err).__name__, "retryable": True},
            )
            self._results[session_id] = res
            return res

        except Exception as exec_err:
            session.update_status(SessionStatus.FAILED)
            err_str = str(exec_err)
            err_lower = err_str.lower()
            logger.error(f"OpenHands SDK execution failed: {err_str}")

            # Precise Classification based on runtime/exception details
            if any(term in err_lower for term in ["connect", "refused", "connection reset", "network", "remote protocol", "server disconnected"]):
                category = FailureCategory.NETWORK_CONNECTION
                retryable = True
            elif any(term in err_lower for term in ["timeout", "timed out", "deadline exceeded"]):
                category = FailureCategory.TIMEOUT
                retryable = True
            elif any(term in err_lower for term in ["badrequesterror", "model", "api key", "provider", "ratelimit", "rate limit", "quota", "overloaded", "context_length", "invalid_request"]):
                category = FailureCategory.MODEL_ERROR
                retryable = any(term in err_lower for term in ["ratelimit", "rate limit", "429", "500", "503", "overloaded", "server error"])
            elif "tool" in err_lower or "action" in err_lower or "command" in err_lower:
                category = FailureCategory.TOOL_ERROR
                retryable = False
            else:
                category = FailureCategory.AGENT_FATAL
                retryable = False

            res = TaskResult(
                session_id=session_id,
                success=False,
                execution_status=ExecutionStatus.AGENT_FAILED,
                failure_category=category,
                retryable=retryable,
                error=err_str,
                error_details={"exception": err_str, "type": type(exec_err).__name__, "retryable": retryable},
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
        """Interrupt and cancel execution of an active OpenHands conversation via official SDK."""
        session = self.get_session(session_id)
        if not isinstance(session, OpenHandsAgentSession) or session.conversation_obj is None:
            return False

        if hasattr(session.conversation_obj, "interrupt"):
            try:
                session.conversation_obj.interrupt()
                session.update_status(SessionStatus.CANCELLED)
                return True
            except Exception as exc:
                logger.error(f"Failed to interrupt OpenHands conversation: {exc}")
        return False

    def close_session(self, session_id: str) -> bool:
        """Close session and release underlying OpenHands SDK resources."""
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
        """Fetch historical events from OpenHands SDK conversation state."""
        session = self.get_session(session_id)
        if not isinstance(session, OpenHandsAgentSession) or session.conversation_obj is None:
            return []

        conv = session.conversation_obj
        if hasattr(conv, "state") and hasattr(conv.state, "events"):
            return [
                self.normalize_event(ev, session.config)
                for ev in conv.state.events
            ]
        return []

    def observe_events(self, session_id: str) -> List[NormalizedEvent]:
        """Retrieve all currently recorded events for a session."""
        return self.get_historical_events(session_id)

    async def subscribe_events(self, session_id: str) -> AsyncIterator[NormalizedEvent]:
        """Stream events asynchronously for a given session."""
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
            try:
                payload = raw_event.model_dump(mode="json")
            except Exception:
                payload = raw_event.model_dump()
        elif isinstance(raw_event, dict):
            payload = raw_event
        else:
            payload = {"raw": str(raw_event)}

        # Class/type inspection
        type_name = type(raw_event).__name__.lower() if not isinstance(raw_event, dict) else ""
        raw_type = str(payload.get("type", "")).lower()

        if (
            "action" in type_name
            or "toolcall" in type_name
            or raw_type in ("action", "tool_call", "actionevent", "acptoolcallevent")
            or "action" in payload
        ):
            event_type = EventType.AGENT_TOOL_STARTED
        elif (
            "observation" in type_name
            or raw_type in ("observation", "observationevent")
            or "observation" in payload
        ):
            event_type = EventType.AGENT_TOOL_FINISHED
        elif (
            "error" in type_name
            or raw_type in ("agenterror", "conversationerror", "error", "agenterrorevent")
        ):
            event_type = EventType.AGENT_FAILED
        elif (
            raw_type in ("completed", "finish", "done")
            or (payload.get("key") == "execution_status" and str(payload.get("value", "")).lower() in ("finished", "completed"))
        ):
            event_type = EventType.AGENT_COMPLETED
        elif (
            "interrupt" in type_name
            or "pause" in type_name
            or raw_type in ("interrupt", "interruptevent", "cancelled", "cancel", "pause")
        ):
            event_type = EventType.GENERATION_CANCELLED
        elif (
            raw_type == "started"
            or (payload.get("key") == "execution_status" and str(payload.get("value", "")).lower() == "running")
        ):
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
