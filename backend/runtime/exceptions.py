"""Runtime exceptions for Tersuite Agent Runtime."""


class AgentRuntimeError(Exception):
    """Base exception for all agent runtime errors."""

    def __init__(self, message: str, details: dict = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class AdapterConnectionError(AgentRuntimeError):
    """Raised when the runtime cannot establish a connection with the Agent Server."""
    pass


class SessionNotFoundError(AgentRuntimeError):
    """Raised when an operation is attempted on a non-existent agent session."""
    pass


class TaskExecutionError(AgentRuntimeError):
    """Raised when an agent task execution fails critically."""
    pass


class TimeoutExecutionError(AgentRuntimeError):
    """Raised when an agent execution exceeds the configured timeout threshold."""
    pass
