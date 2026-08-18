
# B3 — Durable Generation and Workflow Kernel Detailed Implementation Specification

## 1. Authority and baseline

Baseline `main`: `6ab818db61f4fc1eaa8c6ff25574204f95a027e5`

Branch: `feature/b3-durable-workflow-kernel`

Read before editing:

1. `docs/ANTIGRAVITY-SESSION-03-B3-DURABLE-WORKFLOW-KERNEL.md`
2. `AGENTS.md`
3. `docs/TERSUITE-IMPLEMENTATION-ROADMAP.md`
4. `docs/ANTIGRAVITY-DEVELOPMENT-PROTOCOL.md`
5. `docs/B3-DURABLE-WORKFLOW-KERNEL-PHASE-SPEC.md`
6. this file
7. B2 phase/detailed specs
8. API/Data Model contracts
9. current generation/realtime implementation and tests

If a conflict requires out-of-scope work, stop and report. Do not redesign.

## 2. Preflight

Run locally:

```bash
git status --short
git branch --show-current
git fetch origin --prune
git switch main
git pull --ff-only origin main
git rev-parse HEAD
git rev-parse origin/main
```

Both SHAs must be `6ab818db61f4fc1eaa8c6ff25574204f95a027e5`; worktree must be clean.

Then:

```bash
git switch -c feature/b3-durable-workflow-kernel
```

Before editing, audit references:

```bash
git grep -n "GenerationStatus" -- backend
git grep -n "GenerationStep" -- backend
git grep -n "AgentRun" -- backend
git grep -n "GenerationStateMachine" -- backend
git grep -n "transition_state\|url_path=.*transition" -- backend
git grep -n "pause\|resume\|cancel\|retry" -- backend/apps/generations backend/apps/control_center
git grep -n "transaction.on_commit" -- backend
git grep -n "GenerationEventPublisher\|NormalizedEvent\|EventType" -- backend
git grep -n "execute_agent_run" -- backend
git grep -n "OpenHands\|runtime.adapters" -- backend/apps
```

Record impact in the B3 report.

## 3. Add the governing B3 docs first

Before code changes, place the supplied files at:

- `docs/B3-DURABLE-WORKFLOW-KERNEL-PHASE-SPEC.md`
- `docs/B3-DURABLE-WORKFLOW-KERNEL-DETAILED-IMPLEMENTATION.md`
- `docs/ANTIGRAVITY-SESSION-03-B3-DURABLE-WORKFLOW-KERNEL.md`

Do not edit roadmap, AGENTS, or Antigravity protocol.

Recommended first commit:

```bash
git add docs/B3-DURABLE-WORKFLOW-KERNEL-PHASE-SPEC.md \
        docs/B3-DURABLE-WORKFLOW-KERNEL-DETAILED-IMPLEMENTATION.md \
        docs/ANTIGRAVITY-SESSION-03-B3-DURABLE-WORKFLOW-KERNEL.md
git commit -m "docs(b3): define durable workflow kernel contracts"
```

## 4. Generations app

### 4.1 Enums

In `backend/apps/generations/enums.py`:

- replace B2 generation statuses with the exact canonical B3 status list;
- add `MilestoneStatus`;
- extend `StepStatus` to support `READY`, `CANDIDATE_COMPLETE`, `BLOCKED`, `TIMED_OUT` while retaining valid existing values;
- keep workspace/artifact enums unchanged.

Do not touch runtime enums.

### 4.2 Models

In `backend/apps/generations/models.py`:

Add to `Generation`:

```text
state_version
next_transition_sequence
status_changed_at
resume_status
cancel_requested_at
timed_out_at
```

Add `GenerationMilestone(TimeStampedModel)` exactly as phase spec.

Add `GenerationStateTransition(TimeStampedModel)` exactly as phase spec.

End-state: `GenerationStep.milestone` is a non-null FK, related name `steps`.

Keep `AgentRun`, `Workspace`, and `Artifact` structurally intact unless a narrow status compatibility edit is required by tests.

Update `GenerationQuerySet.active()`. Keep `completed()` only as a documented compatibility helper returning successful post-build states (`RELEASE_CANDIDATE`, `AWAITING_DEPLOYMENT_APPROVAL`, `STAGED`, `ACTIVE`).

### 4.3 State machine

Rewrite `backend/apps/generations/services/state_machine.py` so every accepted transition:

1. starts `transaction.atomic()`;
2. re-fetches and locks the generation using `select_for_update()`;
3. checks the canonical transition graph against the locked value;
4. allocates `next_transition_sequence`;
5. increments `state_version`;
6. updates timestamps/resume/cancel fields;
7. creates `GenerationStateTransition`;
8. enqueues the B3 outbox event in the same transaction;
9. saves and returns the refreshed generation.

New transitions must not append to `metadata["state_history"]`.

Expose compatible `can_transition(...)` and `transition(...)` interfaces, but public generic transition calls must not bypass coordinator-only progression.

## 5. New workflows app

Create:

```text
backend/apps/workflows/
  __init__.py
  apps.py
  admin.py
  enums.py
  models.py
  permissions.py
  serializers.py
  urls.py
  views.py
  tasks.py
  migrations/__init__.py
  migrations/0001_initial.py
  services/__init__.py
  services/commands.py
  services/graph.py
  services/scheduler.py
  services/leases.py
  services/retries.py
  services/outbox.py
  tests/__init__.py
  tests/test_models.py
  tests/test_commands.py
  tests/test_graph.py
  tests/test_scheduler.py
  tests/test_leases.py
  tests/test_outbox.py
  tests/test_concurrency.py
  tests/test_tenant_isolation.py
```

Tiny services may be consolidated only if behavior is unchanged and report documents it.

### 5.1 Models and constraints

Implement exact phase-spec fields.

Use `OrganizationOwnedModel` for:

- WorkflowRun
- WorkPackage
- WorkflowCommand
- OutboxEvent

Use `TimeStampedModel` for:

- WorkPackageDependency
- WorkPackageAttempt
- WorkPackageLease

Constraints/indexes:

- WorkflowRun unique `(generation, run_number)`
- WorkPackage unique `(workflow_run, key)`
- dependency unique `(predecessor, successor)` and no self-edge
- attempt unique `(work_package, attempt_number)`
- lease token unique
- one unreleased lease per package with PostgreSQL conditional unique constraint
- command unique `(organization, idempotency_key)`
- outbox indexes for unpublished/available and claim expiry

Validate organization alignment in services, not only `clean()`.

## 6. Graph service

Provide:

```text
add_dependency(predecessor, successor)
validate_graph(workflow_run)
topological_order(workflow_run)
freeze_graph(workflow_run)
```

Rules:

- dependency mutation only while run is `PENDING`;
- same-run only;
- self edge rejected;
- cycle rejected before commit;
- deterministic topological order by stable key/id;
- graph immutable once run starts.

Do not add an external workflow engine or LLM decision.

## 7. Scheduler

### 7.1 Readiness tick

`tick(workflow_run_id=None, now=None, batch_size=None)`:

- PostgreSQL-backed bounded transactions;
- update scheduler heartbeat;
- skip paused/cancelling/terminal run/generation;
- `PENDING -> READY` only when all hard predecessors are `COMPLETED`;
- `RETRY_WAIT -> READY` when next attempt time elapsed;
- irrecoverable failed predecessor -> `BLOCKED`;
- deterministic order;
- repeated tick idempotent;
- each mutation emits an outbox event in same transaction;
- never calls `ExecutionService`, AgentRun, OpenHands, or LLM.

### 7.2 Worker claim

`claim_next(worker_id, workflow_run_id=None, now=None)`:

- normalize non-empty worker ID;
- select READY package with `select_for_update(skip_locked=True)`;
- order `priority DESC, ready_at ASC, id ASC`;
- verify generation/run still claimable after lock;
- increment attempt count;
- create next attempt number;
- create one lease with UUID token and server-time expiry;
- mark attempt/package running;
- set first started_at;
- outbox `work_package.leased` and `work_package.attempt_started`.

Concurrent claimants must never get the same package.

### 7.3 Worker result services

Provide:

```text
record_candidate_complete(attempt_id, lease_token, result_payload)
record_attempt_failure(attempt_id, lease_token, failure_category, error_details, retryable)
mark_validated_complete(work_package_id, validation_evidence)
```

Candidate completion:

- validates active lease token;
- releases lease;
- attempt/package -> `CANDIDATE_COMPLETE`;
- never package `COMPLETED`.

Validated completion:

- requires non-empty structured validation evidence;
- package -> `COMPLETED`;
- roll up step/milestone where applicable;
- dependent packages remain untouched until scheduler tick;
- emit outbox.

Failure:

- releases lease;
- records append-only attempt failure;
- retry or terminal package state via deterministic retry service.

## 8. Lease and reaper

`heartbeat(attempt_id, lease_token, now=None)`:

- lock lease;
- wrong/stale token rejected;
- released/expired lease rejected or documented idempotent no-op as appropriate;
- use server time;
- extend expiry by configured lease duration;
- update attempt heartbeat.

`release(...)` must be token-protected and idempotent for exact repeat.

`reap_expired_leases(now=None, batch_size=None)`:

- bounded `select_for_update(skip_locked=True)`;
- only unreleased, expired leases;
- release with `EXPIRED`;
- active attempt -> `TIMED_OUT`;
- if cancellation requested -> cancel instead of retry;
- else retry if allowed, otherwise terminal timeout/failure;
- repeated reaping no duplicate transition/attempt/event.

## 9. Retry service

Default max attempts 3, base 30, cap 900.

Calculation:

```text
min(retry_base_seconds * 2 ** (attempt_number - 1),
    WORKFLOW_RETRY_MAX_SECONDS)
```

No random jitter in persisted scheduler time.

Retry only when retryable, attempts remain, and not paused/cancelling/terminal.

Never delete old attempts.

## 10. Idempotent command service

`services/commands.py` is the only public mutation path for pause/resume/cancel/retry.

Header: `Idempotency-Key`, trimmed length 1–128.

Canonical request hash is SHA-256 over sorted, compact JSON:

```json
{
  "generation_id": "<uuid>",
  "command_type": "<PAUSE|RESUME|CANCEL|RETRY>",
  "payload": {}
}
```

Transaction algorithm:

1. validate key;
2. resolve tenant generation;
3. compute request hash;
4. lock/read command if exists;
5. same key/different hash -> 409;
6. same key/same hash -> stored replay;
7. absent -> create safely; on uniqueness race, re-read;
8. lock generation and apply command;
9. store response and applied_at;
10. transition and outbox commit atomically.

Pause:
- generation -> PAUSED;
- current RUNNING workflow -> PAUSED;
- no new claims;
- active attempt may finish.

Resume:
- only PAUSED;
- restore resume_status;
- run PAUSED -> RUNNING where applicable.

Cancel:
- nonterminal -> CANCELLING;
- run -> CANCELLING;
- mark active packages cancellation-requested;
- block new claims;
- if no active leases, finalize cancellation;
- otherwise finalizer after release/reap.

Retry:
- only FAILED/TIMED_OUT/BLOCKED;
- only eligible packages;
- preserve attempts/counts/history;
- exhausted max attempts remain terminal;
- generation -> SCHEDULED;
- workflow restarts only from persisted eligible truth.

## 11. Transactional outbox

`enqueue_event`, `claim_batch`, `publish_batch`.

Mutation and outbox insert share transaction.

Claim:

- unpublished and available;
- unclaimed/expired claim;
- `select_for_update(skip_locked=True)`;
- set claim token and claimed_until.

Publish may occur outside DB lock.

Ack transaction:

- re-lock by event ID + claim token;
- success -> published_at, clear claim;
- failure -> bounded last_error, keep pending, clear/age claim;
- reuse stable event ID on retry.

Modify `apps/realtime/event_publisher.py` minimally:

- preserve existing best-effort `publish()`;
- add synchronous raising `publish_durable(event)` for outbox;
- no runtime changes.

Add B3 constants to `apps/realtime/events.py`.

## 12. API

### 12.1 Generation commands

Routes:

- pause
- resume
- cancel
- retry

All require Idempotency-Key.

Success response:

```json
{
  "command_id": "<uuid>",
  "idempotent_replay": false,
  "generation": {}
}
```

Replay flips flag true.

Errors:

- `idempotency_key_required` 400
- `invalid_idempotency_key` 400
- `idempotency_key_conflict` 409
- `direct_transition_requires_coordinator` 409
- `retry_not_available` 409
- tenant-safe 404

### 12.2 Generic transition compatibility

Keep route but do not allow arbitrary forward state forcing.

Supported compatibility control transitions must route through the same command service. Forward/internal targets -> 409 `direct_transition_requires_coordinator`.

No secret bypass switch.

### 12.3 Read-only workflow APIs

Register:

- workflow runs list/detail
- work packages list/detail
- attempts list/detail

Every queryset starts from resolved organization.

Do not expose:

- lease token
- command request/response payload
- outbox payload
- secret-bearing raw error details
- unrestricted internal result payloads

No public write routes for workflow internals.

## 13. Migrations

### 13.1 Frozen migration verification

Never edit/delete/rename a migration present at baseline.

Before/after:

```bash
git diff --diff-filter=MDR --name-only 6ab818db61f4fc1eaa8c6ff25574204f95a027e5 -- 'backend/**/migrations/*.py'
```

Expected empty. Only new `A` migration files are allowed.

### 13.2 Generation next migration

Create next migration after `0002_organization_audit_ownership.py`.

Staged operations:

1. add new generation fields;
2. create milestone and transition models;
3. add nullable step milestone FK;
4. map B2 statuses using phase-spec table;
5. create sequence-1 `Legacy / B2 Steps` only for generations that have steps;
6. attach all existing steps;
7. alter milestone FK non-null;
8. update field choices.

Reverse:

- deterministic B3->B2 status mapping;
- preserve generation/step/run IDs and relationships;
- remove new milestone relation safely.

### 13.3 Workflows migration

Create `apps/workflows/migrations/0001_initial.py`.

### 13.4 MigrationExecutor

Add `backend/tests/migrations/test_b3_workflow_kernel_migration.py`.

Must start from exact B2 leaf state, seed representative B2 statuses and step/run data, migrate forward, assert mapping/IDs/milestones/new fields, reverse, assert B2-compatible rows, then restore current leaf graph.

## 14. Configuration / Celery

Add WorkflowsConfig to INSTALLED_APPS.

Update `.env.example` with:

- WORKFLOW_LEASE_SECONDS
- WORKFLOW_SCHEDULER_BATCH_SIZE
- WORKFLOW_MAX_ATTEMPTS
- WORKFLOW_RETRY_BASE_SECONDS
- WORKFLOW_RETRY_MAX_SECONDS
- OUTBOX_BATCH_SIZE
- OUTBOX_CLAIM_SECONDS

Parse via existing positive integer helper.

Tasks:

- `workflow_scheduler_tick`
- `workflow_reap_expired_leases`
- `workflow_dispatch_outbox`

Tasks are duplicate-safe and must not treat Celery result as state.

Celery Beat may schedule only these bounded tasks. Do not add API keys or OpenHands startup.

## 15. Required tests

Use PostgreSQL.

Generation:
- all allowed/representative forbidden lifecycle edges;
- stale instance cannot overwrite locked current state;
- transition/state version monotonic;
- no new metadata state history;
- pause/resume timestamps;
- completed_at compatibility.

Commands:
- missing key;
- exact replay;
- different request conflict;
- concurrent same-key applies once;
- idempotent cancel.

Graph:
- deterministic topological order;
- self/cross-run/cycle rejection;
- frozen graph mutation rejection;
- dependency readiness.

Lease/concurrency:
- concurrent claim one lease/package;
- wrong token rejected;
- heartbeat extends expiry;
- abandoned lease crash recovery;
- reaper idempotent;
- attempt number monotonic.

Retry:
- exact backoff;
- max attempt terminal;
- non-retryable terminal.

Pause/cancel:
- pause blocks claim;
- resume restores;
- cancelling blocks claim;
- active lease prevents premature CANCELLED;
- release/reap allows final cancellation.

Completion gate:
- candidate complete does not unlock dependencies;
- empty validation evidence rejected;
- validated complete unlocks on next scheduler tick.

Outbox:
- mutation and event same transaction;
- rollback removes both;
- publish failure stays pending;
- retry same event ID;
- concurrent claims disjoint;
- success publishes/acks once logically.

Tenant:
- cross-tenant workflow run/package/attempt list/detail denied;
- workflow endpoints read-only;
- generic transition cannot bypass coordinator.

Migration:
- B2->B3->B2 MigrationExecutor.

Full backend suite must pass without weakening B1/B2 valid assertions.

## 16. Preservation/removal ledger

Report these classifications:

- B2 GenerationStatus graph — `REPLACE`
- metadata state_history as new truth — `REPLACE`, preserve legacy values
- generic public forward transition bypass — `REFACTOR`
- existing `transaction.on_commit(...execute_agent_run.delay...)` execution path — `DEFER` to B4, not B3 scheduler truth
- AgentRun — `KEEP/DEFER` B4
- Workspace/Artifact — `KEEP/DEFER` B5
- backend/runtime — `KEEP`, byte-equivalent
- historical migrations — `KEEP`, byte-equivalent
- direct best-effort realtime publisher — `KEEP` compatibility; B3 workflow events use outbox

Do not delete deferred later-phase objects.

## 17. Docs/report

Update:

- `docs/API-CONTRACT.md`
- `docs/DATA-MODEL.md`
- `README.md`

Create:

- `docs/reports/B3-DURABLE-WORKFLOW-KERNEL-REPORT.md`

Do not modify roadmap/AGENTS/protocol or B1/B2 specs/reports.

Report exact:

- baseline/head
- files
- migrations
- removal ledger
- exact tests
- concurrency evidence
- exact OpenHands live skip reason
- Docker
- CI run ID
- zero runtime diff
- historical migration preservation
- unresolved/scope deviations

## 18. Verification

Backend:

```bash
cd backend
uv sync --frozen --extra dev
uv run python manage.py check
uv run python manage.py makemigrations --check --dry-run
uv run pytest apps/generations/tests apps/workflows/tests tests/migrations/test_b3_workflow_kernel_migration.py -q
uv run pytest
docker compose config
docker build -t tersuite-backend:b3 .
```

Repository:

```bash
git status --short
git diff --name-status 6ab818db61f4fc1eaa8c6ff25574204f95a027e5...HEAD
git diff --name-only 6ab818db61f4fc1eaa8c6ff25574204f95a027e5...HEAD -- backend/runtime
git diff --diff-filter=MDR --name-only 6ab818db61f4fc1eaa8c6ff25574204f95a027e5 -- 'backend/**/migrations/*.py'
```

Runtime diff must be empty. Historical migration M/D/R diff must be empty.

Do not supply OpenRouter key. Existing live OpenHands test may skip because the Agent Server is not running.

## 19. Commits / push

Recommended:

```bash
git commit -m "docs(b3): define durable workflow kernel contracts"
git commit -m "feat(b3): implement durable workflow kernel"
git commit -m "docs(b3): record durable workflow kernel evidence"
```

Push normally:

```bash
git push -u origin feature/b3-durable-workflow-kernel
```

No force push. Do not create/merge PR unless separately instructed.

## 20. Stop conditions

Stop if:

- baseline mismatch;
- unsafe dirty worktree;
- runtime edit appears required;
- historical migration edit appears required;
- authoritative docs conflict;
- PostgreSQL concurrency cannot be tested;
- forward/reverse migration unsafe;
- test success requires weakened assertions;
- credentials/live OpenHands are requested;
- scope expands to B4+.
