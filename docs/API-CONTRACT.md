# API-CONTRACT.md — Tersuite AI Studio REST API Contract (v1)

## 1. Authentication & Common Headers

All private API requests require token-based authentication obtained from `/api/v1/auth/login/` or `/api/v1/auth/register/`.

```http
Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b
X-Tersuite-Organization-ID: d6ade252-754f-43fa-9bc3-88598f0e2114
Content-Type: application/json
Accept: application/json
```

### Organization Context Header (`X-Tersuite-Organization-ID`)
- **Single active membership**: If the authenticated user belongs to exactly one active organization, the header is optional and defaults safely to that organization.
- **Multiple active memberships**: The header `X-Tersuite-Organization-ID` is **required**. Omitting it returns `400 Bad Request` (`organization_context_required`).
- **Invalid UUID**: Returns `400 Bad Request` (`invalid_organization_context`).
- **Non-member / Inactive Organization**: Returns `404 Not Found` (`organization_not_found`).

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

## 2. Organizations API (`/api/v1/organizations/`)

### 2.1. List Organizations
- **Endpoint**: `GET /api/v1/organizations/`
- **Response**: `200 OK` (list of organizations where the user is an active member)

### 2.2. Create Organization
- **Endpoint**: `POST /api/v1/organizations/`
- **Payload**:
  ```json
  {
    "name": "Acme Plugin Studio",
    "slug": "acme-plugin-studio"
  }
  ```
- **Response**: `201 Created` (creator automatically assigned `OWNER` role)

### 2.3. Organization Memberships (`/api/v1/organizations/{id}/members/`)
- **List Members**: `GET /api/v1/organizations/{id}/members/`
- **Add Member**: `POST /api/v1/organizations/{id}/members/`
  - Payload: `{"email": "collaborator@example.com", "role": "MEMBER"}`
- **Update Member Role**: `PATCH /api/v1/organizations/{id}/members/{membership_id}/`
  - Payload: `{"role": "ADMIN"}`
- **Remove Member**: `DELETE /api/v1/organizations/{id}/members/{membership_id}/`

---

## 3. Products API (`/api/v1/products/`)

> **Governed Product Lifecycle**: WordPress products are provisioned automatically through the Project service. Direct creation (`POST /api/v1/products/`), root deletion (`DELETE /api/v1/products/{id}/`), and full replacement (`PUT /api/v1/products/{id}/`) are disallowed and return `405 Method Not Allowed`.

### 3.1. List Products
- **Endpoint**: `GET /api/v1/products/`
- **Query Parameters**: `kind`, `is_archived`, `search`
- **Response**: `200 OK`

### 3.2. Retrieve Product Detail
- **Endpoint**: `GET /api/v1/products/{id}/`
- **Response**: `200 OK` (includes nested `plugin_target`)

### 3.3. Update Product
- **Endpoint**: `PATCH /api/v1/products/{id}/`
- **Payload**:
  ```json
  {
    "display_name": "Updated Plugin Name",
    "is_archived": false
  }
  ```
- **Response**: `200 OK`

---

## 4. WordPress Sites API (`/api/v1/sites/`)

### 4.1. List & Create Sites
- **Endpoint**: `GET /api/v1/sites/`
- **Endpoint**: `POST /api/v1/sites/`
- **Payload**:
  ```json
  {
    "name": "Staging Store",
    "url": "https://staging.example.com",
    "environment": "STAGING",
    "metadata": {"hosting": "Cloudways"}
  }
  ```
- **Response**: `201 Created` (Secret keys in metadata are rejected with `400 Bad Request`)

### 4.2. Site Profile Snapshots (`/api/v1/sites/{site_id}/profiles/`)
- **List Snapshots**: `GET /api/v1/sites/{site_id}/profiles/`
- **Retrieve Snapshot**: `GET /api/v1/sites/{site_id}/profiles/{snapshot_id}/`
- **Record Snapshot**: `POST /api/v1/sites/{site_id}/profiles/`
- **Payload**:
  ```json
  {
    "wordpress_version": "6.7.1",
    "php_version": "8.3.0",
    "multisite": false,
    "locale": "en_US",
    "active_theme": {"name": "Astra", "version": "4.6.0"},
    "active_plugins": [{"name": "WooCommerce", "version": "9.4.0"}],
    "server": {"web_server": "nginx/1.24"},
    "capabilities": {},
    "health": {}
  }
  ```
- **Response**: `201 Created` (immutable snapshot with sequential version and SHA-256 checksum)

---

## 5. Projects API (`/api/v1/projects/`)

### 5.1. List & Create Projects
- **Endpoint**: `GET /api/v1/projects/`
- **Endpoint**: `POST /api/v1/projects/`
- **Payload**:
  ```json
  {
    "name": "WordPress Stripe Connect",
    "slug": "wp-stripe-connect",
    "description": "Marketplace split payment gateway.",
    "wordpress_version": "6.7",
    "php_version": "8.2",
    "metadata": {"preferred_currency": "USD"}
  }
  ```
- **Response**: `201 Created` (automatically provisions underlying `WordPressProduct` and `PluginTarget`)

### 5.2. Root Project Deletion Disallowed
- Root `DELETE /api/v1/projects/{id}/` returns `405 Method Not Allowed`. Projects are archived via `/archive/`.

### 5.3. Link Sites to Project (`/api/v1/projects/{id}/sites/`)
- **List Attached Sites**: `GET /api/v1/projects/{id}/sites/`
- **Attach Site**: `POST /api/v1/projects/{id}/sites/`
  - Payload: `{"site_id": "<uuid>", "purpose": "PRIMARY"}`
- **Retrieve Attached Site**: `GET /api/v1/projects/{id}/sites/{project_site_id}/`
- **Detach Site**: `DELETE /api/v1/projects/{id}/sites/{project_site_id}/`

---

## 6. Conversations API (`/api/v1/conversations/`)

### 6.1. List & Create Conversations
- **Endpoint**: `GET /api/v1/conversations/`
- **Endpoint**: `POST /api/v1/conversations/`
- **Payload**:
  ```json
  {
    "project_id": "<project-uuid>",
    "title": "Architecture Discussions",
    "purpose": "PROJECT_PLANNING"
  }
  ```
- **Response**: `201 Created`

### 6.2. Append Conversation Message (Idempotent)
- **Endpoint**: `POST /api/v1/conversations/{id}/messages/`
- **Payload**:
  ```json
  {
    "content": "Please design the referral cookie attribution handler.",
    "client_message_id": "41699990-28b3-469b-8106-d7b1b369528d",
    "content_format": "MARKDOWN"
  }
  ```
- **Response**:
  - `201 Created` with `idempotent_replay: false` on first submission
  - `200 OK` with `idempotent_replay: true` on duplicate `client_message_id` submission

### 6.3. Retrieve Messages (Append-Only)
- **Endpoint**: `GET /api/v1/conversations/{id}/messages/`
- **Response**: `200 OK` (ordered by monotonic sequence number)

### 6.4. Archive Conversation
- **Endpoint**: `POST /api/v1/conversations/{id}/archive/`
- **Response**: `200 OK` (locks conversation against further message insertion)

---

## 7. Generations API (`/api/v1/generations/`)

> **Durable Generation Retention**: Generation records cannot be deleted via the public REST API (`DELETE /api/v1/generations/{id}/` returns `405 Method Not Allowed`). All generation history remains durable.

### 7.1. List Generations
- **Endpoint**: `GET /api/v1/generations/`
- **Query Parameters**: `project_id`, `status`
- **Response**: `200 OK`

### 7.2. Create Generation
- **Endpoint**: `POST /api/v1/generations/`
- **Payload**:
  ```json
  {
    "project_id": "b1f844b2-9213-4c9f-8547-0b19280d8291",
    "prompt": "Build a WooCommerce affiliate marketing plugin with multi-tier commissions.",
    "spec_version": "1.0.0",
    "plan_version": "1.0.0",
    "metadata": {}
  }
  ```
- **Response**: `201 Created` (auto-initializes `Workspace` record and sets status to `DRAFT`)

### 7.3. Retrieve Generation Detail
- **Endpoint**: `GET /api/v1/generations/{id}/`
- **Response**: `200 OK` (includes nested `steps`, `workspace`, and `artifacts`)

### 7.4. State Machine Transition & Coordinator Gate
- **Endpoint**: `POST /api/v1/generations/{id}/transition/`
- **Protection**: Direct forward progression from the client is protected and requires the backend workflow coordinator (`409 Conflict` with code `direct_transition_requires_coordinator`). Use idempotent control commands (`pause/`, `resume/`, `cancel/`, `retry/`) instead.

### 7.5. Idempotent Generation Control Commands
All control commands accept an optional `Idempotency-Key` request header (or generate a UUID key) and ensure exactly-once execution semantics with cached idempotent replaying.

- **Pause Generation**: `POST /api/v1/generations/{id}/pause/`
  - Payload: `{"reason": "Pausing for user review"}`
  - Response: `200 OK` (sets `status=PAUSED`, records prior state in `resume_status`)
- **Resume Generation**: `POST /api/v1/generations/{id}/resume/`
  - Payload: `{"reason": "Resuming generation"}`
  - Response: `200 OK` (restores state from `resume_status`)
- **Cancel Generation**: `POST /api/v1/generations/{id}/cancel/`
  - Payload: `{"reason": "User requested cancellation"}`
  - Response: `200 OK` (moves through `CANCELLING` to terminal `CANCELLED`)
- **Retry Generation**: `POST /api/v1/generations/{id}/retry/`
  - Payload: `{"reason": "Operator retry"}`
  - Response: `200 OK` (transitions recoverable failures back to `SCHEDULED`)

---

## 8. Workflows API (`/api/v1/`)

All workflows inspection endpoints are tenant-isolated and strictly read-only (`GET` only; mutation methods return `405 Method Not Allowed`).

### 8.1. List Workflow Runs
- **Endpoint**: `GET /api/v1/workflow-runs/`
- **Query Parameters**: `generation_id`, `status`
- **Response**: `200 OK`

### 8.2. Retrieve Workflow Run Detail
- **Endpoint**: `GET /api/v1/workflow-runs/{id}/`
- **Response**: `200 OK` (includes DAG topology and summary counts)

### 8.3. List Work Packages
- **Endpoint**: `GET /api/v1/work-packages/`
- **Query Parameters**: `workflow_run_id`, `status`, `agent_role`
- **Response**: `200 OK`

### 8.4. Retrieve Work Package Detail
- **Endpoint**: `GET /api/v1/work-packages/{id}/`
- **Response**: `200 OK` (includes dependencies and active lease info)

### 8.5. List Work Package Attempts
- **Endpoint**: `GET /api/v1/work-packages/{id}/attempts/`
- **Response**: `200 OK` (ordered by `attempt_number` ascending)

