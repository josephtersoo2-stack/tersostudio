"""Bridges persisted GenerationSteps to the TersuiteAgentRuntime."""
import logging
import os

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
    AGENT_RUNTIME_BACKEND=openhands is set explicitly.
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
    """Creates AgentRuns and executes them against the configured runtime."""

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

        model_name = (
            step.input_payload.get("model")
            or os.getenv("OPENROUTER_MODEL")
            or settings.OPENHANDS_DEFAULT_MODEL
        )

        agent_run = AgentRun.objects.create(
            step=step,
            run_number=step.runs.count() + 1,
            runtime_type=getattr(settings, "AGENT_RUNTIME_BACKEND", "mock"),
            model_name=model_name,
            prompt=step.input_payload.get("prompt")
            or f"{step.name}\n\nAgent role: {step.agent_role}",
            status=AgentRunStatus.QUEUED,
        )

        step.status = StepStatus.RUNNING
        step.started_at = step.started_at or timezone.now()
        step.save(update_fields=["status", "started_at", "updated_at"])

        from ..tasks import execute_agent_run

        transaction.on_commit(lambda: execute_agent_run.delay(str(agent_run.id)))
        return agent_run

    @staticmethod
    def run(agent_run_id: str) -> AgentRun:
        """Execute one AgentRun against the runtime. Called by the Celery task."""
        agent_run = AgentRun.objects.select_related("step__generation").get(id=agent_run_id)

        if agent_run.status != AgentRunStatus.QUEUED:
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

        def stream_event(event: NormalizedEvent) -> None:
            """Stream intermediate events to the generation's Channels group."""
            if not event.generation_id:
                event.generation_id = str(generation.id)
            if not event.agent_run_id:
                event.agent_run_id = str(agent_run.id)
            publisher.publish(event)

        model_name = (
            agent_run.model_name
            or step.input_payload.get("model")
            or os.getenv("OPENROUTER_MODEL")
            or settings.OPENHANDS_DEFAULT_MODEL
        )

        runtime = _build_runtime()
        session_config = SessionConfig(
            generation_id=str(generation.id),
            agent_run_id=str(agent_run.id),
            model=model_name,
            system_prompt=step.input_payload.get("system_prompt", ""),
            max_iterations=step.input_payload.get("max_iterations", 30),
            on_event=stream_event,
        )

        try:
            session = runtime.create_session(session_config)
        except AgentRuntimeError as exc:
            category = getattr(exc, "failure_category", FailureCategory.NETWORK_CONNECTION)
            cat_val = category.value if hasattr(category, "value") else str(category)
            retryable = getattr(exc, "retryable", True)
            ExecutionService._record_failure(
                agent_run, step, generation, publisher,
                error=str(exc),
                failure_category=cat_val,
                retryable=retryable,
                error_details=getattr(exc, "details", {}),
            )
            return agent_run

        agent_run.session_id = session.session_id
        agent_run.remote_conversation_id = session.remote_conversation_id or ""
        agent_run.save(update_fields=["session_id", "remote_conversation_id", "updated_at"])

        try:
            result = runtime.send_task(session.session_id, agent_run.prompt)
        except AgentRuntimeError as exc:
            category = getattr(exc, "failure_category", FailureCategory.AGENT_FATAL)
            cat_val = category.value if hasattr(category, "value") else str(category)
            retryable = getattr(exc, "retryable", False)
            ExecutionService._record_failure(
                agent_run, step, generation, publisher,
                error=str(exc),
                failure_category=cat_val,
                retryable=retryable,
                error_details=getattr(exc, "details", {}),
            )
            return agent_run
        finally:
            ExecutionService._safe_close(runtime, agent_run.session_id)

        if result.success:
            ExecutionService._record_success(agent_run, step, generation, publisher, result)
        else:
            cat_val = result.failure_category.value if hasattr(result.failure_category, "value") else str(result.failure_category)
            ExecutionService._record_failure(
                agent_run, step, generation, publisher,
                error=result.error or "Agent execution failed.",
                failure_category=cat_val,
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
        details = dict(error_details) if error_details else {}
        details["error"] = error
        details["retryable"] = retryable
        agent_run.error_details = details
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
