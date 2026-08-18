# Antigravity Execution Prompt — Session 03: B3 Durable Workflow Kernel

## Overview

Session 03 implements the durable workflow kernel for Tersuite AI Studio, transitioning from provisional single-task generation execution to deterministic, lease-based, dependency-ordered multi-agent work-package orchestration with transactional outbox publishing and row-locked state transitions.

## Key Reference Documents
- `AGENTS.md`
- `docs/TERSUITE-IMPLEMENTATION-ROADMAP.md`
- `docs/ANTIGRAVITY-DEVELOPMENT-PROTOCOL.md`
- `docs/B3-DURABLE-WORKFLOW-KERNEL-PHASE-SPEC.md`
- `docs/B3-DURABLE-WORKFLOW-KERNEL-DETAILED-IMPLEMENTATION.md`
- `docs/reports/B3-DURABLE-WORKFLOW-KERNEL-REPORT.md`

## Summary of B3 Scope & Deliverables
1. **Canonical Generation Lifecycle (`apps/generations`)**: Transitioning from legacy statuses to canonical states (`INITIALIZING`, `ANALYZING`, `PLANNING`, `AWAITING_APPROVAL`, `READY_FOR_EXECUTION`, `EXECUTING`, `VERIFYING`, `CANDIDATE_COMPLETE`, `COMPLETED`, `PAUSED`, `FAILED`, `CANCELLED`).
2. **Transition Ledger & State Machine (`apps/generations`)**: Row-locked monotonic `state_version` increments, transactional ledger records with reason and actor attribution.
3. **Durable Workflow Kernel (`apps/workflows`)**:
   - `WorkflowRun`: Durable container managing orchestration state and budget limits.
   - `WorkPackage`: Atomic unit of work in a dependency DAG (`depends_on`), owned paths, requirement IDs.
   - `WorkPackageAttempt`: Append-only execution attempts with monotonic sequence tracking.
   - `WorkPackageLease`: Distributed lease mechanism with heartbeat renewal and stale-lease reaper.
4. **Deterministic Commands & Operations (`apps/workflows/services`)**:
   - Idempotent command processing (`client_command_id`).
   - Deterministic pause, resume, cancel, and retry state transitions.
5. **Transactional Outbox & Event Publication (`apps/workflows/models`)**:
   - Atomic mutation + outbox event logging.
   - Durable publication ensuring at-least-once delivery to Django Channels without split-brain anomalies.
6. **Read-Only Workflow APIs (`apps/workflows/views`)**:
   - Tenant-isolated listing and detail views for workflow runs, work packages, attempts, and execution DAGs.
7. **Runtime Boundary Preservation**:
   - `backend/runtime/**` remains 100% byte-for-byte identical to baseline.
