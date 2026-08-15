"""Custom exceptions for the Generations domain."""


class GenerationDomainError(Exception):
    """Base exception for generations domain."""
    pass


class InvalidStateTransitionError(GenerationDomainError):
    """Raised when an illegal or unsupported generation state transition is requested."""

    def __init__(self, current_status: str, target_status: str, message: str = ""):
        self.current_status = current_status
        self.target_status = target_status
        msg = message or f"Cannot transition generation from '{current_status}' to '{target_status}'."
        super().__init__(msg)


class ArtifactStorageError(GenerationDomainError):
    """Raised when saving, reading, or deleting an artifact fails in the storage backend."""
    pass


class WorkspaceError(GenerationDomainError):
    """Raised when an operation on a workspace fails."""
    pass


class StepNotExecutableError(GenerationDomainError):
    """Raised when execution is attempted on a step/generation not ready for it."""
    pass
