# API-CONTRACT.md — Tersuite AI Studio REST API Contract (v1)

## 1. Authentication & Common Headers

All private API requests require token-based authentication obtained from `/api/v1/auth/login/` or `/api/v1/auth/register/`.

```http
Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b
Content-Type: application/json
Accept: application/json
```

### Standard Error Response Format

```json
{
  "error": {
    "code": "invalid_state_transition",
    "message": "Cannot transition generation from 'DRAFT' to 'BUILDING'.",
    "status_code": 400,
    "details": {
      "current_status": "DRAFT",
      "target_status": "BUILDING"
    }
  }
}
```

---

## 2. Projects API (`/api/v1/projects/`)

### 2.1. List Projects
- **Endpoint**: `GET /api/v1/projects/`
- **Query Parameters**:
  - `archived`: `true` or `false`
  - `search`: search substring in project name
- **Response**: `200 OK`
  ```json
  [
    {
      "id": "b1f844b2-9213-4c9f-8547-0b19280d8291",
      "user_id": "4fa85f64-5717-4562-b3fc-2c963f66afa6",
      "name": "WooCommerce Affiliate Pro",
      "slug": "woocommerce-affiliate-pro",
      "description": "Multi-tier affiliate tracking plugin.",
      "plugin_slug": "woocommerce-affiliate-pro",
      "wordpress_version": "6.7",
      "php_version": "8.2",
      "metadata": {},
      "is_archived": false,
      "generations_count": 2,
      "created_at": "2026-08-15T00:30:00Z",
      "updated_at": "2026-08-15T00:30:00Z"
    }
  ]
  ```

### 2.2. Create Project
- **Endpoint**: `POST /api/v1/projects/`
- **Payload**:
  ```json
  {
    "name": "WordPress Stripe Connect",
    "description": "Marketplace split payment gateway.",
    "wordpress_version": "6.7",
    "php_version": "8.2",
    "metadata": {"preferred_currency": "USD"}
  }
  ```
- **Response**: `201 Created` (returns created Project)

### 2.3. Retrieve Project
- **Endpoint**: `GET /api/v1/projects/{id}/`
- **Response**: `200 OK`

### 2.4. Update Project
- **Endpoint**: `PATCH /api/v1/projects/{id}/`
- **Payload**: `{"description": "Updated project description."}`
- **Response**: `200 OK`

### 2.5. Archive / Unarchive Project
- **Endpoint**: `POST /api/v1/projects/{id}/archive/`
- **Endpoint**: `POST /api/v1/projects/{id}/unarchive/`
- **Response**: `200 OK`

---

## 3. Generations API (`/api/v1/generations/`)

### 3.1. List Generations
- **Endpoint**: `GET /api/v1/generations/`
- **Query Parameters**:
  - `project_id`: filter by project UUID
  - `status`: filter by status (`DRAFT`, `BUILDING`, `COMPLETED`, etc.)
- **Response**: `200 OK`
  ```json
  [
    {
      "id": "7fa85f64-5717-4562-b3fc-2c963f66afa7",
      "project": "b1f844b2-9213-4c9f-8547-0b19280d8291",
      "project_name": "WooCommerce Affiliate Pro",
      "user": "4fa85f64-5717-4562-b3fc-2c963f66afa6",
      "prompt": "Build a custom affiliate tracking plugin.",
      "status": "DRAFT",
      "current_step_number": 0,
      "total_steps": 6,
      "steps_count": 0,
      "artifacts_count": 0,
      "failure_category": "",
      "error_message": "",
      "created_at": "2026-08-15T00:31:00Z",
      "updated_at": "2026-08-15T00:31:00Z",
      "completed_at": null,
      "failed_at": null,
      "cancelled_at": null,
      "paused_at": null
    }
  ]
  ```

### 3.2. Create Generation
- **Endpoint**: `POST /api/v1/generations/`
- **Payload**:
  ```json
  {
    "project_id": "b1f844b2-9213-4c9f-8547-0b19280d8291",
    "prompt": "Build an affiliate referral plugin with shortcodes.",
    "metadata": {"priority": "high"}
  }
  ```
- **Response**: `201 Created` (auto-creates workspace)

### 3.3. Retrieve Generation Details
- **Endpoint**: `GET /api/v1/generations/{id}/`
- **Response**: `200 OK` (includes nested `steps`, `workspace`, and `artifacts`)

### 3.4. State Transitions
- **Endpoint**: `POST /api/v1/generations/{id}/transition/`
- **Payload**:
  ```json
  {
    "target_status": "SPECIFICATION",
    "reason": "Feature discovery concluded.",
    "metadata": {"discovered_features_count": 42}
  }
  ```
- **Response**: `200 OK` on success, `400 Bad Request` if transition is invalid.

### 3.5. Pause / Cancel / Retry Actions
- `POST /api/v1/generations/{id}/pause/`
- `POST /api/v1/generations/{id}/cancel/`
- `POST /api/v1/generations/{id}/retry/`

---

## 4. Generation Steps API (`/api/v1/steps/`)

### 4.1. List Steps
- **Endpoint**: `GET /api/v1/steps/?generation_id={generation_id}`
- **Response**: `200 OK` (includes nested `runs`)

### 4.2. Retrieve Step
- **Endpoint**: `GET /api/v1/steps/{id}/`
- **Response**: `200 OK`

---

## 5. Agent Runs API (`/api/v1/runs/`)

### 5.1. List Runs
- **Endpoint**: `GET /api/v1/runs/?step_id={step_id}`
- **Response**: `200 OK`
  ```json
  [
    {
      "id": "e4a85f64-5717-4562-b3fc-2c963f66afb1",
      "step": "c3a85f64-5717-4562-b3fc-2c963f66afb0",
      "run_number": 1,
      "runtime_type": "openhands",
      "session_id": "oh-sess-8f7e6d5c4b3a",
      "remote_conversation_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "status": "COMPLETED",
      "model_name": "anthropic/claude-sonnet-4-5-20250929",
      "prompt": "Create WordPress schema migration.",
      "output": "Generated schema migration.",
      "token_usage": {"prompt_tokens": 850, "completion_tokens": 400, "total_tokens": 1250},
      "failure_category": "",
      "error_details": {},
      "started_at": "2026-08-15T00:32:00Z",
      "completed_at": "2026-08-15T00:32:15Z"
    }
  ]
  ```

---

## 6. Workspaces API (`/api/v1/workspaces/`)

### 6.1. Retrieve Workspace
- **Endpoint**: `GET /api/v1/workspaces/{id}/`
- **Endpoint**: `GET /api/v1/generations/{generation_id}/workspace/`
- **Response**: `200 OK`

---

## 7. Artifacts API (`/api/v1/artifacts/`)

### 7.1. List Artifacts
- **Endpoint**: `GET /api/v1/artifacts/?generation_id={generation_id}`
- **Response**: `200 OK`

### 7.2. Retrieve Artifact Metadata
- **Endpoint**: `GET /api/v1/artifacts/{id}/`
- **Response**: `200 OK`

### 7.3. Download Artifact
- **Endpoint**: `GET /api/v1/artifacts/{id}/download/`
- **Headers**:
  - `Content-Type`: MIME type of artifact (e.g. `application/x-php`, `application/zip`)
  - `Content-Disposition`: `attachment; filename="tersuite-affiliate.php"`
- **Response**: `200 OK` (binary stream)
