"""Tersuite Agent Runtime package.

Provides the decoupled runtime abstraction layer between Tersuite Studio
and underlying agent engines (e.g. OpenHands).
"""
from .interfaces.runtime import TersuiteAgentRuntime
from .interfaces.session import AgentSession
from .exceptions import (
    AgentRuntimeError,
    SessionNotFoundError,
    TaskExecutionError,
    AdapterConnectionError,
    TimeoutExecutionError,
)

__all__ = [
    "TersuiteAgentRuntime",
    "AgentSession",
    "AgentRuntimeError",
    "SessionNotFoundError",
    "TaskExecutionError",
    "AdapterConnectionError",
    "TimeoutExecutionError",
]
