# Tersuite AI Studio

<div align="center">

**Enterprise Autonomous Multi-Agent Engineering Platform for WordPress**

[![Status](https://img.shields.io/badge/status-active%20development-blue.svg)](#)
[![Python](https://img.shields.io/badge/python-3.11+-brightgreen.svg)](#)
[![Django](https://img.shields.io/badge/django-5.0+-green.svg)](#)
[![OpenHands](https://img.shields.io/badge/engine-OpenHands%20SDK-orange.svg)](#)
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
| **Backend Core** | Python 3.11+, Django 5.x, Django REST Framework |
| **Real-time & Tasks** | Django Channels (WebSockets), Celery, Redis |
| **Database** | PostgreSQL |
| **Agent Execution** | OpenHands SDK, OpenHands Agent Server |
| **Sandboxing & QA** | Docker, WordPress Core, PHP 8.x, MySQL/MariaDB, WP-CLI |
| **Client Interface** | WordPress Administrative Plugin (PHP / React) |

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

## 🗺️ Roadmap & Documentation

For the comprehensive 25-phase roadmap, architectural milestones, and MVP release strategy, refer to:
👉 [**docs/TERSUITE-IMPLEMENTATION-ROADMAP.md**](docs/TERSUITE-IMPLEMENTATION-ROADMAP.md)
👉 [**docs/TERSUITE-CONTROL-CENTER-CC-01-SPEC.md**](docs/TERSUITE-CONTROL-CENTER-CC-01-SPEC.md)

