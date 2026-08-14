# AGENTS.md — Tersuite AI Studio Multi-Agent Architecture & Operating Guidelines

## 1. Overview & Operating Philosophy

**Tersuite AI Studio** is an enterprise AI engineering platform designed to transform natural language requirements into professional, secure, tested, and production-ready WordPress plugins.

Underneath the business and intelligence layer, the **OpenHands SDK & Agent Server** serves as the programmatic agent execution engine. However, Tersuite provides the domain intelligence, WordPress engineering standards, multi-agent coordination, and automated verification sandboxes.

---

## 2. Non-Negotiable Engineering Rules

1. **Contracts First**: No module can silently invent its own architecture or bypass established contracts (`docs/` contracts are the source of truth).
2. **Runtime Abstraction**: All agent interactions must go through the `TersuiteAgentRuntime` abstraction layer. Never import or couple OpenHands internals directly into core business domains.
3. **Multi-Agent Separation of Concerns**: Agents must adhere strictly to their specialized domain boundaries. A Coder does not invent architecture without the Architect; a Reviewer does not modify code directly without sending findings back through the repair loop.
4. **Mandatory WordPress Sandbox QA**: No generated plugin is accepted until it passes real activation, functional, and security tests inside an isolated Docker WordPress sandbox.
5. **Standard Module Lifecycle**: Every major module must strictly follow the 7-step lifecycle:
   $$\text{Specification} \longrightarrow \text{Architecture} \longrightarrow \text{Implementation} \longrightarrow \text{Tests} \longrightarrow \text{Integration} \longrightarrow \text{Audit} \longrightarrow \text{Freeze}$$

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
- **Primary Function**: Business-level lifecycle orchestrator.
- **Responsibilities**:
  - Validates human inputs and incoming specifications.
  - Determines workflow pipelines and delegates tasks to subagents.
  - Controls approval gates and state transitions (`DRAFT` $\rightarrow$ `COMPLETED`).
  - Monitors token consumption, timeouts, and execution health.

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
  - Implements plugin code strictly against architectural contracts and specifications.
  - Writes robust error handling, sanitization (`sanitize_text_field`), and output escaping (`esc_html`, `esc_attr`).

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
  - Initiates closed repair loops with the Coder agent when issues are identified.

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
