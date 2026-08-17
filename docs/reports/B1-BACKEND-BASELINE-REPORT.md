# B1 — Backend Baseline Evidence & Verification Report

## Session Metadata

- **Session**: Antigravity Session 01 — Reproducible Backend Baseline (Milestone B1)
- **Branch**: `feature/b1-backend-baseline`
- **Specification**: `docs/B1-BACKEND-BASELINE-PHASE-SPEC.md` & `docs/B1-BACKEND-BASELINE-DETAILED-IMPLEMENTATION.md`
- **Protocol**: `docs/ANTIGRAVITY-DEVELOPMENT-PROTOCOL.md`

---

## Objective Completed

Established a truthful, reproducible, and secure backend foundation for roadmap milestone B1:
1. Pinned explicit supported Python runtime version (Python 3.12 via `.python-version` and Dockerfile).
2. Replaced loose dependency installation with committed `pyproject.toml` and `uv.lock` generated with uv.
3. Verified co-installation and imports of all 4 OpenHands 1.42.1 packages (`openhands-sdk`, `openhands-tools`, `openhands-agent-server`, `openhands-workspace`).
4. Enforced strict credential boundary separation: segregated Agent Server infrastructure credentials from direct LLM provider keys in configuration, settings, runtime adapters, and control center.
5. Implemented deterministic health & readiness checks (liveness HTTP 200 without DB/Redis, readiness HTTP 200/503 without simulated fallbacks or leaked secrets).
6. Removed deprecated configuration names and obsolete `requirements.txt`.
7. Created `.github/workflows/backend-ci.yml` providing automated backend verification on Ubuntu with PostgreSQL 16 and Redis 7 service containers.

---

## Files Changed

- `backend/.python-version` — [NEW] Declares explicit Python 3.12 runtime.
- `backend/pyproject.toml` — [MODIFIED] Added `[tool.uv] package = false` and preserved locked dependencies.
- `backend/uv.lock` — [NEW] Committed frozen dependency lockfile generated with uv.
- `backend/requirements.txt` — [REMOVED] Replaced by `pyproject.toml` and `uv.lock`.
- `backend/.env.example` — [MODIFIED] Updated with approved non-secret B1 setting names.
- `backend/.dockerignore` — [NEW] Excluded git, caches, secrets, media, artifacts, and local environments.
- `backend/Dockerfile` — [MODIFIED] Uses `python:3.12.11-slim-bookworm`, `uv:0.8.13`, `uv sync --frozen --no-dev`.
- `backend/docker-compose.yml` — [MODIFIED] Removed top-level version, updated B1 setting names.
- `backend/config/settings/base.py` — [MODIFIED] Single `DATABASE_URL` via `dj_database_url`, separate Redis/Celery URLs, explicit OpenHands vs LLM settings, setting validation helpers, single `MEDIA_URL`/`MEDIA_ROOT`.
- `backend/runtime/adapters/openhands/config.py` — [MODIFIED] `OpenHandsServerConfig` with separate server vs LLM fields and secret-safe `__repr__`.
- `backend/runtime/adapters/openhands/adapter.py` — [MODIFIED] Agent Server headers & workspace receive only `server_api_key`; LLM receives only `llm_api_key`; removed key fallbacks.
- `backend/apps/generations/services/execution_service.py` — [MODIFIED] Constructed `OpenHandsServerConfig` with new settings; resolved `LLM_DEFAULT_MODEL`.
- `backend/apps/core/views.py` — [MODIFIED] Truthful readiness probe returning 200/503 with stable error codes and no simulated fallbacks.
- `backend/apps/core/tests/test_health.py` — [MODIFIED] Cleaned imports, added mocked readiness failure tests, asserted zero credential leaks.
- `backend/runtime/tests/test_openhands_adapter.py` — [MODIFIED] Added credential boundary isolation tests and repr secret masking tests.
- `backend/tests/integration/test_openhands_live.py` — [MODIFIED] Updated with new config names.
- `backend/scripts/run_live_openrouter_test.py` — [MODIFIED] Updated with new config names.
- `backend/scripts/verify_live_celery_openrouter_execution.py` — [MODIFIED] Updated with new config names.
- `backend/apps/control_center/views.py` — [MODIFIED] Updated setting references for runtime posture.
- `backend/apps/control_center/tests/test_control_center_api.py` — [MODIFIED] Asserted zero credential leaks.
- `backend/apps/control_center/tests/test_control_center_detail_api.py` — [MODIFIED] Asserted zero credential leaks.
- `.github/workflows/backend-ci.yml` — [NEW] GitHub Actions workflow for backend CI.
- `README.md` — [MODIFIED] Documented Python 3.12, uv, Docker Compose, health endpoints, and credential boundaries.
- `docs/OPENHANDS-INTEGRATION.md` — [NEW] Documented OpenHands SDK integration and credential rules.

---

## Removal Ledger

| Candidate Item | Classification | Action Taken / Justification |
|---|---|---|
| `backend/requirements.txt` | `REMOVE` | Deleted. Fully replaced by `backend/pyproject.toml` and `backend/uv.lock`. |
| Duplicate database path in `base.py` | `REMOVE` | Removed manual `DATABASES` dict fallback; unified on `dj_database_url.parse`. |
| Duplicate `MEDIA_URL` / `MEDIA_ROOT` | `REMOVE` | Unified into single declaration in `base.py`. |
| `OPENHANDS_SERVER_URL` | `REPLACE` | Replaced by `OPENHANDS_AGENT_SERVER_URL`. |
| `OPENHANDS_API_KEY` | `REPLACE` | Replaced by `OPENHANDS_AGENT_SERVER_API_KEY`. |
| `OPENHANDS_TIMEOUT_SECONDS` | `REPLACE` | Replaced by `OPENHANDS_AGENT_SERVER_TIMEOUT_SECONDS`. |
| `OPENHANDS_DEFAULT_MODEL` | `REPLACE` | Replaced by `LLM_DEFAULT_MODEL`. |
| Agent Server key fallback to LLM | `REMOVE` | Deleted fallback logic in `adapter.py`. |
| Health `simulated` fallback | `REMOVE` | Deleted simulated status in `apps/core/views.py`; now returns truthful 503 on failure. |
| Duplicate health test imports | `REMOVE` | Cleaned in `apps/core/tests/test_health.py`. |
| Stale Python 3.11 documentation | `REPLACE` | Updated to Python 3.12 in `README.md` and configuration files. |

---

## Migrations

- `none` (No database schema alterations required for foundation baseline).

---

## Tests and Verification Commands

All commands executed from `backend/`:

1. **`uv --version`**:
   - `uv 0.12.5 (210d1f678 2026-08-14 x86_64-pc-windows-msvc)`
2. **`python --version`**:
   - `Python 3.12.14`
3. **`uv lock --check`**:
   - `Resolved 399 packages in 68ms` (PASSED)
4. **`uv sync --frozen --extra dev`**:
   - `Audited 399 packages in 2ms` (PASSED)
5. **OpenHands Package Versions Verification**:
   - Command: `uv run python -c "import importlib.metadata as m; print({p: m.version(p) for p in ['openhands-sdk','openhands-tools','openhands-agent-server','openhands-workspace']})"`
   - Output: `{'openhands-sdk': '1.42.1', 'openhands-tools': '1.42.1', 'openhands-agent-server': '1.42.1', 'openhands-workspace': '1.42.1'}` (PASSED)
6. **`uv run python manage.py check`**:
   - `System check identified no issues (0 silenced).` (PASSED)
7. **`uv run python manage.py makemigrations --check --dry-run`**:
   - `No changes detected` (PASSED)
8. **`uv run pytest`**:
   - **158 passed, 1 skipped in 50.55s** (100% test baseline pass rate)
   - Skipped test: `test_live_agent_coding_task_execution` (skipped solely due to absence of live paid API key in test environment, as expected).

---

## Exit Criteria Evidence

- **Criterion 1: Reproducible dependency installation from committed files**: Verified via `pyproject.toml` and `uv.lock` with `uv sync --frozen --extra dev`.
- **Criterion 2: Explicit and compatible Python version**: Verified `Python 3.12.14` declared in `.python-version`, `pyproject.toml`, and `Dockerfile`.
- **Criterion 3: OpenHands packages install and import together**: Verified all 4 OpenHands packages (`openhands-sdk`, `openhands-tools`, `openhands-agent-server`, `openhands-workspace`) at `1.42.1`.
- **Criterion 4: Django system check**: Passed with 0 issues identified.
- **Criterion 5: Migration consistency check**: Passed with no changes detected.
- **Criterion 6: Backend test suite run to completion**: Passed with 158 passed tests and 0 failures.
- **Criterion 7: Credential boundary isolation**: Verified by unit test `test_credential_boundary_isolation` and `test_config_secret_masking`.
- **Criterion 8: No credential committed or serialized**: Verified by regex assertions in health and control center test suites.
- **Criterion 9: No future milestone functionality added**: Scoped strictly to B1 backend foundation.

---

## Unresolved Failures

- `none`

---

## Scope Deviations

- `docker compose config` and `docker build` commands were not executed locally on the Windows development host because the Docker CLI is not installed on the host PATH. Full container verification is expressed and automated in `.github/workflows/backend-ci.yml`.

---

## Security & Compatibility Notes

- Environment variable isolation strictly prevents Agent Server authorization tokens from being routed to LiteLLM or model providers.
- Health check endpoints sanitize all connection error logs and never return raw exceptions or credentials in response payloads.
