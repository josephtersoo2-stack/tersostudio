# B2 — Core Domains Detailed Implementation Specification

## 1. Governing scope and preconditions

This document is the executable, file-by-file specification for roadmap milestone B2. It is subordinate to `docs/ANTIGRAVITY-SESSION-02-B2-CORE-DOMAINS.md` and must be read with:

1. `AGENTS.md`
2. `docs/TERSUITE-IMPLEMENTATION-ROADMAP.md`
3. `docs/ANTIGRAVITY-DEVELOPMENT-PROTOCOL.md`
4. `docs/B2-CORE-DOMAINS-PHASE-SPEC.md`
5. this document

Before editing, verify that the current `main` contains frozen B1 commit `79e0f8c24114592207ad1e38275a51972ece9006` as an ancestor. If it does not, stop. Do not recreate or cherry-pick B1 selectively.

Create `feature/b2-core-domains` from the verified merged B1 `main`. Record the exact base SHA. No dependency version changes are authorized.

## 2. Fixed implementation rules

- Use Django/DRF and the existing PostgreSQL, pytest, pagination, error-envelope, UUID, and timestamp conventions.
- Do not add a third-party tenancy, nested-router, invitation, audit, or schema package.
- Do not edit historical migrations.
- Public tenant access is membership-based. Object creator identity is audit attribution, not authorization.
- All tenant querysets are filtered by the selected organization before lookup.
- Cross-tenant IDs return 404 and never disclose the other tenant's object type, name, owner, or existence.
- Model, serializer, and service validation must agree; serializers must not rely on a later object permission to repair an unscoped lookup.
- Public `DELETE` is prohibited for B2 root resources. Membership removal and project-site detachment are the only public deletes specified here.
- JSON metadata must be a bounded object and must pass the shared secret-key validator.
- B2 must not import OpenHands or change `backend/runtime/**`.

## 3. Shared core changes

### 3.1 Modify `backend/apps/core/models.py`

Preserve `UUIDModel` and `TimeStampedModel`. Add abstract `OrganizationOwnedModel(TimeStampedModel)` with:

- `organization`: `ForeignKey("organizations.Organization", PROTECT, related_name="%(app_label)s_%(class)s_records", db_index=True)`
- `created_by`: nullable `ForeignKey(settings.AUTH_USER_MODEL, SET_NULL, related_name="%(app_label)s_%(class)s_created")`
- `updated_by`: nullable `ForeignKey(settings.AUTH_USER_MODEL, SET_NULL, related_name="%(app_label)s_%(class)s_updated")`

`OrganizationOwnedModel.Meta.abstract = True`. Do not add behavior that silently changes organization or creator during `save()`.

### 3.2 Create `backend/apps/core/validators.py`

Implement reusable deterministic validators:

- `FORBIDDEN_SECRET_KEYS`: normalized exact-key set containing `password`, `passwd`, `pwd`, `secret`, `token`, `access_token`, `refresh_token`, `api_key`, `apikey`, `private_key`, `client_secret`, `authorization`, `cookie`, `set_cookie`, `database_url`, `db_password`, `wp_salts`, and `application_password`.
- `normalize_json_key(value)`: lowercase and replace hyphens/spaces with underscores.
- `find_forbidden_json_key(value)`: recursively inspect dictionaries and lists and return only the forbidden normalized key, never its value.
- `validate_safe_json_object(value, max_bytes=32768)`: require a dictionary, JSON-serialize deterministically, enforce the byte limit, and raise `ValidationError` without echoing values when a forbidden key or size violation exists.
- `normalize_wordpress_url(value)`: accept only absolute `http`/`https`, reject username/password, lowercase the host, remove default ports and fragments, normalize an empty path to `/`, retain query only if empty; B2 site identity URLs must reject non-empty query strings.

Unit-test all nested-key, size, malformed JSON, credential-in-URL, scheme, host-case, port, query, and fragment cases.

### 3.3 Modify `backend/apps/core/exceptions.py`

Preserve the existing response envelope. Ensure DRF `APIException.default_code` is emitted as the stable `error.code`. Do not return raw exception objects or serializer internals.

## 4. Organizations app

### 4.1 Create files

Create:

- `backend/apps/organizations/__init__.py`
- `backend/apps/organizations/apps.py`
- `backend/apps/organizations/enums.py`
- `backend/apps/organizations/models.py`
- `backend/apps/organizations/services.py`
- `backend/apps/organizations/context.py`
- `backend/apps/organizations/permissions.py`
- `backend/apps/organizations/serializers.py`
- `backend/apps/organizations/views.py`
- `backend/apps/organizations/urls.py`
- `backend/apps/organizations/admin.py`
- `backend/apps/organizations/migrations/__init__.py`
- `backend/apps/organizations/migrations/0001_initial.py`
- `backend/apps/organizations/migrations/0002_backfill_personal_organizations.py`
- `backend/apps/organizations/tests/__init__.py`
- `backend/apps/organizations/tests/test_models_and_services.py`
- `backend/apps/organizations/tests/test_context.py`
- `backend/apps/organizations/tests/test_api.py`
- `backend/apps/organizations/tests/test_tenant_isolation.py`

### 4.2 `enums.py`

Define `OrganizationRole(models.TextChoices)`:

- `OWNER`
- `ADMIN`
- `MEMBER`
- `VIEWER`

Define immutable role sets:

- `WRITE_ROLES = {OWNER, ADMIN, MEMBER}`
- `MEMBER_MANAGER_ROLES = {OWNER, ADMIN}`
- `OWNER_ONLY_ROLES = {OWNER}`

### 4.3 `models.py`

`Organization(TimeStampedModel)` fields:

- `name`: `CharField(max_length=255)`
- `slug`: `SlugField(max_length=255, unique=True)`
- `created_by`: nullable user FK with `SET_NULL`, `related_name="organizations_created"`
- `updated_by`: nullable user FK with `SET_NULL`, `related_name="organizations_updated"`
- `is_personal`: `BooleanField(default=False, db_index=True)`
- `is_active`: `BooleanField(default=True, db_index=True)`
- `metadata`: `JSONField(default=dict, blank=True, validators=[validate_safe_json_object])`

Ordering: `name`, then `id`. Add a conditional unique constraint allowing at most one personal organization for each non-null `created_by`.

`OrganizationMembership(TimeStampedModel)` fields:

- `organization`: FK `CASCADE`, `related_name="memberships"`
- `user`: FK `CASCADE`, `related_name="organization_memberships"`
- `role`: choices `OrganizationRole`, default `MEMBER`, indexed
- `is_active`: Boolean default true, indexed
- `created_by`: nullable user FK `SET_NULL`, `related_name="organization_memberships_created"`

Constraints/indexes:

- unique `(organization, user)`
- index `(user, is_active)`
- index `(organization, role, is_active)`

Do not add invitations, pending-email rows, teams, custom permissions, billing fields, or hard-delete cascades from user creator/updater fields.

### 4.4 `services.py`

Implement:

- `build_unique_organization_slug(name, *, seed=None)` using `slugify`, deterministic suffixes, and user UUID suffix for migration collisions.
- `ensure_personal_organization(user)` inside `transaction.atomic()`. Lock the user row, return the existing personal organization if present, otherwise create one and an active `OWNER` membership. Personal name is `<full_name or email local-part>'s Workspace` and slug is collision-safe.
- `add_existing_member(organization, actor, email, role)` using normalized email, role policy, and `transaction.atomic()`.
- `change_membership_role(membership, actor, role)` with locked organization memberships.
- `remove_membership(membership, actor)` with locked organization memberships.
- `archive_organization(organization, actor)`; only a non-personal organization may be archived and only by an active owner.
- `assert_at_least_one_active_owner(organization)`.

Membership removal is a soft deactivation (`is_active=False`), not row deletion. Re-adding an existing inactive membership reactivates the same row after applying the actor's role limits; it does not create a duplicate history row.

All service errors use stable codes and never reveal whether an email belongs to a user outside a request the actor is authorized to make. Adding an unknown email returns validation code `registered_user_not_found` without any additional account data.

### 4.5 `context.py`

Implement:

- `ORGANIZATION_HEADER = "HTTP_X_TERSUITE_ORGANIZATION_ID"`
- API exceptions with codes `organization_context_required`, `invalid_organization_context`, and `organization_not_found`.
- `resolve_request_organization(request)` using only active memberships and active organizations, caching the result as `request.tersuite_organization` and `request.tersuite_membership`.
- `OrganizationContextMixin.initial()` that calls the resolver after authentication and before action execution.

Do not resolve organization from request bodies, query parameters, project ownership, staff status, or a client-supplied user ID.

### 4.6 `permissions.py`

Implement:

- `HasOrganizationReadAccess`: authenticated active membership.
- `HasOrganizationWriteAccess`: safe methods for all roles, mutation only for `WRITE_ROLES`.
- `CanManageOrganizationMembers`: owner/admin with the owner restrictions delegated to services.
- `OrganizationScopedQuerysetMixin` exposing `get_organization()` and requiring subclasses to filter on `organization`.

### 4.7 serializers and views

Serializers:

- `OrganizationSerializer`: IDs/audit/timestamps read-only; `slug`, `is_personal`, and `is_active` read-only; bounded metadata.
- `OrganizationMembershipSerializer`: include membership ID, organization ID, user ID, email, full name, role, active state, creator, timestamps. Email and user fields are read-only after creation.
- `OrganizationCreateSerializer`: name and optional metadata only.
- `MembershipCreateSerializer`: normalized email and role; reject `OWNER` unless actor is owner.
- `MembershipRoleSerializer`: role only.

`OrganizationViewSet`:

- `GET /organizations/`: list active memberships' organizations; optional `include_inactive=true` only for memberships in those organizations.
- `POST /organizations/`: create non-personal organization and owner membership atomically.
- `GET /organizations/{id}/`: membership-scoped.
- `PATCH /organizations/{id}/`: owner/admin; slug and `is_personal` immutable.
- `POST /organizations/{id}/archive/`: owner only; no unarchive in B2.
- `GET|POST /organizations/{id}/members/`; list defaults to active memberships and accepts `include_inactive=true` for authorized member managers.
- `PATCH|DELETE /organizations/{id}/members/{membership_id}/`; DELETE soft-deactivates and returns HTTP 204.
- No organization `DELETE` method.

Organization directory and nested membership routes are scoped by their organization path and do not require the tenant header. If the tenant header is supplied, it must match the path organization or return 404.

### 4.8 personal-organization migrations

`0001_initial.py` creates both models and constraints.

`0002_backfill_personal_organizations.py`:

- depends on `accounts.0001_initial` and `organizations.0001_initial`;
- uses historical models only;
- creates exactly one personal organization and active owner membership for every existing user, including staff and users with no projects;
- preserves timestamps where the historical API permits;
- uses collision-safe deterministic slugs;
- reverse migration removes only organizations with `is_personal=True` created by this migration and their memberships; it must not delete users.

## 5. Products app

### 5.1 Create files

Create the standard Django app files under `backend/apps/products/`, including `enums.py`, `models.py`, `serializers.py`, `views.py`, `urls.py`, `admin.py`, `migrations/0001_initial.py`, and tests `test_models.py`, `test_api.py`, and `test_plugin_boundary.py`.

### 5.2 `enums.py`

`ProductKind(models.TextChoices)` contains `PLUGIN` and `THEME`. Define `B2_WRITABLE_PRODUCT_KINDS = {ProductKind.PLUGIN}`.

### 5.3 `models.py`

`WordPressProduct(OrganizationOwnedModel)` fields:

- `kind`: choices `ProductKind`, default `PLUGIN`, indexed
- `display_name`: `CharField(max_length=255)`
- `slug`: `SlugField(max_length=190)`
- `version`: `CharField(max_length=30, default="0.1.0")`
- `wordpress_version`: `CharField(max_length=20, default="6.7")`
- `php_version`: `CharField(max_length=20, default="8.2")`
- `metadata`: safe bounded JSON object
- `is_archived`: Boolean default false, indexed

Constraint: unique `(organization, slug)`. Index `(organization, kind, is_archived)`.

`PluginTarget(TimeStampedModel)` fields:

- `product`: one-to-one `WordPressProduct`, `CASCADE`, `related_name="plugin_target"`
- `plugin_slug`: `SlugField(max_length=100)`
- `text_domain`: `SlugField(max_length=100)`
- `namespace_prefix`: `CharField(max_length=100)`
- `main_file`: `CharField(max_length=150)`

Validation:

- parent product must be `PLUGIN`;
- plugin slug pattern is lowercase WordPress folder style and equals product slug in B2;
- text domain defaults to and equals plugin slug in B2;
- namespace prefix matches `^[A-Za-z][A-Za-z0-9_]*$`;
- main file is a basename ending `.php`, contains no path separators, and defaults to `<plugin_slug>.php`.

Do not create `ThemeTarget`, `PluginManifest`, hook tables, capability tables, route tables, component references, or template data in B2.

### 5.4 service and API behavior

Create `products/services.py` with:

- `derive_namespace_prefix(plugin_slug)` producing deterministic StudlyCaps plus underscore-safe output.
- `create_plugin_product(...)` that validates selected organization and creates `WordPressProduct` plus `PluginTarget` atomically.
- `update_plugin_product(...)` that locks both rows, prohibits organization/kind changes, and updates actor attribution.

Public product API:

- `GET /products/` and `GET /products/{id}/`: all active roles.
- `PATCH /products/{id}/`: owner/admin/member.
- no public POST; products are created atomically with projects.
- no public DELETE or archive action; project archive controls the paired product.
- filters: `kind`, `archived`, `search` over display name, slug, plugin slug.

`WordPressProductSerializer` returns nested `plugin_target`. Supplying `THEME`, changing kind, or omitting the plugin target for a plugin write returns `unsupported_product_kind` or a field validation error as appropriate.

## 6. Projects migration and API

### 6.1 Modify files

Modify:

- `backend/apps/projects/models.py`
- `backend/apps/projects/serializers.py`
- `backend/apps/projects/views.py`
- `backend/apps/projects/permissions.py`
- `backend/apps/projects/urls.py`
- `backend/apps/projects/admin.py`
- `backend/apps/projects/tests/test_projects.py`

Create:

- `backend/apps/projects/services.py`
- `backend/apps/projects/migrations/0002_organization_product_ownership.py`
- `backend/apps/projects/tests/test_project_sites.py`
- `backend/apps/projects/tests/test_project_compatibility.py`

### 6.2 final `Project` model

Change `Project` to inherit `OrganizationOwnedModel` and retain:

- `name`, `slug`, `description`, `metadata`, `is_archived`
- `product`: one-to-one `WordPressProduct`, `PROTECT`, `related_name="project"`

Remove persistent fields `user`, `plugin_slug`, `wordpress_version`, and `php_version` only through the new migration after backfill.

Replace `unique_user_project_slug` with `unique_organization_project_slug` on `(organization, slug)`. Replace `for_user()` with `for_organization()`. Slug collision checks use organization. Remove `save()` logic that creates plugin configuration; project/product creation belongs to the transaction service.

Add `ProjectSite(TimeStampedModel)`:

- `organization`: FK Organization `PROTECT`, indexed
- `project`: FK Project `CASCADE`, related name `site_links`
- `site`: FK WordPressSite `CASCADE`, related name `project_links`
- `purpose`: choices `PRIMARY`, `STAGING`, `DEVELOPMENT`, `TEST`, default `PRIMARY`
- `created_by`: nullable user FK `SET_NULL`

Constraints: unique `(project, site)`; index `(organization, purpose)`. Validate that all three organizations match.

### 6.3 project migration

`0002_organization_product_ownership.py` depends on organizations backfill, products initial migration, and sites initial migration. Make removal reversal safe by first altering the four legacy fields to nullable state and placing the reversible restore operation before their forward removal. Perform this sequence:

1. Add nullable `organization`, `created_by`, `updated_by`, and `product` fields.
2. Alter legacy `user`, `plugin_slug`, `wordpress_version`, and `php_version` fields to nullable migration state, then remove `unique_user_project_slug`.
3. For each historical project, find its user's personal organization and owner membership.
4. Create a plugin `WordPressProduct` and `PluginTarget`. Preserve the project slug on Project. Derive the product/plugin slug from the historical non-empty `plugin_slug`, falling back to project slug. For duplicates inside one organization, keep the first by `(created_at, id)`, suffix later values deterministically (`-2`, `-3`, ...), and preserve the exact original in `WordPressProduct.metadata["migration"]["legacy_plugin_slug"]`.
5. Set project organization, creator/updater, and product.
6. Verify in migration code that no project remains unassigned; raise a deterministic migration error if the invariant fails.
7. Alter required fields to non-null where specified.
8. Add the organization uniqueness constraint and indexes.
9. Before the forward `RemoveField` operations, include a reversible no-op/restore `RunPython`: its reverse function runs after Django has re-added the nullable legacy columns, repopulates them from `created_by` and product/plugin data, and fails deterministically if no creator/owner can be resolved. Then remove `user`, `plugin_slug`, `wordpress_version`, and `php_version` columns in the forward direction.
10. Create `ProjectSite`.

On reversal, Django first re-adds the legacy columns as nullable, the reverse `RunPython` populates them from product data and recreates `user` from `created_by` or an active owner membership, and the reversed `AlterField` operations restore non-null state before the old constraint is restored. Do not delete product or organization rows from this reverse function; their app migrations own those tables.

### 6.4 project serializers/services

`ProjectService.create_project()` atomically creates the product/plugin target and project for the selected organization and actor. `archive_project()` and `unarchive_project()` lock and change both project and product archive flags together.

The v1 project representation includes:

- `organization_id`, `created_by_id`, `updated_by_id`
- nested `product`
- existing project fields and generation count
- compatibility aliases `user_id`, `plugin_slug`, `wordpress_version`, and `php_version`, each sourced from the authoritative creator/product records

For backward compatibility, `plugin_slug`, `wordpress_version`, and `php_version` may be accepted on create/update, but custom serializer logic must translate them into the single authoritative product fields and reject conflicts with nested product data. `user_id` is always read-only and must never select or replace the actor. Mark all four aliases deprecated in the API contract. Never recreate duplicate database columns.

Project ViewSet uses organization context, `for_organization()`, `select_related("product", "product__plugin_target")`, and write-role permissions. Cross-tenant project IDs return 404. Existing archive/unarchive URLs remain.

Add project-site actions:

- `GET|POST /projects/{id}/sites/`
- `DELETE /projects/{id}/sites/{project_site_id}/`

POST accepts `site_id` and `purpose`; both project and site must belong to the selected organization.

## 7. Sites app

### 7.1 Create files

Create the standard app files under `backend/apps/sites/`, including `enums.py`, `models.py`, `services.py`, `serializers.py`, `views.py`, `urls.py`, `admin.py`, `migrations/0001_initial.py`, and tests `test_models.py`, `test_api.py`, `test_profiles.py`, `test_secret_rejection.py`, and `test_tenant_isolation.py`.

### 7.2 enums and models

Enums:

- `SiteEnvironment`: `PRODUCTION`, `STAGING`, `DEVELOPMENT`, `LOCAL`
- `SiteConnectionStatus`: `UNVERIFIED`, `CONNECTED`, `DISCONNECTED`, `ERROR`
- `SiteProfileSource`: `MANUAL`, `WORDPRESS_CLIENT`

`WordPressSite(OrganizationOwnedModel)` fields:

- `name`: Char 255
- `url`: URL 2048 containing the canonical normalized URL
- `environment`: choices, default `PRODUCTION`, indexed
- `connection_status`: choices, default `UNVERIFIED`, indexed
- `next_profile_version`: positive integer default 1
- `last_profiled_at`: nullable datetime
- `metadata`: safe bounded JSON object
- `is_archived`: Boolean default false, indexed

Constraints/indexes: unique `(organization, url)` and index `(organization, environment, is_archived)`.

Public B2 serializers must make `connection_status`, `next_profile_version`, and `last_profiled_at` read-only. B2 public writes cannot claim `CONNECTED`.

`SiteProfileSnapshot(TimeStampedModel)` fields:

- `organization`: FK Organization `PROTECT`, indexed
- `site`: FK WordPressSite `CASCADE`, related name `profile_snapshots`
- `version`: positive integer
- `source`: choices, default `MANUAL`
- `wordpress_version`: Char 20
- `php_version`: Char 20
- `multisite`: Boolean default false
- `locale`: Char 32, blank
- `timezone`: Char 64, blank
- `active_theme`: safe JSON object
- `active_plugins`: JSON list, default list
- `server`: safe JSON object
- `capabilities`: safe JSON object
- `health`: safe JSON object
- `checksum_sha256`: Char 64, read-only
- `created_by`: nullable user FK `SET_NULL`

Constraints: unique `(site, version)`; index `(organization, created_at)`. Validate organization alignment and apply recursive forbidden-key checks to every JSON field, including list entries.

### 7.3 services and API

`create_site_profile_snapshot()` runs in `transaction.atomic()`, locks the site row, allocates `next_profile_version`, computes SHA-256 over canonical non-secret profile JSON, creates the immutable snapshot, increments the next version, and sets `last_profiled_at`.

Site API:

- list/create/retrieve/patch/archive; no delete;
- normalize URL before uniqueness validation;
- filters `environment`, `status`, `archived`, `search`;
- all records tenant-filtered.

Profile API:

- `GET|POST /sites/{id}/profiles/`
- `GET /sites/{id}/profiles/{snapshot_id}/`
- no PATCH, PUT, or DELETE;
- public POST accepts only source `MANUAL`; `WORDPRESS_CLIENT` is reserved for the future authenticated WordPress client.

No view or service may perform network I/O.

## 8. Conversations app

### 8.1 Create files

Create the standard app files under `backend/apps/conversations/`, including `enums.py`, `models.py`, `services.py`, `serializers.py`, `views.py`, `urls.py`, `admin.py`, `migrations/0001_initial.py`, and tests `test_models.py`, `test_api.py`, `test_messages.py`, `test_idempotency.py`, and `test_tenant_isolation.py`.

### 8.2 enums and models

Enums:

- `ConversationStatus`: `ACTIVE`, `ARCHIVED`
- `ConversationPurpose`: `PROJECT_DISCOVERY`, `PROJECT_PLANNING`, `GENERAL`
- `MessageRole`: `USER`, `ASSISTANT`, `SYSTEM`, `TOOL`
- `MessageFormat`: `PLAIN_TEXT`, `MARKDOWN`

`Conversation(OrganizationOwnedModel)` fields:

- `project`: FK Project `CASCADE`, related name `conversations`
- `title`: Char 255
- `purpose`: choices, default `PROJECT_DISCOVERY`, indexed
- `status`: choices, default `ACTIVE`, indexed
- `next_message_sequence`: positive big integer default 1
- `last_message_at`: nullable datetime, indexed
- `metadata`: safe bounded JSON object

Constraint/index: `(organization, project, status)` index. Validate project organization equality.

`ConversationMessage(TimeStampedModel)` fields:

- `organization`: FK Organization `PROTECT`, indexed
- `conversation`: FK Conversation `CASCADE`, related name `messages`
- `sequence`: positive big integer
- `role`: choices MessageRole, indexed
- `author`: nullable user FK `SET_NULL`, related name `conversation_messages`
- `content`: TextField
- `content_format`: choices, default `MARKDOWN`
- `client_message_id`: nullable UUID
- `metadata`: safe bounded JSON object

Constraints:

- unique `(conversation, sequence)`
- conditional unique `(conversation, client_message_id)` when client ID is non-null
- index `(organization, conversation, sequence)`

Validate organization alignment. Public serializers enforce content length `1..100000` characters and metadata limit 16 KiB. No public update or delete exists.

### 8.3 message service and API

`ConversationMessageService` implements:

- `append_user_message(conversation, actor, content, client_message_id, metadata, content_format)`
- `append_internal_message(conversation, role, content, metadata, *, actor=None)` for later trusted backend callers; reject role `USER` here

Both lock the conversation, reject archived conversations, allocate one sequence, and update `last_message_at`. For a repeated non-null client ID, `append_user_message` returns the existing message without adding a sequence and indicates replay.

Conversation API:

- list/create/retrieve/patch/archive; no delete;
- selected organization plus optional `project_id`, `status`, `purpose`, `search` filters;
- create resolves project only inside the selected organization;
- viewers cannot create conversations or messages;
- archive is idempotent.

Message API:

- `GET|POST /conversations/{id}/messages/`
- `GET /conversations/{id}/messages/{message_id}/`
- public POST either omits role or supplies `USER`; all other roles return 400 code `message_role_not_allowed`;
- first create returns 201 with `idempotent_replay=false`; duplicate client ID returns 200 with the original message and `idempotent_replay=true`;
- list ordering is sequence ascending and uses existing pagination conventions.

B2 must not create an agent run, OpenHands session, completion, tool event, or automatic assistant response.

## 9. Accounts integration

Modify:

- `backend/apps/accounts/serializers.py`
- `backend/apps/accounts/views.py`
- `backend/apps/accounts/tests/test_auth.py`

Registration runs user creation and `ensure_personal_organization()` inside one outer `transaction.atomic()`. If organization creation fails, the user and token are not committed.

Extend `UserSerializer` with read-only `organization_memberships`, each containing organization ID/name/slug/personal flag and role. Do not expose membership creator internals here.

Registration and login responses retain existing token and user keys. Add tests for exactly one personal organization, owner role, rollback, and membership output.

Do not change the authentication scheme, token format, password policy, or logout behavior in B2.

## 10. Existing generation-domain tenant migration

### 10.1 Modify files

Modify:

- `backend/apps/generations/models.py`
- `backend/apps/generations/serializers.py`
- `backend/apps/generations/views.py`
- `backend/apps/generations/permissions.py`
- `backend/apps/generations/admin.py`
- `backend/apps/generations/services/execution_service.py` only where renamed fields require it
- every existing generation test that constructs or asserts user-owned projects/generations

Create `backend/apps/generations/migrations/0002_organization_audit_ownership.py`.

### 10.2 final Generation ownership

`Generation` inherits `OrganizationOwnedModel`.

- Rename `user` to `created_by` using `migrations.RenameField` so existing values are preserved.
- Add nullable `organization` and `updated_by`, backfill organization from project, then make organization required.
- Replace the `(user, status)` index with `(organization, status)` and add `(created_by, status)` only if query evidence justifies it.
- `save()` must validate organization equals project organization; it must not overwrite creator from project.
- `GenerationQuerySet.for_user()` becomes `for_organization()`.

Creation resolves the project in the selected organization and assigns request user as creator/updater. Existing response field `user` remains a deprecated read-only alias sourced from `created_by`; add explicit `organization_id`, `created_by_id`, and `updated_by_id`.

Generation, step, run, workspace, and artifact querysets filter through generation organization. Replace owner permissions with organization read/write permissions while preserving read-only child-resource rules and all current state-machine restrictions.

Do not change generation statuses, transitions, task dispatch, runtime selection, workspace semantics, artifact storage, or OpenHands behavior; B3 owns the workflow redesign.

## 11. Control Center compatibility

Modify only the fields and queries broken by the B2 ownership/product migration:

- `backend/apps/control_center/serializers.py`
- `backend/apps/control_center/views.py`
- `backend/apps/control_center/tests/test_control_center_api.py`
- `backend/apps/control_center/tests/test_control_center_detail_api.py`
- `backend/apps/control_center/tests/test_control_center_actions_api.py`
- `backend/apps/control_center/tests/test_control_center_knowledge_and_projects_api.py`

Required changes:

- project staff list selects organization, creator, product, and plugin target;
- project output retains current plugin compatibility fields sourced from product;
- generation user displays source from `created_by`;
- searches use `created_by__email` and `product__plugin_target__plugin_slug`;
- existing staff-wide behavior remains staff-only and is not forced through a tenant header;
- no new Control Center feature, action, metric, or frontend is added.

## 12. Settings, URL, and admin registration

Modify `backend/config/settings/base.py` to add apps in dependency order:

1. accounts/core remain existing
2. organizations
3. products
4. sites
5. projects
6. conversations
7. generations and remaining apps

Modify `backend/config/urls.py` to add the exact `/api/v1/organizations/`, `/products/`, `/sites/`, and `/conversations/` includes. Preserve all existing routes.

Register all new models in their app admin modules with organization, status/kind/role, creator, archive, and timestamp list filters. Admin must not display raw metadata containing possible sensitive values in list columns.

## 13. API contract update

Modify `docs/API-CONTRACT.md` rather than creating a competing API document.

Required content:

- organization context header/default rules and stable errors;
- role matrix;
- organization and membership endpoints/methods;
- nested project/product representation and deprecated compatibility aliases;
- product endpoints and plugin-only write restriction;
- site, profile snapshot, and project-site endpoints;
- conversation/message endpoints, message idempotency response, and archive behavior;
- explicit statement that B2 chat persistence does not invoke an agent;
- existing generation endpoints updated from user ownership to organization membership;
- cross-tenant 404 behavior;
- standard pagination and error envelope.

Use request/response examples with fictional UUIDs and no secrets.

## 14. Data-model contract update

Modify `docs/DATA-MODEL.md` to replace the user-rooted tree with the organization-rooted model and document:

- all B2 tables, fields, constraints, indexes, and relationships;
- creator/updater semantics;
- personal organization backfill;
- project/product/plugin separation;
- project-site many-to-many association;
- immutable snapshot versioning;
- conversation message ordering/idempotency;
- migrated generation ownership;
- legacy column removal and API aliases;
- B3-owned generation lifecycle explicitly unchanged.

Do not rewrite later workflow, sandbox, artifact-storage, or runtime sections beyond the ownership terms needed for accuracy.

## 15. README and report

Modify `README.md` only to add:

- personal organization behavior;
- `X-Tersuite-Organization-ID` usage and one-membership default;
- B2 migration/test commands;
- explicit statement that sites are metadata-only and conversations do not yet call agents.

Create `docs/reports/B2-CORE-DOMAINS-REPORT.md` using the exact development-protocol report structure. Include every file, migration, removal, compatibility alias, command, test count, unresolved issue, and scope deviation.

## 16. Migration test

Create:

- `backend/tests/migrations/__init__.py`
- `backend/tests/migrations/test_b2_core_domain_migration.py`

Use Django `MigrationExecutor` with a transactional test. Migrate to the B1 leaf state, create at least:

- two users;
- two projects with the same project slug under different users and at least two historical projects in one user's organization with the same plugin slug;
- a generation and at least one child record;
- a user without a project.

Migrate forward to B2 and assert:

- every user has exactly one personal organization and active owner membership;
- projects retain UUID/data and have distinct organization/product/plugin targets;
- old plugin versions/slugs moved exactly when unique, duplicate plugin slugs receive deterministic suffixes, and every changed original is preserved in migration metadata;
- generation and child UUIDs/relations remain intact;
- generation creator and organization are correct;
- organization-scoped uniqueness permits the original cross-user duplicate slug;
- no historical data was silently dropped.

Restore the database to current leaf migrations at test teardown even after assertion failure.

## 17. Required behavioral tests

At minimum, add or update tests for:

### Organization/context

- registration personal organization and owner membership;
- multiple memberships require header;
- sole membership defaults safely;
- malformed header 400;
- nonmember/inactive membership/inactive organization 404;
- staff has no public bypass;
- owner/admin/member/viewer matrix;
- last owner cannot be demoted, deactivated, removed, or leave;
- admin cannot manage owner;
- unknown membership/user IDs do not leak data.

### Products/projects

- product and plugin target created atomically;
- `THEME` public write rejected;
- organization/product/project alignment;
- legacy aliases use product source and conflicting payloads fail;
- archive/unarchive updates project and product together;
- identical project/plugin slugs are allowed in separate organizations but not one organization;
- every project list/detail/mutation is tenant-isolated.

### Sites/profiles

- URL normalization and uniqueness;
- credential/query/scheme rejection;
- status cannot be forged as connected;
- forbidden secret keys rejected recursively without value disclosure;
- snapshot version increments under service calls;
- snapshot update/delete returns 405;
- project-site cross-tenant attachment fails 404;
- site/profile list and detail isolation.

### Conversations/messages

- project/organization alignment;
- viewer read-only;
- public non-user role rejected;
- sequence ordering;
- repeated client ID returns same row and no sequence gap;
- same client ID allowed in different conversations;
- archived conversation blocks messages;
- message update/delete returns 405;
- conversation/message list, detail, and create are tenant-isolated;
- creating a message creates no generation, agent run, runtime session, or assistant response.

### Existing domains

- generation creation by a non-project-creator organization member;
- generation creator attribution remains the initiating member;
- viewer cannot create or transition;
- all child resources honor membership-based tenant scoping;
- Control Center staff tests remain passing;
- all B1 health, runtime, and credential-boundary tests remain passing.

## 18. Removal ledger

Search static and dynamic references before removal. Classify at minimum:

| Candidate | Required classification/action |
|---|---|
| `Project.user` database field | `REPLACE` with organization plus creator attribution after data backfill |
| Project plugin/version database fields | `REPLACE` with product/plugin target storage; keep serializer aliases only |
| `unique_user_project_slug` | `REPLACE` with organization uniqueness |
| `ProjectQuerySet.for_user()` | `REPLACE` with `for_organization()` |
| project `save()` plugin configuration logic | `REMOVE`; creation service owns atomic product setup |
| `IsProjectOwner` | `REPLACE` with organization context/role permissions |
| `Generation.user` | `RENAME/REFACTOR` to `created_by`; preserve API alias temporarily |
| generation `for_user()` and owner permission classes | `REPLACE` with organization-scoped access |
| duplicated tenant lookup helpers | `REMOVE` in favor of organizations context/mixins |
| existing migrations | `KEEP`; never edit or delete |
| B1 runtime/OpenHands code | `KEEP`; outside B2 |
| existing generation lifecycle | `DEFER` redesign to B3 |
| frontend and WordPress client | `DEFER` |

The report must list the exact references searched and every removed symbol/field/constraint/index.

## 19. Protected files and behavior

Do not modify unless an import or ownership rename in this specification makes a listed test adjustment unavoidable:

- `backend/runtime/**`
- OpenHands settings and credential handling
- B1 health/readiness behavior
- dependency versions or `uv.lock`
- generation status enum/state-machine rules
- workspace/artifact storage behavior
- realtime event contract
- frontend/**
- WordPress client/plugin code
- B1 phase, detailed specification, execution prompt, and frozen report
- active Control Center endpoint behavior beyond field compatibility

No future app such as requirements, specifications, planning, approvals, workflows, agents, knowledge, components, sandbox, packaging, billing, or themes may be created in B2.

## 20. Required verification commands

Run from `backend/` unless stated otherwise:

```bash
uv --version
python --version
uv lock --check
uv sync --frozen --extra dev
uv run python manage.py check
uv run python manage.py makemigrations --check --dry-run
uv run python manage.py migrate --plan
uv run pytest apps/organizations apps/products apps/projects apps/sites apps/conversations tests/migrations -q
uv run pytest apps/generations apps/control_center apps/accounts -q
uv run pytest
uv run ruff check --select F401,I001 apps/organizations apps/products apps/projects apps/sites apps/conversations apps/accounts apps/generations apps/control_center apps/core config tests/migrations
docker compose config
docker build -t tersuite-backend:b2 .
```

From repository root:

```bash
git diff --check <B2_BASE_SHA>
git status --short
```

Also run repository searches proving:

- no executable code uses `Project.user` or `Generation.user` as authorization;
- no removed project database field remains a second source of truth;
- no public tenant queryset is unscoped;
- no B2 site code performs network I/O or stores credential fields;
- no B2 conversation code imports runtime/OpenHands or creates agent runs;
- no historical migration changed;
- no frontend file changed;
- no dependency or lockfile changed.

If Docker is unavailable locally, record the commands as not executed locally and require the GitHub workflow to run them successfully. Do not fabricate results.

## 21. Exit criteria

- main/B1 ancestry verified and dedicated B2 branch used;
- schema and backfill migrations are reversible and tested;
- exact organization context and role rules are executable;
- product/plugin target is authoritative and theme writes are blocked;
- projects, sites, snapshots, conversations, messages, generations, and child resources are tenant-isolated;
- audit creator/updater fields are correct;
- legacy compatibility aliases have one source of truth;
- no site credentials or forbidden JSON values are stored or leaked;
- message ordering/idempotency is deterministic;
- all existing and new tests pass;
- documentation matches code;
- removal ledger is complete;
- no out-of-scope feature or refactor exists;
- GitHub CI passes and the pushed commit is independently reviewed.
