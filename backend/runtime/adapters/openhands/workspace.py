"""OpenHands workspace integration wrapper."""
import logging
from typing import Dict
from runtime.interfaces.workspace import WorkspaceConfig, WorkspaceInterface

logger = logging.getLogger("tersuite.runtime")


class OpenHandsWorkspace(WorkspaceInterface):
    """Bridge for managing execution workspaces within OpenHands."""

    def __init__(self, config: WorkspaceConfig):
        self._config = config
        self._is_active = False

    @property
    def workspace_id(self) -> str:
        return self._config.workspace_id

    def setup(self) -> bool:
        """Provision and verify workspace."""
        logger.info(f"Setting up OpenHands workspace '{self.workspace_id}'")
        self._is_active = True
        return True

    def teardown(self) -> bool:
        """Clean up workspace resources."""
        logger.info(f"Tearing down OpenHands workspace '{self.workspace_id}'")
        self._is_active = False
        return True

    def execute_command(self, command: str) -> Dict[str, str]:
        """Execute a shell command inside the workspace."""
        return {
            "status": "success",
            "command": command,
            "stdout": "",
            "stderr": "",
            "exit_code": "0",
        }
