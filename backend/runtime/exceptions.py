"""Runtime exceptions for Tersuite Agent Runtime."""
from typing import Any, Dict, Optional
from runtime.interfaces.session import FailureCategory


class AgentRuntimeError(Exception):
    """Base exception for all agent runtime errors."""

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        failure_category: FailureCategory = FailureCategory.AGENT_FATAL,
        retryable: bool = False,
    ):
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.failure_category = failure_category
        self.retryable = retryable


class AdapterConnectionError(AgentRuntimeError):
    """Raised when the runtime cannot establish a connection with the Agent Server."""

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        retryable: bool = True,
    ):
        super().__init__(
            message=message,
            details=details,
            failure_category=FailureCategory.NETWORK_CONNECTION,
            retryable=retryable,
        )


class SessionNotFoundError(AgentRuntimeError):
    """Raised when an operation is attempted on a non-existent agent session."""

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            details=details,
            failure_category=FailureCategory.AGENT_FATAL,
            retryable=False,
        )


class TaskExecutionError(AgentRuntimeError):
    """Raised when an agent task execution fails."""

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        failure_category: FailureCategory = FailureCategory.AGENT_FATAL,
        retryable: bool = False,
    ):
        super().__init__(
            message=message,
            details=details,
            failure_category=failure_category,
            retryable=retryable,
        )


class TimeoutExecutionError(AgentRuntimeError):
    """Raised when an agent execution exceeds the configured timeout threshold."""

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        retryable: bool = True,
    ):
        super().__init__(
            message=message,
            details=details,
            failure_category=FailureCategory.TIMEOUT,
            retryable=retryable,
        )
