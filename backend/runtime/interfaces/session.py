"""Agent session models, status enums, and abstract session interface."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class SessionStatus(str, Enum):
    """Lifecycle states of an Agent Session."""

    INITIALIZING = "INITIALIZING"
    ACTIVE = "ACTIVE"
    RUNNING = "RUNNING"
    WAITING = "WAITING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class ExecutionStatus(str, Enum):
    """Standardized task execution outcome status."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    AGENT_FAILED = "AGENT_FAILED"
    INFRASTRUCTURE_UNAVAILABLE = "INFRASTRUCTURE_UNAVAILABLE"
    AUTHENTICATION_FAILED = "AUTHENTICATION_FAILED"
    TIMEOUT = "TIMEOUT"
    CANCELLED = "CANCELLED"


class FailureCategory(str, Enum):
    """Classification of failures encountered during agent execution."""

    NONE = "NONE"
    NETWORK_CONNECTION = "NETWORK_CONNECTION"
    AUTHENTICATION = "AUTHENTICATION"
    TIMEOUT = "TIMEOUT"
    MODEL_ERROR = "MODEL_ERROR"
    TOOL_ERROR = "TOOL_ERROR"
    AGENT_FATAL = "AGENT_FATAL"
    WORKSPACE_ERROR = "WORKSPACE_ERROR"


@dataclass
class SessionConfig:
    """Configuration payload for instantiating an Agent Session."""

    generation_id: str
    agent_run_id: str
    model: str = "anthropic/claude-sonnet-4-5-20250929"
    system_prompt: str = ""
    tools: List[str] = field(default_factory=list)
    max_iterations: int = 30
    timeout_seconds: int = 300
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskResult:
    """Standardized outcome payload returned upon task completion.

    Preserves structured failure category and execution status rather than
    collapsing errors into generic strings.
    """

    session_id: str
    success: bool
    execution_status: ExecutionStatus = ExecutionStatus.SUCCESS
    failure_category: FailureCategory = FailureCategory.NONE
    output: str = ""
    artifacts: List[str] = field(default_factory=list)
    error: Optional[str] = None
    error_details: Dict[str, Any] = field(default_factory=dict)
    retryable: bool = False
    token_usage: Dict[str, int] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class AgentSession(ABC):
    """Abstract interface representing an active agent execution session.

    NOTE: In Phase 1, sessions are tracked in-memory by the runtime adapter.
    Durable ORM persistence in PostgreSQL is scheduled for Phase 2.
    """

    @property
    @abstractmethod
    def session_id(self) -> str:
        """Return the unique Tersuite session identifier (UUID)."""
        pass

    @property
    @abstractmethod
    def remote_conversation_id(self) -> Optional[str]:
        """Return the underlying OpenHands conversation identifier, if assigned."""
        pass

    @property
    @abstractmethod
    def config(self) -> SessionConfig:
        """Return the configuration used to create this session."""
        pass

    @property
    @abstractmethod
    def status(self) -> SessionStatus:
        """Return the current execution status of the session."""
        pass

    @abstractmethod
    def update_status(self, new_status: SessionStatus) -> None:
        """Update the internal session status."""
        pass
