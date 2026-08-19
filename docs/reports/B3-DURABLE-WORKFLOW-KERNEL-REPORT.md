# B3-DURABLE-WORKFLOW-KERNEL-REPORT.md — Milestone B3 Durable Workflow Kernel Completion Report

- **Project**: Tersuite AI Studio
- **Milestone**: B3 — Durable Generation and Workflow Kernel
- **Status**: B3 CORRECTION 02 IMPLEMENTED — PENDING INDEPENDENT FREEZE REVIEW
- **Baseline Main SHA**: `6ab818db61f4fc1eaa8c6ff25574204f95a027e5`
- **Reviewed Head**: `c6e8658d00ab86ec44fce54002e1a8e490977589`
- **Feature Branch**: `feature/b3-durable-workflow-kernel`
- **Published B3 Commit**: `[Pending Implementation Commit SHA]`
- **GitHub Actions CI Run**: `[Pending CI Run URL]`
- **CI Status & Conclusion**: Pending CI Run Verification
- **Django System Check**: 0 Issues (`System check identified no issues (0 silenced)`)
- **Migration Consistency**: Clean (`makemigrations --check --dry-run` reports `No changes detected`)
- **Migration Verification**: Real Django `MigrationExecutor` forward & reverse test passed in `backend/tests/migrations/test_b3_workflow_kernel_migration.py`
- **Runtime Integrity**: `backend/runtime/**` is 100% byte-for-byte identical to baseline (0 diff)

---

## 1. Executive Summary

Milestone B3 implements a deterministic, PostgreSQL-backed durable workflow coordination kernel and transactional outbox engine for Tersuite AI Studio.

In Correction 02, all findings from the independent review were comprehensively resolved:
1. **Governing Document Restoration (Finding 01)**: Restored `docs/ANTIGRAVITY-SESSION-03-B3-DURABLE-WORKFLOW-KERNEL.md` to the exact 342-line governing prompt.
2. **Strict Model Provenance (Finding 02)**: Removed all fallback auto-creation of "Default Milestone", steps, or agent roles from `GenerationStep.save()` and `WorkPackage.save()`. Relational foreign keys are strictly validated and required before persistence.
3. **Database Audit (Finding 03)**: Audited local database to verify zero orphan or unlinked `WorkPackage` records exist.
4. **Retry Delay & Package Overrides (Finding 04)**: Enforced `work_package.retry_base_seconds` precedence over global base backoff settings.
5. **Atomic Monotonic State Versioning on Retry (Finding 05)**: Centralized retry state transitions in `WorkflowRetryService.schedule_retry()`, atomically incrementing `state_version += 1` on worker failures, reaper timeouts, and manual retry commands.
6. **Canonical Non-Runnable States for Automatic Retries (Finding 06)**: Blocked automatic retries for `BLOCKED`, `PAUSED`, `CANCELLING`, `CANCELLED`, `FAILED`, `TIMED_OUT`, `ACTIVE`, `STAGED`, and `RELEASE_CANDIDATE`. Allowed manual retries specifically for `FAILED`, `TIMED_OUT`, and `BLOCKED` through explicit command authorization.
7. **Generation-Wide Cancellation Quiescence (Finding 07 & 08)**: Enforced that `WorkflowCancellationService.finalize_if_quiescent()` verifies zero active leases across the entire generation before marking `CANCELLED`.
8. **Active Attempt Reconciliation on Cancellation (Finding 09)**: Active `RUNNING` or `QUEUED` attempts are deterministically transitioned to `CANCELLED` with `completed_at` timestamps upon generation cancellation finalization.
9. **Cooperative Release Finalization (Finding 10)**: Bound `WorkflowLeaseService.release_lease()` to trigger cancellation finalization when cancellation is pending.
10. **Active-Lease Validation Centralization (Finding 11)**: Centralized token, expiration, attempt binding, and package state validation in `_validate_active_lease()`, rejecting submissions from expired leases so the reaper exclusively manages timeout recovery.
11. **Completion Gate & Attempt Truth (Finding 12)**: Enforced relational validation in `mark_validated_complete()`, verifying that `latest_attempt.status == CANDIDATE_COMPLETE` and `latest_attempt.attempt_number == package.attempt_count`.

---

## 2. Technical Architecture & Invariants

### 2.1. Generation State Machine (`apps.generations`)
- **Canonical 24-State Lifecycle**: Deterministic forward and control state progression.
- **Relational Transition Audit**: `GenerationStateTransition` logs monotonic `sequence`, timestamps, actor attribution, and reason metadata without mutating generation metadata.
- **Strict Hierarchy**: `GenerationMilestone` $\rightarrow$ `GenerationStep` with non-null foreign keys and `models.PROTECT` cascading safety.

### 2.2. Durable Workflows Engine (`apps.workflows`)
- **WorkflowRun & WorkPackage**: Tenant-scoped, generation-scoped execution containers with single active run constraint and non-null step association.
- **Acyclic Graph (DAG)**: `WorkflowGraphService` provides cycle detection, self-edge rejection, frozen graph protection, and priority-aware topological sorting.
- **Scheduler & Leases**: `WorkflowSchedulerService` and `WorkflowLeaseService` provide `select_for_update(skip_locked=True)` claiming, attempt tracking, lease heartbeat extension with execution deadline capping, and stale lease reaping.
- **Completion Gate**: Two-phase candidate completion (`CANDIDATE_COMPLETE` $\rightarrow$ `COMPLETED`) requiring structured validation evidence and relational attempt truth.
- **Control Commands**: `WorkflowCommandService` executes idempotent `PAUSE`, `RESUME`, `CANCEL`, and `RETRY` operations with savepoint concurrency protection and exponential backoff.
- **Transactional Outbox**: `OutboxService` enqueues domain events within database transactions, filters forbidden secrets, and dispatches batches to Django Channels / Redis.

---

## 3. Verification & Test Evidence

### 3.1. Local Pytest Execution
- **Command**: `python -m pytest apps/ tests/ -q`
- **Result**: `255 passed, 1 skipped`
- **Key Test Modules**:
  - `apps/generations/tests/test_generations.py`: Validates missing milestone rejection and strict foreign key integrity.
  - `apps/generations/tests/test_state_machine.py`: 24-status transitions, monotonic versioning, no metadata mutation.
  - `apps/generations/tests/test_authorization.py`: Multi-tenant boundary isolation.
  - `apps/generations/tests/test_execution_service.py`: Generation run dispatching and failure categorization.
  - `apps/workflows/tests/test_models.py`: Constraints, unique active run, self-dependency check, step requirement.
  - `apps/workflows/tests/test_graph.py`: DAG validation, topological sorting, cycle detection.
  - `apps/workflows/tests/test_scheduler.py`: Ready queue, worker claims, expired lease rejection, cancellation finalization on candidate response, candidate completion gate, attempt truth validation.
  - `apps/workflows/tests/test_leases.py`: Lease acquisition, heartbeats, deadline capping, stale lease reaper, cancellation finalization on release, generation-wide lease quiescence.
  - `apps/workflows/tests/test_retries.py`: Exponential backoff calculations, package custom base delay, state_version persistence, canonical non-runnable state checks, manual retry policy.
  - `apps/workflows/tests/test_commands.py`: Idempotent pause, resume, cancel finalization, retry eligibility, delay calculation.
  - `apps/workflows/tests/test_outbox.py`: Transactional enqueue, secret stripping, batch claim, backoff.
  - `apps/workflows/tests/test_concurrency.py`: Multi-threaded PostgreSQL concurrency safety (claim race, idempotency race, outbox race, transition race).
  - `apps/workflows/tests/test_api.py`: Tenant-isolated read-only REST inspection endpoints.
  - `apps/control_center/tests/test_control_center_actions_api.py`: Staff-only pause, resume, retry, and cancellation.
  - `tests/migrations/test_b3_workflow_kernel_migration.py`: MigrationExecutor forward and reverse verification.

### 3.2. Scope & Constraint Verification
- `git diff --stat 6ab818db61f4fc1eaa8c6ff25574204f95a027e5 -- backend/runtime`: 0 files changed, 0 insertions, 0 deletions.
- `git diff --stat 6ab818db61f4fc1eaa8c6ff25574204f95a027e5 -- AGENTS.md docs/TERSUITE-IMPLEMENTATION-ROADMAP.md docs/ANTIGRAVITY-DEVELOPMENT-PROTOCOL.md`: 0 files changed, 0 insertions, 0 deletions.
- Historical migrations from baseline: 100% untouched.

---

## 4. Conclusion

Milestone B3 Correction 02 is fully implemented and verified locally across all test suites, migrations, and concurrency checks.
