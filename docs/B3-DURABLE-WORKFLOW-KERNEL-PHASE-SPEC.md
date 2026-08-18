
# B3 — Durable Generation and Workflow Kernel Phase Specification

## 1. Phase identity

- Roadmap milestone: `B3`
- Product area: deterministic backend control plane / durable workflow coordination
- Required predecessor: B2 merged and independently verified at `main` commit `6ab818db61f4fc1eaa8c6ff25574204f95a027e5`
- Implementation branch: `feature/b3-durable-workflow-kernel`
- Implementer: Google Antigravity
- Reviewer: independent inspection of the pushed GitHub commit and CI evidence
- Runtime posture: OpenHands runtime remains frozen at the B2 baseline during B3
- Evidence report: `docs/reports/B3-DURABLE-WORKFLOW-KERNEL-REPORT.md`

## 2. Purpose

B3 replaces the remaining prototype generation-control behavior with a deterministic, PostgreSQL-backed workflow kernel that survives duplicate delivery, concurrent workers, worker crashes, stale leases, retries, pause/resume, and cancellation.

Django/PostgreSQL owns state, dependencies, leases, attempts, retry budgets, idempotency, cancellation intent, transition history, and transactional event publication. Celery performs bounded jobs but is not the source of truth. LLMs and OpenHands do not decide workflow state.

B3 does **not** correct or extend the OpenHands runtime. It must not require an OpenRouter API key, an OpenHands Agent Server, live model spend, or a real agent conversation. Those belong to B4.

## 3. Required outcomes

At completion:

1. `GenerationStatus` matches the canonical roadmap lifecycle.
2. Generation transitions are serialized with database row locks and a monotonic state version.
3. New transition history is relational, not appended to `Generation.metadata["state_history"]`.
4. Existing B2 generation rows migrate without loss and reverse deterministically.
5. Each generation supports ordered `GenerationMilestone` records; every existing step is backfilled to a milestone.
6. A new `workflows` app owns `WorkflowRun`, `WorkPackage`, `WorkPackageDependency`, `WorkPackageAttempt`, `WorkPackageLease`, `WorkflowCommand`, and `OutboxEvent`.
7. Workflow graphs become immutable once execution starts.
8. Dependency readiness and scheduling are deterministic and independent of LLM judgment.
9. Concurrent workers cannot create two active leases for one package.
10. Leases support opaque token, expiry, heartbeat, release, and stale-lease recovery.
11. Attempts are append-only and monotonically numbered per package.
12. Retry is bounded and uses deterministic exponential backoff.
13. Pause/resume/cancel/retry commands are idempotent by `Idempotency-Key`.
14. Pause blocks new claims but does not pretend to interrupt a running OpenHands conversation.
15. Cancellation uses `CANCELLING` before `CANCELLED` and waits for active leases to end or expire.
16. Domain mutation and event intent are committed atomically through a transactional outbox.
17. Outbox delivery is at-least-once with a stable `event_id`.
18. New workflow inspection APIs remain tenant-scoped and read-only.
19. Existing `AgentRun`, `ExecutionService`, workspace, artifact, and runtime code are not redesigned in B3.
20. B3 CI passes without a live OpenHands server or LLM key.

## 4. Fixed architecture

### 4.1 Ownership

`apps/generations` owns:

- `Generation`
- `GenerationMilestone`
- `GenerationStep`
- `GenerationStateTransition`
- canonical generation lifecycle
- public generation control commands

`apps/workflows` owns:

- `WorkflowRun`
- `WorkPackage`
- `WorkPackageDependency`
- `WorkPackageAttempt`
- `WorkPackageLease`
- `WorkflowCommand`
- `OutboxEvent`
- DAG validation
- readiness scheduling
- worker claim/lease/heartbeat/reaping
- deterministic retry
- transactional outbox delivery
- read-only workflow inspection

No OpenHands SDK object or runtime adapter belongs in either domain.

### 4.2 Canonical generation statuses

Forward lifecycle:

`DRAFT`
→ `DISCOVERY`
→ `SPECIFICATION_DRAFT`
→ `PLAN_DRAFT`
→ `AWAITING_APPROVAL`
→ `APPROVED`
→ `SCHEDULED`
→ `BUILDING`
→ `INTEGRATING`
→ `REVIEWING`
→ `CORRECTING`
→ `SANDBOX_QA`
→ `RELEASE_CANDIDATE`
→ `AWAITING_DEPLOYMENT_APPROVAL`
→ `STAGED`
→ `ACTIVE`

Control/terminal:

- `PAUSED`
- `CANCELLING`
- `CANCELLED`
- `FAILED`
- `TIMED_OUT`
- `BLOCKED`
- `ROLLED_BACK`
- `SUPERSEDED`

B2-only current values `SPECIFICATION`, `PLANNING`, `TESTING`, `REVIEW`, `PACKAGING`, `COMPLETED`, and `RETRYING` are retired after migration.

### 4.3 Allowed lifecycle edges

Normal:

- `DRAFT -> DISCOVERY`
- `DISCOVERY -> SPECIFICATION_DRAFT`
- `SPECIFICATION_DRAFT -> PLAN_DRAFT`
- `PLAN_DRAFT -> AWAITING_APPROVAL`
- `AWAITING_APPROVAL -> APPROVED`
- `APPROVED -> SCHEDULED`
- `SCHEDULED -> BUILDING`
- `BUILDING -> INTEGRATING`
- `INTEGRATING -> REVIEWING`
- `REVIEWING -> SANDBOX_QA`
- `REVIEWING -> CORRECTING`
- `CORRECTING -> BUILDING`
- `CORRECTING -> INTEGRATING`
- `CORRECTING -> REVIEWING`
- `SANDBOX_QA -> RELEASE_CANDIDATE`
- `SANDBOX_QA -> CORRECTING`
- `RELEASE_CANDIDATE -> AWAITING_DEPLOYMENT_APPROVAL`
- `AWAITING_DEPLOYMENT_APPROVAL -> STAGED`
- `STAGED -> ACTIVE`
- `ACTIVE -> ROLLED_BACK`

Revision:

- `AWAITING_APPROVAL -> SPECIFICATION_DRAFT`
- `AWAITING_APPROVAL -> PLAN_DRAFT`

Coordinator-only failure/control transitions may enter `BLOCKED`, `FAILED`, or `TIMED_OUT`. Retry from these states is only through the idempotent retry command and returns to `SCHEDULED` if retry policy permits.

`SUPERSEDED`, `CANCELLED`, and `ROLLED_BACK` are terminal. `ACTIVE` is terminal except rollback.

### 4.4 Pause and resume

Pausable:

- `DISCOVERY`
- `SPECIFICATION_DRAFT`
- `PLAN_DRAFT`
- `AWAITING_APPROVAL`
- `SCHEDULED`
- `BUILDING`
- `INTEGRATING`
- `REVIEWING`
- `CORRECTING`
- `SANDBOX_QA`
- `RELEASE_CANDIDATE`
- `AWAITING_DEPLOYMENT_APPROVAL`

Pause stores the prior status in `resume_status`, sets `PAUSED`, and sets `paused_at`. Resume restores the saved state and clears both fields.

B3 pause is cooperative: no new work may be claimed after commit. B4 will own real runtime interruption.

### 4.5 Cancellation

- Non-terminal generation -> `CANCELLING`.
- Current workflow run -> `CANCELLING`.
- No new claims are allowed.
- Active packages receive `cancel_requested_at`.
- With no active lease, cancellation may finalize immediately.
- Otherwise finalization waits for attempt acknowledgement or lease expiry/reaping.
- Final state `CANCELLED` is terminal.
- B3 must not claim that an OpenHands process was interrupted.

## 5. Generation persistence

Add to `Generation`:

- `state_version` positive bigint default 0
- `next_transition_sequence` positive bigint default 1
- `status_changed_at`
- `resume_status`
- `cancel_requested_at`
- `timed_out_at`

Retain B2 compatibility timestamps. `completed_at` remains but now records first entry into `RELEASE_CANDIDATE`, not site activation.

Add `GenerationStateTransition`:

- generation FK
- monotonic `sequence`
- `from_status`
- `to_status`
- nullable `command_id`
- nullable actor FK
- reason
- metadata
- timestamps
- unique `(generation, sequence)`

New lifecycle truth must be written here. Preserve legacy metadata history but do not append to it.

## 6. Milestones and steps

Add `GenerationMilestone`:

- generation FK
- sequence
- name
- status
- metadata
- started/completed timestamps
- unique `(generation, sequence)`

Every existing B2 step receives a migration-created milestone:

- sequence `1`
- name `Legacy / B2 Steps`

`GenerationStep.milestone` is non-null after backfill.

Do not delete or redesign `agent_role`, step payloads, `AgentRun`, `Workspace`, or `Artifact`.

## 7. Workflow models

### 7.1 WorkflowRun

Organization-owned; fields:

- generation
- run_number
- status
- state_version
- started_at
- completed_at
- paused_at
- cancel_requested_at
- last_scheduler_heartbeat_at
- failure_category
- error_message
- metadata

Unique `(generation, run_number)`. Only one non-terminal run per generation.

Statuses:

- `PENDING`
- `RUNNING`
- `PAUSED`
- `CANCELLING`
- `CANCELLED`
- `COMPLETED`
- `FAILED`
- `TIMED_OUT`
- `BLOCKED`

### 7.2 WorkPackage

Organization-owned; fields:

- workflow_run
- generation_step
- stable `key` unique within run
- name
- status
- priority
- max_attempts
- attempt_count
- timeout_seconds
- retry_base_seconds
- next_attempt_at
- cancel_requested_at
- input_payload
- result_payload
- validation_evidence
- failure_category
- error_message
- ready_at
- started_at
- completed_at
- state_version

Statuses:

- `PENDING`
- `READY`
- `LEASED`
- `RUNNING`
- `CANDIDATE_COMPLETE`
- `COMPLETED`
- `RETRY_WAIT`
- `FAILED`
- `BLOCKED`
- `CANCELLING`
- `CANCELLED`
- `TIMED_OUT`

A worker may only produce `CANDIDATE_COMPLETE`. `COMPLETED` requires an explicit deterministic acceptance service with validation evidence.

### 7.3 Dependency

`WorkPackageDependency`:

- workflow_run
- predecessor
- successor
- dependency_type default `HARD`

Rules:

- same workflow run
- no self-edge
- unique edge
- cycle rejection
- immutable after run starts
- successor becomes ready only when all hard predecessors are `COMPLETED`

### 7.4 Attempt

Append-only `WorkPackageAttempt`:

- work_package
- attempt_number
- status
- worker_id
- started_at
- completed_at
- heartbeat_at
- retryable
- failure_category
- error_details
- result_payload

Unique `(work_package, attempt_number)`.

Statuses:

- `QUEUED`
- `RUNNING`
- `CANDIDATE_COMPLETE`
- `FAILED`
- `TIMED_OUT`
- `CANCELLED`

### 7.5 Lease

`WorkPackageLease`:

- work_package
- attempt
- unique UUID `lease_token`
- worker_id
- acquired_at
- heartbeat_at
- expires_at
- released_at
- release_reason

At most one unreleased lease per package. Claim uses PostgreSQL `select_for_update(skip_locked=True)`. Heartbeat/release require the matching lease token. Expiry uses server time.

## 8. Scheduler and retry

Readiness tick:

- operates in bounded batches;
- updates workflow scheduler heartbeat;
- never claims work while generation/run is paused, cancelling, or terminal;
- `PENDING -> READY` only when all hard dependencies complete;
- `RETRY_WAIT -> READY` only after `next_attempt_at`;
- irrecoverable failed predecessor -> dependent `BLOCKED`;
- repeated tick is idempotent;
- never calls LLM/OpenHands.

Worker claim:

- deterministic ordering `priority DESC, ready_at ASC, id ASC`;
- one atomic transaction creates the next attempt and lease;
- concurrent claimants never receive the same package.

Default retry:

- max attempts `3`
- base `30s`
- cap `900s`
- delay = `min(base * 2 ** (attempt_number - 1), cap)`
- no random jitter in persisted scheduler calculations

Retry only if marked retryable, attempts remain, and generation/run is not paused/cancelling/terminal.

## 9. Idempotent commands

`WorkflowCommand` is organization-owned:

- generation
- command_type
- idempotency_key
- request_hash
- request_payload
- response_payload
- status
- applied_at
- actor fields

Unique `(organization, idempotency_key)`.

Public `pause`, `resume`, `cancel`, `retry` require `Idempotency-Key` (trimmed 1–128 chars).

Hash is SHA-256 of canonical JSON containing generation ID, command type, and normalized payload.

Rules:

- first request applies once and stores response;
- same key + same hash replays stored response;
- same key + different hash -> HTTP 409 `idempotency_key_conflict`;
- concurrent insert races resolve through DB uniqueness/re-read;
- no secret values in stored request/response.

## 10. Transactional outbox

`OutboxEvent` is organization-owned:

- stable UUID `event_id`
- nullable generation
- aggregate_type
- aggregate_id
- event_type
- payload
- occurred_at
- available_at
- claim_token
- claimed_until
- published_at
- publish_attempts
- last_error

Domain mutation and event row must commit in the same transaction.

Delivery:

- at-least-once
- `select_for_update(skip_locked=True)` batch claim
- stable event ID across retries
- successful publish -> `published_at`
- failure leaves event retryable
- crash after publish before ack may duplicate; event ID is dedupe key
- B3 workflow events publish existing `NormalizedEvent` through a durable/raising Channels send path
- old best-effort direct publisher may remain for compatibility, but B3 workflow state events originate from outbox

## 11. Public API

Keep organization-scoped generation list/create/retrieve.

Control routes:

- `POST /api/v1/generations/{id}/pause/`
- `POST /api/v1/generations/{id}/resume/`
- `POST /api/v1/generations/{id}/cancel/`
- `POST /api/v1/generations/{id}/retry/`

All require `Idempotency-Key`.

Old `POST /api/v1/generations/{id}/transition/` stays only as a compatibility route. It may route control requests to the command service, but arbitrary forward/internal state forcing returns 409 `direct_transition_requires_coordinator`.

Read-only workflow inspection:

- `GET /api/v1/workflow-runs/`
- `GET /api/v1/workflow-runs/{id}/`
- `GET /api/v1/work-packages/`
- `GET /api/v1/work-packages/{id}/`
- `GET /api/v1/work-package-attempts/`
- `GET /api/v1/work-package-attempts/{id}/`

No public writes for graph, lease, attempt, command, or outbox records.

## 12. B2 -> B3 migration mapping

| B2 | B3 |
|---|---|
| `DRAFT` | `DRAFT` |
| `SPECIFICATION` | `SPECIFICATION_DRAFT` |
| `APPROVED` | `APPROVED` |
| `PLANNING` | `PLAN_DRAFT` |
| `BUILDING` | `BUILDING` |
| `TESTING` | `SANDBOX_QA` |
| `REVIEW` | `REVIEWING` |
| `PACKAGING` | `RELEASE_CANDIDATE` |
| `COMPLETED` | `RELEASE_CANDIDATE` |
| `FAILED` | `FAILED` |
| `CANCELLED` | `CANCELLED` |
| `PAUSED` | `PAUSED` |
| `RETRYING` | `SCHEDULED` |

Reverse mapping must use the nearest B2 semantic state and be documented/tested.

Never edit any migration already present at the baseline.

## 13. Configuration

Add safe non-secret defaults:

- `WORKFLOW_LEASE_SECONDS=60`
- `WORKFLOW_SCHEDULER_BATCH_SIZE=20`
- `WORKFLOW_MAX_ATTEMPTS=3`
- `WORKFLOW_RETRY_BASE_SECONDS=30`
- `WORKFLOW_RETRY_MAX_SECONDS=900`
- `OUTBOX_BATCH_SIZE=100`
- `OUTBOX_CLAIM_SECONDS=60`

Periodic Celery work may include readiness tick, lease reaper, and outbox dispatcher only. No OpenHands startup or model call.

## 14. Required B3 events

At minimum:

- `generation.state_changed`
- `generation.paused`
- `generation.resumed`
- `generation.cancellation_requested`
- `generation.cancelled`
- `generation.failed`
- `generation.timed_out`
- `generation.blocked`
- `workflow.run_created`
- `workflow.run_status_changed`
- `work_package.ready`
- `work_package.leased`
- `work_package.attempt_started`
- `work_package.candidate_complete`
- `work_package.completed`
- `work_package.retry_scheduled`
- `work_package.failed`
- `work_package.cancelled`
- `work_package.timed_out`

No secrets or unrestricted raw prompts in event payloads.

## 15. In scope

- three B3 governing docs and report
- canonical lifecycle correction
- transition history
- milestones/step backfill
- new `apps/workflows`
- DAG/scheduler
- attempts/leases
- heartbeat/reaper/retry
- pause/resume/cancel
- idempotent commands
- transactional outbox
- B3 event additions
- read-only workflow APIs
- B3 config/admin
- migration/concurrency/crash tests
- API/Data Model/README updates
- only minimal Control Center compatibility changes proven necessary

## 16. Out of scope

- any `backend/runtime/**` change
- OpenHands adapter/SDK/session correction
- OpenRouter or other LLM keys
- forcing live OpenHands integration
- B4 runtime work
- B5 workspace/file backend redesign
- B6 intelligence registries
- B7 requirement/spec/plan/approval models
- B8 multi-agent profile/orchestration/review loops
- B9 experience/evaluation
- WordPress sandbox/package/deploy
- frontend/WordPress plugin
- theme generation
- unrelated cleanup, including inherited Docker casing warning

## 17. Protected baseline

Absolutely no B3 changes to:

- `backend/runtime/**`
- any migration file already present at `6ab818db61f4fc1eaa8c6ff25574204f95a027e5`
- B2 tenant/security/product/conversation semantics
- `AGENTS.md`
- `docs/TERSUITE-IMPLEMENTATION-ROADMAP.md`
- `docs/ANTIGRAVITY-DEVELOPMENT-PROTOCOL.md`

B3 may update `docs/API-CONTRACT.md`, `docs/DATA-MODEL.md`, and `README.md`.

## 18. Required tests / exit evidence

Must prove:

- canonical transition table
- concurrent/stale transition serialization
- monotonic transition sequence/state version
- pause/resume
- idempotent cancel
- cancellation waits for active lease
- same-key replay and different-payload conflict
- concurrent same-key command applies once
- DAG order/cycle/self/cross-run protection
- deterministic readiness
- concurrent claim creates one lease only
- wrong lease token rejection
- heartbeat extension
- expired lease reaper idempotency
- monotonic retry attempts/backoff/max
- pause/cancel block claims
- candidate-complete != completed
- validation evidence required for completion
- failed predecessor blocking
- transactional outbox rollback safety
- outbox retry keeps same event ID
- concurrent outbox claim safety
- workflow tenant isolation
- B2->B3->B2 MigrationExecutor
- complete backend tests
- existing live OpenHands test may remain skipped because server is not running

B3 freezes only after local tests, Docker checks, GitHub Actions, truthful report, zero runtime diff, historical migration preservation, and independent final diff review.
