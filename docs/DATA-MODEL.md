# DATA-MODEL.md — Tersuite AI Studio Domain Data Model Specification

## 1. Entity-Relationship Overview

The Phase 2 durable domain architecture organizes multi-agent WordPress plugin engineering into a strict, user-scoped hierarchical tree:

```
┌─────────────────────────────────────────────────────────────┐
│                            User                             │
│                  (Custom UUID Auth Model)                   │
└──────────────────────────────┬──────────────────────────────┘
                               │ 1:N
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                           Project                           │
│              (WordPress Target, Slugs & Config)             │
└──────────────────────────────┬──────────────────────────────┘
                               │ 1:N
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                         Generation                          │
│          (Lifecycle State Machine, Prompt, Audit)           │
└──────────────┬──────────────────────────────┬───────────────┘
               │ 1:N                          │ 1:1
               ▼                              ▼
┌─────────────────────────────┐┌──────────────────────────────┐
│       GenerationStep        ││          Workspace           │
│   (Logical Work Unit/Spec)  ││   (Mounted Working Dir)      │
└──────────────┬──────────────┘└──────────────────────────────┘
               │ 1:N
               ▼
┌─────────────────────────────┐
│          AgentRun           │
│   (Physical Attempt/SDK)    │
└──────────────┬──────────────┘
               │ 1:N
               ▼
┌─────────────────────────────┐
│          Artifact           │
│  (Durable Files & Packages) │
└─────────────────────────────┘
```

---

## 2. Table Specifications & Schema Definitions

### 2.1. `accounts_user`
- **Model**: `apps.accounts.models.User`
- **Inheritance**: `AbstractBaseUser`, `PermissionsMixin`, `TimeStampedModel`

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | No | `uuid4()` | Primary Key (UUIDv4) |
| `email` | `VARCHAR(255)` | No | — | Unique login email address (Indexed) |
| `password` | `VARCHAR(128)` | No | — | Salted argon2/bcrypt password hash |
| `first_name` | `VARCHAR(150)` | Yes | `""` | User given name |
| `last_name` | `VARCHAR(150)` | Yes | `""` | User surname |
| `is_active` | `BOOLEAN` | No | `True` | Account activity flag |
| `is_staff` | `BOOLEAN` | No | `False` | Staff admin privilege flag |
| `is_superuser`| `BOOLEAN` | No | `False` | Superuser privilege flag |
| `date_joined` | `TIMESTAMPTZ` | No | `now()` | Registration timestamp |
| `created_at` | `TIMESTAMPTZ` | No | `now()` | Entity creation timestamp (Indexed) |
| `updated_at` | `TIMESTAMPTZ` | No | `now()` | Entity modification timestamp |

---

### 2.2. `projects_project`
- **Model**: `apps.projects.models.Project`
- **Inheritance**: `TimeStampedModel`

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | No | `uuid4()` | Primary Key (UUIDv4) |
| `user_id` | `UUID` | No | — | Foreign Key $\rightarrow$ `accounts_user.id` (ON DELETE CASCADE) |
| `name` | `VARCHAR(255)` | No | — | Human-readable project name (Indexed) |
| `slug` | `VARCHAR(255)` | No | — | URL-safe slug (Unique per user) |
| `description` | `TEXT` | No | `""` | High-level requirements summary |
| `plugin_slug` | `VARCHAR(100)` | No | `""` | WordPress plugin folder slug |
| `wordpress_version` | `VARCHAR(20)` | No | `"6.7"` | Target WordPress version |
| `php_version` | `VARCHAR(20)` | No | `"8.2"` | Target PHP runtime version |
| `metadata` | `JSONB` | No | `{}` | Tags, preferences, and custom config |
| `is_archived` | `BOOLEAN` | No | `False` | Soft-archival flag (Indexed) |
| `created_at` | `TIMESTAMPTZ` | No | `now()` | Entity creation timestamp |
| `updated_at` | `TIMESTAMPTZ` | No | `now()` | Entity modification timestamp |

**Constraints**:
- `UniqueConstraint(fields=["user", "slug"], name="unique_user_project_slug")`

---

### 2.3. `generations_generation`
- **Model**: `apps.generations.models.Generation`
- **Inheritance**: `TimeStampedModel`

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | No | `uuid4()` | Primary Key (UUIDv4) |
| `project_id` | `UUID` | No | — | Foreign Key $\rightarrow$ `projects_project.id` (ON DELETE CASCADE) |
| `user_id` | `UUID` | No | — | Foreign Key $\rightarrow$ `accounts_user.id` (ON DELETE CASCADE) |
| `prompt` | `TEXT` | No | — | User prompt / initial instructions |
| `status` | `VARCHAR(30)` | No | `"DRAFT"` | Lifecycle state machine status (Indexed) |
| `current_step_number` | `INTEGER` | No | `0` | Active step sequence index |
| `total_steps` | `INTEGER` | No | `0` | Total planned milestone count |
| `metadata` | `JSONB` | No | `{}` | State audit history & agent flags |
| `error_message` | `TEXT` | No | `""` | Diagnostic error message on failure |
| `failure_category` | `VARCHAR(50)` | No | `""` | Classified failure category |
| `completed_at` | `TIMESTAMPTZ` | Yes | `NULL` | Timestamp of packaging completion |
| `failed_at` | `TIMESTAMPTZ` | Yes | `NULL` | Timestamp of fatal error termination |
| `cancelled_at` | `TIMESTAMPTZ` | Yes | `NULL` | Timestamp of user/agent cancellation |
| `paused_at` | `TIMESTAMPTZ` | Yes | `NULL` | Timestamp when generation was paused |
| `created_at` | `TIMESTAMPTZ` | No | `now()` | Entity creation timestamp |
| `updated_at` | `TIMESTAMPTZ` | No | `now()` | Entity modification timestamp |

**Indexes**:
- `Index(fields=["project", "status"])`
- `Index(fields=["user", "status"])`

---

### 2.4. `generations_generationstep`
- **Model**: `apps.generations.models.GenerationStep`
- **Inheritance**: `TimeStampedModel`

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | No | `uuid4()` | Primary Key (UUIDv4) |
| `generation_id` | `UUID` | No | — | Foreign Key $\rightarrow$ `generations_generation.id` (ON DELETE CASCADE) |
| `step_number` | `INTEGER` | No | — | Order index in generation sequence (1-indexed) |
| `name` | `VARCHAR(255)` | No | — | Step name (e.g. "Architecture Blueprint") |
| `agent_role` | `VARCHAR(100)` | No | — | Agent domain role (e.g. "architect", "coder") |
| `status` | `VARCHAR(30)` | No | `"PENDING"` | Step execution status (Indexed) |
| `input_payload` | `JSONB` | No | `{}` | Input contracts / prompt context |
| `output_payload` | `JSONB` | No | `{}` | Output data / specifications generated |
| `error_message` | `TEXT` | No | `""` | Step error details on failure |
| `started_at` | `TIMESTAMPTZ` | Yes | `NULL` | Execution start timestamp |
| `completed_at` | `TIMESTAMPTZ` | Yes | `NULL` | Execution finish timestamp |
| `created_at` | `TIMESTAMPTZ` | No | `now()` | Entity creation timestamp |
| `updated_at` | `TIMESTAMPTZ` | No | `now()` | Entity modification timestamp |

**Constraints**:
- `UniqueConstraint(fields=["generation", "step_number"], name="unique_generation_step_number")`

---

### 2.5. `generations_agentrun`
- **Model**: `apps.generations.models.AgentRun`
- **Inheritance**: `TimeStampedModel`

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | No | `uuid4()` | Primary Key (UUIDv4) |
| `step_id` | `UUID` | No | — | Foreign Key $\rightarrow$ `generations_generationstep.id` (ON DELETE CASCADE) |
| `run_number` | `INTEGER` | No | `1` | Attempt index (1, 2, 3...) |
| `runtime_type` | `VARCHAR(50)` | No | `"openhands"` | Runtime engine ("openhands" / "mock") |
| `session_id` | `VARCHAR(255)` | No | `""` | TersuiteAgentRuntime session ID (Indexed) |
| `remote_conversation_id` | `VARCHAR(255)` | No | `""` | OpenHands RemoteConversation UUID (Indexed) |
| `status` | `VARCHAR(30)` | No | `"QUEUED"` | Execution status (`QUEUED`, `RUNNING`, `COMPLETED`, `FAILED`, `CANCELLED`, `TIMED_OUT`) |
| `model_name` | `VARCHAR(150)` | No | `""` | LLM model identifier |
| `prompt` | `TEXT` | No | — | Full prompt passed to agent |
| `output` | `TEXT` | No | `""` | Raw agent output text |
| `token_usage` | `JSONB` | No | `{}` | Token metrics (prompt, completion, total) |
| `failure_category` | `VARCHAR(50)` | No | `""` | Failure classification code |
| `error_details` | `JSONB` | No | `{}` | Structured stack trace / debug details |
| `started_at` | `TIMESTAMPTZ` | Yes | `NULL` | Run start timestamp |
| `completed_at` | `TIMESTAMPTZ` | Yes | `NULL` | Run completion timestamp |
| `created_at` | `TIMESTAMPTZ` | No | `now()` | Entity creation timestamp |
| `updated_at` | `TIMESTAMPTZ` | No | `now()` | Entity modification timestamp |

**Constraints**:
- `UniqueConstraint(fields=["step", "run_number"], name="unique_step_run_number")`

---

### 2.6. `generations_workspace`
- **Model**: `apps.generations.models.Workspace`
- **Inheritance**: `TimeStampedModel`

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | No | `uuid4()` | Primary Key (UUIDv4) |
| `generation_id` | `UUID` | No | — | OneToOne $\rightarrow$ `generations_generation.id` (ON DELETE CASCADE) |
| `workspace_path` | `VARCHAR(512)` | No | — | Relative workspace storage path |
| `storage_type` | `VARCHAR(50)` | No | `"LOCAL"` | Storage backend (`LOCAL`, `EPHEMERAL_CONTAINER`, `REMOTE_STORAGE`) |
| `is_active` | `BOOLEAN` | No | `True` | Whether directory is mounted / available |
| `disk_usage_bytes` | `BIGINT` | No | `0` | Space consumption in bytes |
| `metadata` | `JSONB` | No | `{}` | Container IDs, mount metadata |
| `created_at` | `TIMESTAMPTZ` | No | `now()` | Entity creation timestamp |
| `updated_at` | `TIMESTAMPTZ` | No | `now()` | Entity modification timestamp |

---

### 2.7. `generations_artifact`
- **Model**: `apps.generations.models.Artifact`
- **Inheritance**: `TimeStampedModel`

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | No | `uuid4()` | Primary Key (UUIDv4) |
| `generation_id` | `UUID` | No | — | Foreign Key $\rightarrow$ `generations_generation.id` (ON DELETE CASCADE) |
| `agent_run_id` | `UUID` | Yes | `NULL` | Foreign Key $\rightarrow$ `generations_agentrun.id` (ON DELETE SET NULL) |
| `name` | `VARCHAR(255)` | No | — | Human-readable filename (Indexed) |
| `file_path` | `VARCHAR(512)` | No | — | Relative path within plugin directory scaffold |
| `artifact_type` | `VARCHAR(50)` | No | `"SOURCE_CODE"` | Type (`SOURCE_CODE`, `CONFIGURATION`, `TEST_REPORT`, `DOCUMENTATION`, `ZIP_ARCHIVE`, `SECURITY_REPORT`, `OTHER`) |
| `mime_type` | `VARCHAR(100)` | No | `"text/plain"` | MIME content type |
| `size_bytes` | `BIGINT` | No | `0` | File size in bytes |
| `checksum_sha256` | `VARCHAR(64)` | No | `""` | SHA-256 integrity hash |
| `storage_backend` | `VARCHAR(50)` | No | `"local_filesystem"` | Storage backend driver |
| `storage_key` | `VARCHAR(512)` | No | — | Lookup URI / key in storage |
| `metadata` | `JSONB` | No | `{}` | Syntax validity, LOC, audit flags |
| `created_at` | `TIMESTAMPTZ` | No | `now()` | Entity creation timestamp |
| `updated_at` | `TIMESTAMPTZ` | No | `now()` | Entity modification timestamp |

**Indexes**:
- `Index(fields=["generation", "artifact_type"])`

---

## 3. Generation State Machine & Transitions

```
                    ┌──────────────┐
                    │    DRAFT     │
                    └──────┬───────┘
                           │
                           ▼
                    ┌──────────────┐
                    │SPECIFICATION │
                    └──────┬───────┘
                           │
                           ▼
                    ┌──────────────┐
                    │   APPROVED   │
                    └──────┬───────┘
                           │
                           ▼
                    ┌──────────────┐◄──────────────┐ (Retrying)
                    │   PLANNING   │               │
                    └──────┬───────┘               │
                           │                       │
                           ▼                       │
         ┌─────────►┌──────────────┐               │
         │ (Repair) │   BUILDING   │               │
         │          └──────┬───────┘               │
         │                 │                       │
         │                 ▼                       │
         ├──────────┌──────────────┐               │
         │ (Repair) │   TESTING    │               │
         │          └──────┬───────┘               │
         │                 │                       │
         │                 ▼                       │
         └──────────┌──────────────┐               │
                    │    REVIEW    │               │
                    └──────┬───────┘               │
                           │                       │
                           ▼                       │
                    ┌──────────────┐               │
                    │  PACKAGING   │               │
                    └──────┬───────┘               │
                           │                       │
                           ▼                       │
                    ┌──────────────┐        ┌──────┴───────┐
                    │  COMPLETED   │        │   RETRYING   │
                    └──────────────┘        └──────▲───────┘
                                                   │
     Control States:                               │
     [Any Active Phase] ──► PAUSED ──► Resumed ────┤
     [Any Active Phase] ──► FAILED ──► [Retry] ────┘
     [Any State]        ──► CANCELLED
```

---

## 4. Artifact Storage Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Artifact Storage Layer                   │
└──────────────────────────────┬──────────────────────────────┘
                               │
               ┌───────────────┴───────────────┐
               ▼                               ▼
┌─────────────────────────────┐ ┌─────────────────────────────┐
│ LocalFileSystemStorage      │ │   Future Cloud Storage      │
│ (MEDIA_ROOT/artifacts/...)  │ │       (S3 / GCS)            │
└─────────────────────────────┘ └─────────────────────────────┘
```

The pluggable `ArtifactStorageBackend` abstraction manages all file binary I/O, generating cryptographic SHA-256 checksums on save and decoupling the Django database models from filesystem specifics.
