"""Artifact storage backend factory."""
from .base import ArtifactStorageBackend
from .local import LocalFileSystemArtifactStorage

_default_storage: ArtifactStorageBackend | None = None


def get_artifact_storage() -> ArtifactStorageBackend:
    """Return the configured artifact storage backend singleton."""
    global _default_storage
    if _default_storage is None:
        _default_storage = LocalFileSystemArtifactStorage()
    return _default_storage
