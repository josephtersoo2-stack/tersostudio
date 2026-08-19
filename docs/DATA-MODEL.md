# DATA-MODEL.md — Tersuite AI Studio Domain Data Model Specification

## 1. Entity-Relationship Overview

The Phase 2 durable domain architecture organizes multi-agent WordPress plugin engineering into a strict, organization-scoped hierarchical model:

```
┌─────────────────────────────────────────────────────────────┐
│                        Organization                         │
│               (Tenant Boundary, Slug, Audit)                │
└──────────────┬──────────────────────────────┬───────────────┘
               │ 1:N                          │ 1:N
               ▼                              ▼
┌─────────────────────────────┐┌──────────────────────────────┐
│   OrganizationMembership    ││       WordPressProduct       │
│      (Roles & Access)       ││ (kind=PLUGIN, versions, slug)│
└─────────────────────────────┘└──────────────┬───────────────┘
                                              │ 1:1
                                              ▼
                               ┌──────────────────────────────┐
                               │         PluginTarget         │
                               │  (plugin_slug, namespaces)   │
                               └──────────────┬───────────────┘
                                              │ 1:1
                                              ▼
┌─────────────────────────────┐┌──────────────────────────────┐
│        WordPressSite        ││           Project            │
│  (Metadata, Environment)    ││(Organization-owned Container)│
└──────────────┬──────────────┘└──────┬──────────────┬────────┘
               │ 1:N                  │              │ 1:N
               ▼                      │              ▼
┌─────────────────────────────┐       │┌──────────────────────────────┐
│     SiteProfileSnapshot     │       ││         Conversation         │
│  (Immutable, SHA256 Hash)   │       ││   (Message thread, Seq)      │
└─────────────────────────────┘       │└──────────────┬───────────────┘
               ▲                      │               │ 1:N
               │ 1:N                  │               ▼
┌──────────────┴──────────────┐       │┌──────────────────────────────┐
│         ProjectSite         │◀──────┘│     ConversationMessage      │
│ (Purpose: STAGING, DEV, etc)│        │   (Immutable, Idempotent)    │
└─────────────────────────────┘        └──────────────┬───────────────┘
                                                      │ 1:N
                                                      ▼
                                       ┌──────────────────────────────┐
                                       │          Generation          │
                                       │ (State Machine, Audited Org) │
                                       └──────┬──────────────┬────────┘
                                              │ 1:N          │ 1:1
                                              ▼              ▼
                               ┌─────────────────────┐┌────────────────┐
                               │   GenerationStep    ││   Workspace    │
                               │(Logical Work Unit)  ││  (Init Path)   │
                               └──────────┬──────────┘└────────────────┘
                                          │ 1:N
                                          ▼
                               ┌─────────────────────┐
                               │      AgentRun       │
                               │ (Runtime Execution) │
                               └──────────┬──────────┘
                                          │ 1:N
                                          ▼
                               ┌─────────────────────┐
                               │      Artifact       │
                               │ (Storage & Package) │
                               └─────────────────────┘
```

---

## 2. Core Domain Principles & Constraints

1. **Multi-Tenancy & Scoping**:
   - `Organization` is the mandatory security and persistence boundary for all core engineering resources.
   - All tenant models inherit from `OrganizationOwnedModel` (`organization`, `created_by`, `updated_by`).
   - Requests enforce tenant resolution via `X-Tersuite-Organization-ID` header or unambiguous single-membership default.

2. **WordPress Product Boundary**:
   - Technical plugin properties reside in `WordPressProduct` and `PluginTarget` models.
   - Only `kind="PLUGIN"` is supported in B2. Any attempt to create or generate `THEME` products is rejected at the validator and model layer.

3. **WordPress Site Security & Immutability**:
   - `WordPressSite` stores metadata only with URLs strictly normalized by `normalize_wordpress_url`.
   - Embedded secrets, passwords, tokens, and credentials in site metadata or snapshot payloads are prohibited and rejected by `validate_safe_json_object`.
   - `SiteProfileSnapshot` records are strictly immutable and verify payload integrity via deterministic SHA-256 checksums.

4. **Conversations & Message Ordering**:
   - `Conversation` threads maintain sequential message indexing (`next_message_sequence`).
   - `ConversationMessage` rows are immutable and support deterministic deduplication via `client_message_id`.

5. **Durable Generation Retention**:
   - Generation records cannot be deleted via the public REST API (`DELETE /api/v1/generations/{id}/` returns `405 Method Not Allowed`).
   - Generations transition to terminal states (`COMPLETED`, `CANCELLED`, `FAILED`) while preserving full step, run, and artifact provenance.

---

## 3. Table Specifications & Schema Definitions

### 3.1. `organizations_organization`
- **Model**: `apps.organizations.models.Organization`
- **Inheritance**: `TimeStampedModel`

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | No | `uuid4()` | Primary Key (UUIDv4) |
| `name` | `VARCHAR(255)` | No | — | Organization display name |
| `slug` | `VARCHAR(255)` | No | — | Unique URL-safe organization slug |
| `is_personal` | `BOOLEAN` | No | `False` | Whether this is a default user personal workspace |
| `is_active` | `BOOLEAN` | No | `True` | Active status flag |
| `created_by_id` | `UUID` | Yes | `NULL` | User who created the organization |
| `created_at` | `TIMESTAMPTZ` | No | `now()` | Record creation timestamp |
| `updated_at` | `TIMESTAMPTZ` | No | `now()` | Record update timestamp |

### 3.2. `organizations_organizationmembership`
- **Model**: `apps.organizations.models.OrganizationMembership`
- **Inheritance**: `TimeStampedModel`

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | No | `uuid4()` | Primary Key (UUIDv4) |
| `organization_id` | `UUID` | No | — | FK $\rightarrow$ `organizations_organization.id` |
| `user_id` | `UUID` | No | — | FK $\rightarrow$ `accounts_user.id` |
| `role` | `VARCHAR(20)` | No | `'MEMBER'` | Membership role (`OWNER`, `ADMIN`, `MEMBER`, `VIEWER`) |
| `is_active` | `BOOLEAN` | No | `True` | Active membership flag |

### 3.3. `products_wordpressproduct`
- **Model**: `apps.products.models.WordPressProduct`
- **Inheritance**: `OrganizationOwnedModel`

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | No | `uuid4()` | Primary Key (UUIDv4) |
| `organization_id` | `UUID` | No | — | FK $\rightarrow$ `organizations_organization.id` |
| `kind` | `VARCHAR(20)` | No | `'PLUGIN'` | Product kind (only `PLUGIN` allowed) |
| `display_name` | `VARCHAR(255)` | No | — | Human-readable product name |
| `slug` | `VARCHAR(255)` | No | — | Unique slug within organization |
| `version` | `VARCHAR(50)` | No | `'0.1.0'` | Semantic version |
| `wordpress_version` | `VARCHAR(50)` | No | `'6.7'` | Target WordPress Core version |
| `php_version` | `VARCHAR(50)` | No | `'8.2'` | Target PHP runtime version |
| `is_archived` | `BOOLEAN` | No | `False` | Soft-deletion flag |

### 3.4. `products_plugintarget`
- **Model**: `apps.products.models.PluginTarget`
- **Inheritance**: `TimeStampedModel`

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `product_id` | `UUID` | No | — | Primary Key / OneToOne $\rightarrow$ `products_wordpressproduct.id` |
| `plugin_slug` | `VARCHAR(255)` | No | — | WordPress plugin folder/slug |
| `text_domain` | `VARCHAR(255)` | No | — | Gettext translation text domain |
| `namespace_prefix` | `VARCHAR(255)` | No | — | Root PHP namespace prefix |
| `main_file` | `VARCHAR(255)` | No | — | Main plugin entrypoint PHP filename |

### 3.5. `sites_wordpresssite`
- **Model**: `apps.sites.models.WordPressSite`
- **Inheritance**: `OrganizationOwnedModel`

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | No | `uuid4()` | Primary Key (UUIDv4) |
| `organization_id` | `UUID` | No | — | FK $\rightarrow$ `organizations_organization.id` |
| `name` | `VARCHAR(255)` | No | — | Human-friendly site label |
| `url` | `VARCHAR(2048)` | No | — | Normalized base URL (credentials/queries stripped) |
| `environment` | `VARCHAR(20)` | No | `'DEVELOPMENT'` | Site environment (`DEVELOPMENT`, `STAGING`, `PRODUCTION`) |
| `connection_status` | `VARCHAR(20)` | No | `'DISCONNECTED'` | Remote status |
| `next_profile_version` | `INTEGER` | No | `1` | Monotonic profile snapshot counter |

### 3.6. `sites_siteprofilesnapshot`
- **Model**: `apps.sites.models.SiteProfileSnapshot`
- **Inheritance**: `OrganizationOwnedModel`

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | No | `uuid4()` | Primary Key (UUIDv4) |
| `organization_id` | `UUID` | No | — | FK $\rightarrow$ `organizations_organization.id` |
| `site_id` | `UUID` | No | — | FK $\rightarrow$ `sites_wordpresssite.id` |
| `version` | `INTEGER` | No | — | Snapshot version number |
| `source` | `VARCHAR(50)` | No | `'MANUAL'` | Profile acquisition source |
| `wordpress_version` | `VARCHAR(50)` | No | `""` | WordPress Core version |
| `php_version` | `VARCHAR(50)` | No | `""` | PHP version |
| `checksum_sha256` | `VARCHAR(64)` | No | — | Deterministic SHA-256 payload checksum |

---

## 4. B3 Workflow Kernel & Coordination Models

### 4.1. `generations_generationmilestone`
- **Model**: `apps.generations.models.GenerationMilestone`
- **Inheritance**: `OrganizationOwnedModel`

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | No | `uuid4()` | Primary Key (UUIDv4) |
| `organization_id` | `UUID` | No | — | FK $\rightarrow$ `organizations_organization.id` |
| `generation_id` | `UUID` | No | — | FK $\rightarrow$ `generations_generation.id` |
| `sequence` | `INTEGER` | No | — | Sequence order within generation |
| `name` | `VARCHAR(255)` | No | — | Milestone label |
| `status` | `VARCHAR(50)` | No | `'PENDING'` | Lifecycle status |

### 4.2. `generations_generationstatetransition`
- **Model**: `apps.generations.models.GenerationStateTransition`
- **Inheritance**: `models.Model` (Immutable Audit)

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | No | `uuid4()` | Primary Key (UUIDv4) |
| `generation_id` | `UUID` | No | — | FK $\rightarrow$ `generations_generation.id` |
| `sequence` | `INTEGER` | No | — | Monotonic sequence number |
| `from_status` | `VARCHAR(50)` | No | — | Prior state |
| `to_status` | `VARCHAR(50)` | No | — | New state |
| `command_id` | `UUID` | Yes | `NULL` | Optional triggering command |
| `created_at` | `TIMESTAMPTZ` | No | `now()` | Transition timestamp |

### 4.3. `workflows_workflowrun`
- **Model**: `apps.workflows.models.WorkflowRun`
- **Inheritance**: `OrganizationOwnedModel`

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | No | `uuid4()` | Primary Key (UUIDv4) |
| `organization_id` | `UUID` | No | — | FK $\rightarrow$ `organizations_organization.id` |
| `generation_id` | `UUID` | No | — | FK $\rightarrow$ `generations_generation.id` |
| `run_number` | `INTEGER` | No | `1` | Monotonic run number per generation |
| `status` | `VARCHAR(50)` | No | `'PENDING'` | Workflow run status |

### 4.4. `workflows_workpackage`
- **Model**: `apps.workflows.models.WorkPackage`
- **Inheritance**: `OrganizationOwnedModel`

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | No | `uuid4()` | Primary Key (UUIDv4) |
| `organization_id` | `UUID` | No | — | FK $\rightarrow$ `organizations_organization.id` |
| `workflow_run_id` | `UUID` | No | — | FK $\rightarrow$ `workflows_workflowrun.id` |
| `key` | `VARCHAR(100)` | No | — | Unique key within workflow run |
| `status` | `VARCHAR(50)` | No | `'PENDING'` | Package execution status |
| `max_attempts` | `INTEGER` | No | `3` | Maximum retry budget |
| `current_attempt_number` | `INTEGER` | No | `0` | Monotonic attempt counter |

### 4.5. `workflows_workpackagedependency`
- **Model**: `apps.workflows.models.WorkPackageDependency`
- **Inheritance**: `models.Model` (Immutable DAG Edge)

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | No | `uuid4()` | Primary Key (UUIDv4) |
| `workflow_run_id` | `UUID` | No | — | FK $\rightarrow$ `workflows_workflowrun.id` |
| `predecessor_id` | `UUID` | No | — | FK $\rightarrow$ `workflows_workpackage.id` |
| `successor_id` | `UUID` | No | — | FK $\rightarrow$ `workflows_workpackage.id` |
| `dependency_type` | `VARCHAR(50)` | No | `'REQUIRED'` | Edge rule (`REQUIRED`, `OPTIONAL`, `ON_FAILURE`) |

### 4.6. `workflows_workpackageattempt`
- **Model**: `apps.workflows.models.WorkPackageAttempt`
- **Inheritance**: `models.Model` (Append-Only Attempt History)

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | No | `uuid4()` | Primary Key (UUIDv4) |
| `work_package_id` | `UUID` | No | — | FK $\rightarrow$ `workflows_workpackage.id` |
| `attempt_number` | `INTEGER` | No | — | Monotonic attempt index |
| `worker_id` | `VARCHAR(255)` | No | — | Worker identifier |
| `status` | `VARCHAR(50)` | No | `'RUNNING'` | Attempt status |

### 4.7. `workflows_workpackagelease`
- **Model**: `apps.workflows.models.WorkPackageLease`
- **Inheritance**: `models.Model` (Active Worker Concurrency Fence)

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | No | `uuid4()` | Primary Key (UUIDv4) |
| `work_package_id` | `UUID` | No | — | FK $\rightarrow$ `workflows_workpackage.id` |
| `attempt_id` | `UUID` | No | — | FK $\rightarrow$ `workflows_workpackageattempt.id` |
| `worker_id` | `VARCHAR(255)` | No | — | Worker identity holding lease |
| `lease_token` | `UUID` | No | `uuid4()` | Opaque token for heartbeat/release |
| `acquired_at` | `TIMESTAMPTZ` | No | `now()` | Lease creation time |
| `expires_at` | `TIMESTAMPTZ` | No | — | Expiry threshold |
| `released_at` | `TIMESTAMPTZ` | Yes | `NULL` | Release timestamp |

### 4.8. `workflows_workflowcommand`
- **Model**: `apps.workflows.models.WorkflowCommand`
- **Inheritance**: `OrganizationOwnedModel` (Idempotency Ledger)

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | No | `uuid4()` | Primary Key (UUIDv4) |
| `organization_id` | `UUID` | No | — | FK $\rightarrow$ `organizations_organization.id` |
| `generation_id` | `UUID` | No | — | FK $\rightarrow$ `generations_generation.id` |
| `command_type` | `VARCHAR(50)` | No | — | Command type (`PAUSE`, `RESUME`, `CANCEL`, `RETRY`) |
| `idempotency_key` | `VARCHAR(255)` | No | — | Client or generated idempotency key |
| `request_hash` | `VARCHAR(64)` | No | — | SHA-256 hash of payload |
| `status` | `VARCHAR(50)` | No | `'APPLIED'` | Command execution outcome |
| `response_payload` | `JSONField` | No | `{}` | Cached response for replay |

### 4.9. `workflows_outboxevent`
- **Model**: `apps.workflows.models.OutboxEvent`
- **Inheritance**: `models.Model` (Transactional Outbox)

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `BIGSERIAL` | No | — | Auto-increment Primary Key |
| `event_id` | `UUID` | No | `uuid4()` | Stable unique event UUID |
| `organization_id` | `UUID` | No | — | FK $\rightarrow$ `organizations_organization.id` |
| `generation_id` | `UUID` | Yes | `NULL` | Optional FK $\rightarrow$ `generations_generation.id` |
| `aggregate_type` | `VARCHAR(100)` | No | — | Aggregate entity type |
| `aggregate_id` | `VARCHAR(255)` | No | — | Target entity ID |
| `event_type` | `VARCHAR(100)` | No | — | Normalized event name |
| `payload` | `JSONField` | No | `{}` | Sanitized event payload |
| `occurred_at` | `TIMESTAMPTZ` | No | `now()` | Origin timestamp |
| `available_at` | `TIMESTAMPTZ` | No | `now()` | Delivery eligibility threshold |
| `published_at` | `TIMESTAMPTZ` | Yes | `NULL` | Dispatch confirmation time |

