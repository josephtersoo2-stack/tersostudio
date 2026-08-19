"""Normalized event schema and constants for Tersuite AI Studio."""
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional


class EventType:
    """Normalized event types across Tersuite Studio, Durable Workflows, and Agent Runtime."""

    # Generation events (Lifecycle & State Machine)
    GENERATION_CREATED = "generation.created"
    GENERATION_STARTED = "generation.started"
    GENERATION_STATE_CHANGED = "generation.state_changed"
    GENERATION_PAUSED = "generation.paused"
    GENERATION_RESUMED = "generation.resumed"
    GENERATION_CANCELLATION_REQUESTED = "generation.cancellation_requested"
    GENERATION_CANCELLED = "generation.cancelled"
    GENERATION_FAILED = "generation.failed"
    GENERATION_TIMED_OUT = "generation.timed_out"
    GENERATION_BLOCKED = "generation.blocked"
    GENERATION_STEP_STARTED = "generation.step_started"
    GENERATION_STEP_COMPLETED = "generation.step_completed"
    GENERATION_COMPLETED = "generation.completed"

    # Workflow Run events
    WORKFLOW_RUN_CREATED = "workflow.run_created"
    WORKFLOW_RUN_STATUS_CHANGED = "workflow.run_status_changed"
    WORKFLOW_RUN_STARTED = "workflow.run_started"
    WORKFLOW_RUN_PAUSED = "workflow.run_paused"
    WORKFLOW_RUN_CANCELLED = "workflow.run_cancelled"
    WORKFLOW_RUN_COMPLETED = "workflow.run_completed"
    WORKFLOW_RUN_FAILED = "workflow.run_failed"

    # Work Package events
    WORK_PACKAGE_READY = "work_package.ready"
    WORK_PACKAGE_LEASED = "work_package.leased"
    WORK_PACKAGE_ATTEMPT_STARTED = "work_package.attempt_started"
    WORK_PACKAGE_CANDIDATE_COMPLETE = "work_package.candidate_complete"
    WORK_PACKAGE_COMPLETED = "work_package.completed"
    WORK_PACKAGE_RETRY_SCHEDULED = "work_package.retry_scheduled"
    WORK_PACKAGE_FAILED = "work_package.failed"
    WORK_PACKAGE_CANCELLED = "work_package.cancelled"
    WORK_PACKAGE_TIMED_OUT = "work_package.timed_out"

    # Agent Lifecycle events
    AGENT_STARTED = "agent.started"
    AGENT_THINKING = "agent.thinking"
    AGENT_TOOL_STARTED = "agent.tool_started"
    AGENT_TOOL_FINISHED = "agent.tool_finished"
    AGENT_WAITING = "agent.waiting"
    AGENT_COMPLETED = "agent.completed"
    AGENT_FAILED = "agent.failed"

    # Task events
    TASK_CREATED = "task.created"
    TASK_STARTED = "task.started"
    TASK_COMPLETED = "task.completed"

    # Workspace events
    WORKSPACE_CREATED = "workspace.created"
    WORKSPACE_DESTROYED = "workspace.destroyed"

    # Testing & Review events
    TEST_STARTED = "test.started"
    TEST_PASSED = "test.passed"
    TEST_FAILED = "test.failed"
    REVIEW_STARTED = "review.started"
    REVIEW_PASSED = "review.passed"
    REVIEW_FAILED = "review.failed"

    # Artifact & Delivery events
    ARTIFACT_CREATED = "artifact.created"
    SECURITY_SCAN_STARTED = "security.scan_started"
    SECURITY_FINDING_RECORDED = "security.finding_recorded"
    SECURITY_SCAN_COMPLETED = "security.scan_completed"

    # System & Heartbeat
    SYSTEM_PING = "system.ping"
    SYSTEM_ERROR = "system.error"


@dataclass
class NormalizedEvent:
    """Standardized event envelope passed across Channels and Agent Runtime."""

    event_type: str
    payload: Dict[str, Any] = field(default_factory=dict)
    generation_id: Optional[str] = None
    agent_run_id: Optional[str] = None
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Convert normalized event to JSON-serializable dictionary."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "generation_id": self.generation_id,
            "agent_run_id": self.agent_run_id,
            "timestamp": self.timestamp,
            "payload": self.payload,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NormalizedEvent":
        """Reconstruct normalized event from dictionary payload."""
        return cls(
            event_id=data.get("event_id", str(uuid.uuid4())),
            event_type=data.get("event_type", EventType.SYSTEM_PING),
            generation_id=data.get("generation_id"),
            agent_run_id=data.get("agent_run_id"),
            timestamp=data.get("timestamp", datetime.now(timezone.utc).isoformat()),
            payload=data.get("payload", {}),
        )
