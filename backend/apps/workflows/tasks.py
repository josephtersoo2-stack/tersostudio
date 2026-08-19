"""Celery background tasks for the durable workflow kernel."""
import logging
from celery import shared_task

from .services.leases import WorkflowLeaseService
from .services.outbox import OutboxService
from .services.scheduler import WorkflowSchedulerService

logger = logging.getLogger("tersuite.workflows.tasks")


@shared_task(bind=True, max_retries=0, name="apps.workflows.tasks.workflow_scheduler_tick")
def workflow_scheduler_tick(self) -> int:
    """Periodic task evaluating DAG readiness and advancing pending/retry packages."""
    try:
        return WorkflowSchedulerService.tick()
    except Exception as exc:
        logger.exception("Unexpected failure in workflow_scheduler_tick: %s", exc)
        raise


@shared_task(bind=True, max_retries=0, name="apps.workflows.tasks.workflow_reap_expired_leases")
def workflow_reap_expired_leases(self) -> int:
    """Periodic task reaping expired worker leases and scheduling retries."""
    try:
        return WorkflowLeaseService.reap_expired_leases()
    except Exception as exc:
        logger.exception("Unexpected failure in workflow_reap_expired_leases: %s", exc)
        raise


@shared_task(bind=True, max_retries=0, name="apps.workflows.tasks.workflow_dispatch_outbox")
def workflow_dispatch_outbox(self) -> int:
    """Periodic task claiming and dispatching transactional outbox events to Channels."""
    try:
        return OutboxService.publish_batch()
    except Exception as exc:
        logger.exception("Unexpected failure in workflow_dispatch_outbox: %s", exc)
        raise
