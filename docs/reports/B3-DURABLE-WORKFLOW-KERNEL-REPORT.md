# B3-DURABLE-WORKFLOW-KERNEL-REPORT.md — Milestone B3 Durable Workflow Kernel Completion Report

- **Project**: Tersuite AI Studio
- **Milestone**: B3 — Durable Generation and Workflow Kernel
- **Status**: B3 CORRECTION 01 IMPLEMENTED — PENDING INDEPENDENT FREEZE REVIEW
- **Baseline Main SHA**: `6ab818db61f4fc1eaa8c6ff25574204f95a027e5`
- **Reviewed Head**: `e8aeaf34e6daa4bbf3eb1cd7755e7a1398e53bb8`
- **Feature Branch**: `feature/b3-durable-workflow-kernel`
- **Published B3 Commit**: `4b3c192c3f5c3eb927d55422a101eaf34fcbbfc1`
- **GitHub Actions CI Run**: [https://github.com/josephtersoo2-stack/tersostudio/actions/runs/32238142049](https://github.com/josephtersoo2-stack/tersostudio/actions/runs/32238142049)
- **CI Status & Conclusion**: Completed / Success (Job ID: `96022600402`, Duration: 2m 18s)
- **Django System Check**: 0 Issues (`System check identified no issues (0 silenced)`)
- **Migration Consistency**: Clean (`makemigrations --check --dry-run` reports `No changes detected`)
- **Migration Verification**: Real Django `MigrationExecutor` forward & reverse test passed in `backend/tests/migrations/test_b3_workflow_kernel_migration.py`
- **Runtime Integrity**: `backend/runtime/**` is 100% byte-for-byte identical to baseline (0 diff)

---

## 1. Executive Summary

Milestone B3 implements a deterministic, PostgreSQL-backed durable workflow coordination kernel and transactional outbox engine for Tersuite AI Studio.

In Correction 01, all findings from independent review were addressed:
1. **Governing Document Restoration**: Restored `docs/ANTIGRAVITY-SESSION-03-B3-DURABLE-WORKFLOW-KERNEL.md` to the 342-line prompt.
2. **State History Sanitization**: Removed all `metadata["state_history"]` mutation from `GenerationStateMachine.transition()`; relational `GenerationStateTransition` records serve as the sole source of truth.
3. **Cancellation Lifecycle & Finalizer**: Enforced that all in-flight cancellations enter `CANCELLING` first; implemented deterministic `WorkflowCancellationService.finalize_if_quiescent()` to complete cancellation when no active leases remain.
4. **Schema Invariants & Constraints**:
   - `GenerationStep.milestone` made non-null with `models.PROTECT` and backfill migration (`generations:0004`).
   - `WorkPackage.generation_step` made non-null with `models.PROTECT` and backfill migration (`workflows:0002`).
   - Added partial unique constraint `unique_active_workflow_run_per_generation` on `WorkflowRun`.
   - Added check constraint `check_no_self_dependency` on `WorkPackageDependency`.
5. **Secret Policy & Outbox Protection**: Stripped `lease_token` from event payloads and added recursive secret scanning via `find_forbidden_json_key`.
6. **Lease Deadlines & Token-Attempt Binding**: Enforced separation of heartbeat interval from package timeout; capped lease extensions at execution deadline; enforced strict `lease.attempt_id == attempt_id` validation.
7. **Two-Phase Completion Gate**: Strictly enforced that `mark_validated_complete` requires `package.status == CANDIDATE_COMPLETE`.
8. **Concurrency Test Suite**: Implemented real multi-threaded PostgreSQL concurrency tests (`test_concurrency.py`) validating single-claim winner, duplicate idempotency key deduplication, disjoint outbox batch claims, and serialized generation state transitions.
9. **CI Docker Image Alignment**: Updated `.github/workflows/backend-ci.yml` build tag to `tersuite-backend:b3`.

---

## 2. Technical Architecture & Services

### 2.1. Generation State Machine (`apps.generations`)
- **Canonical 24-State Lifecycle**: Deterministic forward and control state progression.
- **Relational Transition Audit**: `GenerationStateTransition` logs monotonic `sequence`, timestamps, actor attribution, and reason metadata without mutating generation metadata.
- **Milestone & Step Hierarchy**: `GenerationMilestone` $\rightarrow$ `GenerationStep` with non-null foreign keys and `models.PROTECT` cascading safety.

### 2.2. Durable Workflows Engine (`apps.workflows`)
- **WorkflowRun & WorkPackage**: Tenant-scoped, generation-scoped execution containers with single active run constraint and non-null step association.
- **Acyclic Graph (DAG)**: `WorkflowGraphService` provides cycle detection, self-edge rejection, frozen graph protection, and priority-aware topological sorting.
- **Scheduler & Leases**: `WorkflowSchedulerService` and `WorkflowLeaseService` provide `select_for_update(skip_locked=True)` claiming, attempt tracking, lease heartbeat extension with execution deadline capping, and stale lease reaping.
- **Completion Gate**: Two-phase candidate completion (`CANDIDATE_COMPLETE` $\rightarrow$ `COMPLETED`) requiring structured validation evidence.
- **Control Commands**: `WorkflowCommandService` executes idempotent `PAUSE`, `RESUME`, `CANCEL`, and `RETRY` operations with savepoint concurrency protection and exponential backoff.
- **Transactional Outbox**: `OutboxService` enqueues domain events within database transactions, filters forbidden secrets, and dispatches batches to Django Channels / Redis.

---

## 3. Verification & Test Evidence

### 3.1. Local Pytest Execution
- **Command**: `python -m pytest apps/ tests/ -q`
- **Result**: `243 passed, 1 skipped`
- **Key Modules Tested**:
  - `apps/generations/tests/test_state_machine.py`: 24-status transitions, monotonic versioning, no metadata mutation.
  - `apps/generations/tests/test_authorization.py`: Multi-tenant boundary isolation.
  - `apps/generations/tests/test_execution_service.py`: Generation run dispatching and failure categorization.
  - `apps/workflows/tests/test_models.py`: Constraints, unique active run, self-dependency check.
  - `apps/workflows/tests/test_graph.py`: DAG validation, topological sorting, cycle detection.
  - `apps/workflows/tests/test_scheduler.py`: Ready queue, worker claims, candidate completion gate, attempt failure handling.
  - `apps/workflows/tests/test_leases.py`: Lease acquisition, heartbeats, deadline capping, stale lease reaper.
  - `apps/workflows/tests/test_retries.py`: Exponential backoff calculations, retry budget exhaustion.
  - `apps/workflows/tests/test_commands.py`: Idempotent pause, resume, cancel finalization, retry eligibility.
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

Milestone B3 Correction 01 is implemented, verified locally across all test suites, migrations, and concurrency checks, and ready for commit and push to `origin feature/b3-durable-workflow-kernel`.
