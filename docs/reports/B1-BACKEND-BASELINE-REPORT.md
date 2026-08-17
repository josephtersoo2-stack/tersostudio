# B1 — Backend Baseline Evidence & Verification Report

## Session Metadata

- **Session**: Antigravity Session 01 — Reproducible Backend Baseline (Correction 02 Finalization)
- **Branch**: `feature/b1-backend-baseline`
- **Base / Parent Commit**: `74345f5a82ce52922ae32db861db1633e4d4eb35`
- **Original Reviewed Commit**: `ae3273d9327991308d5840b9085702613a128c97`
- **Correction 01 Commit**: `af994f26ec0ca40174f62c9e0259df284f169879`
- **Specification**: `docs/B1-BACKEND-BASELINE-PHASE-SPEC.md` & `docs/B1-BACKEND-BASELINE-DETAILED-IMPLEMENTATION.md`
- **Protocol**: `docs/ANTIGRAVITY-DEVELOPMENT-PROTOCOL.md`

---

## Objective Completed

Established a truthful, reproducible, and secure backend foundation for roadmap milestone B1, resolving all findings across review iterations:
1. Pinned explicit supported Python runtime version (Python 3.12 minor line via `.python-version` and `Dockerfile`).
2. Replaced unpinned dependency installation with committed `pyproject.toml` and `uv.lock` generated and verified with exact `uv 0.8.13`.
3. Verified co-installation and imports of all 4 OpenHands 1.42.1 packages (`openhands-sdk`, `openhands-tools`, `openhands-agent-server`, `openhands-workspace`).
4. Enforced strict credential boundary separation using `pydantic.SecretStr | None` for `server_api_key` and `llm_api_key`. The Agent Server secret is unwrapped with `.get_secret_value()` solely for `OpenHandsRemoteWorkspace.api_key`, while the provider `SecretStr` is passed to `OpenHandsLLM.api_key`.
5. Implemented table-driven model prefix credential selection (`openrouter/`, `anthropic/`, `openai/`, `gemini/`, `groq/`) with zero credential borrowing across providers and strict isolation from Agent Server tokens.
6. Applied `server_timeout_seconds` to `RemoteWorkspace(read_timeout=...)` and enforced mandatory TLS verification (`server_verify_ssl=True`), rejecting `server_verify_ssl=False` with a clear configuration error.
7. Removed dead handwritten `_get_headers` helper and cleaned all unused imports.
8. Configured `AGENT_RUNTIME_BACKEND=mock` as the safe default in `docker-compose.yml` and `.env.example`, removing forced localhost Agent Server endpoints from the Compose baseline.
9. Added container configuration validation (`docker compose config`) and image build (`docker build -t tersuite-backend:b1 .`) to `.github/workflows/backend-ci.yml`, and configured PostgreSQL health command with `-U tersuite -d tersuite_test_db`.
10. Restored all 6 protected active architecture contracts and authoritative instructions (`AGENTS.md`, roadmap Principle 13, protocol three-document workflow, Session 01 execution prompt). Removed duplicate `docs/AGENTS.md` and tracked binary ZIP.

---

## Files Changed Across Review & Corrections

### Correction 02 Changes (Current)
- `.github/workflows/backend-ci.yml` — [MODIFIED] Added explicit user and database flags to PostgreSQL service health check (`pg_isready -U tersuite -d tersuite_test_db`) and removed extra blank line at EOF.
- `backend/runtime/adapters/openhands/adapter.py` — [MODIFIED] Removed unused OpenHands SDK imports and sorted imports.
- `backend/runtime/adapters/openhands/config.py` — [MODIFIED] Removed unused `typing.Union` import and sorted imports.
- `backend/runtime/tests/test_openhands_adapter.py` — [MODIFIED] Removed unused `NormalizedEvent` import and sorted imports.
- `backend/runtime/tests/test_runtime_contracts.py` — [MODIFIED] Removed unused `os` import, sorted imports, and removed extra blank line at EOF.
- `backend/apps/core/views.py` — [MODIFIED] Formatted and sorted imports.
- `backend/apps/core/tests/test_health.py` — [MODIFIED] Formatted and sorted imports.
- `docs/ANTIGRAVITY-SESSION-01-BACKEND-BASELINE.md` — [MODIFIED] Replaced completely with the authoritative prompt from Appendix A without a closed file list.
- `docs/OPENHANDS-INTEGRATION.md` — [MODIFIED] Fixed relative markdown links (`../AGENTS.md`, `TERSUITE-IMPLEMENTATION-ROADMAP.md`), clarified Python 3.12 and PostgreSQL 16 minor/major line definitions, and stated exact SecretStr handling.
- `docs/B1-BACKEND-BASELINE-DETAILED-IMPLEMENTATION.md` — [MODIFIED] Removed extra blank line at EOF to satisfy base-to-head `git diff --check`.
- `docs/B1-BACKEND-BASELINE-PHASE-SPEC.md` — [MODIFIED] Removed extra blank line at EOF to satisfy base-to-head `git diff --check`.
- `docs/reports/B1-BACKEND-BASELINE-REPORT.md` — [MODIFIED] Updated comprehensive verification evidence and diff history.

### Earlier B1 Changes & Restorations (ae3273d + af994f2)
- `.github/workflows/backend-ci.yml` — [NEW] GitHub Actions workflow.
- `backend/.dockerignore` — [NEW] Excluded caches, secrets, media, artifacts, venvs.
- `backend/.python-version` — [NEW] Declares Python 3.12.
- `backend/uv.lock` — [NEW] Committed frozen dependency lockfile generated with uv 0.8.13.
- `AGENTS.md` — [MODIFIED] Authoritative multi-agent operating guidelines.
- `README.md` — [MODIFIED] Documented Python 3.12, uv, Docker Compose, health probes, and credential separation.
- `backend/.env.example` — [MODIFIED] Safe environment template with `AGENT_RUNTIME_BACKEND=mock`.
- `backend/Dockerfile` — [MODIFIED] Multi-stage build with Python 3.12.11-slim-bookworm and uv 0.8.13.
- `backend/docker-compose.yml` — [MODIFIED] Safe Compose baseline with `mock` backend.
- `backend/pyproject.toml` — [MODIFIED] Added `[tool.uv] package = false`.
- `backend/config/settings/base.py` — [MODIFIED] Single `DATABASE_URL`, setting validation helpers, explicit setting names.
- `backend/apps/generations/services/execution_service.py` — [MODIFIED] Resolved `LLM_DEFAULT_MODEL`; decoupled provider key assignment.
- `backend/apps/core/views.py` — [MODIFIED] Truthful liveness and readiness probes.
- `backend/apps/control_center/views.py` — [MODIFIED] Updated setting names in runtime posture.
- `docs/TERSUITE-IMPLEMENTATION-ROADMAP.md` — [MODIFIED] Restored Principle 13, milestone removal rules, and B0 obsolete-code ledger.
- `docs/ANTIGRAVITY-DEVELOPMENT-PROTOCOL.md` — [MODIFIED] Restored three-document workflow, non-invention rule, and pre-deletion rules.
- `docs/API-CONTRACT.md` — [RESTORED] Active API contract restored from parent commit `74345f5`.
- `docs/CC-02 Implementation Spec.md` — [RESTORED] Active Control Center specification restored from parent commit `74345f5`.
- `docs/CC-03-OPERATIONAL-ACTIONS-SPEC.md` — [RESTORED] Active Control Center actions spec restored from parent commit `74345f5`.
- `docs/DATA-MODEL.md` — [RESTORED] Active Data Model contract restored from parent commit `74345f5`.
- `docs/TERSUITE-CONTROL-CENTER-CC-01-SPEC.md` — [RESTORED] Active Control Center specification restored from parent commit `74345f5`.
- `docs/TERSUITE-CONTROL-CENTER-CC-02-SPEC.md` — [RESTORED] Active Control Center specification restored from parent commit `74345f5`.
- `backend/requirements.txt` — [REMOVED] Replaced by `pyproject.toml` and `uv.lock`.
- `docs/AGENTS.md` — [REMOVED] Merged into authoritative root `AGENTS.md`.
- `docs/doc (dont open or use).zip` — [REMOVED] Tracked in commit `ae3273d` and removed in `af994f2` without extraction or usage.
- `docs/TERSUITE-PHASE-1-CORRECTION-SPEC.md` — [REMOVED] Pre-existing user-approved cleanup of superseded milestone spec.
- `docs/TERSUITE-PHASE-2-IMPLEMENTATION-SPEC.md` — [REMOVED] Pre-existing user-approved cleanup of superseded milestone spec.
- `docs/Tersuite AI Studio Phase 5 Implementation Spec.md` — [REMOVED] Pre-existing user-approved cleanup of superseded milestone spec.

---

## Removal Ledger

| Item | Classification | Action Taken / Justification |
|---|---|---|
| `backend/requirements.txt` | `REMOVE` | Deleted. Fully replaced by `backend/pyproject.toml` and `backend/uv.lock`. |
| `docs/AGENTS.md` | `REMOVE` | Duplicate removed; content moved to authoritative root `AGENTS.md`. |
| `docs/doc (dont open or use).zip` | `REMOVE` | Tracked in commit `ae3273d` and removed in `af994f2` without extraction or usage. |
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

All commands executed from `backend/` and repository root:

1. **`git diff --check 74345f5a82ce52922ae32db861db1633e4d4eb35`**:
   - Clean output with 0 whitespace errors (PASSED). Acknowledges resolution of prior end-of-file blank-line warnings.
2. **`uv --version`**:
   - `uv 0.8.13 (ede75fe62 2025-08-21)` (PASSED - exact required version).
3. **`uv lock --check`**:
   - `Resolved 399 packages in 4ms` (PASSED - lockfile completely satisfied).
4. **`uv sync --frozen --extra dev`**:
   - Audited/installed cleanly in 818ms (PASSED).
5. **Focused Import Hygiene (Ruff)**:
   - Command: `uv run ruff check --select F401,I001 runtime/adapters/openhands/config.py runtime/adapters/openhands/adapter.py runtime/tests/test_openhands_adapter.py runtime/tests/test_runtime_contracts.py apps/core/views.py apps/core/tests/test_health.py`
   - Output: `All checks passed!` with 0 errors (PASSED).
6. **OpenHands Package Versions Verification**:
   - Command: `uv run python -c "import importlib.metadata as m; print({p: m.version(p) for p in ['openhands-sdk','openhands-tools','openhands-agent-server','openhands-workspace']})"`
   - Output: `{'openhands-sdk': '1.42.1', 'openhands-tools': '1.42.1', 'openhands-agent-server': '1.42.1', 'openhands-workspace': '1.42.1'}` (PASSED).
7. **`uv run python manage.py check`**:
   - `System check identified no issues (0 silenced).` (PASSED).
8. **`uv run python manage.py makemigrations --check --dry-run`**:
   - `No changes detected` (PASSED).
9. **`uv run pytest`**:
   - **161 passed, 1 skipped in 40.76s** (100% test pass rate).
10. **GitHub Actions CI Run for Correction 01 (Commit af994f2)**:
    - Run URL: `https://github.com/josephtersoo2-stack/tersostudio/actions/runs/32013363279`
    - Result: **Successful** (161 passed, 1 skipped, Docker Compose config and container image build passed).

---

## Exit Criteria Evidence

- **Criterion 1: Reproducible dependency installation**: Verified with `pyproject.toml` and `uv.lock` using exact `uv 0.8.13`.
- **Criterion 2: Explicit Python version**: Verified Python 3.12 declared in `.python-version`, `pyproject.toml`, and `Dockerfile`.
- **Criterion 3: OpenHands packages install and import together**: Verified all 4 OpenHands packages (`openhands-sdk`, `openhands-tools`, `openhands-agent-server`, `openhands-workspace`) at `1.42.1`.
- **Criterion 4: Django system check**: Passed with 0 issues identified.
- **Criterion 5: Migration consistency check**: Passed with no changes detected.
- **Criterion 6: Backend test suite run to completion**: Passed with 161 passed tests and 0 failures.
- **Criterion 7: Credential boundary isolation & SecretStr protection**: Verified by `test_config_secret_masking`, `test_credential_boundary_isolation`, and `test_table_driven_provider_credential_selection`.
- **Criterion 8: Timeout & TLS enforcement**: Verified by `test_workspace_timeout_propagation` and `test_tls_verification_mandatory`.
- **Criterion 9: No credential committed or serialized**: Verified by regex assertions in health and control center test suites.
- **Criterion 10: Safe Compose defaults**: Verified by `test_compose_and_env_mock_backend_default`.
- **Criterion 11: Active contracts preserved**: All 6 active contracts restored and verified.
- **Criterion 12: Whitespace and diff hygiene**: Verified with `git diff --check` against base commit `74345f5`.

---

## Unresolved Failures

- `none`

---

## Scope Deviations

- `none`
