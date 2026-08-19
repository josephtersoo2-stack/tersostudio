"""Django Admin registration for Workflows domain models."""
from django.contrib import admin
from .models import (
    WorkflowRun,
    WorkPackage,
    WorkPackageDependency,
    WorkPackageAttempt,
    WorkPackageLease,
    WorkflowCommand,
    OutboxEvent,
)


@admin.register(WorkflowRun)
class WorkflowRunAdmin(admin.ModelAdmin):
    list_display = ["id", "generation", "run_number", "status", "organization", "created_at"]
    list_filter = ["status", "organization"]
    search_fields = ["id", "generation__id"]


@admin.register(WorkPackage)
class WorkPackageAdmin(admin.ModelAdmin):
    list_display = ["id", "key", "name", "workflow_run", "status", "priority", "attempt_count", "created_at"]
    list_filter = ["status", "priority", "organization"]
    search_fields = ["id", "key", "name"]


@admin.register(WorkPackageDependency)
class WorkPackageDependencyAdmin(admin.ModelAdmin):
    list_display = ["id", "workflow_run", "predecessor", "successor", "dependency_type"]
    list_filter = ["dependency_type"]


@admin.register(WorkPackageAttempt)
class WorkPackageAttemptAdmin(admin.ModelAdmin):
    list_display = ["id", "work_package", "attempt_number", "status", "worker_id", "started_at", "completed_at"]
    list_filter = ["status", "worker_id"]


@admin.register(WorkPackageLease)
class WorkPackageLeaseAdmin(admin.ModelAdmin):
    list_display = ["id", "lease_token", "work_package", "worker_id", "expires_at", "released_at", "release_reason"]
    list_filter = ["release_reason"]


@admin.register(WorkflowCommand)
class WorkflowCommandAdmin(admin.ModelAdmin):
    list_display = ["id", "generation", "command_type", "idempotency_key", "status", "applied_at"]
    list_filter = ["command_type", "status", "organization"]
    search_fields = ["idempotency_key", "generation__id"]


@admin.register(OutboxEvent)
class OutboxEventAdmin(admin.ModelAdmin):
    list_display = ["event_id", "event_type", "aggregate_type", "aggregate_id", "published_at", "available_at", "publish_attempts"]
    list_filter = ["event_type", "aggregate_type"]
    search_fields = ["event_id", "aggregate_id"]
