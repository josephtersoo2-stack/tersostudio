"""Abstract interface for artifact storage backends."""
from abc import ABC, abstractmethod
from typing import Tuple


class ArtifactStorageBackend(ABC):
    """Abstract interface for storing, reading, and deleting durable artifacts."""

    @abstractmethod
    def save_artifact(
        self,
        generation_id: str,
        artifact_id: str,
        filename: str,
        content: bytes,
    ) -> Tuple[str, int, str]:
        """Save artifact bytes to storage backend.

        Returns:
            Tuple of (storage_key, size_bytes, checksum_sha256)
        """
        pass

    @abstractmethod
    def read_artifact(self, storage_key: str) -> bytes:
        """Read artifact content bytes by storage key."""
        pass

    @abstractmethod
    def delete_artifact(self, storage_key: str) -> bool:
        """Delete artifact from storage backend by storage key."""
        pass

    @abstractmethod
    def get_absolute_path_or_url(self, storage_key: str) -> str:
        """Return the absolute local file path or public/signed URL for download."""
        pass
