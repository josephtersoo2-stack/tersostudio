# Tersuite AI Studio CC-03 Implementation Spec
## Module Name
`CC-03: Control Center Operational Actions and Mutation Controls`

## Purpose
Complete the operational capabilities of the Control Center by introducing safe, staff-only mutation actions for cancelling running generations and retrying failed execution steps.

---

## Backend Requirements (apps/control_center/)

1. **Cancel Generation Endpoint:**
   - `POST /api/v1/control-center/generations/<generation_id>/cancel/`
   - Permissions: `IsStaffControlCenterUser`
   - Allowed statuses: `PLANNING`, `BUILDING`, `TESTING`, `REVIEW`
   - Action: Transitions generation to `CANCELLED`, marks active steps/runs as `CANCELLED`, and revokes Celery tasks.
   - Response: `200 OK` with updated generation detail payload.

2. **Retry Step Endpoint:**
   - `POST /api/v1/control-center/steps/<step_id>/retry/`
   - Permissions: `IsStaffControlCenterUser`
   - Allowed statuses: `FAILED`, `CANCELLED`
   - Action: Transitions step to `PENDING`, increments `retry_count`, transitions parent generation to appropriate active state (e.g. `BUILDING`), and dispatches execution via `ExecutionService`.
   - Response: `200 OK` with updated step and new `AgentRun` summary.

3. **Backend Tests:**
   - Permission checks (401 anonymous, 403 non-staff, 200 staff).
   - Valid cancellation transition updates timestamps and child statuses.
   - Invalid cancellation (e.g. on already `COMPLETED` generation) returns 400 Bad Request.
   - Retry step creates new `AgentRun` attempt and updates sequence.
   - Invalid retry (e.g. on `COMPLETED` step) returns 400 Bad Request.

---

## Frontend Requirements (frontend/)

1. **Generation Detail Page Actions:**
   - Add "Cancel Generation" button in header (active only when generation is in-flight).
   - Confirmation dialog warning the operator before cancelling.
   - Add "Retry" action button next to failed/cancelled steps in the Steps table.
   - Confirmation dialog before initiating step retry.

2. **UI State & Mutation Feedback:**
   - TanStack mutation hooks with loading spinners and error toast alerts.
   - Auto-refetch generation detail on mutation success.

3. **Navigation / Menu Finalization:**
   - Finalize `Sidebar.tsx` navigation items: Dashboard, Generations, Agent Runs, Runtime Health, Artifacts.
   - Mark future items ("Knowledge Base", "Sandboxes") with clean "Phase 5+" badges.

---

## Quality & Security Guardrails
1. No secret keys or raw credentials in payloads.
2. Only staff users can execute mutation endpoints.
3. No direct DB tampering; all state changes must pass through the centralized `Generation` state transition service.
