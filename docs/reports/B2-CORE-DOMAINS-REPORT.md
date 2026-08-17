# B2-CORE-DOMAINS-REPORT.md — Milestone B2 Core Domains Completion Report

- **Project**: Tersuite AI Studio
- **Milestone**: B2 — Core Identity, Product, Project, Site, and Conversation Domains
- **Status**: COMPLETED & VERIFIED
- **Baseline Git Commit (B2_BASE_SHA)**: `b651815cf380174f8df347a8d754a287f4e9a8bb`
- **Published B2 Code Git Commit**: `0150f31f111474076d9358dac3f4c7c14bc7f069`
- **Branch**: `feature/b2-core-domains`
- **GitHub Actions CI Run**: [https://github.com/josephtersoo2-stack/tersostudio/actions/runs/32052323974](https://github.com/josephtersoo2-stack/tersostudio/actions/runs/32052323974)
- **CI Status & Conclusion**: Completed / Success (All steps passed)
- **Test Suite Status**: 234 Passed, 1 Skipped (Live LLM API test without credentials), 0 Failed
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
- **Exception Envelope Normalization (`apps.core.exceptions`)**:
  - All DRF exceptions and custom domain exceptions return the standardized `{ "error": { "code": "...", "message": "...", "status_code": ..., "details": ... } }` contract envelope.

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
- **Plugin-Only Policy & Route Restrictions**:
  - Direct creation (`POST /products/`), replacement (`PUT`), and hard deletion (`DELETE`) are disallowed via API returning `405 Method Not Allowed`.
  - Products are provisioned safely via the Project creation workflow or service layer.
  - Creation of `THEME` products is strictly prohibited and rejected with `400 Bad Request` (`unsupported_product_kind`).
- **Service Layer**:
  - `create_plugin_product`: Deterministically derives PSR-4 compliant namespace prefixes (e.g. `affiliate-hub` $\rightarrow$ `AffiliateHub`) and main entrypoint file names.

### 2.4. WordPress Sites & Profiles Domain (`apps.sites`)
- **Models**:
  - `WordPressSite`: Stores site metadata, environment (`DEVELOPMENT`, `STAGING`, `PRODUCTION`), and normalized URL.
  - `SiteProfileSnapshot`: Strictly immutable sequential version snapshots (`version = 1, 2, ...`) of WordPress core version, PHP version, active plugins, active theme, server metadata, and health metrics.
- **Nested Profile Routes**:
  - Snapshot operations are scoped under `/api/v1/sites/{site_id}/profiles/` (GET list, POST create) and `/api/v1/sites/{site_id}/profiles/{snapshot_id}/` (GET retrieve).
- **Integrity & Security**:
  - Every snapshot computes and persists a deterministic SHA-256 checksum over sorted JSON sections.
  - Storage of passwords, authentication tokens, application passwords, or database credentials is strictly rejected.
  - Zero network I/O or active probing is performed against WordPress sites in B2.

### 2.5. Projects & Site Association Domain (`apps.projects`)
- **Models**:
  - `Project`: Organization-owned container linked 1:1 to a `WordPressProduct`.
  - `ProjectSite`: Junction linking an organization's WordPress site to a Project with explicit role purpose (`DEVELOPMENT`, `STAGING`, `PRIMARY`, `TEST`) defaulting to `PRIMARY`.
- **Route Protections**:
  - Root `DELETE /api/v1/projects/{id}/` returns `405 Method Not Allowed` (projects are archived).
  - Site detachment is exposed via `/api/v1/projects/{id}/sites/{project_site_id}/` DELETE.
- **Backward Compatibility**:
  - Project model and serializer expose property aliases (`plugin_slug`, `wordpress_version`, `php_version`, `user`) sourcing from `WordPressProduct` and `created_by`.
- **Service Layer (`ProjectService`)**:
  - Atomically creates `Project`, `WordPressProduct`, and `PluginTarget` records.
  - Enforces cross-tenant validation ensuring sites linked to a project belong strictly to the same tenant organization.

### 2.6. Conversations & Messages Domain (`apps.conversations`)
- **Models**:
  - `Conversation`: Project-scoped discussion thread with monotonic `next_message_sequence` counter and archive lifecycle support.
  - `ConversationMessage`: Immutable message log with ordered sequence numbers and client idempotency key support (`client_message_id` as UUID).
- **Service Layer (`ConversationMessageService`)**:
  - `append_user_message`: Transactional row-level locking (`select_for_update`) ensuring deterministic sequential numbering and duplicate submission idempotency.
  - Returns `idempotent_replay: false` (HTTP 201) on new message, and `idempotent_replay: true` (HTTP 200) on replay.
  - Message endpoints are append-only (`GET` and `POST` only; mutation/deletion returns `405`).

### 2.7. Generations Domain Tenant Migration & Scoping (`apps.generations`)
- **Data Model Migration**:
  - Migrated `Generation` to inherit `OrganizationOwnedModel`.
  - Backfilled existing generations with `organization_id` derived directly from parent `Project.organization_id`.
  - Cross-tenant validation: `clean()` and `save()` enforce `generation.organization == project.organization`.
  - Replaced legacy `user_id` indexes with compound `(organization, status)` index.
- **Execution & State Machine Stability**:
  - `GenerationStateMachine` automatically clears error and failure fields upon recovery from `RETRYING` to active states.
  - `ExecutionService` preserves execution dispatch and mock runtime compatibility.

### 2.8. Runtime Adapters (`runtime.adapters.openhands`)
- Implemented robust error classification in `send_task`:
  - `TimeoutError` $\rightarrow$ `ExecutionStatus.TIMEOUT` / `FailureCategory.TIMEOUT`
  - `WebSocketConnectionError` / `httpx.ConnectError` $\rightarrow$ `ExecutionStatus.INFRASTRUCTURE_UNAVAILABLE` / `FailureCategory.NETWORK_CONNECTION`
  - Model / Tool errors $\rightarrow$ `ExecutionStatus.AGENT_FAILED` with appropriate `FailureCategory.MODEL_ERROR` / `TOOL_ERROR`.

### 2.9. Real MigrationExecutor Verification (`tests.migrations.test_b2_core_domain_migration`)
- Real Django `MigrationExecutor` tests verify bidirectional migration safety on live PostgreSQL test database:
  - Forward backfill of B1 records to B2 multi-tenant schema with slug collision handling and metadata preservation.
  - Backward unapplication restoring legacy B1 fields and indexes.
  - Verification that pre-existing unmarked personal organizations survive `organizations.0002` reversal.

---

## 3. Test Suite Verification Summary

```
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0
django: version: 5.1.15, settings: config.settings.test (from ini)
rootdir: C:\xampp\htdocs\tersostudio new\backend
collected 235 items

apps\accounts\tests\test_auth.py ............                            [  5%]
apps\control_center\tests\test_control_center_actions_api.py ........... [  9%]
..                                                                       [ 10%]
apps\control_center\tests\test_control_center_api.py ................... [ 18%]
...                                                                      [ 20%]
apps\control_center\tests\test_control_center_detail_api.py ............ [ 25%]
.                                                                        [ 25%]
apps\control_center\tests\test_control_center_knowledge_and_projects_api.py . [ 25%]
........                                                                 [ 29%]
apps\conversations\tests\test_api.py ..                                  [ 30%]
apps\conversations\tests\test_idempotency.py .                           [ 30%]
apps\conversations\tests\test_messages.py ...                            [ 31%]
apps\conversations\tests\test_models.py ..                               [ 32%]
apps\conversations\tests\test_tenant_isolation.py ..                     [ 33%]
apps\core\tests\test_health.py ......                                    [ 36%]
apps\generations\tests\test_artifacts_and_workspace.py ....              [ 37%]
apps\generations\tests\test_authorization.py .......                     [ 40%]
apps\generations\tests\test_execution_service.py ..........              [ 45%]
apps\generations\tests\test_generations.py .........                     [ 48%]
apps\generations\tests\test_state_machine.py ........                    [ 52%]
apps\organizations\tests\test_api.py ......                              [ 54%]
apps\organizations\tests\test_context.py .......                         [ 57%]
apps\organizations\tests\test_models_and_services.py .......             [ 60%]
apps\organizations\tests\test_tenant_isolation.py ....                   [ 62%]
apps\products\tests\test_api.py ....                                     [ 64%]
apps\products\tests\test_models.py ...                                   [ 65%]
apps\products\tests\test_plugin_boundary.py ..                           [ 66%]
apps\projects\tests\test_project_compatibility.py .                      [ 66%]
apps\projects\tests\test_project_sites.py ...                            [ 68%]
apps\projects\tests\test_projects.py ........                            [ 71%]
apps\realtime\tests\test_realtime.py .                                   [ 71%]
apps\sites\tests\test_api.py ..                                          [ 72%]
apps\sites\tests\test_models.py ..                                       [ 73%]
apps\sites\tests\test_profiles.py ..                                     [ 74%]
apps\sites\tests\test_secret_rejection.py ..                             [ 75%]
apps\sites\tests\test_tenant_isolation.py ..                             [ 76%]
tests\test_system_integration.py .                                       [ 76%]
tests\migrations\test_b2_core_domain_migration.py ..                     [ 77%]
apps\core\tests\test_health.py .                                         [ 77%]
apps\core\tests\test_validators.py .............                         [ 83%]
apps\realtime\tests\test_realtime.py ..                                  [ 84%]
knowledge_base\tests\test_knowledge_engine.py .............              [ 89%]
runtime\tests\test_mock_adapter.py ...                                   [ 91%]
runtime\tests\test_openhands_adapter.py ...............                  [ 97%]
runtime\tests\test_runtime_contracts.py .....                            [ 99%]
tests\integration\test_openhands_live.py s                               [100%]

======================= 234 passed, 1 skipped in 45.69s =======================
```

---

## 4. Conclusion & Hand-off

Milestone B2 is fully completed, verified against contracts, tested with real database migrations, and confirmed passing on GitHub Actions CI. The codebase is prepared for Milestone B3 (Multi-Agent Roster & OpenHands Execution Engine).
