# Tersuite AI Studio — Control Center CC-01 Specification

## Module Name
`CC-01: Backend Control Center Foundation & React Frontend Shell`

---

## 1. Purpose

Module CC-01 establishes the production-grade internal **Control Center** for Tersuite AI Studio. It equips Tersuite operators and staff engineers with a secure, staff-only REST API and a typed React TypeScript frontend dashboard to monitor real system-wide executions (`Projects`, `Generations`, `GenerationSteps`, `AgentRuns`, `Workspaces`, `Artifacts`, and execution runtime posture).

---

## 2. Architecture Position

```text
Tersuite Control Center React UI (frontend/)
              │
              ▼  (HTTP / Token Auth)
Staff-Only Control Center API (/api/v1/control-center/)
              │
              ▼  (Django ORM / PostgreSQL)
Domain Persistence Layer (Projects, Generations, Steps, Runs, Workspaces, Artifacts)
              │
              ▼  (Celery / Redis / WebSocket)
Execution Runtime (ExecutionService, OpenHands SDK 1.42.1, OpenHands Agent Server, OpenRouter)
```

---

## 3. Security & Permission Architecture

### 3.1. Staff-Only Authorization Boundary
- **Permission Class**: `apps.control_center.permissions.IsStaffControlCenterUser`
- **Enforcement Rules**:
  - `Anonymous` requests are rejected with **401 Unauthorized**.
  - Authenticated `non-staff` customer accounts are rejected with **403 Forbidden**.
  - Authenticated `staff` and `superuser` accounts (`is_staff=True` or `is_superuser=True`) have full read-only visibility across all tenants.

### 3.2. Zero Credential Exposure
- The summary endpoint strictly returns boolean configuration flags (`openrouter_configured: true`, `openhands_api_key_configured: false`) and sanitized server URLs.
- Raw API keys (`OPENROUTER_API_KEY`, `OPENHANDS_API_KEY`), database passwords, Redis URIs, and Celery broker credentials are never serialized.

---

## 4. Backend API Contract

### 4.1. `GET /api/v1/control-center/summary/`
Returns high-level operational metrics and runtime posture.

```json
{
  "projects": {
    "total": 2,
    "active": 2,
    "archived": 0
  },
  "generations": {
    "total": 4,
    "active": 3,
    "draft": 0,
    "specification": 0,
    "approved": 0,
    "planning": 0,
    "building": 3,
    "testing": 0,
    "review": 0,
    "packaging": 0,
    "completed": 0,
    "failed": 1,
    "cancelled": 0,
    "paused": 0,
    "retrying": 0
  },
  "agent_runs": {
    "total": 4,
    "queued": 0,
    "running": 0,
    "completed": 3,
    "failed": 1,
    "cancelled": 0,
    "timed_out": 0
  },
  "steps": {
    "total": 4,
    "pending": 0,
    "running": 0,
    "completed": 3,
    "failed": 1,
    "cancelled": 0,
    "skipped": 0
  },
  "artifacts": {
    "total": 1,
    "source_code": 0,
    "configuration": 1,
    "test_report": 0,
    "documentation": 0,
    "zip_archive": 0,
    "security_report": 0,
    "other": 0
  },
  "runtime": {
    "default_backend": "openhands",
    "openhands_server_url": "http://localhost:8010",
    "openrouter_configured": true,
    "openhands_api_key_configured": false
  }
}
```

### 4.2. `GET /api/v1/control-center/generations/`
Staff-visible paginated list of all generations across all projects and users.

- **Query Parameters**: `page`, `page_size`, `status`, `project_id`, `user_id`, `search`
- **Ordering**: `-created_at`
- **Preview Constraints**: `prompt_preview` (max 140 chars), `error_message_preview` (max 140 chars)
- **Response Format**:
  ```json
  {
    "pagination": {
      "count": 4,
      "total_pages": 1,
      "current_page": 1,
      "next": null,
      "previous": null,
      "page_size": 20
    },
    "results": [
      {
        "id": "de247df2-acef-4df4-8608-d9b432b1891c",
        "project_id": "2af6668b-9871-4e1d-8229-34ff654e6320",
        "project_name": "Real Celery Pipeline Verification Project",
        "user_id": "729b1bed-ed44-4aef-ae4a-08ab49f728cc",
        "user_email": "celery.verification@tersuite.com",
        "prompt_preview": "Create a file named TERSUITE_CELERY_TEST.txt containing...",
        "status": "BUILDING",
        "current_step_number": 0,
        "total_steps": 0,
        "steps_count": 1,
        "runs_count": 1,
        "artifacts_count": 0,
        "workspace_id": null,
        "failure_category": "",
        "error_message_preview": "",
        "created_at": "2026-08-16T01:46:25.019806Z",
        "updated_at": "2026-08-16T01:46:25.019806Z",
        "completed_at": null,
        "failed_at": null,
        "cancelled_at": null,
        "paused_at": null
      }
    ]
  }
  ```

### 4.3. `GET /api/v1/control-center/runs/`
Staff-visible paginated list of all AgentRuns across all generations and users.

- **Query Parameters**: `page`, `page_size`, `status`, `runtime_type`, `model`, `failure_category`, `generation_id`, `step_id`, `search`
- **Ordering**: `-created_at`
- **Preview Constraints**: `prompt_preview` (max 140 chars), `output_preview` (max 180 chars)
- **Response Format**:
  ```json
  {
    "pagination": {
      "count": 4,
      "total_pages": 1,
      "current_page": 1,
      "next": null,
      "previous": null,
      "page_size": 20
    },
    "results": [
      {
        "id": "6cdbee95-5416-4821-8d11-ee37890d92a8",
        "generation_id": "de247df2-acef-4df4-8608-d9b432b1891c",
        "generation_status": "BUILDING",
        "project_id": "2af6668b-9871-4e1d-8229-34ff654e6320",
        "project_name": "Real Celery Pipeline Verification Project",
        "user_id": "729b1bed-ed44-4aef-ae4a-08ab49f728cc",
        "user_email": "celery.verification@tersuite.com",
        "step_id": "7d14539a-bd75-4e6b-9a99-0d76571ae446",
        "step_name": "Real Celery Execution Step",
        "step_number": 1,
        "run_number": 1,
        "runtime_type": "openhands",
        "status": "COMPLETED",
        "model_name": "openrouter/openai/gpt-4o-mini",
        "session_id": "oh-sess-ca84ed07862f",
        "remote_conversation_id": "c366a374-b68b-4a25-a1e4-ad09e7357e0a",
        "prompt_preview": "Create a file named TERSUITE_CELERY_TEST.txt in the current directory...",
        "output_preview": "Execution completed.",
        "token_usage": {
          "usage_to_metrics": { ... }
        },
        "failure_category": "",
        "started_at": "2026-08-16T01:46:33.879482Z",
        "completed_at": "2026-08-16T01:47:01.748796Z",
        "created_at": "2026-08-16T01:46:25.019806Z",
        "updated_at": "2026-08-16T01:47:01.749301Z"
      }
    ]
  }
  ```

---

## 5. React TypeScript Frontend Structure

```text
frontend/
├── src/
│   ├── app/
│   │   ├── App.tsx             (QueryClientProvider + AuthProvider + RouterProvider)
│   │   ├── router.tsx          (Route definitions with RequireStaff guard)
│   │   └── queryClient.ts      (TanStack query cache configuration)
│   ├── components/
│   │   ├── layout/
│   │   │   ├── AppShell.tsx    (Main dashboard frame with Sidebar & Topbar)
│   │   │   ├── Sidebar.tsx     (Navigation with active states & Coming Soon tags)
│   │   │   └── Topbar.tsx      (Environment indicator, staff badge & logout)
│   │   └── ui/
│   │       ├── Badge.tsx       (Semantic status badges with pulse dots)
│   │       ├── Button.tsx      (Interactive button with spin states)
│   │       ├── EmptyState.tsx  (Clean dashed empty states)
│   │       ├── ErrorState.tsx  (Error alerts with retry CTA)
│   │       ├── LoadingState.tsx(Animated skeletons)
│   │       ├── Pagination.tsx  (Standard page switcher)
│   │       └── StatBlock.tsx   (Dashboard metric card)
│   ├── features/
│   │   ├── auth/
│   │   │   ├── LoginPage.tsx       (Operator authentication form)
│   │   │   ├── authStore.tsx       (Auth context, token storage & session verifier)
│   │   │   ├── RequireStaff.tsx    (Staff route guard)
│   │   │   └── AccessDeniedPage.tsx(403 non-staff warning page)
│   │   ├── dashboard/
│   │   │   ├── DashboardPage.tsx   (KPI metrics, breakdown & runtime status)
│   │   │   ├── dashboardApi.ts     (Summary query hook with 10s auto-refresh)
│   │   │   └── dashboardTypes.ts   (Summary TypeScript interfaces)
│   │   ├── generations/
│   │   │   ├── GenerationsPage.tsx (Paginated directory, filter & search)
│   │   │   ├── generationsApi.ts   (Generations query hook)
│   │   │   └── generationsTypes.ts (Generation list interfaces)
│   │   └── agent-runs/
│   │       ├── AgentRunsPage.tsx   (Paginated runs, runtime/model badges & search)
│   │       ├── agentRunsApi.ts     (Agent runs query hook)
│   │       └── agentRunsTypes.ts   (Agent run interfaces)
│   └── lib/
│       ├── apiClient.ts    (Typed fetch client with token injection & 401/403 interceptors)
│       ├── authToken.ts    (Encapsulated token persistence)
│       ├── formatters.ts   (Dates, durations, token count formatters)
│       └── statusStyles.ts (Tailwind color mapping per state machine status)
```

---

## 6. Verification Results

1. **Backend Test Suite**:
   - `python -m pytest`: **106 passed in 32.75s** against PostgreSQL 16.
   - `apps/control_center/tests/test_control_center_api.py`: **22 passed in 5.38s**.
2. **Frontend Production Build**:
   - `npm run build`: **0 TypeScript errors**, bundle size 306kB (91.69kB gzip).
3. **API Probe & Permissions**:
   - Anonymous access to `/summary/`, `/generations/`, `/runs/` returns **401 Unauthorized**.
   - Authenticated non-staff access returns **403 Forbidden**.
   - Authenticated staff access returns **200 OK** with accurate system-wide metrics.

---

## 7. Deferred to CC-02

The following items are deferred to CC-02:
1. Generation detail view (`/generations/:id`).
2. AgentRun detail view (`/agent-runs/:id`).
3. Live event streaming timeline via Django Channels WebSocket in the UI.
4. Workspace explorer & artifact file downloads.
5. Dedicated runtime health check endpoint & ping dashboard.
6. Safe operational actions (retry, pause, cancel).
