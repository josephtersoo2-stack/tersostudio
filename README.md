# Tersuite AI Studio

<div align="center">

**Enterprise Autonomous Multi-Agent Engineering Platform for WordPress**

[![Status](https://img.shields.io/badge/status-active%20development-blue.svg)](#)
[![Python](https://img.shields.io/badge/python-3.12-brightgreen.svg)](#)
[![Django](https://img.shields.io/badge/django-5.1+-green.svg)](#)
[![OpenHands](https://img.shields.io/badge/engine-OpenHands%20SDK%201.42.1-orange.svg)](#)
[![License](https://img.shields.io/badge/license-Proprietary-red.svg)](#)

</div>

---

## 📖 Overview

**Tersuite AI Studio** is a full-lifecycle autonomous software engineering platform purpose-built for WordPress. It bridges the gap between high-level human ideas and production-grade WordPress plugins by combining:
- **Feature Discovery & Structured Specifications**: Transforms ambiguous requests into comprehensive, reviewable capability matrices before coding.
- **Deep WordPress Domain Intelligence**: Enforces WordPress Coding Standards (WPCS), security best practices (nonces, capabilities, sanitization/escaping), and modular architecture.
- **Multi-Agent Collaboration**: Specialized agents (Coordinator, Planner, Architect, Domain Specialist, UX/UI, Coder, Critic, Security, QA, Packaging) orchestrated cleanly over the OpenHands SDK engine.
- **Automated Docker Sandbox QA**: Real-world activation, functional, and security testing inside isolated WordPress runtime environments.
- **Client Safety & Emergency Recovery**: Built-in safe mode and fatal error interception to prevent site lockouts.

---

## 🏛️ System Architecture

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

---

## 🛠️ Technology Stack

| Layer | Technologies |
|---|---|
| **Backend Core** | Python 3.12, Django 5.1+, Django REST Framework, uv |
| **Real-time & Tasks** | Django Channels (WebSockets), Celery, Redis |
| **Database** | PostgreSQL 16 |
| **Agent Execution** | OpenHands SDK 1.42.1, OpenHands Agent Server 1.42.1 |
| **Sandboxing & QA** | Docker, WordPress Core, PHP 8.x, MySQL/MariaDB, WP-CLI |
| **Client Interface** | WordPress Administrative Plugin & React Control Center |

---

## 🚀 Backend Setup & Verification (Milestone B1)

### 1. Prerequisites
- Python 3.12
- `uv` (v0.8.13+)
- PostgreSQL 16 & Redis 7

### 2. Quickstart with uv
```bash
# Navigate to backend directory
cd backend

# Install locked dependencies (production + dev group)
uv sync --frozen --extra dev

# Run Django system checks and migrations
uv run python manage.py check
uv run python manage.py migrate

# Run backend test suite
uv run pytest
```

### 3. Quickstart with Docker Compose
```bash
cd backend
docker compose up -d
```

### 4. Health & Readiness Probes
- **Liveness probe**: `GET /api/v1/health/live/` (HTTP 200 without querying external services)
- **Readiness probe**: `GET /api/v1/health/ready/` (checks PostgreSQL, Redis, and Celery broker; returns HTTP 200 if all healthy, HTTP 503 if any service is down)

### 5. OpenHands & Model Provider Credentials
Tersuite strictly isolates execution infrastructure from LLM model providers:
- **Agent Server**: Configured via `OPENHANDS_AGENT_SERVER_URL` and `OPENHANDS_AGENT_SERVER_API_KEY` (used solely for workspace and container interaction).
- **Model Providers**: Direct provider credentials (such as `OPENROUTER_API_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`) are passed exclusively to LiteLLM model instances and never exposed to the Agent Server or frontend.

---

## 🤖 Multi-Agent Ecosystem

Tersuite divides engineering responsibilities across specialized agent roles governed by the **Coordinator**:

- **Coordinator**: Business-level orchestrator managing generation states and approvals.
- **Feature Discovery Agent**: Expands prompts into structured capability matrices.
- **Planner Agent**: Builds deterministic, dependency-ordered execution graphs.
- **WordPress Architect Agent**: Enforces database schemas, hooks/filters, and PSR-4 structures.
- **Domain Specialists**: Injects domain rules (Affiliate, WooCommerce, Membership, LMS, Booking).
- **UX/UI Agent**: Designs admin dashboards, Gutenberg blocks, and accessible frontend interfaces.
- **Coder Agent**: Writes secure, clean, and modular plugin code.
- **Security Agent**: Audits for XSS, CSRF, SQLi, permission bypasses, and data exposure.
- **Reviewer / Critic Agent**: Performs iterative code inspection and initiates repair loops.
- **QA & Sandbox Agent**: Executes automated activation and functional tests in Docker.
- **Packaging Agent**: Compiles standard zip packages with manifests, checksums, and changelogs.

For detailed guidelines and role definitions, see [AGENTS.md](AGENTS.md).

---

## 📁 Repository Structure

```
tersostudio/
├── AGENTS.md                               # Multi-agent architecture and operational guidelines
├── README.md                               # Project overview and repository documentation
├── docs/                                   # Architectural contracts & specifications
│   └── TERSUITE-IMPLEMENTATION-ROADMAP.md  # Master 25-phase implementation roadmap
└── ...
```

---

## 📜 Standard Module Lifecycle

Every major component must strictly pass through the 7-stage lifecycle before completion:
1. **Specification** $\rightarrow$ Define functional and technical boundaries.
2. **Architecture** $\rightarrow$ Model data structures, events, and API interfaces.
3. **Implementation** $\rightarrow$ Code against established contracts.
4. **Tests** $\rightarrow$ Comprehensive unit, integration, and sandbox testing.
5. **Integration** $\rightarrow$ Wire into the global coordinator and event streams.
6. **Audit** $\rightarrow$ Security, performance, and code quality verification.
7. **Freeze** $\rightarrow$ Contract lock to prevent architectural regression.

---

## 🖥️ Operations & Control Center (CC-01)

Tersuite includes an internal **Control Center** dashboard (`frontend/`) providing real-time operational visibility into backend multi-tenant generation lifecycles, Celery asynchronous execution queues, and OpenHands SDK runtime health.

### 1. Backend Control Center API
- Endpoint prefix: `/api/v1/control-center/`
- Staff permission required (`is_staff=True` or `is_superuser=True`).
- Endpoints:
  - `GET /api/v1/control-center/summary/` — Global metrics & runtime posture.
  - `GET /api/v1/control-center/generations/` — Paginated, filtered, and searchable generation lifecycles.
  - `GET /api/v1/control-center/runs/` — Low-level agent execution attempts and token statistics.

### 2. Frontend Development & Build
The Control Center frontend is built with React 18, TypeScript, Vite, and Tailwind CSS.

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start local development server
npm run dev

# Compile production bundle
npm run build
```

Environment configuration in `frontend/.env`:
```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_WS_BASE_URL=ws://localhost:8000
```

---

## ⚡ Durable Workflow Kernel (B3)

Tersuite AI Studio includes a deterministic, high-concurrency **Durable Workflow Kernel** (`backend/apps/workflows/`) that orchestrates generation milestones and tasks:
- **DAG Execution & Validation**: Acyclic dependency graph construction, topological sorting, and parallel ready-queue progression.
- **Worker Leases & Heartbeat Reaper**: Time-bounded worker leases (`WorkPackageLease`) with periodic heartbeat extensions, execution deadlines, and automated stale-lease recovery.
- **Two-Phase Completion Gate**: Workers submit `CANDIDATE_COMPLETE` payloads with changed-file manifests; progression to `COMPLETED` requires deterministic validation evidence.
- **Idempotent Control Commands**: `PAUSE`, `RESUME`, `CANCEL`, and `RETRY` operations guarded by tenant-scoped idempotency keys, state versioning, and deterministic exponential backoff.
- **Transactional Outbox Engine**: ACID transactional event publishing (`OutboxEvent`) with secret-stripping protection and partitioned worker batch claims.

---

## 🗺️ Roadmap & Documentation

For the comprehensive 25-phase roadmap, architectural milestones, and MVP release strategy, refer to:
👉 [**docs/TERSUITE-IMPLEMENTATION-ROADMAP.md**](docs/TERSUITE-IMPLEMENTATION-ROADMAP.md)
👉 [**docs/B3-DURABLE-WORKFLOW-KERNEL-PHASE-SPEC.md**](docs/B3-DURABLE-WORKFLOW-KERNEL-PHASE-SPEC.md)
👉 [**docs/TERSUITE-CONTROL-CENTER-CC-01-SPEC.md**](docs/TERSUITE-CONTROL-CENTER-CC-01-SPEC.md)

