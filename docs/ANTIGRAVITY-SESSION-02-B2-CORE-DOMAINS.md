# Antigravity Execution Prompt — Session 02: B2 Core Domains

## Overview

Session 02 implements the authoritative core domain foundations for Tersuite AI Studio across Organizations, Products, Sites, Projects, Conversations, and Generations multi-tenant data structures and API contracts.

## Key Reference Documents
- `AGENTS.md`
- `docs/TERSUITE-IMPLEMENTATION-ROADMAP.md`
- `docs/ANTIGRAVITY-DEVELOPMENT-PROTOCOL.md`
- `docs/B2-CORE-DOMAINS-PHASE-SPEC.md`
- `docs/B2-CORE-DOMAINS-DETAILED-IMPLEMENTATION.md`
- `docs/reports/B2-CORE-DOMAINS-REPORT.md`

## Summary of B2 Scope & Deliverables
1. **Core Utilities & Models (`apps/core`)**: `OrganizationOwnedModel`, safety validators, secret rejection, URL normalization, exception envelope normalization.
2. **Organizations Domain (`apps/organizations`)**: Multi-tenant boundary, role-based memberships (`OWNER`, `ADMIN`, `MEMBER`, `VIEWER`), header-based context resolution (`X-Tersuite-Organization-ID`), auto-provisioning.
3. **Products Domain (`apps/products`)**: `WordPressProduct` and `PluginTarget`, `kind="PLUGIN"` boundary, 405 on direct root mutations.
4. **Sites Domain (`apps/sites`)**: `WordPressSite`, immutable `SiteProfileSnapshot` with SHA-256 integrity hashing and zero secret retention, nested `/profiles/` endpoints.
5. **Projects Domain (`apps/projects`)**: Organization-owned projects, 1:1 `WordPressProduct` linking, `ProjectSite` attachments (`PRIMARY` default), root 405 DELETE protection.
6. **Conversations Domain (`apps/conversations`)**: Monotonic message sequence counters, idempotent message submission via `client_message_id` UUID, append-only logs.
7. **Generations Domain (`apps/generations`)**: Tenant isolation migration, state machine error clearing, execution dispatch.
8. **Real Migration Safety**: Reversible data & schema migrations verified with `MigrationExecutor` tests on live PostgreSQL test runner.
