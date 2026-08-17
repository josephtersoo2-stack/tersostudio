# Tersuite AI Studio — Master Implementation Roadmap

**Status:** Authoritative implementation plan

**Version:** 2.0

**Primary delivery order:** Backend first, then web studio, WordPress client, and enterprise expansion

**Execution engine:** Official OpenHands Software Agent SDK and Agent Server

**Primary product:** WordPress plugin engineering

**Future product boundary:** WordPress theme engineering

---

## 1. Product Mission

Tersuite AI Studio is a WordPress-native software engineering platform that converts a user's idea into an approved, traceable, tested, secure, and deployable WordPress product.

The initial product is a professional WordPress plugin builder. Users plan with Tersuite through chat, approve a formal specification and implementation plan, observe specialist agents implement the work, review evidence, test the plugin in disposable WordPress sandboxes, and explicitly approve installation or activation on a connected WordPress site.

Tersuite is not a generic chatbot that happens to write PHP. The entire product revolves around WordPress:

- WordPress terminology and workflows;
- WordPress Core and ecosystem knowledge;
- plugin-family feature catalogues;
- licensed reusable components;
- WordPress-specific agent roles;
- WordPress compatibility and security policies;
- real WordPress sandbox validation;
- safe WordPress delivery, activation, monitoring, and rollback.

The long-term platform must support WordPress themes without weakening the plugin-first focus. Theme implementation is deferred, but core domain boundaries must avoid assuming that every future product is a plugin.

---

## 2. Non-Negotiable Product Principles

1. **WordPress-native, not generic** — WordPress rules, APIs, compatibility, security, packaging, and user experience are first-class domain concepts.
2. **Plan before build** — planning never changes source code. Implementation begins only after explicit approval.
3. **Approved contracts are immutable** — an approved specification and implementation plan are versioned and hash-locked. Later changes create a new revision.
4. **Tersuite owns orchestration** — Django/PostgreSQL controls workflow state, approvals, dependencies, retries, cancellation, and auditability. OpenHands executes agent conversations and tools.
5. **Reuse before generation** — agents must search the approved component and template registry before writing new infrastructure.
6. **Evidence before completion** — an agent's statement that work is finished is not proof. Deterministic validation, independent review, and sandbox evidence decide completion.
7. **Independent review** — the implementing agent cannot approve its own work.
8. **Isolated execution** — every major work package receives an isolated workspace or Git worktree.
9. **No untested activation** — every release passes disposable WordPress QA and a target-site preflight before user-approved activation.
10. **Safe learning** — generated code, failures, fixes, and outcomes improve Tersuite only through a governed evidence and promotion pipeline.
11. **Truthful phase reporting** — a phase is complete only when its exit criteria and verification evidence are present in the repository.
12. **Preserve working code** — re-baselining the existing application means auditing and correcting it, not deleting correct work or performing an unnecessary rewrite.

---

## 3. System Boundaries

```text
WordPress Studio Plugin ─┐
                         ├──> Django API / Channels ──> Durable Workflow Coordinator
Tersuite Web Studio ─────┘                                  │
                                                            ├──> WordPress Intelligence
                                                            ├──> Component / Blueprint Registry
                                                            ├──> OpenHands Agent Server
                                                            ├──> Isolated Workspaces
                                                            ├──> WordPress Sandbox QA
                                                            ├──> Artifact / Release Service
                                                            └──> Experience & Evaluation System
```

### 3.1 Tersuite control plane

Django and PostgreSQL are the source of truth for users, organizations, sites, projects, conversations, requirements, specifications, plans, approvals, workflows, work packages, agent runs, events, findings, artifacts, sandbox results, deployments, usage, and audit records.

Celery executes bounded background jobs. Celery is not the durable workflow state machine. The coordinator must persist all state transitions and implement idempotency, leases, heartbeats, cancellation, retry rules, and transactionally published events.

### 3.2 OpenHands execution plane

OpenHands provides remote conversations, tools, event streaming, workspace execution, interruption, conversation state, and optional bounded nested delegation.

Primary Tersuite specialist agents are separate Tersuite-managed OpenHands conversations. OpenHands `TaskToolSet` may be used only for bounded internal delegation such as code exploration or running a focused test command. It is not the primary enterprise workflow orchestrator.

### 3.3 WordPress delivery plane

The WordPress client is a thin, permission-aware client. It communicates with Tersuite, supplies an authorized site profile, displays plans and progress, previews files and reports, verifies signed artifacts, stages releases, performs preflight checks, and executes explicit activation or rollback actions.

Raw LLM credentials and Agent Server credentials must never be exposed to the WordPress browser or stored in generated plugins.

---

## 4. Canonical User Workflow

### 4.1 Discover mode

1. The user describes the desired plugin.
2. Tersuite optionally reads an authorized, redacted `SiteProfile`.
3. The plugin-family classifier selects relevant WordPress blueprints and knowledge sets.
4. The feature recommender proposes essential, recommended, advanced, and enterprise capabilities.
5. The agent asks only the business questions that cannot safely be inferred.
6. Requirements are continuously normalized into uniquely identified records.

### 4.2 Plan mode

Plan mode is read-only with respect to project source code. It produces:

- a feature selection;
- a versioned `ProductSpecification`;
- a `DataContract`;
- a `UIContract` where applicable;
- an implementation strategy (`ONE_SHOT`, `PHASED`, `INCREMENTAL`, or `HOTFIX`);
- an `ImplementationPlan` containing milestones, work packages, dependencies, risks, reusable components, tests, budgets, and sandbox targets.

### 4.3 Approval gate

The user can approve, remove, add, modify, or reorder features and plan items. On approval:

- the specification and plan receive immutable versions and hashes;
- an `ApprovalRecord` records the actor and time;
- every downstream task references the approved versions;
- later scope changes create a revision rather than silently mutating the approved contract.

### 4.4 Build mode

1. The coordinator converts approved milestones into a dependency graph of `WorkPackage` records.
2. The component composer selects the approved kernel, modules, blueprint, dashboard templates, and validation suites.
3. Ready work packages are assigned to versioned WordPress agent profiles.
4. Each major agent runs in an isolated workspace or worktree.
5. Agents submit candidate results, changed-file manifests, requirement coverage, validation evidence, and commits.
6. Deterministic validators independently rerun required checks.
7. The integration agent combines accepted work.
8. Reviewer and security agents compare the integrated result with the approved specification.
9. Structured findings produce correction packages until blocking findings are resolved or the workflow escalates to a human.

### 4.5 Sandbox and release mode

1. A release candidate is packaged.
2. Fast previews may run in WordPress Playground where appropriate.
3. Authoritative QA runs in disposable Docker WordPress environments.
4. The test matrix covers configured WordPress, PHP, database, WooCommerce, and integration profiles.
5. Installation, activation, deactivation, reactivation, upgrade, migration, uninstall, rollback, REST, cron, UI, security, and domain flows are tested.
6. The artifact service produces a signed ZIP, checksum, manifest, changelog, test report, security report, and rollback artifact.
7. The WordPress client downloads and verifies the artifact, performs a site preflight, and stages it.
8. The user explicitly approves activation.
9. Post-activation health checks trigger rollback when the release is unhealthy.

---

## 5. Build Strategies

| Strategy | Use | Orchestration |
|---|---|---|
| `ONE_SHOT` | Small, low-risk plugin | One implementation milestone; reviewer and full QA still mandatory |
| `PHASED` | Multiple domains, payments, migrations, complex UI, or large scope | Dependency-ordered milestones with integration checkpoints |
| `INCREMENTAL` | Updating a Tersuite-managed product | Branch from the last approved release and preserve migration history |
| `HOTFIX` | Narrow defect or security repair | Minimal patch, focused reproduction, full relevant regression and rollback evidence |

The user or planner may recommend a strategy. Tersuite policy may require `PHASED` for high-risk work. No strategy bypasses review, sandbox QA, packaging integrity, or activation approval.

---

## 6. WordPress Intelligence Platform

The existing knowledge work becomes one part of a larger WordPress Intelligence Platform.

### 6.1 Authoritative knowledge

Knowledge sources include versioned and reviewed material for:

- WordPress Core APIs, hooks, lifecycle, security, privacy, i18n, REST, cron, filesystem, and WP-CLI;
- Gutenberg and WordPress admin interfaces;
- WooCommerce and selected ecosystem integrations;
- plugin architecture, database, testing, performance, accessibility, and distribution;
- plugin-family domain rules.

Every source records authority, provenance, license, effective date, compatibility scope, checksum, and review status.

### 6.2 Plugin-family ontology

`PluginFamily` and `FeatureDefinition` records describe normal capabilities, dependencies, incompatibilities, risk, and acceptance tests for affiliate, membership, booking, WooCommerce, LMS, CRM, directory, forms, analytics, payment, notification, and other plugin families.

The system uses this ontology to recommend a complete starting feature set so users do not need to invent every requirement themselves.

### 6.3 Professional product research

Existing enterprise plugins may inform feature maps, public workflows, terminology, reports, integrations, and architectural lessons. Sources must be public, properly licensed, owned, commissioned, or explicitly authorized.

Tersuite must not ingest nulled software, bypass licensing, copy protected branding/assets, or promote third-party code into reusable components without verified provenance and license compatibility.

### 6.4 Component registry

Agents follow `REUSE -> EXTEND -> GENERATE`.

Reusable assets are versioned, tested, licensed, and reviewed:

- minimal plugin kernel;
- compatibility and lifecycle support;
- settings, capability, migration, REST, logging, notifications, cron, privacy, updater, safe-mode, and integration modules;
- test harnesses and release tooling.

Not every plugin receives every component. The composer includes only approved dependencies to avoid bloat.

### 6.5 Blueprints and UI contracts

A blueprint defines a plugin family's feature catalogue, architecture defaults, data patterns, agent team, reusable modules, dashboard presets, knowledge sets, and validation suites.

Admin and user dashboard templates are schema-driven. Each control declares its data binding, capability, sanitization, validation, action, and tests. A visual prototype may be approved before implementation, producing an immutable `UIContract`.

### 6.6 Tersuite product manifest

Every project and release records a machine-readable manifest describing its product kind, blueprint, kernel, component versions, requirements, WordPress/PHP compatibility, hooks, tables, options, capabilities, routes, cron events, migrations, tests, and artifact hashes.

The manifest is the primary input for future updates, conflict checks, support, and theme/plugin evolution.

---

## 7. Agent and Orchestration Architecture

### 7.1 Durable agent profiles

`AgentProfile` versions define role, WordPress instructions, tools, skills, model policy, budget, permission policy, validation policy, and allowed scope.

Initial profiles:

1. Coordinator policy assistant
2. Feature discovery agent
3. Planner
4. WordPress architect
5. Domain specialists
6. WordPress backend engineer
7. Database/migration engineer
8. Admin/UI engineer
9. Integration engineer
10. Test engineer
11. Security reviewer
12. Integrator
13. Reviewer/critic
14. Sandbox operator
15. Packaging/release agent

### 7.2 Work-package contract

Every `WorkPackage` declares:

- approved specification and plan versions;
- requirement IDs;
- agent profile version;
- dependencies;
- owned paths;
- base commit;
- deliverables;
- validation commands;
- maximum iterations, time, and budget;
- result manifest and commit;
- retry and correction history.

An agent returns `CANDIDATE_COMPLETE`, never directly `COMPLETED`. Only validation and review gates can complete a package.

### 7.3 Isolation and integration

Every major work package uses a unique workspace or worktree. Overlapping path ownership is rejected unless the coordinator creates an explicit shared integration task. Accepted work is merged into an integration branch by the integrator, not by parallel workers writing to one directory.

### 7.4 Finding and repair loop

Every finding records requirement ID, severity, expected behavior, actual behavior, evidence, affected paths, repair instruction, owner, and retest command.

- `CRITICAL` and `HIGH`: mandatory repair;
- `MEDIUM`: repair or explicit authorized waiver;
- `LOW`: repair or recorded follow-up;
- retry limits: escalation prevents infinite loops.

---

## 8. Governed Self-Improvement and Experience Memory

Tersuite must learn from generated products, failures, reviewer findings, sandbox failures, production incidents, repair attempts, and successful fixes. This is an evidence system, not uncontrolled online model training.

### 8.1 Experience ledger

The backend records:

- the originating specification, plan, blueprint, components, agent/model versions, and site/sandbox profile;
- normalized error fingerprint and failure category;
- reproduction steps and relevant redacted logs;
- attempted fixes and their outcomes;
- final verified root cause and resolution;
- tests that prove the resolution;
- compatibility boundaries;
- recurrence count and confidence.

Core records include `FailureOccurrence`, `ErrorFingerprint`, `ResolutionAttempt`, `VerifiedResolution`, `KnowledgeCandidate`, `GoldenProject`, and `EvaluationCase`.

### 8.2 Learning pipeline

```text
Capture -> Redact -> Normalize -> Fingerprint -> Deduplicate -> Diagnose
        -> Attempt Fix -> Verify -> Review -> Promote -> Retrieve -> Re-evaluate
```

Only verified resolutions can be promoted. Failed attempts remain useful negative evidence but are never recommended as fixes.

### 8.3 Generated-product corpus

Generated products remain attached to their specifications, manifests, diffs, tests, findings, and outcomes.

- drafts and failed builds are error/evaluation data;
- sandbox-passing builds are candidates;
- human-approved, production-proven releases may become `GoldenProject` examples;
- reusable code is promoted only through license, generalization, security, compatibility, and test review.

### 8.4 Retrieval before model training

Initial improvement uses case-based retrieval, structured patterns, component reuse, and evaluation. Later offline fine-tuning may use a curated, licensed, redacted dataset. Tersuite must never automatically change model weights from live customer code or raw incidents.

### 8.5 Safety and privacy

Secrets, credentials, personal data, payment data, license keys, customer content, and sensitive logs are removed or access-restricted before indexing. Tenant-private experiences remain tenant-private unless explicit rights and promotion policies permit broader use.

Every promoted lesson is versioned, reversible, attributable, and periodically revalidated against supported WordPress environments.

---

## 9. Plugin-First, Theme-Ready Domain Design

The first implementation supports `ProductKind.PLUGIN`. Core contracts must also allow a future `ProductKind.THEME` without making current plugin models vague.

Theme-ready boundaries:

- `WordPressProduct` / `ProductTarget` stores shared identity and compatibility;
- `PluginManifest` stores plugin-specific hooks, capabilities, tables, routes, and lifecycle;
- future `ThemeManifest` can store templates, patterns, styles, blocks, and theme configuration;
- `Blueprint.kind`, `Component.kind`, `KnowledgeSet.kind`, `Artifact.kind`, `SandboxProfile.kind`, and `QualityPolicy.kind` are explicit;
- a `WordPressProductAdapter` interface owns product-specific planning, validation, packaging, and sandbox rules.

Do not implement theme generation during the plugin backend milestones. First establish the boundary and tests proving plugin behavior remains explicit.

---

## 10. Backend Domain Modules

```text
backend/apps/
├── accounts/
├── organizations/
├── sites/
├── projects/
├── conversations/
├── requirements/
├── specifications/
├── planning/
├── approvals/
├── workflows/
├── agents/
├── workspaces/
├── knowledge/
├── plugin_families/
├── components/
├── blueprints/
├── manifests/
├── validation/
├── reviews/
├── sandboxes/
├── artifacts/
├── deployments/
├── experience/
├── evaluations/
├── usage/
├── billing/
├── realtime/
├── notifications/
└── audit/
```

Modules may be combined while small, but their domain boundaries and ownership must remain clear. Core domains must not import OpenHands implementation internals.

---

## 11. Canonical Lifecycle

```text
DRAFT
  -> DISCOVERY
  -> SPECIFICATION_DRAFT
  -> PLAN_DRAFT
  -> AWAITING_APPROVAL
  -> APPROVED
  -> SCHEDULED
  -> BUILDING
  -> INTEGRATING
  -> REVIEWING
  -> CORRECTING (loop)
  -> SANDBOX_QA
  -> RELEASE_CANDIDATE
  -> AWAITING_DEPLOYMENT_APPROVAL
  -> STAGED
  -> ACTIVE
```

Control states: `PAUSED`, `CANCELLING`, `CANCELLED`, `FAILED`, `TIMED_OUT`, `BLOCKED`, `ROLLED_BACK`, and `SUPERSEDED`.

Every transition declares allowed origins, authorization, idempotency key, side effects, audit event, and compensation behavior.

---

## 12. Backend-First Implementation Sequence

The repository already contains partial work. Each milestone begins with a gap audit, preserves correct code, corrects defects, and adds only the scoped capability. Existing later-phase work remains provisional until its prerequisites pass.

### B0 — Architecture re-baseline

Deliverables:

- this master roadmap;
- system and module contracts aligned with it;
- corrected AGENTS operating rules;
- explicit plugin-first/theme-ready boundary;
- current implementation inventory and gap matrix.

Exit criteria: no contradictory authoritative documents and every backend milestone has testable boundaries.

### B1 — Reproducible backend foundation

Deliverables:

- supported Python version fixed and documented;
- deterministic dependency management and committed lock/constraints;
- OpenHands packages install together at the selected release;
- PostgreSQL, Redis, Celery, and Channels configuration validated;
- health/readiness checks;
- baseline migrations and test commands;
- all secrets read through configuration and never serialized.

Exit criteria: a clean environment installs reproducibly and the backend baseline tests pass.

### B2 — Core identity, product, project, and site domains

Deliverables:

- organization-scoped authorization;
- `ProductKind` and plugin-first product target;
- projects, connected-site metadata, site-profile snapshots, conversations, and messages;
- audit ownership and tenant isolation;
- versioned APIs and serializers.

Exit criteria: cross-tenant access tests, lifecycle tests, and API contract tests pass.

### B3 — Durable generation and workflow kernel

Deliverables:

- corrected lifecycle state machine;
- generation, milestone, step, workflow run, work package, dependency, lease, and attempt models;
- idempotent commands;
- transactional outbox;
- heartbeat, timeout, retry, pause, resume, and cancellation semantics;
- deterministic workflow scheduler independent of LLM judgment.

Exit criteria: crash/retry/duplicate/cancellation tests prove durable behavior across processes.

### B4 — OpenHands runtime correction

Deliverables:

- public SDK imports only;
- separate Agent Server and LLM credentials/base URLs;
- real engineering tools and default OpenHands instructions;
- unique workspaces;
- correct typed event, final response, statistics, timeout, interruption, and artifact handling;
- persisted conversation IDs and reconnect/resume behavior;
- `delete_on_close=False` until explicit retention cleanup;
- mock and real-runtime contract tests.

Exit criteria: one remote agent creates, validates, returns, and preserves a real artifact with live events and working cancellation.

### B5 — Artifact, file, and workspace backend

Deliverables:

- safe path normalization and traversal prevention;
- versioned workspace snapshots;
- file tree/read/diff/search/edit APIs;
- artifact object storage, checksums, manifests, provenance, and retention;
- Git branch/worktree integration and isolated path ownership.

Exit criteria: artifacts survive worker restarts, unauthorized paths are rejected, and versions can be restored.

### B6 — WordPress intelligence core

Deliverables:

- knowledge-source governance and ingestion;
- version-aware retrieval;
- plugin-family and feature ontology;
- component and license registry;
- plugin kernel version 1;
- blueprint schema and WordPress product manifest;
- reusable admin and user dashboard contract schemas.

Exit criteria: an affiliate request retrieves the correct feature catalogue, approved components, compatibility rules, and validation policy without leaking unrelated knowledge.

### B7 — Discovery, specification, planning, and approval

Deliverables:

- chat-backed requirement extraction;
- feature recommendations;
- immutable specification, data contract, UI contract, and plan revisions;
- approval hashes and actor records;
- build-strategy and risk classification;
- cost/agent/sandbox estimate;
- change-request workflow.

Exit criteria: no build can start without a valid approved contract, and every downstream object traces to its approved requirement IDs.

### B8 — Multi-agent coordinator

Deliverables:

- versioned agent profiles;
- capability-based agent selection;
- work-package DAG creation;
- isolated workspaces/worktrees;
- concurrency and budget controls;
- candidate-result schema;
- deterministic validation gates;
- integration, structured findings, correction packages, and escalation limits.

Exit criteria: parallel agents complete non-overlapping packages, integration is reproducible, and failed requirements create bounded repair loops.

### B9 — Governed experience and evaluation system

Deliverables:

- failure occurrences, fingerprints, attempts, verified resolutions, knowledge candidates, golden projects, and evaluation cases;
- secret/PII redaction;
- similarity retrieval and compatibility filtering;
- promotion/rejection workflow;
- regression evaluations proving promoted lessons help rather than harm.

Exit criteria: a reproduced failure retrieves a previously verified compatible fix, while an unverified or incompatible fix is not recommended.

### B10 — WordPress sandbox and QA

Deliverables:

- disposable Docker profiles;
- optional Playground preview profiles;
- WP-CLI, unit, integration, browser, lifecycle, security, accessibility, performance, and Plugin Check runners;
- fixtures for plugin-family domain tests;
- compatibility matrix and machine-readable evidence.

Exit criteria: a generated plugin passes install-to-uninstall lifecycle tests across its declared target matrix.

### B11 — Release, site delivery, and rollback backend

Deliverables:

- signed artifacts and release channels;
- stable/beta/development versions;
- target-site preflight;
- staged install and explicit activation approval;
- health monitoring, automatic rollback, and recovery tokens;
- update and migration history.

Exit criteria: a release can be staged, activated, monitored, and rolled back without direct manual file editing.

### B12 — Usage, billing, observability, and hardening

Deliverables:

- usage and cost ledger;
- quotas and budgets;
- structured traces and audit export;
- encrypted secrets;
- container/network policy;
- rate limits, backups, retention, and operational runbooks.

Exit criteria: tenant, security, recovery, load, and billing reconciliation tests pass.

---

## 13. Frontend and WordPress Delivery Sequence

Frontend work begins after the supporting backend contracts are stable.

### F1 — Tersuite web planning studio

Project chat, Discover/Plan/Build modes, requirement editor, plan approval, progress timeline, findings, and reports.

### F2 — Web file-manager IDE

Monaco editor, file tree, diffs, history, search, test panel, requirement traceability, agent references, pause/take-control, and restore.

### W1 — WordPress Studio client

Secure site pairing, chat, planning/approval, live progress, files/reports, artifact delivery, diagnostics, and permission controls.

### W2 — Safe staging and activation

Signature verification, preflight, staged install, backup, explicit activation, health checks, rollback, and support bundle.

### E1 — Enterprise product

Organizations, teams, granular roles, quotas, billing, audit/compliance, model policies, private components, tenant knowledge, and optional hybrid/self-hosted execution.

### T1 — Theme creator extension (future)

Theme intelligence, theme blueprints, templates, patterns, blocks, styles, visual preview, theme-specific agents, Theme Check policies, and theme packaging. This phase begins only after the plugin platform is stable.

---

## 14. Initial Vertical and Benchmark Strategy

1. Prove the runtime with one small WordPress plugin.
2. Build the Tersuite plugin kernel and dashboard contracts.
3. Implement Affiliate Blueprint v1 as the first deep commercial vertical.
4. Implement Membership Blueprint v1 using shared components but separate domain rules.
5. Maintain golden benchmark projects for settings, custom post type, REST, WooCommerce, membership, affiliate, booking, and Gutenberg use cases.

Every change to models, prompts, knowledge, components, blueprints, or validation must run relevant benchmark cases and compare requirement coverage, security, test success, architecture, repair cycles, time, and cost.

---

## 15. Antigravity Development and Verification Protocol

Implementation is delivered in small, bounded sessions. Each session receives one authoritative instruction document and must not implement future milestones.

Antigravity must report:

- branch and commit SHA;
- files created, changed, and deleted;
- migrations;
- commands and tests executed with counts;
- unresolved failures;
- scope deviations;
- security or compatibility concerns;
- documentation updated.

The report is evidence to locate work, not proof of correctness. After every session:

1. The user supplies the report and GitHub commit/branch.
2. The reviewer inspects the actual repository commit and diff.
3. The reviewer checks scope, contracts, migrations, tests, security, and exit criteria.
4. If correct, the milestone receives a verified approval note.
5. If incomplete or misleading, the reviewer produces an exact correction map and a bounded Antigravity repair prompt.
6. No later milestone begins until blocking findings are resolved.

See `docs/ANTIGRAVITY-DEVELOPMENT-PROTOCOL.md` for the reusable session contract and `docs/ANTIGRAVITY-SESSION-01-BACKEND-BASELINE.md` for the first implementation session.

---

## 16. Definition of Done

A module or phase is complete only when all seven lifecycle stages are evidenced:

1. Specification
2. Architecture
3. Implementation
4. Tests
5. Integration
6. Audit
7. Freeze

A generated WordPress product is complete only when:

- every mandatory requirement maps to code and passing evidence;
- no unresolved critical/high finding remains;
- approved components and licenses are traceable;
- the declared compatibility matrix passes;
- lifecycle, migration, security, and domain tests pass;
- the signed artifact and rollback release exist;
- the user has approved deployment/activation separately from plan approval.

---

## 17. Explicit Early Non-Goals

Until their milestones begin, do not prematurely build:

- theme generation;
- arbitrary third-party plugin modification;
- uncontrolled live self-training;
- production activation without approval;
- third-party component marketplace;
- broad billing plans before accurate usage exists;
- a custom replacement for the official OpenHands Agent Server;
- a monolithic plugin template containing every optional feature.

The initial commercial boundary is new plugin creation and updates to plugins already managed by Tersuite. Importing and safely modifying arbitrary third-party plugins is a later capability.
