"""Agent session models and abstract session interface."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class SessionStatus(str, Enum):
    """Lifecycle states of an Agent Session."""

    INITIALIZING = "INITIALIZING"
    ACTIVE = "ACTIVE"
    WAITING = "WAITING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


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
    """Standardized outcome payload returned upon task completion."""

    session_id: str
    success: bool
    output: str = ""
    artifacts: List[str] = field(default_factory=list)
    error: Optional[str] = None
    token_usage: Dict[str, int] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class AgentSession(ABC):
    """Abstract interface representing an active agent execution session."""

    @property
    @abstractmethod
    def session_id(self) -> str:
        """Return the unique session identifier."""
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
