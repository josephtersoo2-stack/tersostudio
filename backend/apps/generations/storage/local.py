"""Local filesystem implementation of the artifact storage backend."""
import hashlib
import os
from pathlib import Path
from typing import Tuple
from django.conf import settings

from apps.generations.exceptions import ArtifactStorageError
from .base import ArtifactStorageBackend


class LocalFileSystemArtifactStorage(ArtifactStorageBackend):
    """Stores artifacts in the local server media/filesystem directory."""

    def __init__(self, base_dir: Path | None = None):
        if base_dir is None:
            media_root = getattr(settings, "MEDIA_ROOT", Path(settings.BASE_DIR) / "media")
            self.base_dir = Path(media_root) / "artifacts"
        else:
            self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save_artifact(
        self,
        generation_id: str,
        artifact_id: str,
        filename: str,
        content: bytes,
    ) -> Tuple[str, int, str]:
        """Save artifact bytes to disk and compute SHA-256 checksum."""
        try:
            gen_dir = self.base_dir / str(generation_id)
            gen_dir.mkdir(parents=True, exist_ok=True)

            safe_filename = os.path.basename(filename) or "artifact.bin"
            file_path = gen_dir / f"{artifact_id}_{safe_filename}"

            with open(file_path, "wb") as f:
                f.write(content)

            size_bytes = len(content)
            checksum_sha256 = hashlib.sha256(content).hexdigest()
            storage_key = str(file_path.relative_to(self.base_dir)).replace("\\", "/")

            return storage_key, size_bytes, checksum_sha256
        except Exception as exc:
            raise ArtifactStorageError(f"Failed to save artifact '{filename}': {exc}") from exc

    def read_artifact(self, storage_key: str) -> bytes:
        """Read artifact bytes from disk."""
        try:
            file_path = self.base_dir / storage_key
            if not file_path.exists():
                raise ArtifactStorageError(f"Artifact file '{storage_key}' not found on disk.")
            with open(file_path, "rb") as f:
                return f.read()
        except Exception as exc:
            raise ArtifactStorageError(f"Failed to read artifact '{storage_key}': {exc}") from exc

    def delete_artifact(self, storage_key: str) -> bool:
        """Delete artifact file from disk."""
        try:
            file_path = self.base_dir / storage_key
            if file_path.exists():
                file_path.unlink()
                return True
            return False
        except Exception as exc:
            raise ArtifactStorageError(f"Failed to delete artifact '{storage_key}': {exc}") from exc

    def get_absolute_path_or_url(self, storage_key: str) -> str:
        """Return the absolute path on disk."""
        return str(self.base_dir / storage_key)
