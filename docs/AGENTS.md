# AGENTS.md — Tersuite AI Studio Multi-Agent Architecture & Operating Guidelines

## 1. Overview & Operating Philosophy

**Tersuite AI Studio** is an enterprise, WordPress-native AI engineering platform designed to transform natural language requirements into professional, secure, tested, and production-ready WordPress products. The initial and primary product is plugin engineering. Theme engineering is a future extension behind explicit product-type contracts.

Underneath the business and intelligence layer, the **OpenHands SDK & Agent Server** serves as the programmatic agent execution engine. However, Tersuite provides the domain intelligence, WordPress engineering standards, multi-agent coordination, and automated verification sandboxes.

The durable workflow coordinator is deterministic Django/PostgreSQL application logic. LLM agents may recommend plans and actions, but they do not own persistence, authorization, approval gates, state transitions, retries, cancellation, or completion decisions.

---

## 2. Non-Negotiable Engineering Rules

1. **Contracts First**: No module can silently invent its own architecture or bypass established contracts (`docs/` contracts are the source of truth).
2. **Runtime Abstraction**: All agent interactions must go through the `TersuiteAgentRuntime` abstraction layer. Never import or couple OpenHands internals directly into core business domains.
3. **Multi-Agent Separation of Concerns**: Agents must adhere strictly to their specialized domain boundaries. A Coder does not invent architecture without the Architect; a Reviewer does not modify code directly without sending findings back through the repair loop.
4. **Mandatory WordPress Sandbox QA**: No generated plugin is accepted until it passes real activation, functional, and security tests inside an isolated Docker WordPress sandbox.
5. **Standard Module Lifecycle**: Every major module must strictly follow the 7-step lifecycle:
   $$\text{Specification} \longrightarrow \text{Architecture} \longrightarrow \text{Implementation} \longrightarrow \text{Tests} \longrightarrow \text{Integration} \longrightarrow \text{Audit} \longrightarrow \text{Freeze}$$
6. **Plan Before Build**: Planning and discovery are read-only with respect to source code. Implementation requires an immutable, versioned, human-approved specification and implementation plan.
7. **Reuse Before Generation**: Agents must search the approved component, blueprint, and template registries before creating new infrastructure. Unverified third-party code must not be copied into generated products.
8. **Evidence Before Completion**: Agents submit candidate results. Deterministic validation, independent review, sandbox evidence, and policy gates decide whether work is complete.
9. **Governed Learning Only**: Generated products, failures, and fixes may enter the experience ledger, but only redacted, licensed, verified, reviewed outcomes may be promoted as reusable knowledge or components.
10. **Plugin-First, Theme-Ready**: Current implementation must remain explicitly optimized for plugins while core product, blueprint, artifact, sandbox, and quality contracts preserve a future `THEME` product kind.

---

## 3. Agent Roster & Domain Responsibilities

```
                                 COORDINATOR
                                      │
                         ┌────────────┴────────────┐
                         ▼                         ▼
              FEATURE DISCOVERY AGENT           PLANNER
                         │                         │
                         ▼                         ▼
                    UX/UI AGENT          WORDPRESS ARCHITECT
                         │                         │
                         └────────────┬────────────┘
                                      ▼
                             DOMAIN SPECIALIST
                        (Affiliate / Woo / LMS / ...)
                                      │
                                      ▼
                                 CODER AGENT
                                      │
                         ┌────────────┴────────────┐
                         ▼                         ▼
                   REVIEWER / CRITIC        SECURITY AGENT
                         │                         │
                         └────────────┬────────────┘
                                      ▼
                                   QA AGENT
                                      │
                                      ▼
                               SANDBOX AGENT
                                      │
                                      ▼
                              PACKAGING AGENT
```

### 3.1. Coordinator Agent
- **Primary Function**: Planning and decision-support assistant to the deterministic workflow coordinator.
- **Responsibilities**:
  - Validates human inputs and incoming specifications.
  - Proposes workflow pipelines, work-package decomposition, and specialist assignments.
  - Explains blockers, findings, costs, risks, and recommended corrections.
  - Never directly authorizes approval gates or state transitions.
  - Operates within budgets, policies, and assignments enforced by the backend coordinator.

### 3.2. Feature Discovery Agent
- **Primary Function**: Deep requirement extraction and capability structuring.
- **Responsibilities**:
  - Analyzes user intent and queries the WordPress & Domain Knowledge Bases.
  - Discovers comprehensive capabilities (standard, advanced, optional).
  - Groups capabilities into logical modules for user review & approval.

### 3.3. Planner Agent
- **Primary Function**: Execution graph and milestone planning.
- **Responsibilities**:
  - Deconstructs approved specifications into atomic, dependency-ordered engineering tasks.
  - Produces step-by-step implementation blueprints for domain specialists and coders.

### 3.4. WordPress Architect Agent
- **Primary Function**: Technical blueprinting and WordPress standards enforcement.
- **Responsibilities**:
  - Designs database schemas (custom tables vs. CPTs/metadata), hook architectures, and REST API endpoints.
  - Enforces WordPress Coding Standards (WPCS), PSR-4 / class autoloading, action/filter lifecycle, and admin menu hierarchies.

### 3.5. Domain Specialist Agents (Dynamic Selection)
- **Primary Function**: High-fidelity business domain rules injection.
- **Specializations**:
  - **Affiliate Specialist**: Referral tracking cookies, commission attribution rules, multi-tier payouts, fraud prevention.
  - **WooCommerce Specialist**: Hooking into checkout, order status state machines, cart recalculation, product types.
  - **Membership Specialist**: Content restriction logic, member level hierarchy, subscription recurring billing webhooks.
  - **Booking / LMS / CRM Specialists**: Scheduling engines, course progression, customer lifecycle hooks.

### 3.6. UX / UI Agent
- **Primary Function**: Modern WordPress administrative & frontend UI engineering.
- **Responsibilities**:
  - Designs clean, responsive admin dashboards (Gutenberg blocks, React/Tailwind/vanilla CSS where applicable, native WP Admin UI aesthetics).
  - Enforces accessible frontend forms, shortcodes, and client-side notifications.

### 3.7. Coder Agent
- **Primary Function**: Polyglot code generation (PHP 8+, JavaScript/TypeScript, SQL, CSS).
- **Responsibilities**:
  - Applies `REUSE -> EXTEND -> GENERATE`, using approved components and blueprints before writing replacement infrastructure.
  - Implements plugin code strictly against architectural contracts and specifications.
  - Writes robust error handling, sanitization (`sanitize_text_field`), and output escaping (`esc_html`, `esc_attr`).
  - Submits changed-file manifests, requirement coverage, validation evidence, and a candidate result rather than self-approving completion.

### 3.8. Security Agent
- **Primary Function**: Static & dynamic security auditing.
- **Responsibilities**:
  - Checks for XSS, CSRF (nonce verification on every state change), SQL Injection (`$wpdb->prepare`), and Privilege Escalation (`current_user_can`).
  - Audits REST API permission callbacks, file uploads, path traversal, and sensitive data leakage.
  - Flags findings (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, `PASS`) and blocks packaging on unresolved critical/high vulnerabilities.

### 3.9. Reviewer / Critic Agent
- **Primary Function**: Code quality inspection and iterative refinement.
- **Responsibilities**:
  - Performs code review against style guides, maintainability metrics, and edge case coverage.
  - Produces structured findings tied to requirement IDs, evidence, affected paths, repair instructions, and retest commands.
  - Initiates closed repair loops through the coordinator and never silently edits the implementation it is reviewing.

### 3.10. QA & Sandbox Agents
- **Primary Function**: Runtime validation inside disposable WordPress Docker containers.
- **Responsibilities**:
  - Provisions runtime sandboxes (WP Core, PHP 8.x, MySQL, WP-CLI).
  - Validates plugin activation, deactivation, uninstallation, table creation, settings persistence, REST endpoints, and admin UI rendering without fatal PHP errors.
  - Generates structured, machine-readable QA reports.

### 3.11. Packaging Agent
- **Primary Function**: Distribution artifact compilation.
- **Responsibilities**:
  - Packages the final plugin into a standard, clean `.zip` archive.
  - Generates `readme.txt`, manifest, version tags, SHA-256 checksums, and changelog documents.

---

## 4. Model Routing Strategy

To balance reasoning capability, coding quality, and operational cost:
- **High-Reasoning Models**: Coordinator, Feature Discovery, Planner, Reviewer, Security.
- **High-Performance Coding Models**: WordPress Architect, Coder Agent.
- **Fast / Lightweight Models**: Token counting, state summarizing, log formatting.

---

## 5. Event Contract & Streaming Rules

All agent actions and thoughts are normalized into a unified event stream broadcasted over Django Channels:
- `agent.started`, `agent.thinking`, `agent.tool_started`, `agent.tool_finished`, `agent.completed`, `agent.failed`
- `task.created`, `task.started`, `task.completed`
- `test.started`, `test.passed`, `test.failed`
- `security.scan_started`, `security.finding_recorded`, `security.scan_completed`

Every event payload must be strictly serialized, timestamped, and tied to a unique `GenerationID` and `AgentRunID`.

---

## 6. Work-Package and Completion Rules

Primary specialist agents are separate Tersuite-managed OpenHands conversations with durable `AgentRun` records and isolated workspaces or Git worktrees. OpenHands nested subagents are allowed only for bounded internal delegation and do not replace Tersuite workflow records.

Every work package must reference approved specification and plan versions, requirement IDs, an agent-profile version, dependencies, owned paths, validation commands, time/budget limits, and expected deliverables.

The only successful agent submission state is `CANDIDATE_COMPLETE`. A work package becomes complete only after deterministic checks and required independent reviews pass. Parallel agents must not write into the same unpartitioned workspace.

---

## 7. Governed Experience Memory

Tersuite records normalized failure occurrences, error fingerprints, attempted resolutions, verified fixes, compatibility boundaries, tests, reviewer findings, and production outcomes.

- Secrets and sensitive tenant data are redacted or access-restricted before indexing.
- Failed attempts remain negative evidence and are not recommended as fixes.
- Only verified, reviewed resolutions can be promoted.
- Generated code becomes reusable only after provenance, license, generalization, security, compatibility, and test review.
- Initial improvement uses retrieval and evaluation; live customer data must not automatically modify model weights.

---

## 8. Product-Type Boundary

The implemented product kind is `PLUGIN`. Shared contracts may use a `WordPressProduct` or `ProductTarget` abstraction, but plugin-specific behavior remains in explicit plugin manifests, policies, blueprints, agents, validation, packaging, and sandbox adapters.

Theme generation must not be implemented until its roadmap phase. Future theme support receives its own manifest and WordPress product adapter rather than adding theme conditionals throughout plugin logic.
