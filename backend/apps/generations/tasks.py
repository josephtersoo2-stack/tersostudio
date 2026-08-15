"""Celery tasks for the generations execution pipeline.

Discovered automatically by config/celery.py's app.autodiscover_tasks()
since it lives at the top level of an installed app package.
"""
import logging

from celery import shared_task

logger = logging.getLogger("tersuite.orchestration")


@shared_task(
    bind=True,
    # AgentRun-level retries are a deliberate decision (create a new
    # AgentRun via ExecutionService.create_and_dispatch, bumping
    # run_number) rather than a silent Celery re-delivery of the same
    # run — see AgentRun.run_number and the retry flow in the roadmap.
    max_retries=0,
    acks_late=True,
)
def execute_agent_run(self, agent_run_id: str) -> str:
    """Execute a single AgentRun against the configured runtime adapter.

    Enqueued by ExecutionService.create_and_dispatch(). All the actual
    work, and all failure handling, lives in ExecutionService.run() so it
    stays directly testable without a running Celery worker.
    """
    from apps.generations.services.execution_service import ExecutionService

    agent_run = ExecutionService.run(agent_run_id)
    logger.info("AgentRun %s finished with status %s", agent_run_id, agent_run.status)
    return str(agent_run.id)
