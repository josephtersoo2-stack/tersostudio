"""Celery background tasks for the durable workflow kernel."""
import logging
from celery import shared_task

from .services.leases import WorkflowLeaseService
from .services.outbox import OutboxService
from .services.scheduler import WorkflowSchedulerService

logger = logging.getLogger("tersuite.workflows.tasks")


@shared_task(bind=True, name="apps.workflows.tasks.workflow_scheduler_tick")
def workflow_scheduler_tick(self) -> int:
    """Periodic task evaluating DAG readiness and advancing pending/retry packages."""
    try:
        count = WorkflowSchedulerService.tick()
        return count
    except Exception as exc:
        logger.exception("Error in workflow_scheduler_tick: %s", exc)
        return 0


@shared_task(bind=True, name="apps.workflows.tasks.workflow_reap_expired_leases")
def workflow_reap_expired_leases(self) -> int:
    """Periodic task reaping expired worker leases and scheduling retries."""
    try:
        count = WorkflowLeaseService.reap_expired_leases()
        return count
    except Exception as exc:
        logger.exception("Error in workflow_reap_expired_leases: %s", exc)
        return 0


@shared_task(bind=True, name="apps.workflows.tasks.workflow_dispatch_outbox")
def workflow_dispatch_outbox(self) -> int:
    """Periodic task claiming and dispatching transactional outbox events to Channels."""
    try:
        count = OutboxService.publish_batch()
        return count
    except Exception as exc:
        logger.exception("Error in workflow_dispatch_outbox: %s", exc)
        return 0
