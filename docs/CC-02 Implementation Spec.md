# Tersuite AI Studio CC-02 Implementation Spec
## Module Name
`CC-02: Control Center Operational Detail and Live Monitoring`
## Purpose
Extend CC-01 from summary/list visibility into full operational triage. CC-02 gives staff users deep inspection of a generation lifecycle, agent-run diagnostics, runtime health, and artifact access, including live event observation.
---
## Preconditions
CC-01 is complete and frozen:
1. Staff-only Control Center API boundary exists.
2. Control Center summary endpoint exists.
3. Control Center generation list endpoint exists.
4. Control Center run list endpoint exists.
5. React Control Center shell with auth guard exists.
6. Real Celery -> ExecutionService -> OpenHands -> OpenRouter path remains untouched.
---
## Primary Goal
Add read-first operational depth:
1. Generation detail API and page.
2. Agent run detail API and page.
3. Runtime/system health API and page.
4. Artifact listing and safe download endpoint.
5. Live event timeline on generation detail using WebSocket.
---
## Non-Goals
Do not implement in CC-02:
1. Feature Discovery.
2. Planner/Coordinator logic.
3. Sandbox redesign.
4. Retry/cancel mutation actions unless explicitly approved as CC-02b.
5. Runtime architecture changes.
6. OpenHands adapter refactor.
7. Celery task flow changes.
8. Any credential serialization.
---
## Backend Scope
Use existing `backend/apps/control_center/` app.
Add/extend:
1. `serializers.py`
2. `views.py`
3. `urls.py`
4. `tests/test_control_center_api.py`
Optional new test module is acceptable:
`backend/apps/control_center/tests/test_control_center_detail_api.py`
---
## Backend Endpoints
All endpoints remain staff-only.
### 1) Generation Detail
`GET /api/v1/control-center/generations/<generation_id>/`
Returns full operational generation view:
1. Base generation fields.
2. Full prompt.
3. Status and transition timestamps.
4. Metadata and state history.
5. Full step list.
6. Each step's run attempts summary.
7. Workspace details if present.
8. Artifact summaries.
9. Error/failure diagnostics.
Response shape (minimum):
```json
{
  "id": "uuid",
  "project": {"id": "uuid", "name": "..."},
  "user": {"id": "uuid", "email": "..."},
  "prompt": "full prompt",
  "status": "BUILDING",
  "current_step_number": 1,
  "total_steps": 3,
  "metadata": {},
  "failure_category": "",
  "error_message": "",
  "timestamps": {
    "created_at": "...",
    "updated_at": "...",
    "completed_at": null,
    "failed_at": null,
    "cancelled_at": null,
    "paused_at": null
  },
  "steps": [],
  "workspace": null,
  "artifacts": []
}
```
### 2) Agent Run Detail
`GET /api/v1/control-center/runs/<run_id>/`
Returns full run diagnostics:
1. Generation + step context.
2. Runtime type/model.
3. Full prompt and output.
4. Session and remote conversation IDs.
5. Token usage payload.
6. Failure category and error details.
7. Timing fields.
Response shape (minimum):
```json
{
  "id": "uuid",
  "generation": {"id": "uuid", "status": "BUILDING"},
  "step": {"id": "uuid", "name": "...", "step_number": 1},
  "run_number": 1,
  "runtime_type": "openhands",
  "status": "COMPLETED",
  "model_name": "openrouter/openai/gpt-4o-mini",
  "session_id": "oh-sess-...",
  "remote_conversation_id": "uuid",
  "prompt": "full prompt",
  "output": "full output",
  "token_usage": {},
  "failure_category": "",
  "error_details": {},
  "started_at": "...",
  "completed_at": "...",
  "created_at": "...",
  "updated_at": "..."
}
```
### 3) Runtime Health
`GET /api/v1/control-center/health/`
Health payload must include:
1. Database reachability.
2. Redis reachability.
3. Celery broker connectivity.
4. OpenHands server reachability.
5. Runtime backend configured value.
6. OpenRouter configured boolean.
No secrets in response.
Example:
```json
{
  "status": "ready",
  "services": {
    "database": {"status": "healthy", "latency_ms": 3.1},
    "redis": {"status": "healthy", "latency_ms": 2.4},
    "celery_broker": {"status": "healthy", "transport": "redis"},
    "openhands": {"status": "healthy", "server_url": "http://localhost:8010"}
  },
  "runtime": {
    "backend": "openhands",
    "openrouter_configured": true,
    "openhands_api_key_configured": false
  }
}
```
### 4) Artifact List (staff-global)
`GET /api/v1/control-center/artifacts/`
Filters:
1. `generation_id`
2. `artifact_type`
3. `search`
4. pagination
### 5) Artifact Download
`GET /api/v1/control-center/artifacts/<artifact_id>/download/`
Rules:
1. Staff-only.
2. Resolve via configured storage backend.
3. Return safe file response.
4. Block path traversal.
5. Return 404 if missing.
---
## Backend Security Rules
1. Reuse `IsStaffControlCenterUser` permission for all CC-02 endpoints.
2. Never serialize API keys, tokens, database URLs, or broker URLs with credentials.
3. Artifact download must validate record-backed storage key, not arbitrary path input.
4. Keep all detail endpoints read-only in CC-02.
---
## Backend Performance Rules
1. Use `select_related` and `prefetch_related` in detail endpoints.
2. Keep pagination on artifact list.
3. Avoid N+1 queries in nested step/run serialization.
---
## Frontend Scope
Extend existing frontend app under `frontend/`.
Add routes:
1. `/generations/:generationId`
2. `/agent-runs/:runId`
3. `/runtime-health`
4. `/artifacts`
Add pages:
1. `GenerationDetailPage.tsx`
2. `AgentRunDetailPage.tsx`
3. `RuntimeHealthPage.tsx`
4. `ArtifactsPage.tsx`
Add feature API/type files accordingly.
---
## Frontend Generation Detail Page Requirements
Display:
1. Generation header with status badge.
2. Full prompt.
3. Status timeline/timestamps.
4. Steps table.
5. Run summary per step.
6. Workspace card.
7. Artifacts card.
8. Failure diagnostics.
9. Live events panel.
Live events panel:
1. Subscribe to `ws/v1/events/<generation_id>/`.
2. Append incoming normalized events.
3. Distinguish event types visually.
4. Show connection state.
5. Handle disconnect/reconnect gracefully.
---
## Frontend Agent Run Detail Page Requirements
Display:
1. Run status.
2. Runtime/model/session IDs.
3. Full prompt block.
4. Full output block.
5. Token usage viewer.
6. Failure category + details.
7. Start/end/duration metrics.
8. Link back to generation detail.
---
## Frontend Runtime Health Page Requirements
Display:
1. Overall health status.
2. Database health.
3. Redis health.
4. Celery broker health.
5. OpenHands server health.
6. Runtime backend config.
7. OpenRouter configured indicator.
States:
1. Loading
2. Error
3. Degraded
4. Healthy
---
## Frontend Artifacts Page Requirements
Display:
1. Paginated artifacts table.
2. Type filter.
3. Search.
4. Generation linkage.
5. File name/type/size/checksum.
6. Download button bound to staff-authenticated endpoint.
---
## Testing Requirements
### Backend tests
Add tests for:
1. Staff-only permission boundary on all new endpoints.
2. Generation detail returns nested expected structure.
3. Run detail returns expected diagnostics fields.
4. Health endpoint excludes secrets.
5. Artifact list pagination/filtering.
6. Artifact download happy path.
7. Artifact download missing file path (404).
### Frontend verification
1. Build passes (`npm run build`).
2. Route guard still blocks non-staff.
3. Detail pages render loading/error/empty/success states.
4. Live event panel can connect and render incoming items.
---
## Verification Commands
Backend:
```text
python -m pytest
```
Frontend:
```text
npm run build
```
Optional endpoint checks:
1. `/api/v1/control-center/generations/<id>/`
2. `/api/v1/control-center/runs/<id>/`
3. `/api/v1/control-center/health/`
4. `/api/v1/control-center/artifacts/`
---
## Acceptance Criteria
CC-02 is complete when:
1. All five CC-02 endpoints exist and are staff-only.
2. Generation detail page is functional and populated from API.
3. Agent run detail page is functional and populated from API.
4. Runtime health page is functional and safe.
5. Artifacts page and download action are functional.
6. Live event timeline works on generation detail.
7. No secret values are exposed.
8. Backend tests pass.
9. Frontend build passes.
10. No runtime execution architecture changes were introduced.
---
## Deferred To CC-02b or CC-03
1. Retry action endpoint.
2. Cancel generation endpoint from Control Center.
3. Manual run control operations.
4. Advanced audit history UI.
5. Planner/Coordinator/Feature Discovery modules.
---
## Commit Message
Use:
`phase-04-6: add control center detail, health, artifacts, and live monitoring`
