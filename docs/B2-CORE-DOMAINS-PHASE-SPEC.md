# B2 — Core Identity, Product, Project, Site, and Conversation Domains

## 1. Phase identity

- Roadmap milestone: `B2`
- Product area: backend control-plane domains
- Required predecessor: frozen B1 head `79e0f8c24114592207ad1e38275a51972ece9006` merged into `main`
- Implementer: Google Antigravity
- Reviewer: independent inspection of the pushed GitHub commit and CI evidence
- Product posture: WordPress plugin-first, theme-ready by explicit type boundaries

## 2. Purpose

B2 replaces the remaining user-owned prototype domain boundary with a durable organization-owned foundation. It introduces the minimum identity and tenancy contracts needed for several people to work safely inside one organization, gives every project an explicit WordPress product target, stores WordPress site metadata and immutable site-profile snapshots, and persists project conversations and messages without yet invoking agents.

B2 is a domain and authorization milestone. It does not implement discovery agents, planning, approvals, workflow orchestration, OpenHands conversations, code generation, WordPress pairing, sandbox execution, packaging, billing, or themes.

## 3. Required outcomes

At completion:

1. Every public domain record is scoped to an organization rather than directly owned by one user.
2. Every existing user receives one personal organization and an active owner membership through a reversible data migration.
3. New registrations receive a personal organization transactionally.
4. A user may belong to multiple organizations with one of four B2 roles: `OWNER`, `ADMIN`, `MEMBER`, or `VIEWER`.
5. Tenant-scoped APIs resolve one explicit organization context and never expose another organization's records.
6. Existing projects are migrated without data loss into organization-owned projects with explicit creator/updater audit fields.
7. Every project has one `WordPressProduct` and one plugin-specific `PluginTarget`.
8. `ProductKind` includes `PLUGIN` and the reserved future value `THEME`, but B2 public writes accept only `PLUGIN`.
9. WordPress site records contain metadata only—never credentials—and support immutable, versioned site-profile snapshots.
10. Projects may target multiple sites through an explicit association model.
11. Project conversations and ordered messages are persisted with deterministic idempotency and organization isolation.
12. Existing generation, workspace, run, and artifact APIs are migrated to organization membership authorization without redesigning their B3 lifecycle.
13. Existing B1 functionality and all protected contracts continue to pass.
14. API and data-model documentation truthfully describe the new v1 contracts and compatibility behavior.

## 4. Fixed architectural decisions

These are approved decisions, not choices for Antigravity.

### 4.1 Organization context

- Tenant header: `X-Tersuite-Organization-ID` containing a UUID.
- If the authenticated user has exactly one active membership, the header may be omitted and that organization is selected.
- If the user has more than one active membership and omits the header, return HTTP 400 with code `organization_context_required`.
- An invalid UUID returns HTTP 400 with code `invalid_organization_context`.
- An unknown organization, inactive organization, or organization without an active membership returns HTTP 404 with code `organization_not_found` so existence is not disclosed.
- Staff and superusers do not bypass public tenant scoping. Staff-wide inspection remains restricted to existing Control Center endpoints.
- The selected organization is cached on `request.tersuite_organization` for the request lifecycle.

### 4.2 B2 roles

| Role | Read tenant data | Create/update/archive domain data | Manage ordinary members | Assign or change `OWNER` | Archive organization |
|---|---:|---:|---:|---:|---:|
| `OWNER` | Yes | Yes | Yes | Yes | Yes |
| `ADMIN` | Yes | Yes | Yes, except owners | No | No |
| `MEMBER` | Yes | Yes | No | No | No |
| `VIEWER` | Yes | No | No | No | No |

- An organization must always retain at least one active owner.
- An admin cannot edit or remove an owner membership.
- Membership creation in B2 adds an already registered user by normalized email. Invitations and outbound email belong to a later phase.
- Hard deletion of organizations, projects, products, sites, conversations, messages, generations, or site snapshots is not exposed publicly.

### 4.3 Audit ownership

B2 audit ownership means explicit immutable creator and current updater attribution, not the future enterprise audit-export system.

- Organization-owned mutable roots store `organization`, `created_by`, and `updated_by`.
- `created_by` is immutable after creation.
- `updated_by` is set from the authenticated actor on each accepted mutation.
- Creator/updater foreign keys use `SET_NULL` so historical records survive account removal.
- Messages store their human author separately and are immutable after creation.
- B2 does not add a general audit-event ledger; structured audit export remains a later enterprise milestone.

### 4.4 Product boundary

- Shared model: `WordPressProduct`.
- Plugin-specific one-to-one model: `PluginTarget`.
- `ProductKind.PLUGIN` is the only writable B2 kind.
- `ProductKind.THEME` is reserved and serializable but public creation/update requests using it return HTTP 400 with code `unsupported_product_kind`.
- Theme manifests, templates, blocks, visual editing, Theme Check, and theme generation are prohibited in B2.
- Existing project plugin fields are migrated into the product models and removed from project storage. The v1 project serializer retains deprecated compatibility aliases, translating accepted writes into the single authoritative product records so existing clients do not immediately break.

### 4.5 WordPress sites

- B2 stores site identity and profile metadata only.
- It must not store passwords, application passwords, cookies, OAuth tokens, API keys, private keys, database credentials, or WordPress salts.
- It must not contact a WordPress site, test credentials, install a plugin, or claim a site is connected.
- Site status defaults to `UNVERIFIED`; secure pairing is a WordPress client milestone.
- Site-profile snapshots are immutable and monotonically versioned per site.
- Snapshot JSON is rejected if any nested key matches the forbidden secret-key policy defined in the detailed specification.

### 4.6 Conversations and messages

- B2 stores chat history but does not call an LLM or OpenHands.
- A conversation belongs to exactly one organization and one project.
- Public message creation accepts only role `USER`; assistant/system/tool messages are internal-only service operations for later milestones.
- Messages are immutable, ordered by a transactionally allocated sequence number, and optionally idempotent by `client_message_id`.
- An archived conversation accepts no new messages.

## 5. Domain model summary

### Organizations

- `Organization`
- `OrganizationMembership`
- `OrganizationRole`

### Products

- `ProductKind`
- `WordPressProduct`
- `PluginTarget`

### Projects

- migrated `Project`
- `ProjectSite`

### Sites

- `WordPressSite`
- `SiteProfileSnapshot`

### Conversations

- `Conversation`
- `ConversationMessage`

### Existing generation domain

- migrated `Generation.organization`
- renamed `Generation.user` to `Generation.created_by`
- added `Generation.updated_by`
- tenant-scoped authorization for generations and all child resources

## 6. API surface

All paths remain under `/api/v1/`.

- `/organizations/`
- `/organizations/{organization_id}/`
- `/organizations/{organization_id}/members/`
- `/organizations/{organization_id}/members/{membership_id}/`
- `/products/`
- `/products/{product_id}/`
- `/projects/` and existing project actions
- `/projects/{project_id}/sites/`
- `/projects/{project_id}/sites/{project_site_id}/`
- `/sites/`
- `/sites/{site_id}/`
- `/sites/{site_id}/profiles/`
- `/sites/{site_id}/profiles/{snapshot_id}/`
- `/conversations/`
- `/conversations/{conversation_id}/`
- `/conversations/{conversation_id}/archive/`
- `/conversations/{conversation_id}/messages/`
- `/conversations/{conversation_id}/messages/{message_id}/`
- existing generation/step/run/workspace/artifact endpoints, now organization-scoped

The detailed specification fixes allowed methods, serializers, error codes, filtering, and compatibility fields.

## 7. Migration and compatibility requirements

1. Never edit or delete existing migrations.
2. Migrations must work from the B1 schema with existing users, projects, generations, steps, runs, workspaces, and artifacts.
3. Create one personal organization and owner membership for every existing user, including users without projects.
4. Preserve project UUIDs, slugs, timestamps, archive flags, metadata, and generation relationships.
5. Create one plugin product target per existing project using the existing project name, plugin slug, WordPress version, and PHP version while preserving the project slug separately. Resolve historical duplicate plugin slugs deterministically and preserve the original value in migration metadata.
6. Preserve generation UUIDs, status, prompt, timestamps, child relationships, and initiating user as `created_by`.
7. Backfill every migrated project's and generation's organization consistently.
8. Remove the superseded user-owned constraints and legacy project storage fields only after successful backfill.
9. Provide a migration test that starts from the B1 migration state, inserts representative historical records, migrates to B2, and verifies the full backfill.
10. API compatibility aliases `user_id`, `plugin_slug`, `wordpress_version`, and `php_version` may remain where specified. `user_id` stays read-only. Accepted writes for the three plugin compatibility fields must be translated into one authoritative product source and conflicting values must be rejected. Mark every alias deprecated in `API-CONTRACT.md`.

## 8. Security requirements

- Every tenant queryset begins with the resolved organization, never with an unscoped model manager followed by an object permission.
- Cross-tenant list, retrieve, update, archive, membership, site, snapshot, conversation, message, generation, and artifact tests are mandatory.
- Foreign-key IDs supplied by clients are resolved inside the selected organization.
- Cross-tenant object IDs return 404 without confirming existence.
- Role changes and last-owner protection run inside `transaction.atomic()` with locked membership rows.
- Project/product/site/conversation organization alignment is validated in both services/serializers and model constraints where representable.
- User-controlled metadata is size-bounded, must be a JSON object, and is recursively checked for forbidden secret keys.
- Site URLs allow only normalized `http` or `https` URLs, strip fragments, lowercase the host, and reject embedded credentials.
- Message content and titles have explicit length limits.
- API serializers never expose password hashes, tokens, provider keys, raw site credentials, or unrestricted internal metadata.

## 9. In scope

- new `organizations`, `products`, `sites`, and `conversations` backend apps
- organization context and basic membership authorization
- personal-organization creation/backfill
- project/product migration and compatibility serialization
- site metadata, project-site associations, and profile snapshots
- conversation/message persistence and ordering
- organization scoping of the existing generation domain
- required Control Center compatibility updates
- admin registration for new models
- API, data-model, README, tests, migrations, and B2 report

## 10. Out of scope

- agent creation, agent profiles, subagents, orchestration, work packages, or repair loops
- calling OpenHands, creating OpenHands conversations, or changing runtime adapters
- requirements extraction, specifications, plans, approvals, or project phases
- WordPress authentication/pairing, remote requests, diagnostics, activation, rollback, or plugin delivery
- code generation, workspaces, file manager IDE, sandbox QA, packaging, or deployment
- component/blueprint/knowledge registries or learned experience promotion
- invitations, email delivery, SSO, SCIM, granular custom roles, billing, quotas, or audit export
- theme creation or theme-specific storage
- frontend or WordPress plugin changes
- destructive cleanup unrelated to the B2 ownership migration

## 11. Completion gate

B2 is complete only when:

1. B1 is present in `main` and the implementation branch starts from that merged commit.
2. The detailed B2 specification is implemented without invention.
3. All migrations and migration-backfill tests pass.
4. All existing and new backend tests pass with exact counts reported.
5. Cross-tenant tests prove no list, detail, mutation, nested, generation, or artifact leak.
6. Role and last-owner tests pass.
7. Product plugin-only and future-theme boundary tests pass.
8. Site secret rejection and snapshot immutability tests pass.
9. Conversation idempotency, ordering, archive, and role tests pass.
10. API and data-model contracts match executable behavior.
11. GitHub CI passes from a clean environment.
12. The actual GitHub diff is independently reviewed and frozen.
