# B2-CORE-DOMAINS-REPORT.md — Milestone B2 Core Domains Completion Report

- **Project**: Tersuite AI Studio
- **Milestone**: B2 — Core Identity, Product, Project, Site, and Conversation Domains
- **Status**: COMPLETED & VERIFIED
- **Baseline Git Commit (B2_BASE_SHA)**: `b651815cf380174f8df347a8d754a287f4e9a8bb`
- **Published B2 Git Commit**: `6fa8d46f78617d620d5bdbcb2851aeef43bee7e6`
- **Branch**: `feature/b2-core-domains`
- **GitHub Actions CI Run**: [https://github.com/josephtersoo2-stack/tersostudio/actions/runs/32031817345](https://github.com/josephtersoo2-stack/tersostudio/actions/runs/32031817345)
- **CI Status & Conclusion**: Completed / Success (All 12 validation steps passed)
- **Test Suite Status**: 223 Passed, 1 Skipped (Live LLM API test without credentials), 0 Failed
- **Django System Check**: 0 Issues
- **Migration Integrity Check**: Clean (`makemigrations --check --dry-run` reported No changes detected)

---

## 1. Executive Summary

Milestone B2 establishes the authoritative core domain data model, tenant boundary architecture, product target isolation, metadata-only WordPress site tracking, strictly ordered conversations, and deterministic multi-tenant security foundations for Tersuite AI Studio.

All changes were executed strictly in accordance with:
- `AGENTS.md`
- `docs/B2-CORE-DOMAINS-PHASE-SPEC.md`
- `docs/B2-CORE-DOMAINS-DETAILED-IMPLEMENTATION.md`
- `docs/TERSUITE-IMPLEMENTATION-ROADMAP.md`

No out-of-scope features, agent orchestrations, subagents, remote network calls, live WordPress credentials, frontend UI modifications, or theme product implementations were introduced.

---

## 2. Milestone Deliverables & Accomplishments

### 2.1. Shared Core Domain Foundations (`apps.core`)
- **`OrganizationOwnedModel`**: Abstract base model providing `organization` (`PROTECT`), `created_by` (`SET_NULL`), and `updated_by` (`SET_NULL`) with automatic request user propagation.
- **Safety Validators (`apps.core.validators`)**:
  - `find_forbidden_json_key`: Comprehensive recursive scan detecting secret keys (passwords, tokens, api keys, credentials, app passwords, jwt).
  - `validate_safe_json_object`: Enforces strict dictionary type, payload size bounds ($\le 256\text{ KB}$), and zero-secret policies.
  - `normalize_wordpress_url`: Normalizes site URLs by enforcing standard `http`/`https` protocols, lowercased hostnames, and automatically stripping userinfo, query parameters, and fragments.

### 2.2. Organizations & Multi-Tenancy Domain (`apps.organizations`)
- **Models**:
  - `Organization`: Primary tenant boundary entity with support for personal user workspaces (`is_personal`) and custom team workspaces.
  - `OrganizationMembership`: Maps users to organizations with strict hierarchical role enforcement (`OWNER`, `ADMIN`, `MEMBER`, `VIEWER`).
- **Context Resolution (`OrganizationContextMixin`)**:
  - Automatically resolves organization context using `X-Tersuite-Organization-ID` header.
  - Safely defaults for users with a single active membership when header is omitted.
  - Rejects ambiguous multi-membership requests without a header with `400 Bad Request` (`organization_context_required`).
  - Rejects unknown or unaffiliated organizations with `404 Not Found`.
- **Permissions**:
  - `HasOrganizationReadAccess`: All active organization members.
  - `HasOrganizationWriteAccess`: Mutation actions restricted to `OWNER`, `ADMIN`, `MEMBER`.
  - `CanManageOrganizationMembers`: Membership operations restricted to `OWNER`, `ADMIN`.
- **Automatic Provisioning**: Registered users automatically receive a personal organization and `OWNER` membership inside an atomic database transaction.

### 2.3. WordPress Products Domain (`apps.products`)
- **Models**:
  - `WordPressProduct`: Authoritative product definition (`kind="PLUGIN"`, `display_name`, `slug`, `version`, `wordpress_version`, `php_version`, `is_archived`).
  - `PluginTarget`: `OneToOneField(WordPressProduct)` storing `plugin_slug`, `text_domain`, `namespace_prefix`, and `main_file`.
- **Plugin-Only Policy**:
  - Creation of `THEME` products is strictly prohibited and rejected with `400 Bad Request` (`invalid_product_kind`).
- **Service Layer**:
  - `create_plugin_product`: Deterministically derives PSR-4 compliant namespace prefixes (e.g. `affiliate-hub` $\rightarrow$ `AffiliateHub`) and main entrypoint file names.

### 2.4. WordPress Sites & Profiles Domain (`apps.sites`)
- **Models**:
  - `WordPressSite`: Stores site metadata, environment (`DEVELOPMENT`, `STAGING`, `PRODUCTION`), and normalized URL.
  - `SiteProfileSnapshot`: Strictly immutable sequential version snapshots (`version = 1, 2, ...`) of WordPress core version, PHP version, active plugins, active theme, server metadata, and health metrics.
- **Integrity & Security**:
  - Every snapshot computes and persists a deterministic SHA-256 checksum over sorted JSON sections.
  - Storage of passwords, authentication tokens, application passwords, or database credentials is strictly rejected.
  - Zero network I/O or active probing is performed against WordPress sites in B2.

### 2.5. Projects & Site Association Domain (`apps.projects`)
- **Models**:
  - `Project`: Organization-owned container linked 1:1 to a `WordPressProduct`.
  - `ProjectSite`: Junction linking an organization's WordPress site to a Project with explicit role purpose (`DEVELOPMENT`, `STAGING`, `PRIMARY`, `TEST`).
- **Backward Compatibility**:
  - Project model and serializer expose property aliases (`plugin_slug`, `wordpress_version`, `php_version`, `user`) sourcing from `WordPressProduct` and `created_by`.
- **Service Layer (`ProjectService`)**:
  - Atomically creates `Project`, `WordPressProduct`, and `PluginTarget` records.
  - Enforces cross-tenant validation ensuring sites linked to a project belong strictly to the same tenant organization.

### 2.6. Conversations & Messages Domain (`apps.conversations`)
- **Models**:
  - `Conversation`: Project-scoped discussion thread with monotonic `next_message_sequence` counter and archive lifecycle support.
  - `ConversationMessage`: Immutable message log with ordered sequence numbers and client idempotency key support (`client_message_id`).
- **Service Layer (`ConversationMessageService`)**:
  - `append_user_message`: Transactional row-level locking (`select_for_update`) ensuring deterministic sequential numbering and duplicate submission idempotency.
  - Prevents agent invocation or generation triggers during message posting.

### 2.7. Generations Domain Tenant Migration & Scoping (`apps.generations`)
- **Data Model Migration**:
  - Migrated `Generation` to inherit `OrganizationOwnedModel`.
  - Backfilled existing generations with `organization_id` derived directly from parent `Project.organization_id`.
  - Replaced legacy `user_id` indexes with compound `(organization, status)` index.
- **Execution & State Machine Stability**:
  - `GenerationStateMachine` automatically clears error and failure fields upon recovery from `RETRYING` to active states.
  - `ExecutionService` preserves execution dispatch and mock runtime compatibility.

### 2.8. Control Center & Operational Staff API (`apps.control_center`)
- **Cross-Tenant Visibility**:
  - Maintained complete staff-only cross-tenant operational visibility over all projects, generations, agent runs, artifacts, and knowledge units.
  - Updated all querysets and serializers to read `created_by` and `product__plugin_target` relationships seamlessly.
- **Actions API**:
  - Verified staff operational mutation endpoints (`POST /api/v1/control-center/generations/{id}/cancel/` and `POST /api/v1/control-center/steps/{id}/retry/`).

---

## 3. Automated Verification & Test Results

The entire backend test suite was executed against the PostgreSQL and in-memory test databases:

```
platform win32 -- Python 3.12.14, pytest-9.1.1, pluggy-1.6.0
django: version: 5.1.15, settings: config.settings.test
rootdir: C:\xampp\htdocs\tersostudio new\backend
configfile: pyproject.toml
plugins: anyio-4.14.2, libtmux-0.62.0, asyncio-1.4.0, django-4.14.0

============================= 223 passed, 1 skipped in 47.33s =============================
```

### Breakdown by Domain Test Suite:
1. `apps/accounts/tests/`: 11 passed
2. `apps/core/tests/`: 14 passed
3. `apps/organizations/tests/`: 24 passed
4. `apps/products/tests/`: 6 passed
5. `apps/sites/tests/`: 10 passed
6. `apps/projects/tests/`: 12 passed
7. `apps/conversations/tests/`: 10 passed
8. `apps/generations/tests/`: 27 passed
9. `apps/control_center/tests/`: 57 passed
10. `apps/realtime/tests/`: 2 passed
11. `knowledge_base/tests/`: 13 passed
12. `runtime/tests/`: 31 passed
13. `tests/migrations/`: 6 passed

---

## 4. Migration & Schema Verification

Django migration consistency was verified via automated checks:

1. `python manage.py check`:
   ```
   System check identified no issues (0 silenced).
   ```

2. `python manage.py makemigrations --check --dry-run`:
   ```
   No changes detected
   ```

3. Applied migrations:
   - `organizations.0001_initial`
   - `organizations.0002_backfill_personal_organizations`
   - `products.0001_initial`
   - `sites.0001_initial`
   - `projects.0002_organization_product_ownership`
   - `conversations.0001_initial`
   - `generations.0002_organization_audit_ownership`

---

## 5. Artifacts and Documentation Updated

1. [API-CONTRACT.md](file:///c:/xampp/htdocs/tersostudio%20new/docs/API-CONTRACT.md) — Fully documented B2 endpoints for Organizations, Products, Sites, Projects, Conversations, and Generations.
2. [DATA-MODEL.md](file:///c:/xampp/htdocs/tersostudio%20new/docs/DATA-MODEL.md) — Comprehensive entity relationship model and database table specifications.
3. [B2-CORE-DOMAINS-REPORT.md](file:///c:/xampp/htdocs/tersostudio%20new/docs/reports/B2-CORE-DOMAINS-REPORT.md) — Final verifiable milestone report.
4. [test_b2_core_domain_migration.py](file:///c:/xampp/htdocs/tersostudio%20new/backend/tests/migrations/test_b2_core_domain_migration.py) — End-to-end integration migration test suite.

---

## 6. GitHub Actions CI Run Evidence

- **Workflow Name**: `Backend Baseline CI`
- **Run ID**: `32031817345`
- **Run URL**: `https://github.com/josephtersoo2-stack/tersostudio/actions/runs/32031817345`
- **Head Branch**: `feature/b2-core-domains`
- **Head SHA**: `6fa8d46f78617d620d5bdbcb2851aeef43bee7e6`
- **Status / Conclusion**: `completed / success`
- **Step Breakdown**:
  - `Checkout Repository`: Completed / Success
  - `Install uv (v0.8.13)`: Completed / Success
  - `Setup Python (3.12)`: Completed / Success
  - `Install Locked Dependencies (Frozen + Dev)`: Completed / Success
  - `Verify OpenHands Packages (v1.42.1)`: Completed / Success
  - `Run Django System Check`: Completed / Success
  - `Run Migration Consistency Check`: Completed / Success
  - `Run Backend Test Suite`: Completed / Success (223 passed, 1 skipped)
  - `Validate Docker Compose Configuration`: Completed / Success
  - `Build Docker Container Image`: Completed / Success
