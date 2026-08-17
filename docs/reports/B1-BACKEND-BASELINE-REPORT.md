# B1 — Backend Baseline Evidence & Verification Report

## Session Metadata

- **Session**: Antigravity Session 01 — Reproducible Backend Baseline (Milestone B1 Correction & Finalization)
- **Branch**: `feature/b1-backend-baseline`
- **Base / Parent Commit**: `74345f5a82ce52922ae32db861db1633e4d4eb35`
- **Original Reviewed Commit**: `ae3273d9327991308d5840b9085702613a128c97`
- **Specification**: `docs/B1-BACKEND-BASELINE-PHASE-SPEC.md` & `docs/B1-BACKEND-BASELINE-DETAILED-IMPLEMENTATION.md`
- **Protocol**: `docs/ANTIGRAVITY-DEVELOPMENT-PROTOCOL.md`

---

## Objective Completed

Established a truthful, reproducible, and secure backend foundation for roadmap milestone B1, resolving all 12 review findings:
1. Pinned explicit supported Python runtime version (Python 3.12 via `.python-version` and `Dockerfile`).
2. Replaced unpinned dependency installation with committed `pyproject.toml` and `uv.lock` generated and verified with exact `uv 0.8.13`.
3. Verified co-installation and imports of all 4 OpenHands 1.42.1 packages (`openhands-sdk`, `openhands-tools`, `openhands-agent-server`, `openhands-workspace`).
4. Enforced strict credential boundary separation using `pydantic.SecretStr | None` for `server_api_key` and `llm_api_key`. Secrets are unwrapped only at the exact SDK sink (`OpenHandsRemoteWorkspace.api_key` and `OpenHandsLLM.api_key`).
5. Implemented table-driven model prefix credential selection (`openrouter/`, `anthropic/`, `openai/`, `gemini/`, `groq/`) with zero credential borrowing across providers and strict isolation from Agent Server tokens.
6. Applied `server_timeout_seconds` to `RemoteWorkspace(read_timeout=...)` and enforced mandatory TLS verification (`server_verify_ssl=True`), rejecting `server_verify_ssl=False` with a clear configuration error.
7. Removed dead handwritten `_get_headers` helper.
8. Configured `AGENT_RUNTIME_BACKEND=mock` as the safe default in `docker-compose.yml` and `.env.example`, removing forced localhost Agent Server endpoints from the Compose baseline.
9. Added container configuration validation (`docker compose config`) and image build (`docker build -t tersuite-backend:b1 .`) to `.github/workflows/backend-ci.yml`.
10. Restored all 6 protected active architecture contracts and authoritative instructions (`AGENTS.md`, roadmap Principle 13, protocol three-document workflow, Session 01 execution prompt). Removed duplicate `docs/AGENTS.md` and untracked binary ZIP.

---

## Files Changed, Restored, Created, and Removed

### Created
- `.github/workflows/backend-ci.yml` — [NEW] GitHub Actions CI workflow with PostgreSQL 16, Redis 7, uv 0.8.13, Django checks, pytest, Docker compose validation, and container build.
- `backend/.dockerignore` — [NEW] Excluded git, caches, secrets, media, artifacts, and local virtual environments.
- `backend/.python-version` — [NEW] Declares explicit Python 3.12 runtime.
- `backend/uv.lock` — [NEW] Committed frozen dependency lockfile generated and validated with uv 0.8.13.
- `docs/reports/B1-BACKEND-BASELINE-REPORT.md` — [NEW] Committed comprehensive evidence and verification report.

### Modified
- `AGENTS.md` — [MODIFIED] Replaced with authoritative multi-agent guidelines; sole authoritative AGENTS file.
- `README.md` — [MODIFIED] Documented Python 3.12, uv, Docker Compose quickstart, health endpoints, and credential boundaries.
- `backend/.env.example` — [MODIFIED] Set `AGENT_RUNTIME_BACKEND=mock`, clean placeholders, separate Agent Server vs LLM provider keys.
- `backend/Dockerfile` — [MODIFIED] Uses `python:3.12.11-slim-bookworm`, `uv:0.8.13`, `uv sync --frozen --no-dev`.
- `backend/docker-compose.yml` — [MODIFIED] Set `AGENT_RUNTIME_BACKEND=mock` on web and celery; removed forced localhost Agent Server settings.
- `backend/pyproject.toml` — [MODIFIED] Added `[tool.uv] package = false` and preserved locked dependencies.
- `backend/config/settings/base.py` — [MODIFIED] Single `DATABASE_URL` via `dj_database_url`, separate Redis/Celery URLs, explicit OpenHands vs LLM settings, setting validation helpers, single `MEDIA_URL`/`MEDIA_ROOT`.
- `backend/runtime/adapters/openhands/config.py` — [MODIFIED] `OpenHandsServerConfig` with `pydantic.SecretStr | None` keys, mandatory TLS verification in `__post_init__`, and standard dataclass repr masking.
- `backend/runtime/adapters/openhands/adapter.py` — [MODIFIED] Prefix-matched provider credential resolution, unwrapped `read_timeout` on `RemoteWorkspace`, removed `_get_headers`.
- `backend/apps/generations/services/execution_service.py` — [MODIFIED] Resolved `LLM_DEFAULT_MODEL`; does not hardcode OpenRouter key to generic LLM.
- `backend/apps/core/views.py` — [MODIFIED] Truthful readiness probe returning 200/503 with stable error codes and no simulated fallbacks.
- `backend/apps/core/tests/test_health.py` — [MODIFIED] Cleaned imports, added mocked readiness failure tests, asserted zero credential leaks.
- `backend/runtime/tests/test_openhands_adapter.py` — [MODIFIED] Added secret masking tests (`repr`, `asdict`, `json.dumps`), TLS mandatory rejection tests, workspace timeout propagation tests, and table-driven provider selection tests.
- `backend/runtime/tests/test_runtime_contracts.py` — [MODIFIED] Added test asserting default Compose and `.env.example` backend is mock with no forced Agent Server.
- `backend/tests/integration/test_openhands_live.py` — [MODIFIED] Updated with new configuration setting names.
- `backend/scripts/run_live_openrouter_test.py` — [MODIFIED] Updated with new configuration setting names.
- `backend/scripts/verify_live_celery_openrouter_execution.py` — [MODIFIED] Updated with new configuration setting names.
- `backend/apps/control_center/views.py` — [MODIFIED] Updated setting references for runtime posture.
- `backend/apps/control_center/tests/test_control_center_api.py` — [MODIFIED] Asserted zero credential leaks.
- `backend/apps/control_center/tests/test_control_center_detail_api.py` — [MODIFIED] Asserted zero credential leaks.
- `docs/OPENHANDS-INTEGRATION.md` — [MODIFIED] Restored from parent commit and updated with B1 uv install, OpenHands 1.42.1, setting names, and TLS/timeout rules.
- `docs/TERSUITE-IMPLEMENTATION-ROADMAP.md` — [MODIFIED] Restored Principle 13, milestone removal requirements, and B0 obsolete-code ledger.
- `docs/ANTIGRAVITY-DEVELOPMENT-PROTOCOL.md` — [MODIFIED] Restored three-document workflow, non-invention rule, removal reporting, and pre-deletion rules.
- `docs/ANTIGRAVITY-SESSION-01-BACKEND-BASELINE.md` — [MODIFIED] Restored as final execution-only prompt requiring reading order.

### Restored Active Contracts (from Parent Commit `74345f5`)
- `docs/API-CONTRACT.md` — [RESTORED] Active API contract.
- `docs/CC-02 Implementation Spec.md` — [RESTORED] Active Control Center specification.
- `docs/CC-03-OPERATIONAL-ACTIONS-SPEC.md` — [RESTORED] Active Control Center actions specification.
- `docs/DATA-MODEL.md` — [RESTORED] Active Data Model contract.
- `docs/TERSUITE-CONTROL-CENTER-CC-01-SPEC.md` — [RESTORED] Active Control Center specification.
- `docs/TERSUITE-CONTROL-CENTER-CC-02-SPEC.md` — [RESTORED] Active Control Center specification.

### Removed
- `backend/requirements.txt` — [REMOVED] Replaced by `backend/pyproject.toml` and `backend/uv.lock`.
- `docs/AGENTS.md` — [REMOVED] Merged into authoritative root `AGENTS.md`.
- `docs/doc (dont open or use).zip` — [REMOVED] Unused binary archive removed from tracking.
- `docs/TERSUITE-PHASE-1-CORRECTION-SPEC.md` — [REMOVED] Pre-existing user-approved cleanup of superseded milestone spec.
- `docs/TERSUITE-PHASE-2-IMPLEMENTATION-SPEC.md` — [REMOVED] Pre-existing user-approved cleanup of superseded milestone spec.
- `docs/Tersuite AI Studio Phase 5 Implementation Spec.md` — [REMOVED] Pre-existing user-approved cleanup of superseded milestone spec.

---

## Removal Ledger

| Candidate Item | Classification | Action Taken / Justification |
|---|---|---|
| `backend/requirements.txt` | `REMOVE` | Deleted. Fully replaced by `backend/pyproject.toml` and `backend/uv.lock`. |
| `docs/AGENTS.md` | `REMOVE` | Deleted duplicate; content moved to authoritative root `AGENTS.md`. |
| `docs/doc (dont open or use).zip` | `REMOVE` | Untracked binary ZIP removed without extraction or usage. |
| Duplicate database path in `base.py` | `REMOVE` | Removed manual `DATABASES` dict fallback; unified on `dj_database_url.parse`. |
| Duplicate `MEDIA_URL` / `MEDIA_ROOT` | `REMOVE` | Unified into single declaration in `base.py`. |
| `_get_headers` helper in `adapter.py` | `REMOVE` | Deleted dead handwritten header generator; SDK RemoteWorkspace owns authentication. |
| `OPENHANDS_SERVER_URL` | `REPLACE` | Replaced by `OPENHANDS_AGENT_SERVER_URL`. |
| `OPENHANDS_API_KEY` | `REPLACE` | Replaced by `OPENHANDS_AGENT_SERVER_API_KEY`. |
| `OPENHANDS_TIMEOUT_SECONDS` | `REPLACE` | Replaced by `OPENHANDS_AGENT_SERVER_TIMEOUT_SECONDS`. |
| `OPENHANDS_DEFAULT_MODEL` | `REPLACE` | Replaced by `LLM_DEFAULT_MODEL`. |
| Agent Server key fallback to LLM | `REMOVE` | Deleted fallback logic in `adapter.py`. |
| Health `simulated` fallback | `REMOVE` | Deleted simulated status in `apps/core/views.py`; now returns truthful 503 on failure. |
| Duplicate health test imports | `REMOVE` | Cleaned in `apps/core/tests/test_health.py`. |
| Stale Python 3.11 documentation | `REPLACE` | Updated to Python 3.12 in `README.md` and configuration files. |
| `docs/TERSUITE-PHASE-1-CORRECTION-SPEC.md` | `REMOVE` | Pre-existing user-approved cleanup of superseded milestone spec. |
| `docs/TERSUITE-PHASE-2-IMPLEMENTATION-SPEC.md` | `REMOVE` | Pre-existing user-approved cleanup of superseded milestone spec. |
| `docs/Tersuite AI Studio Phase 5 Implementation Spec.md` | `REMOVE` | Pre-existing user-approved cleanup of superseded milestone spec. |

---

## Migrations

- `none` (No database schema alterations required for foundation baseline).

---

## Tests and Verification Commands

All commands executed from `backend/`:

1. **`git diff --check`**:
   - Clean output with 0 whitespace or formatting errors (PASSED).
2. **`uv --version`**:
   - `uv 0.8.13 (ede75fe62 2025-08-21)` (PASSED - exact required version).
3. **`uv lock --check`**:
   - `Resolved 399 packages in 4ms` (PASSED - lockfile completely satisfied).
4. **`uv sync --frozen --extra dev`**:
   - `Installed 5 packages in 818ms` (PASSED).
5. **OpenHands Package Versions Verification**:
   - Command: `uv run python -c "import importlib.metadata as m; print({p: m.version(p) for p in ['openhands-sdk','openhands-tools','openhands-agent-server','openhands-workspace']})"`
   - Output: `{'openhands-sdk': '1.42.1', 'openhands-tools': '1.42.1', 'openhands-agent-server': '1.42.1', 'openhands-workspace': '1.42.1'}` (PASSED).
6. **`uv run python manage.py check`**:
   - `System check identified no issues (0 silenced).` (PASSED).
7. **`uv run python manage.py makemigrations --check --dry-run`**:
   - `No changes detected` (PASSED).
8. **`uv run pytest`**:
   - **161 passed, 1 skipped in 40.76s** (100% test pass rate).
   - Skipped test: `test_live_agent_coding_task_execution` (skipped solely due to absence of live paid model key in test environment, as expected).

---

## Exit Criteria Evidence

- **Criterion 1: Reproducible dependency installation from committed files**: Verified with `pyproject.toml` and `uv.lock` using exact `uv 0.8.13`.
- **Criterion 2: Explicit and compatible Python version**: Verified Python 3.12 declared in `.python-version`, `pyproject.toml`, and `Dockerfile`.
- **Criterion 3: OpenHands packages install and import together**: Verified all 4 OpenHands packages (`openhands-sdk`, `openhands-tools`, `openhands-agent-server`, `openhands-workspace`) at `1.42.1`.
- **Criterion 4: Django system check**: Passed with 0 issues identified.
- **Criterion 5: Migration consistency check**: Passed with no changes detected.
- **Criterion 6: Backend test suite run to completion**: Passed with 161 passed tests and 0 failures.
- **Criterion 7: Credential boundary isolation & SecretStr protection**: Verified by `test_config_secret_masking`, `test_credential_boundary_isolation`, and `test_table_driven_provider_credential_selection`.
- **Criterion 8: Timeout & TLS enforcement**: Verified by `test_workspace_timeout_propagation` and `test_tls_verification_mandatory`.
- **Criterion 9: No credential committed or serialized**: Verified by regex assertions in health and control center test suites.
- **Criterion 10: Safe Compose defaults**: Verified by `test_compose_and_env_mock_backend_default`.
- **Criterion 11: Active contracts preserved**: All 6 active contracts restored and verified.
- **Criterion 12: No future milestone functionality added**: Scoped strictly to B1 backend baseline.

---

## Unresolved Failures

- `none`

---

## Scope Deviations

- In the original commit `ae3273d`, documentation cleanups for superseded phase documents were bundled without explicit reporting. This correction report now explicitly catalogs all restored active contracts, authoritative instructions, and pre-existing legacy document removals.
- `docker compose config` and `docker build` commands cannot be executed directly on the Windows development host because the host lacks Docker CLI on PATH; both commands are explicitly integrated and automated in `.github/workflows/backend-ci.yml`.

---

## Security & Compatibility Notes

- `OpenHandsServerConfig` stores `server_api_key` and `llm_api_key` as `pydantic.SecretStr | None`. Standard dataclass representations, `asdict`, and JSON serializations mask secrets and never leak plaintext tokens.
- Secret tokens are unwrapped with `.get_secret_value()` strictly at the SDK sink (`OpenHandsRemoteWorkspace.api_key` and `OpenHandsLLM.api_key`).
- Provider credentials are strictly mapped based on the model prefix (`openrouter/`, `anthropic/`, `openai/`, `gemini/`, `groq/`). Unknown prefixes receive no key and never borrow credentials from other providers or the Agent Server.
