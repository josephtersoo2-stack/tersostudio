# B3-DURABLE-WORKFLOW-KERNEL-REPORT.md — Milestone B3 Durable Workflow Kernel Completion Report

- **Project**: Tersuite AI Studio
- **Milestone**: B3 — Durable Generation and Workflow Kernel
- **Status**: B3 CORRECTION 03 IMPLEMENTED — PENDING INDEPENDENT FREEZE REVIEW
- **Baseline Main SHA**: `6ab818db61f4fc1eaa8c6ff25574204f95a027e5`
- **Reviewed Head**: `3930ac30beaf401237c4f2b7b55682c314d65c78`
- **Feature Branch**: `feature/b3-durable-workflow-kernel`
- **Published B3 Commit**: `2927d0fe980055a402f1d73b54973c37a52cddb6`
- **GitHub Actions CI Run**: [https://github.com/josephtersoo2-stack/tersostudio/actions/runs/32279990695](https://github.com/josephtersoo2-stack/tersostudio/actions/runs/32279990695)
- **CI Status & Conclusion**: Completed / Success (Job ID: `96156233928`, Duration: 2m 22s)
- **Django System Check**: 0 Issues (`System check identified no issues (0 silenced)`)
- **Migration Consistency**: Clean (`makemigrations --check --dry-run` reports `No changes detected`)
- **Migration Verification**: Real Django `MigrationExecutor` forward & reverse test passed in `backend/tests/migrations/test_b3_workflow_kernel_migration.py`
- **Runtime Integrity**: `backend/runtime/**` is 100% byte-for-byte identical to baseline (0 diff)

---

## 1. Executive Summary

Milestone B3 implements a deterministic, PostgreSQL-backed durable workflow coordination kernel and transactional outbox engine for Tersuite AI Studio.

In Correction 03, the remaining durability invariant was comprehensively resolved:
1. **Reaper State Versioning (+1 Exact)**: Refactored `WorkflowLeaseService.reap_expired_leases()` to ensure single ownership of `state_version` increments across all branches. Stale-lease retries now delegate directly to `WorkflowRetryService.schedule_retry()`, ensuring `state_version` increments exactly `+1` (from `RUNNING` to `RETRY_WAIT`).
2. **Reaper Regression Tests**: Strengthened `test_reap_expired_leases_and_schedule_retry` and added `test_reap_expired_leases_cancellation_and_terminal_branches` in `apps/workflows/tests/test_leases.py` asserting exact-once monotonic increments across retry, cancellation, and terminal timeout paths.
3. **Verified Invariants Maintained**:
   - Strict `GenerationStep` and `WorkPackage` foreign key provenance (no fallback auto-creation).
   - Package-specific `retry_base_seconds` precedence and canonical non-runnable automatic retry filtering.
   - Generation-wide cancellation quiescence and active attempt reconciliation.
   - Active lease validation rejecting expired lease submissions.
   - Candidate completion gate requiring latest attempt candidate complete truth.
   - Zero diff under `backend/runtime/**`, `AGENTS.md`, and roadmap files.

---

## 2. Technical Architecture & Invariants

### 2.1. Generation State Machine (`apps.generations`)
- **Canonical 24-State Lifecycle**: Deterministic forward and control state progression.
- **Relational Transition Audit**: `GenerationStateTransition` logs monotonic `sequence`, timestamps, actor attribution, and reason metadata without mutating generation metadata.
- **Strict Hierarchy**: `GenerationMilestone` $\rightarrow$ `GenerationStep` with non-null foreign keys and `models.PROTECT` cascading safety.

### 2.2. Durable Workflows Engine (`apps.workflows`)
- **WorkflowRun & WorkPackage**: Tenant-scoped, generation-scoped execution containers with single active run constraint and non-null step association.
- **Acyclic Graph (DAG)**: `WorkflowGraphService` provides cycle detection, self-edge rejection, frozen graph protection, and priority-aware topological sorting.
- **Scheduler & Leases**: `WorkflowSchedulerService` and `WorkflowLeaseService` provide `select_for_update(skip_locked=True)` claiming, attempt tracking, lease heartbeat extension with execution deadline capping, and stale lease reaping with single-owner state versioning.
- **Completion Gate**: Two-phase candidate completion (`CANDIDATE_COMPLETE` $\rightarrow$ `COMPLETED`) requiring structured validation evidence and relational attempt truth.
- **Control Commands**: `WorkflowCommandService` executes idempotent `PAUSE`, `RESUME`, `CANCEL`, and `RETRY` operations with savepoint concurrency protection and exponential backoff.
- **Transactional Outbox**: `OutboxService` enqueues domain events within database transactions, filters forbidden secrets, and dispatches batches to Django Channels / Redis.

---

## 3. Verification & Test Evidence

### 3.1. Local Pytest Execution
- **Command**: `python -m pytest apps/ tests/ -q`
- **Result**: `256 passed, 1 skipped`
- **Key Test Modules**:
  - `apps/generations/tests/test_generations.py`: Validates missing milestone rejection and strict foreign key integrity.
  - `apps/generations/tests/test_state_machine.py`: 24-status transitions, monotonic versioning, no metadata mutation.
  - `apps/generations/tests/test_authorization.py`: Multi-tenant boundary isolation.
  - `apps/generations/tests/test_execution_service.py`: Generation run dispatching and failure categorization.
  - `apps/workflows/tests/test_models.py`: Constraints, unique active run, self-dependency check, step requirement.
  - `apps/workflows/tests/test_graph.py`: DAG validation, topological sorting, cycle detection.
  - `apps/workflows/tests/test_scheduler.py`: Ready queue, worker claims, expired lease rejection, cancellation finalization on candidate response, candidate completion gate, attempt truth validation.
  - `apps/workflows/tests/test_leases.py`: Lease acquisition, heartbeats, deadline capping, stale lease reaper with exact +1 state_version delta, cancellation finalization on release, generation-wide lease quiescence.
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

Milestone B3 Correction 03 is fully implemented, verified with green GitHub Actions CI on the implementation commit (`2927d0fe980055a402f1d73b54973c37a52cddb6`), and submitted for final freeze review.
