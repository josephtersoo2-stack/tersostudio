"""Bridges persisted GenerationSteps to the TersuiteAgentRuntime.

This is the connective tissue the Phase 1 correction pass flagged as
missing: create_session() / send_task() were previously only ever called
from tests. Nothing in the request/response or Celery layer invoked the
runtime adapter at all.

Scope here is deliberately narrow — create one AgentRun for one
GenerationStep, execute it, record exactly what happened. Deciding which
step runs next, retry policy, and multi-agent sequencing are orchestrator
concerns for a later pass, not this file's job.
"""
import logging

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.realtime.event_publisher import GenerationEventPublisher
from apps.realtime.events import EventType, NormalizedEvent
from runtime.exceptions import AgentRuntimeError
from runtime.interfaces.session import FailureCategory, SessionConfig

from ..enums import AgentRunStatus, GenerationStatus, StepStatus
from ..exceptions import InvalidStateTransitionError, StepNotExecutableError
from ..models import AgentRun, GenerationStep
from .state_machine import GenerationStateMachine

logger = logging.getLogger("tersuite.orchestration")


def _build_runtime():
    """Select the configured runtime adapter.

    Defaults to the mock adapter so local dev and CI never accidentally
    hit a real OpenHands server (and real model spend) unless
    AGENT_RUNTIME_BACKEND=openhands is set explicitly. See the
    settings.py addition noted alongside this file.
    """
    backend = getattr(settings, "AGENT_RUNTIME_BACKEND", "mock")

    if backend == "openhands":
        from runtime.adapters.openhands import OpenHandsAgentRuntime, OpenHandsServerConfig

        config = OpenHandsServerConfig(
            server_url=settings.OPENHANDS_SERVER_URL,
            api_key=settings.OPENHANDS_API_KEY or None,
            default_model=settings.OPENHANDS_DEFAULT_MODEL,
            timeout_seconds=settings.OPENHANDS_TIMEOUT_SECONDS,
        )
        return OpenHandsAgentRuntime(config=config)

    from runtime.adapters.mock_adapter import MockAgentRuntime

    return MockAgentRuntime()


class ExecutionService:
    """Creates AgentRuns and executes them against the configured runtime.

    A fresh runtime instance is built per call rather than shared or
    pooled: the adapters keep session state in a plain instance dict, and
    a Celery worker interleaves many unrelated runs, so a shared instance
    would be a real state-leak risk for very little benefit.
    """

    @staticmethod
    @transaction.atomic
    def create_and_dispatch(step: GenerationStep) -> AgentRun:
        """Create a QUEUED AgentRun for `step` and enqueue its execution.

        Raises StepNotExecutableError if the step or its parent Generation
        isn't in a state that should be executed right now.
        """
        generation = step.generation

        if generation.status != GenerationStatus.BUILDING:
            raise StepNotExecutableError(
                f"Generation {generation.id} is '{generation.status}', not "
                f"BUILDING; refusing to execute step {step.step_number}."
            )
        if step.status not in (StepStatus.PENDING, StepStatus.FAILED):
            raise StepNotExecutableError(
                f"Step {step.id} is '{step.status}'; only PENDING or FAILED "
                f"steps can be (re)executed."
            )

        agent_run = AgentRun.objects.create(
            step=step,
            run_number=step.runs.count() + 1,
            runtime_type=getattr(settings, "AGENT_RUNTIME_BACKEND", "mock"),
            model_name=settings.OPENHANDS_DEFAULT_MODEL,
            prompt=step.input_payload.get("prompt")
            or f"{step.name}\n\nAgent role: {step.agent_role}",
            status=AgentRunStatus.QUEUED,
        )

        step.status = StepStatus.RUNNING
        step.started_at = step.started_at or timezone.now()
        step.save(update_fields=["status", "started_at", "updated_at"])

        # Imported here, not at module load, so this module stays safe to
        # import before Celery's autodiscover_tasks() has fully loaded
        # every app's task module.
        from ..tasks import execute_agent_run

        transaction.on_commit(lambda: execute_agent_run.delay(str(agent_run.id)))
        return agent_run

    @staticmethod
    def run(agent_run_id: str) -> AgentRun:
        """Execute one AgentRun against the runtime. Called by the Celery task."""
        agent_run = AgentRun.objects.select_related("step__generation").get(id=agent_run_id)

        if agent_run.status != AgentRunStatus.QUEUED:
            # Guards against Celery's acks_late redelivering a task whose
            # AgentRun already started (e.g. after a worker restart).
            logger.warning(
                "AgentRun %s is '%s', not QUEUED; skipping duplicate execution.",
                agent_run_id, agent_run.status,
            )
            return agent_run

        step = agent_run.step
        generation = step.generation
        publisher = GenerationEventPublisher()

        agent_run.status = AgentRunStatus.RUNNING
        agent_run.started_at = timezone.now()
        agent_run.save(update_fields=["status", "started_at", "updated_at"])
        publisher.publish(NormalizedEvent(
            event_type=EventType.AGENT_STARTED,
            generation_id=str(generation.id),
            agent_run_id=str(agent_run.id),
            payload={"step": step.name, "run_number": agent_run.run_number},
        ))

        runtime = _build_runtime()
        session_config = SessionConfig(
            generation_id=str(generation.id),
            agent_run_id=str(agent_run.id),
            model=agent_run.model_name or settings.OPENHANDS_DEFAULT_MODEL,
            system_prompt=step.input_payload.get("system_prompt", ""),
            max_iterations=step.input_payload.get("max_iterations", 30),
        )

        try:
            session = runtime.create_session(session_config)
        except AgentRuntimeError as exc:
            ExecutionService._record_failure(
                agent_run, step, generation, publisher,
                error=str(exc),
                failure_category=FailureCategory.NETWORK_CONNECTION.value,
                retryable=True,
            )
            return agent_run

        agent_run.session_id = session.session_id
        agent_run.remote_conversation_id = session.remote_conversation_id or ""
        agent_run.save(update_fields=["session_id", "remote_conversation_id", "updated_at"])

        try:
            result = runtime.send_task(session.session_id, agent_run.prompt)
        except AgentRuntimeError as exc:
            ExecutionService._record_failure(
                agent_run, step, generation, publisher,
                error=str(exc),
                failure_category=FailureCategory.AGENT_FATAL.value,
                retryable=False,
            )
            return agent_run
        finally:
            ExecutionService._safe_close(runtime, agent_run.session_id)

        if result.success:
            ExecutionService._record_success(agent_run, step, generation, publisher, result)
        else:
            ExecutionService._record_failure(
                agent_run, step, generation, publisher,
                error=result.error or "Agent execution failed.",
                failure_category=result.failure_category.value,
                retryable=result.retryable,
                output=result.output,
                token_usage=result.token_usage,
                error_details=result.error_details,
            )
        return agent_run

    @staticmethod
    def _safe_close(runtime, session_id: str) -> None:
        if not session_id or not hasattr(runtime, "close_session"):
            return
        try:
            runtime.close_session(session_id)
        except Exception:
            logger.warning("Failed to close runtime session %s", session_id, exc_info=True)

    @staticmethod
    def _record_success(agent_run, step, generation, publisher, result) -> None:
        agent_run.status = AgentRunStatus.COMPLETED
        agent_run.output = result.output
        agent_run.token_usage = result.token_usage
        agent_run.completed_at = timezone.now()
        agent_run.save(update_fields=[
            "status", "output", "token_usage", "completed_at", "updated_at",
        ])

        step.status = StepStatus.COMPLETED
        step.completed_at = timezone.now()
        step.save(update_fields=["status", "completed_at", "updated_at"])

        publisher.publish(NormalizedEvent(
            event_type=EventType.AGENT_COMPLETED,
            generation_id=str(generation.id),
            agent_run_id=str(agent_run.id),
            payload={"output_preview": (result.output or "")[:500]},
        ))
        publisher.publish(NormalizedEvent(
            event_type=EventType.GENERATION_STEP_COMPLETED,
            generation_id=str(generation.id),
            agent_run_id=str(agent_run.id),
            payload={"step_number": step.step_number, "step_name": step.name},
        ))

    @staticmethod
    def _record_failure(
        agent_run, step, generation, publisher, *,
        error: str, failure_category: str, retryable: bool,
        output: str = "", token_usage=None, error_details=None,
    ) -> None:
        agent_run.status = AgentRunStatus.FAILED
        agent_run.failure_category = failure_category
        agent_run.error_details = error_details or {"error": error, "retryable": retryable}
        agent_run.output = output
        agent_run.token_usage = token_usage or {}
        agent_run.completed_at = timezone.now()
        agent_run.save(update_fields=[
            "status", "failure_category", "error_details",
            "output", "token_usage", "completed_at", "updated_at",
        ])

        step.status = StepStatus.FAILED
        step.error_message = error
        step.completed_at = timezone.now()
        step.save(update_fields=["status", "error_message", "completed_at", "updated_at"])

        try:
            GenerationStateMachine.transition(
                generation=generation,
                target_status=GenerationStatus.FAILED,
                reason=f"Step {step.step_number} ({step.name}) failed.",
                error_message=error,
                failure_category=failure_category,
            )
        except InvalidStateTransitionError:
            # Generation already left BUILDING (paused/cancelled/etc. by
            # something else) — the AgentRun/Step failure above still stands.
            logger.info(
                "Generation %s no longer transitionable to FAILED (already %s).",
                generation.id, generation.status,
            )

        publisher.publish(NormalizedEvent(
            event_type=EventType.AGENT_FAILED,
            generation_id=str(generation.id),
            agent_run_id=str(agent_run.id),
            payload={
                "error": error,
                "failure_category": failure_category,
                "retryable": retryable,
            },
        ))
        publisher.publish(NormalizedEvent(
            event_type=EventType.GENERATION_FAILED,
            generation_id=str(generation.id),
            agent_run_id=str(agent_run.id),
            payload={"step_number": step.step_number, "reason": error},
        ))
