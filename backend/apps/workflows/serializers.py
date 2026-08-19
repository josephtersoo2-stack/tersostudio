"""Serializers for Workflow Runs, Work Packages, Attempts, and Dependencies."""
from rest_framework import serializers

from .models import (
    WorkflowRun,
    WorkPackage,
    WorkPackageAttempt,
    WorkPackageDependency,
)


class WorkPackageDependencySerializer(serializers.ModelSerializer):
    """Serializer for DAG dependencies."""

    class Meta:
        model = WorkPackageDependency
        fields = [
            "id",
            "predecessor",
            "successor",
            "dependency_type",
            "created_at",
        ]
        read_only_fields = fields


class WorkPackageAttemptSerializer(serializers.ModelSerializer):
    """Serializer for work package execution attempts."""

    class Meta:
        model = WorkPackageAttempt
        fields = [
            "id",
            "work_package",
            "attempt_number",
            "status",
            "worker_id",
            "started_at",
            "completed_at",
            "heartbeat_at",
            "retryable",
            "failure_category",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class WorkPackageSerializer(serializers.ModelSerializer):
    """Serializer for work packages."""

    class Meta:
        model = WorkPackage
        fields = [
            "id",
            "workflow_run",
            "generation_step",
            "key",
            "name",
            "status",
            "priority",
            "max_attempts",
            "attempt_count",
            "timeout_seconds",
            "retry_base_seconds",
            "next_attempt_at",
            "ready_at",
            "started_at",
            "completed_at",
            "failure_category",
            "error_message",
            "state_version",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class WorkflowRunSerializer(serializers.ModelSerializer):
    """Serializer for workflow runs."""

    packages = WorkPackageSerializer(many=True, read_only=True)

    class Meta:
        model = WorkflowRun
        fields = [
            "id",
            "generation",
            "run_number",
            "status",
            "state_version",
            "started_at",
            "completed_at",
            "paused_at",
            "cancel_requested_at",
            "failure_category",
            "error_message",
            "metadata",
            "packages",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields
