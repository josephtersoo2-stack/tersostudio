# B1 — Backend Baseline Evidence & Verification Report

## Session Metadata

- **Session**: Antigravity Session 01 — Reproducible Backend Baseline (Milestone B1 Verification & Finalization)
- **Branch**: `feature/b1-backend-baseline`
- **Base / Parent Commit**: `74345f5a82ce52922ae32db861db1633e4d4eb35`
- **Original Reviewed Commit**: `ae3273d9327991308d5840b9085702613a128c97`
- **Correction 01 Commit**: `af994f26ec0ca40174f62c9e0259df284f169879`
- **Reviewed Implementation Commit**: `4488a760d36b5f16054f105ce46ec524f2c85bab`
- **Specification**: `docs/B1-BACKEND-BASELINE-PHASE-SPEC.md` & `docs/B1-BACKEND-BASELINE-DETAILED-IMPLEMENTATION.md`
- **Protocol**: `docs/ANTIGRAVITY-DEVELOPMENT-PROTOCOL.md`

---

## Objective Completed

Established a truthful, reproducible, and secure backend foundation for roadmap milestone B1, resolving all findings across review iterations:
1. Pinned explicit supported Python runtime version (Python 3.12 minor line via `.python-version` and `Dockerfile`).
2. Replaced unpinned dependency installation with committed `pyproject.toml` and `uv.lock` generated and verified with exact `uv 0.8.13`.
3. Verified co-installation and imports of all 4 OpenHands 1.42.1 packages (`openhands-sdk`, `openhands-tools`, `openhands-agent-server`, `openhands-workspace`).
4. Enforced strict credential boundary separation using `pydantic.SecretStr | None` for `server_api_key` and `llm_api_key`. The Agent Server secret is unwrapped with `.get_secret_value()` solely for `OpenHandsRemoteWorkspace.api_key`, while the provider `SecretStr` is passed directly to `OpenHandsLLM.api_key`.
5. Implemented table-driven model prefix credential selection (`openrouter/`, `anthropic/`, `openai/`, `gemini/`, `groq/`) with zero credential borrowing across providers and strict isolation from Agent Server tokens.
6. Applied `server_timeout_seconds` to `RemoteWorkspace(read_timeout=...)` and enforced mandatory TLS verification (`server_verify_ssl=True`), rejecting `server_verify_ssl=False` with a clear configuration error.
7. Removed dead handwritten `_get_headers` helper and cleaned all unused imports to pass focused Ruff checks (`F401`, `I001`).
8. Configured `AGENT_RUNTIME_BACKEND=mock` as the safe default in `docker-compose.yml` and `.env.example`, removing forced localhost Agent Server endpoints from the Compose baseline.
9. Added container configuration validation (`docker compose config`) and image build (`docker build -t tersuite-backend:b1 .`) to `.github/workflows/backend-ci.yml`, and configured PostgreSQL health command with `-U tersuite -d tersuite_test_db`.
10. Restored all 6 protected active architecture contracts and authoritative instructions (`AGENTS.md`, roadmap Principle 13, protocol three-document workflow, Session 01 execution prompt). Removed duplicate `docs/AGENTS.md` and tracked binary ZIP.

---

## Files Changed Across Review & Corrections

### Correction 03 Changes (Current)
- `docs/reports/B1-BACKEND-BASELINE-REPORT.md` — [MODIFIED] Documentation-only evidence correction recording final verified local and CI execution data, restoring required protocol sections (Security/Compatibility Notes, Documentation Updated), documenting resolved historical scope deviations, and restoring complete exit-criteria evidence.

### Correction 02 Changes (Implementation Commit `4488a76`)
- `.github/workflows/backend-ci.yml` — [MODIFIED] Added explicit user and database flags to PostgreSQL service health check (`pg_isready -U tersuite -d tersuite_test_db`) and removed extra blank line at EOF.
- `backend/runtime/adapters/openhands/adapter.py` — [MODIFIED] Removed unused OpenHands SDK imports (`RemoteEventsList`, `ActionEvent`, `AgentErrorEvent`, `InterruptEvent`, `MessageEvent`, `ObservationEvent`) and sorted imports.
- `backend/runtime/adapters/openhands/config.py` — [MODIFIED] Removed unused `typing.Union` import and sorted imports.
- `backend/runtime/tests/test_openhands_adapter.py` — [MODIFIED] Removed unused `NormalizedEvent` import and sorted imports.
- `backend/runtime/tests/test_runtime_contracts.py` — [MODIFIED] Removed unused `os` import, sorted imports, and removed extra blank line at EOF.
- `backend/apps/core/views.py` — [MODIFIED] Formatted and sorted imports.
- `backend/apps/core/tests/test_health.py` — [MODIFIED] Formatted and sorted imports.
- `docs/ANTIGRAVITY-SESSION-01-BACKEND-BASELINE.md` — [MODIFIED] Replaced completely with the authoritative prompt from Appendix A without a closed file list.
- `docs/OPENHANDS-INTEGRATION.md` — [MODIFIED] Fixed relative markdown links (`../AGENTS.md`, `TERSUITE-IMPLEMENTATION-ROADMAP.md`), clarified Python 3.12 and PostgreSQL 16 minor/major line descriptions, and stated exact SecretStr handling.
- `docs/B1-BACKEND-BASELINE-DETAILED-IMPLEMENTATION.md` — [MODIFIED] Removed extra blank line at EOF to satisfy base-to-head `git diff --check`.
- `docs/B1-BACKEND-BASELINE-PHASE-SPEC.md` — [MODIFIED] Removed extra blank line at EOF to satisfy base-to-head `git diff --check`.

### Earlier B1 Changes & Restorations (ae3273d + af994f2)
- `.github/workflows/backend-ci.yml` — [NEW] GitHub Actions workflow.
- `backend/.dockerignore` — [NEW] Excluded caches, secrets, media, artifacts, venvs.
- `backend/.python-version` — [NEW] Declares Python 3.12.
- `backend/uv.lock` — [NEW] Committed frozen dependency lockfile generated with uv 0.8.13.
- `AGENTS.md` — [MODIFIED] Authoritative multi-agent operating guidelines at root.
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

### Local Environment Verification Commands (Executed from `backend/` and repository root)

1. **`git diff --check 74345f5a82ce52922ae32db861db1633e4d4eb35`**:
   - Clean output with 0 whitespace errors (PASSED). Acknowledges resolution of prior end-of-file blank-line warnings.
2. **`uv --version`**:
   - `uv 0.8.13 (ede75fe62 2025-08-21)` (PASSED - exact required version).
3. **`python --version`**:
   - `Python 3.12.14` (PASSED).
4. **`uv lock --check`**:
   - `Resolved 399 packages in 4ms` (PASSED - lockfile completely satisfied).
5. **`uv sync --frozen --extra dev`**:
   - `Audited 403 packages in 10ms` (PASSED).
6. **Focused Import Hygiene (Ruff)**:
   - Command: `uv run ruff check --select F401,I001 runtime/adapters/openhands/config.py runtime/adapters/openhands/adapter.py runtime/tests/test_openhands_adapter.py runtime/tests/test_runtime_contracts.py apps/core/views.py apps/core/tests/test_health.py`
   - Output: `All checks passed!` with 0 errors (PASSED).
7. **OpenHands Package Versions Verification**:
   - Command: `uv run python -c "import importlib.metadata as m; print({p: m.version(p) for p in ['openhands-sdk','openhands-tools','openhands-agent-server','openhands-workspace']})"`
   - Output: `{'openhands-sdk': '1.42.1', 'openhands-tools': '1.42.1', 'openhands-agent-server': '1.42.1', 'openhands-workspace': '1.42.1'}` (PASSED).
8. **`uv run python manage.py check`**:
   - `System check identified no issues (0 silenced).` (PASSED).
9. **`uv run python manage.py makemigrations --check --dry-run`**:
   - `No changes detected` (PASSED).
10. **`uv run pytest`**:
    - **161 passed, 1 skipped in 45.85s** (PASSED - 100% test pass rate).
    - Skipped test: `test_live_agent_coding_task_execution` (skipped solely due to absence of live paid model key in test environment, as expected).

### GitHub Actions CI Verification Runs

- **Correction 02 Run (Implementation Commit `4488a76`)**:
  - Run URL: `https://github.com/josephtersoo2-stack/tersostudio/actions/runs/32014594749`
  - Status: Completed
  - Conclusion: **Success**
  - Test Suite: **161 passed, 1 skipped in 9.49s**
  - OpenHands Packages: All four packages verified at `1.42.1`
  - Django System Check: Passed with zero issues
  - Migration Check: No changes detected
  - Docker Compose Validation: `docker compose config` passed
  - Docker Image Build: `docker build -t tersuite-backend:b1 .` passed
  - PostgreSQL Service Probe: Configured with `pg_isready -U tersuite -d tersuite_test_db` (zero role "root" does not exist noise)

- **Correction 01 Run (Historical Evidence - Commit `af994f2`)**:
  - Run URL: `https://github.com/josephtersoo2-stack/tersostudio/actions/runs/32013363279`
  - Status: Completed
  - Conclusion: **Success** (161 passed, 1 skipped; Compose config and image build passed)

---

## Security & Compatibility Notes

- **Secret Storage**: Agent Server infrastructure credentials (`OPENHANDS_AGENT_SERVER_API_KEY`) and model provider credentials (`OPENROUTER_API_KEY`, `ANTHROPIC_API_KEY`, etc.) are stored as `Optional[SecretStr]` in runtime configuration models (`OpenHandsServerConfig`). Standard dataclass `__repr__`, `dataclasses.asdict()`, and JSON serializations mask secrets and never leak plaintext tokens.
- **Unwrapping Boundary**: The Agent Server secret is unwrapped using `.get_secret_value()` exclusively for `OpenHandsRemoteWorkspace.api_key`. Provider credentials remain `SecretStr` objects when passed directly to `OpenHandsLLM.api_key`.
- **Provider Key Selection & Isolation**: Model provider keys are mapped table-driven by the model identifier prefix (`openrouter/`, `anthropic/`, `openai/`, `gemini/`, `groq/`). Unknown prefixes receive `None` and never borrow credentials from other providers or from the Agent Server.
- **Mandatory TLS Verification**: B1 strictly enforces TLS verification (`server_verify_ssl=True`). Attempting to initialize configuration with `server_verify_ssl=False` is rejected with an explicit `ValueError`.
- **Safe Docker Compose Baseline**: `docker-compose.yml` defaults to `AGENT_RUNTIME_BACKEND=mock` on `web` and `celery_worker`, preventing accidental calls to non-existent localhost Agent Server endpoints.

---

## Documentation Updated

The following documentation files were updated and verified across Milestone B1:
1. `docs/TERSUITE-IMPLEMENTATION-ROADMAP.md` — Restored Principle 13 (scoped retirement of dead code), milestone reference search rules, and B0 obsolete-code ledger.
2. `docs/ANTIGRAVITY-DEVELOPMENT-PROTOCOL.md` — Restored the mandatory three-document authoring workflow, non-invention rule, removal reporting, pre-deletion checks, and historical migration preservation.
3. `docs/B1-BACKEND-BASELINE-PHASE-SPEC.md` — Formatted and cleaned trailing EOF whitespace.
4. `docs/B1-BACKEND-BASELINE-DETAILED-IMPLEMENTATION.md` — Formatted and cleaned trailing EOF whitespace.
5. `docs/ANTIGRAVITY-SESSION-01-BACKEND-BASELINE.md` — Replaced completely with the authoritative prompt from Appendix A; removed closed file list.
6. `docs/OPENHANDS-INTEGRATION.md` — Restored runtime architecture and event streaming; updated with B1 uv install, OpenHands 1.42.1, accurate Python 3.12 and PostgreSQL 16 descriptions, repository-relative links, and exact `SecretStr` handling.
7. `README.md` — Documented Python 3.12, uv, Docker Compose, health endpoints, and credential boundaries.
8. `AGENTS.md` — Established root `AGENTS.md` as the sole authoritative agent-rules file.
9. `docs/reports/B1-BACKEND-BASELINE-REPORT.md` — Comprehensive, truthful evidence report for Milestone B1.

---

## Scope Deviations

1. **Documentation Cleanup Bundling (Resolved)**:
   - *Historical record*: In original commit `ae3273d9327991308d5840b9085702613a128c97`, documentation cleanup for superseded milestone specs was bundled without explicit reporting.
   - *Resolution*: In Correction 01 and 02, all 6 active architecture contracts were restored, authoritative root instructions were aligned, and the three authorized legacy-document deletions were fully catalogued in the removal ledger.
2. **Local Host Docker Availability (Resolved via CI)**:
   - *Historical record*: The Windows development host lacks Docker CLI on PATH, so `docker compose config` and `docker build -t tersuite-backend:b1 .` could not be executed directly on the local host.
   - *Resolution*: Both commands were integrated into `.github/workflows/backend-ci.yml` and verified successfully in GitHub Actions runs 32013363279 and 32014594749.

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
- **Criterion 12: No future milestone functionality added**: No out-of-scope feature or refactor appears in the final B1 base-to-head diff.
- **Criterion 13: Whitespace and diff hygiene**: Verified with `git diff --check` against base commit `74345f5`.

---

## Unresolved Failures

- `none`
