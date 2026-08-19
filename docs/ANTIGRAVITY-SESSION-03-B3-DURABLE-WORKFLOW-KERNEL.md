Antigravity Execution Prompt — Session 03: B3 Durable Workflow Kernel

Mission

Implement B3 on the user's local Tersuite checkout, verify locally, commit locally, and push feature/b3-durable-workflow-kernel for independent review.

Do not make GitHub-only edits.
Do not merge.

Frozen baseline

Repository: josephtersoo2-stack/tersostudio

Required main SHA:

6ab818db61f4fc1eaa8c6ff25574204f95a027e5

Mandatory reading order

this prompt

AGENTS.md

docs/TERSUITE-IMPLEMENTATION-ROADMAP.md

docs/ANTIGRAVITY-DEVELOPMENT-PROTOCOL.md

supplied docs/B3-DURABLE-WORKFLOW-KERNEL-PHASE-SPEC.md

supplied docs/B3-DURABLE-WORKFLOW-KERNEL-DETAILED-IMPLEMENTATION.md

B2 contracts/current code

The B3 specs contain fixed architecture. Do not redesign.

1. Preflight

git status --short
git branch --show-current
git fetch origin --prune
git switch main
git pull --ff-only origin main
git rev-parse HEAD
git rev-parse origin/main

Both SHAs must equal 6ab818db61f4fc1eaa8c6ff25574204f95a027e5. Worktree must be clean.

git switch -c feature/b3-durable-workflow-kernel

If not, stop and report.

2. Put the three B3 docs into the local repo first

Copy the supplied approved files to:

docs/B3-DURABLE-WORKFLOW-KERNEL-PHASE-SPEC.md
docs/B3-DURABLE-WORKFLOW-KERNEL-DETAILED-IMPLEMENTATION.md
docs/ANTIGRAVITY-SESSION-03-B3-DURABLE-WORKFLOW-KERNEL.md

Read them fully.

Do not edit:

AGENTS.md
docs/TERSUITE-IMPLEMENTATION-ROADMAP.md
docs/ANTIGRAVITY-DEVELOPMENT-PROTOCOL.md

Recommended:

git add docs/B3-DURABLE-WORKFLOW-KERNEL-PHASE-SPEC.md \
        docs/B3-DURABLE-WORKFLOW-KERNEL-DETAILED-IMPLEMENTATION.md \
        docs/ANTIGRAVITY-SESSION-03-B3-DURABLE-WORKFLOW-KERNEL.md
git commit -m "docs(b3): define durable workflow kernel contracts"

3. Audit before editing

Run all git grep commands from the detailed spec.

Inspect at minimum:

generation enums/models/state machine;

generation migrations/tests;

serializers/views;

existing ExecutionService/Celery task;

Control Center references;

realtime events/publisher;

every old generation-status reference.

Record findings in B3 report.

4. Implement exactly B3

Required:

canonical generation lifecycle;

row-locked transitions;

state version + transition ledger;

generation milestones and step backfill;

new apps/workflows;

WorkflowRun;

WorkPackage DAG/dependency validation;

WorkPackageAttempt;

WorkPackageLease;

heartbeat/reaper;

deterministic retry;

idempotent pause/resume/cancel/retry;

transactional outbox;

durable B3 event publication;

read-only tenant-scoped workflow APIs;

B3 configuration/admin/tests/migrations/docs.

Runtime boundary

Absolutely no change under:

backend/runtime/**

Do not change OpenHands runtime tests.
Do not request/add OpenRouter key.
Do not start a live OpenHands Agent Server.
Do not force test_openhands_live.py to execute.
Do not implement B4.

Existing AgentRun/ExecutionService remains provisional compatibility code and is not B3 scheduler truth.

5. Migrations

Never modify existing migrations.

Create only:

next generations B3 migration(s);

workflows 0001_initial.py;

MigrationExecutor B2->B3->B2 test.

Verify:

git diff --diff-filter=MDR --name-only 6ab818db61f4fc1eaa8c6ff25574204f95a027e5 -- 'backend/**/migrations/*.py'

Must be empty.

6. Required concurrency/durability evidence

Tests must use PostgreSQL row locks/uniqueness with separate DB connections/threads where concurrency matters.

Prove:

two concurrent claimers never claim same package;

concurrent same idempotency key applies once;

abandoned lease survives worker crash and is reaped/retried after expiry;

attempts remain append-only and increment;

cancellation does not finalize while an active lease remains;

candidate completion does not unlock dependency before deterministic validation;

outbox mutation/event rollback together;

outbox retry reuses event ID.

Do not weaken B1/B2 valid tests.

7. Docs/report

Update only:

docs/API-CONTRACT.md
docs/DATA-MODEL.md
README.md

Create:

docs/reports/B3-DURABLE-WORKFLOW-KERNEL-REPORT.md

Report must include exact files, migration names, test totals, concurrency evidence, runtime zero-diff proof, historical migration preservation, exact OpenHands skip reason, Docker/CI evidence, unresolved items and deviations.

8. Local verification

cd backend
uv sync --frozen --extra dev
uv run python manage.py check
uv run python manage.py makemigrations --check --dry-run
uv run pytest apps/generations/tests apps/workflows/tests tests/migrations/test_b3_workflow_kernel_migration.py -q
uv run pytest
docker compose config
docker build -t tersuite-backend:b3 .

Then repo root:

git status --short
git diff --name-status 6ab818db61f4fc1eaa8c6ff25574204f95a027e5...HEAD
git diff --name-only 6ab818db61f4fc1eaa8c6ff25574204f95a027e5...HEAD -- backend/runtime
git diff --diff-filter=MDR --name-only 6ab818db61f4fc1eaa8c6ff25574204f95a027e5 -- 'backend/**/migrations/*.py'

Runtime diff: EMPTY.
Historical migration M/D/R diff: EMPTY.

9. Commit/push

Recommended:

git add <B3 implementation/test files only>
git commit -m "feat(b3): implement durable workflow kernel"

git add docs/API-CONTRACT.md docs/DATA-MODEL.md README.md \
        docs/reports/B3-DURABLE-WORKFLOW-KERNEL-REPORT.md
git commit -m "docs(b3): record durable workflow kernel evidence"

Inspect diff and status, then:

git push -u origin feature/b3-durable-workflow-kernel

No force push.
No PR/merge unless separately instructed.

Monitor branch CI if triggered and capture exact result. Correct only B3 failures on same branch.

Hard prohibitions

no backend/runtime/** edits

no historical migration edits

no roadmap/AGENTS/protocol edits

no B4+

no live API keys

no LLM-controlled scheduler

no third-party workflow engine

no frontend/WordPress

no inherited Docker warning cleanup

no force push

no merge

no fabricated evidence

Stop conditions

Stop/report if baseline mismatch, unsafe local changes, required runtime/historical migration edit, authoritative conflict, unavailable PostgreSQL concurrency testing, unsafe migration reversal, test weakening required, live credentials requested, or scope jump.

Final handoff

Return:

B3 Durable Workflow Kernel — Antigravity Handoff

Baseline:
Branch:
Final HEAD:

Commits:
- <sha> <message>

Files changed:
- <path> — <reason>

Migration files added:
- <path>

Historical migrations modified/deleted/renamed:
- NONE / details

backend/runtime diff vs B2 baseline:
- EMPTY / details

Canonical lifecycle:
- implemented:
- migration mapping verified:

Workflow kernel:
- WorkflowRun:
- WorkPackage/DAG:
- Attempt/Lease:
- Heartbeat/Reaper:
- Retry:
- Pause/Resume:
- Cancellation:
- Idempotent Commands:
- Transactional Outbox:

Concurrency evidence:
- duplicate claim:
- duplicate command:
- stale lease recovery:

Migrations:
- forward:
- reverse:
- MigrationExecutor:

Local verification:
- Django check:
- migration consistency:
- focused B3 tests:
- full pytest:
- Docker Compose:
- Docker build:

OpenHands live integration:
- executed/skipped:
- exact reason:
- API key supplied: NO

CI:
- run ID:
- conclusion:
- exact pytest totals:
- skip reason:
- Docker:

Unresolved failures:
- NONE / details

Scope deviations:
- NONE / details

Worktree:
- clean:

Push:
- origin/feature/b3-durable-workflow-kernel updated:

PR:
- NOT CREATED

Merge:
- NOT PERFORMED
