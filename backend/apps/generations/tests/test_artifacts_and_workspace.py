"""Tests for Artifacts, Storage Backends, and Workspaces."""
import tempfile
from pathlib import Path
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.generations.enums import ArtifactType
from apps.generations.models import Artifact, Generation, Workspace
from apps.generations.storage.local import LocalFileSystemArtifactStorage
from apps.projects.models import Project

User = get_user_model()


class ArtifactStorageAndAPITests(TestCase):
    """Test suite verifying artifact persistence, storage abstraction, and download API."""

    databases = {"default"}

    def setUp(self):
        self.client = APIClient()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage = LocalFileSystemArtifactStorage(base_dir=Path(self.temp_dir.name))

        self.user = User.objects.create_user(
            email="artifact.tester@tersuite.com",
            password="StrongPassword123!",
        )
        self.project = Project.objects.create(
            user=self.user,
            name="WordPress LMS Core",
        )
        self.generation = Generation.objects.create(
            project=self.project,
            user=self.user,
            prompt="Build LMS core plugin.",
        )
        self.workspace = Workspace.objects.create(
            generation=self.generation,
            workspace_path=f"workspaces/{self.generation.id}",
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_local_storage_save_read_and_checksum(self):
        """Verify storage backend writes bytes, returns SHA-256 and reads accurately."""
        sample_code = b"<?php\n// Plugin Main File\nfunction tersuite_init() {}\n"
        storage_key, size_bytes, checksum = self.storage.save_artifact(
            generation_id=str(self.generation.id),
            artifact_id="art-001",
            filename="tersuite-lms.php",
            content=sample_code,
        )

        self.assertEqual(size_bytes, len(sample_code))
        self.assertEqual(len(checksum), 64)  # SHA-256 hex string length
        self.assertIn("tersuite-lms.php", storage_key)

        read_bytes = self.storage.read_artifact(storage_key)
        self.assertEqual(read_bytes, sample_code)

    def test_artifact_model_creation_and_api_list(self):
        """Verify Artifact records are listed via REST API."""
        content = b"manifest content"
        storage_key, size_bytes, checksum = self.storage.save_artifact(
            generation_id=str(self.generation.id),
            artifact_id="art-002",
            filename="manifest.json",
            content=content,
        )

        artifact = Artifact.objects.create(
            generation=self.generation,
            name="manifest.json",
            file_path="manifest.json",
            artifact_type=ArtifactType.CONFIGURATION,
            mime_type="application/json",
            size_bytes=size_bytes,
            checksum_sha256=checksum,
            storage_backend="local_filesystem",
            storage_key=storage_key,
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.get(f"/api/v1/generations/{self.generation.id}/artifacts/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], str(artifact.id))
        self.assertEqual(response.data[0]["checksum_sha256"], checksum)

    def test_artifact_download_endpoint(self):
        """Verify GET /api/v1/artifacts/{id}/download/ streams artifact bytes."""
        from unittest.mock import patch
        php_code = b"<?php echo 'Tersuite Plugin'; ?>"
        storage_key, size_bytes, checksum = self.storage.save_artifact(
            generation_id=str(self.generation.id),
            artifact_id="art-003",
            filename="plugin.php",
            content=php_code,
        )

        artifact = Artifact.objects.create(
            generation=self.generation,
            name="plugin.php",
            file_path="plugin.php",
            artifact_type=ArtifactType.SOURCE_CODE,
            mime_type="application/x-php",
            size_bytes=size_bytes,
            checksum_sha256=checksum,
            storage_backend="local_filesystem",
            storage_key=storage_key,
        )

        self.client.force_authenticate(user=self.user)
        with patch("apps.generations.views.get_artifact_storage", return_value=self.storage):
            response = self.client.get(f"/api/v1/artifacts/{artifact.id}/download/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.content, php_code)
        self.assertEqual(response["Content-Type"], "application/x-php")
        self.assertIn("plugin.php", response["Content-Disposition"])

    def test_generation_workspace_endpoint(self):
        """Verify GET /api/v1/generations/{id}/workspace/ returns workspace details."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f"/api/v1/generations/{self.generation.id}/workspace/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], str(self.workspace.id))
        self.assertEqual(response.data["workspace_path"], f"workspaces/{self.generation.id}")
        self.assertTrue(response.data["is_active"])
