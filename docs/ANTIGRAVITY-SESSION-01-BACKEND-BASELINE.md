# Implementation Instruction — Antigravity Session 01 (B1 Backend Baseline)

You are working on the existing Tersuite AI Studio repository. This is an implementation and verification session, not a rewrite.

---

## 1. Objective

Establish a truthful, reproducible, and secure backend foundation for roadmap milestone B1. Inspect the existing backend first, preserve correct work, correct only foundation defects within this scope, and provide evidence that a clean environment can install and run the backend test baseline.

---

## 2. Required Reading Order

Read completely in this strict order before editing:

1. `AGENTS.md`
2. `docs/TERSUITE-IMPLEMENTATION-ROADMAP.md`
3. `docs/ANTIGRAVITY-DEVELOPMENT-PROTOCOL.md`
4. `docs/B1-BACKEND-BASELINE-PHASE-SPEC.md`
5. `docs/B1-BACKEND-BASELINE-DETAILED-IMPLEMENTATION.md`

If these documents conflict, stop and report the conflict before implementing the affected behavior.

---

## 3. Non-Invention & Implementation Scope

Antigravity is an implementer, not an architect. Do not invent unapproved features, dependencies, models, settings, routes, synthetic fallbacks, or alternative architectures.

This session may change only:
- Python version declaration and documentation (`.python-version`, `pyproject.toml`, `Dockerfile`, `README.md`)
- Dependency management and lockfiles (`pyproject.toml`, `uv.lock`, removal of `requirements.txt`)
- Docker, Compose, and environment baseline configurations (`Dockerfile`, `docker-compose.yml`, `.dockerignore`, `.env.example`)
- Configuration settings parsing and credential separation (`backend/config/settings/base.py`, `backend/runtime/adapters/openhands/config.py`)
- OpenHands adapter configuration and secret safety (`backend/runtime/adapters/openhands/adapter.py`, `backend/apps/generations/services/execution_service.py`)
- Truthful health checks (`backend/apps/core/views.py`, `backend/apps/core/tests/test_health.py`)
- CI workflow (`.github/workflows/backend-ci.yml`)
- OpenHands integration documentation (`docs/OPENHANDS-INTEGRATION.md`)
- B1 evidence report (`docs/reports/B1-BACKEND-BASELINE-REPORT.md`)

---

## 4. Protected Files & Prohibited Changes

Do not modify or delete:
- `frontend/**`
- Active architecture contracts (`docs/API-CONTRACT.md`, `docs/DATA-MODEL.md`, `docs/CC-02 Implementation Spec.md`, `docs/CC-03-OPERATIONAL-ACTIONS-SPEC.md`, `docs/TERSUITE-CONTROL-CENTER-CC-01-SPEC.md`, `docs/TERSUITE-CONTROL-CENTER-CC-02-SPEC.md`)
- Django database models or historical database migrations
- Knowledge-base implementation or seed knowledge data
- Realtime consumers, auth tokens, state machine, or existing mock adapter
- B2 or later roadmap features

---

## 5. Removal Ledger & Pre-Deletion Checks

Every removal must be classified in the report using `KEEP`, `REFACTOR`, `REPLACE`, `REMOVE`, or `DEFER`. Before deleting any file or configuration setting, perform repository searches to ensure no active code or test relies on orphaned references.

---

## 6. Stop Conditions

Stop and report immediately if:
- Required documents conflict or are missing.
- OpenHands 1.42.1 packages fail to install or import together on Python 3.12.
- A test failure cannot be resolved within the B1 boundary.
- Unspecified architectural decisions are required.

---

## 7. Required Verification Commands

Execute and report the exact results of:
```bash
git diff --check
uv --version
uv lock --check
uv sync --frozen --extra dev
uv run python -c "import importlib.metadata as m; print({p: m.version(p) for p in ['openhands-sdk','openhands-tools','openhands-agent-server','openhands-workspace']})"
uv run python manage.py check
uv run python manage.py makemigrations --check --dry-run
uv run pytest
docker compose config
docker build -t tersuite-backend:b1 .
```

---

## 8. Required Evidence Report

Produce `docs/reports/B1-BACKEND-BASELINE-REPORT.md` following the protocol structure with complete file changes, removal ledger, exact test counts, and exit criteria evidence.

---

## 9. Independent GitHub Review Gate

Commit and push to `feature/b1-backend-baseline`. A milestone is complete only after independent review verifies the GitHub commit and passing CI checks.
