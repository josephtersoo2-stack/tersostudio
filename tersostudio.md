# Tersuite AI Studio — Full Implementation Roadmap

## 1. System Architecture Overview

The target end-state architecture:

```
                              USER
                                │
                                ▼
                     TERSUITE WORDPRESS STUDIO
                                │
                                ▼
                         Django REST API
                                │
       ┌────────────────────────┼─────────────────────────┐
       │                        │                         │
       ▼                        ▼                         ▼
   Identity                  Projects                 Credits
   Users                     Generations              Billing
   Roles                     Files                    Usage
       │                        │                         │
       └────────────────────────┬─────────────────────────┘
                                ▼
                       TERSUITE INTELLIGENCE
                                │
          ┌─────────────────────┼─────────────────────┐
          ▼                     ▼                     ▼
   WordPress Knowledge    Domain Knowledge      Project Memory
          │                     │                     │
          └─────────────────────┼─────────────────────┘
                                ▼
                      FEATURE DISCOVERY ENGINE
                                │
                                ▼
                         USER APPROVAL
                                │
                                ▼
                          COORDINATOR
                                │
                                ▼
                            PLANNER
                                │
               ┌────────────────┼────────────────┐
               ▼                ▼                ▼
          WP ARCHITECT      DOMAIN AGENT       UX AGENT
               │                │                │
               └────────────────┼────────────────┘
                                ▼
                             CODER
                                │
                         ┌──────┴──────┐
                         ▼             ▼
                       CRITIC       SECURITY
                         │             │
                         └──────┬──────┘
                                ▼
                              TEST
                                │
                                ▼
                       WORDPRESS SANDBOX
                                │
                     ┌──────────┴──────────┐
                     ▼                     ▼
                FUNCTIONAL QA         SECURITY QA
                     │                     │
                     └──────────┬──────────┘
                                ▼
                           PACKAGE ZIP
                                │
                                ▼
                           USER DELIVERY
```

> **Note on OpenHands**: OpenHands sits beneath the Tersuite intelligence/business layers as the agent execution engine, not as the product itself. Its SDK explicitly supports programmatic agents, tools, conversations, workspaces, and remote Agent Server execution.

---

## 2. Phased Roadmap

### PHASE 0 — Architecture Freeze
Before writing production code, establish system contracts.

#### Deliverables: Master Technical Documents
Create the following documentation structure:
```
docs/
├── SYSTEM-ARCHITECTURE.md
├── MODULE-MAP.md
├── DATA-MODEL.md
├── AGENT-ARCHITECTURE.md
├── OPENHANDS-INTEGRATION.md
├── KNOWLEDGE-ARCHITECTURE.md
├── GENERATION-LIFECYCLE.md
├── WORDPRESS-SANDBOX.md
├── API-CONTRACT.md
├── EVENT-CONTRACT.md
├── SECURITY-ARCHITECTURE.md
└── TESTING-STRATEGY.md
```

#### Non-negotiable Rule
- No module can silently invent its own architecture or bypass established contracts.

#### Exit Condition
- Ability to trace and draw the entire system from database → API → agent → sandbox → ZIP without architectural gaps.

---

### PHASE 1 — New Django Foundation
Start a completely new backend repository.

#### Technology Stack:
- Python
- Django & Django REST Framework
- PostgreSQL
- Redis & Celery
- Django Channels
- OpenHands SDK & OpenHands Agent Server
- Docker

#### Core Django Modules:
```
backend/
├── config/
├── apps/
│   ├── accounts/
│   ├── organizations/
│   ├── projects/
│   ├── generations/
│   ├── agents/
│   ├── workflows/
│   ├── knowledge/
│   ├── specifications/
│   ├── workspaces/
│   ├── artifacts/
│   ├── usage/
│   ├── credits/
│   ├── subscriptions/
│   ├── providers/
│   ├── notifications/
│   ├── audit/
│   ├── logs/
│   └── realtime/
```

#### Exit Condition
- Backend runs cleanly with Django, PostgreSQL, Redis, Celery, and Channels. Includes authentication, migrations, health checks, API versioning, structured configuration, and test infrastructure.

---

### PHASE 2 — Identity, Projects and Generation Model
Establish a rock-solid data foundation before integrating agents.

#### Core Data Entities:
- `User`
- `Organization`
- `Project`
- `Generation`
- `GenerationStep`
- `AgentRun`
- `Artifact`
- `Workspace`
- `Specification`
- `KnowledgeSource`
- `UsageRecord`
- `CreditTransaction`

#### Generation Lifecycle:
```
DRAFT ──► SPECIFICATION ──► APPROVED ──► PLANNING ──► BUILDING ──► TESTING ──► REVIEW ──► PACKAGING ──► COMPLETED
```
*Failure & control states:* `FAILED`, `CANCELLED`, `PAUSED`, `RETRYING`.

#### Exit Condition
- Create a project and generation tied to it via API with full state tracking.

---

### PHASE 3 — OpenHands Integration
First major engineering milestone: control OpenHands reliably via an adapter abstraction.

#### Architecture:
```
Tersuite Generation ──► OpenHands Adapter (TersuiteAgentRuntime) ──► Agent Server ──► Agent ──► Workspace
```

#### Key Requirement:
- Create `TersuiteAgentRuntime` abstraction layer so Tersuite never couples directly to OpenHands internals.

#### Exit Condition
- A Django API call can create a workspace, create an OpenHands conversation, launch an agent, send a task, observe events, receive completion, collect generated files, and persist the generation record.

---

### PHASE 4 — Real-Time Agent Event System
Live streaming of generation and agent events via Django Channels.

#### Normalized Event Model:
- **Generation:** `generation.created`, `generation.started`, `generation.completed`, `generation.failed`
- **Agent:** `agent.started`, `agent.thinking`, `agent.tool_started`, `agent.tool_finished`, `agent.waiting`, `agent.completed`, `agent.failed`
- **Task:** `task.created`, `task.started`, `task.completed`
- **Workspace:** `workspace.created`, `workspace.destroyed`
- **Test:** `test.started`, `test.failed`, `test.passed`
- **Review:** `review.started`, `review.failed`, `review.passed`
- **Artifact:** `artifact.created`

#### Exit Condition
- A browser can watch an entire generation lifecycle live via WebSockets.

---

### PHASE 5 — WordPress Engineering Knowledge System
Structured engineering and domain knowledge system.

```
knowledge/
├── wordpress/
├── woocommerce/
├── security/
├── plugin-architecture/
├── database/
├── admin-ui/
├── frontend/
├── testing/
├── performance/
└── domains/
    ├── affiliate/
    ├── membership/
    ├── ecommerce/
    ├── booking/
    ├── crm/
    ├── lms/
    └── ...
```

#### Knowledge Unit Schema:
- Concept, Category, Description, Rules, Patterns, Examples, Dependencies, Constraints, Anti-patterns, Security considerations, Compatibility considerations, Sources, Confidence.

#### Exit Condition
- Given a request like *"Build an affiliate plugin"*, Tersuite identifies relevant domains (WordPress + Affiliate + WooCommerce/Membership) and retrieves the proper knowledge sets.

---

### PHASE 6 — Professional Plugin Knowledge Extraction Pipeline
Extract, generalize, and normalize domain models from existing commercial/professional plugins.

```
SOURCE ──► ANALYZE ──► GENERALIZE ──► NORMALIZE ──► KNOWLEDGE RECORD ──► DOMAIN KNOWLEDGE BASE
```
*Aggregating multiple domain sources yields a comprehensive domain model (common, unique, advanced capabilities).*

#### Exit Condition
- Given multiple professional products, Tersuite produces a consolidated domain feature model.

---

### PHASE 7 — Feature Discovery Engine
Transform vague user prompts into rich, organized capabilities before coding.

```
User Request ──► Intent Analysis ──► Domain Classification ──► Knowledge Retrieval ──► Professional Feature Discovery ──► Feature Grouping ──► Recommendation
```

- Example: Identifies 87 potential capabilities (61 recommended, 15 advanced, 11 optional) grouped into modules.
- User UI Controls: Approve (✓), Remove (✗), Add (＋), Modify (✎), Reorder (↕).

#### Exit Condition
- Transform a vague request into a complete, user-approved software specification without generating code yet.

---

### PHASE 8 — Specification Engine
The approved feature set is transformed into a formal, versioned `ProductSpecification` contract (objectives, target users, features, business rules, workflows, data models, APIs, security, performance, test criteria).

#### Exit Condition
- Every generation is backed by a versioned, human-approved specification contract.

---

### PHASE 9 — Tersuite Coordinator
The business-level orchestration engine controlling the workflow, agents, knowledge retrieval, model routing, workspaces, and approval checkpoints.

#### Exit Condition
- Generations are driven by explicit multi-phase production workflows.

---

### PHASE 10 — Tersuite WordPress Agent Team
Specialized agent team:
1. **Coordinator**
2. **Feature Discovery Agent**
3. **Planner**
4. **WordPress Architect**
5. **Domain Specialist** (dynamic: Affiliate, Membership, WooCommerce, Booking, etc.)
6. **UX/UI Agent**
7. **Coder**
8. **Security Agent**
9. **QA Agent**
10. **Reviewer**
11. **Sandbox Agent**
12. **Packaging Agent**

---

### PHASE 11 — Model & Provider Router
Intelligent LLM routing based on task and commercial policies:
- Coordinator / Planner / Reviewer ➔ High-reasoning models
- Architect / Coder ➔ Specialized coding models
- Security ➔ Security / reasoning models

---

### PHASE 12 — WordPress Sandbox
Automated, disposable Docker-based runtime testing environment:
- WordPress Core + PHP + MySQL/MariaDB + WP-CLI (+ WooCommerce/Membership profiles).

#### Exit Condition
- Tersuite can install a generated plugin in a disposable WordPress container and execute real CLI/browser tests.

---

### PHASE 13 — WordPress QA Engine
Comprehensive automated verification beyond static unit tests:
- Lifecycle (activation, deactivation, uninstall), admin/frontend rendering, DB migrations, settings, nonces, REST/AJAX endpoints, shortcodes, blocks, and domain-specific workflows (e.g. affiliate registrations, payouts, fraud checks).

#### Exit Condition
- Machine-readable QA report generated per build.

---

### PHASE 14 — Security Agent
Dedicated security analysis stage checking for:
- XSS, CSRF, SQLi, privilege escalation, capability checks, nonce validation, sanitization/escaping, REST permissions, path traversal, SSRF, data exposure.
- Enforces build failure/blocking on critical/high severity findings.

---

### PHASE 15 — Review / Critic Loop
Iterative repair loop between Coder, Reviewer, and QA with hard iteration limits:
```
Coder ──► Reviewer/QA ──► Issues? ──[No]──► Continue
                               └──[Yes]──► Repair ──► Re-test ──► Re-review
```

---

### PHASE 16 — Artifact & Delivery Engine
Packages and validates final deliverables:
- Validated ZIP file (e.g., `affiliate-membership-pro.zip`) containing proper WP plugin structure, readme, manifests, checksums, test & security reports, and architecture changelog.

---

### PHASE 17 — Project Memory
Structured memory retention distinguishing:
- Facts, Architectural decisions, Approved/rejected features, User preferences, Generated files, Test results, Security findings, and Model usage (separated from transient execution state).

---

### PHASE 18 — Credits, Usage and Billing
Tracking tokens, agent/workspace compute time, tool executions, and credit metering across tiered plans (Starter, Growth, Professional, Enterprise).

---

### PHASE 19 — WordPress Plugin (Client)
Thin-client WordPress administrative plugin:
- Connects to Django REST API
- Handles auth, project selection, prompt input, feature specification approvals, live progress streaming, file downloads, and recovery dashboard.

---

### PHASE 20 — Plugin Emergency Recovery & Logging
Safety subsystem built into the WordPress plugin:
- Safe Mode, fatal error interception, emergency deactivation, recovery tokens, health checks, and debug logging to ensure generated plugins never brick client sites.

---

### PHASE 21 — Observability & Audit
Full audit trail and execution timeline for every action, tool call, decision, test, and approval.

---

### PHASE 22 — Evaluation Benchmark Suite
Standardized test suite (e.g., simple settings plugin, CPT plugin, WooCommerce integration, Affiliate, Membership, Complex reporting, Security-sensitive) to objectively benchmark requirement coverage, architecture quality, WP compliance, security, and build success across agent revisions.

---

### PHASE 23 — Production Hardening
Tenant isolation, container security/cleanup, network restrictions, rate limiting, quotas, backup, and monitoring.

---

### PHASE 24 — Commercial Launch
Landing page, billing integration, docs, onboarding, user dashboard, licensing.

---

## 3. Step-by-Step Development Order

1. Architecture Contracts (Phase 0)
2. Django Foundation (Phase 1)
3. Project & Generation Data Models (Phase 2)
4. OpenHands Adapter (Phase 3)
5. Agent Server & Workspaces (Phase 3)
6. Event Streaming / Channels (Phase 4)
7. Basic Single-Agent Execution (MVP-1)
8. Subagents & Delegation (Phase 10)
9. Tersuite Coordinator (Phase 9)
10. Planner Agent (Phase 10)
11. WordPress Knowledge System (Phase 5)
12. Feature Discovery Engine (Phase 7)
13. Approval & Specification Engine (Phase 8)
14. WordPress Specialist Agents (Phase 10)
15. Docker WordPress Sandbox (Phase 12)
16. QA Engine (Phase 13)
17. Security Agent (Phase 14)
18. Review & Repair Loop (Phase 15)
19. Artifact Packaging (Phase 16)
20. Project Memory (Phase 17)
21. Usage & Credits (Phase 18)
22. WordPress Client Plugin (Phase 19)
23. Emergency Recovery & Logging (Phase 20)
24. Evaluation Benchmark (Phase 22)
25. Production Hardening (Phase 23)
26. Commercial Launch (Phase 24)

---

## 4. MVP Staging Strategy

- **MVP-1 (Infrastructure Proof of Concept)**:  
  API ➔ Create Project ➔ Create Generation ➔ OpenHands Agent ➔ Docker Workspace ➔ Create & test a simple Python script ➔ Stream events ➔ Return completed artifact. *(Deliberately non-WordPress to prove foundational runtime).*
- **MVP-2**: Basic WordPress plugin generation and packaging.
- **MVP-3**: Professional multi-agent WordPress plugin generation with knowledge base and sandbox QA.

---

## 5. Standard Module Development Lifecycle Rule
Every major module must pass through:
1. **Specification**
2. **Architecture**
3. **Implementation**
4. **Tests**
5. **Integration**
6. **Audit**
7. **Freeze**
