"""Minimal workspace abstraction for Phase 1 execution."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class WorkspaceConfig:
    """Configuration payload for workspace provisioning."""

    workspace_id: str
    base_dir: Optional[str] = None
    environment_variables: Dict[str, str] = field(default_factory=dict)


class WorkspaceInterface(ABC):
    """Abstract interface defining the execution boundary for agent workspaces."""

    @property
    @abstractmethod
    def workspace_id(self) -> str:
        """Return the unique workspace identifier."""
        pass

    @abstractmethod
    def setup(self) -> bool:
        """Initialize and prepare the execution workspace."""
        pass

    @abstractmethod
    def teardown(self) -> bool:
        """Clean up and destroy the workspace."""
        pass

    @abstractmethod
    def execute_command(self, command: str) -> Dict[str, str]:
        """Execute a raw command inside the workspace."""
        pass
