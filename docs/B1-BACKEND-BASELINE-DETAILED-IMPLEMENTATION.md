# B1 — Backend Baseline Detailed Implementation Specification

## 1. Governing rule

This document expands `docs/B1-BACKEND-BASELINE-PHASE-SPEC.md` into the exact implementation Antigravity must perform. Antigravity has no authority to invent features, architecture, dependencies, endpoints, settings, files, abstractions, fallbacks, or user behavior.

If an instruction is impossible because the repository differs from this specification, stop and report the mismatch. Do not create an alternative design.

## 2. Required repository inspection before editing

Read every file named in Sections 4–8 and search the complete repository for:

- `requirements.txt`, `pip install`, `python 3.11`, `python 3.12`, and dependency installation commands;
- every old and new OpenHands setting name;
- all uses of `OpenHandsServerConfig`;
- every health URL, health serializer/view, and health test;
- PostgreSQL, Redis, Channels, Celery, Daphne, pytest, and Docker configuration;
- secrets, `.env` references, credential serialization, and runtime-status response fields.

Record candidates for removal in the B1 report before deleting them.

## 3. Approved dependency layout

### 3.1 `backend/.python-version` — create

Content must be exactly:

```text
3.12
```

### 3.2 `backend/pyproject.toml` — modify

- Keep the project identity and Python requirement on the 3.12 line.
- Keep the current direct production dependency names and exact versions.
- Keep the current `dev` optional dependency group and its existing direct requirements.
- Add `[tool.uv]` with `package = false` so the backend is treated as a dependency application rather than an installed distributable package.
- Keep pytest configuration in this file.
- Do not add a second dependency manifest.
- Do not add a dependency that is not already required by B1 behavior.
- Do not change a direct version to make resolution pass. A resolution conflict is a stop-and-report condition.

### 3.3 `backend/uv.lock` — create

- Generate with uv 0.8.13 from `backend/pyproject.toml`.
- Include production and `dev` resolution.
- Commit the complete generated lock.
- Do not hand-edit the lock.
- Verify `uv sync --frozen --extra dev` from an empty virtual environment.

### 3.4 `backend/requirements.txt` — remove

Remove it only after all Docker, README, script, and CI references use the frozen uv workflow. The B1 report must identify `backend/pyproject.toml` plus `backend/uv.lock` as its replacement.

Do not create `requirements-dev.txt`, `constraints.txt`, Poetry files, Pipenv files, or Conda files.

## 4. Environment and container files

### 4.1 `backend/.env.example` — create

Create a safe, commented example containing names and non-secret local defaults only. It must cover:

- `DJANGO_SETTINGS_MODULE`
- `SECRET_KEY` with an obvious replace-me placeholder
- `DEBUG`
- `ALLOWED_HOSTS`
- `CORS_ALLOWED_ORIGINS`
- `DATABASE_URL`
- `REDIS_URL`
- `CELERY_BROKER_URL`
- `CELERY_RESULT_BACKEND`
- `AGENT_RUNTIME_BACKEND`
- `OPENHANDS_AGENT_SERVER_URL`
- `OPENHANDS_AGENT_SERVER_API_KEY` with an empty value
- `OPENHANDS_AGENT_SERVER_TIMEOUT_SECONDS`
- `OPENHANDS_AGENT_SERVER_VERIFY_SSL`
- `LLM_DEFAULT_MODEL`
- `OPENROUTER_API_KEY` with an empty value
- `OPENROUTER_BASE_URL`

Do not include a working credential or a deprecated name from Section 6.5.

### 4.2 `backend/.dockerignore` — create

Exclude Git metadata, `.env`, virtual environments, Python caches, pytest/coverage caches, local media/artifacts, logs, and editor/OS files. Do not exclude `pyproject.toml`, `uv.lock`, application source, migrations, or tests.

### 4.3 `backend/Dockerfile` — modify

- Use Python `3.12.11-slim-bookworm` for the runtime image.
- Obtain uv `0.8.13` from the official `ghcr.io/astral-sh/uv:0.8.13` image.
- Copy `pyproject.toml` and `uv.lock` before application source.
- Install production dependencies with `uv sync --frozen --no-dev`.
- Put `/app/.venv/bin` on `PATH`.
- Keep the non-root `tersuite` runtime user.
- Keep Daphne as the default command.
- Do not install from `requirements.txt`.
- Do not copy `.env` or credentials into the image.

### 4.4 `backend/docker-compose.yml` — modify

- Remove the obsolete top-level Compose `version` field.
- Preserve the existing `db`, `redis`, `web`, and `celery_worker` services and named volumes.
- Preserve PostgreSQL and Redis health checks.
- Use the new credential/configuration names from Section 6.
- Do not embed Agent Server or LLM credentials.
- Add no WordPress, OpenHands Agent Server, sandbox, frontend, scheduler, monitoring, or proxy service in B1.
- Keep service dependencies on healthy PostgreSQL and Redis.

## 5. Django settings and service configuration

### 5.1 `backend/config/settings/base.py` — modify

- Keep installed apps, middleware, REST Framework, ASGI, media, logging, and service roles unless this specification says otherwise.
- Use `DATABASE_URL` as the single database configuration path through `dj_database_url.parse`; remove the duplicate independent DB field assembly path.
- Do not silently catch a missing `dj_database_url`, because it is a required locked dependency.
- Retain PostgreSQL as the normal backend.
- Keep `REDIS_URL`, `CELERY_BROKER_URL`, and `CELERY_RESULT_BACKEND` as separate URLs.
- Replace the old OpenHands/model settings with the exact names in Section 6.
- Parse timeout as a positive integer and SSL verification as a strict boolean using a small private settings helper. Invalid values must fail startup with a clear configuration error that contains no secret.
- Remove duplicate `MEDIA_URL`/`MEDIA_ROOT` declarations.
- Do not alter authentication, pagination, CORS policy, or logging format beyond references required by this phase.

### 5.2 `backend/config/settings/development.py` — modify only if needed

- Preserve the in-memory Channels default for local development.
- Preserve opt-in Redis Channels through `USE_REDIS_CHANNELS`.
- Ensure imports required by this file are explicit and valid.
- Do not make failed production dependencies appear ready.

### 5.3 `backend/config/settings/test.py` — modify only if needed

- Preserve PostgreSQL as the default test database.
- Preserve `TEST_USE_SQLITE=1` only as an explicitly selected unit-test fallback.
- Preserve in-memory Channels and eager Celery for isolated tests.
- Do not make readiness tests depend on simulated success; readiness dependencies must be mocked explicitly per test or exercised by CI services.

### 5.4 `backend/config/settings/production.py` — modify only if needed

Keep existing production security behavior. Do not add deployment-platform-specific settings.

### 5.5 Bootstrap files — inspect; change only for a demonstrated B1 defect

This applies to:

- `backend/config/asgi.py`
- `backend/config/celery.py`
- `backend/config/urls.py`
- `backend/config/wsgi.py`

Any change must be tied to a failing B1 check and explained in the report. Do not reorganize these files.

## 6. Exact credential separation implementation

### 6.1 Settings names

Define and use:

```text
OPENHANDS_AGENT_SERVER_URL
OPENHANDS_AGENT_SERVER_API_KEY
OPENHANDS_AGENT_SERVER_TIMEOUT_SECONDS
OPENHANDS_AGENT_SERVER_VERIFY_SSL
LLM_DEFAULT_MODEL
OPENROUTER_API_KEY
OPENROUTER_BASE_URL
```

Provider-specific keys already supported by the adapter may remain provider-specific environment variables.

### 6.2 `backend/runtime/adapters/openhands/config.py` — modify

`OpenHandsServerConfig` must expose separate fields:

```text
server_url
server_api_key
server_timeout_seconds
server_verify_ssl
llm_default_model
llm_api_key
llm_base_url
max_retries
```

Secret fields must remain optional and must not appear in dataclass representation, logs, serialized metadata, or exception details. Use secret-safe field representation rather than storing a displayable plaintext dataclass field.

### 6.3 `backend/apps/generations/services/execution_service.py` — modify

- Construct `OpenHandsServerConfig` with the new explicit settings.
- Pass Agent Server values only to server fields.
- Pass the selected provider credential only to `llm_api_key`.
- Use `LLM_DEFAULT_MODEL` for the default model.
- Do not introduce new provider-selection behavior.

### 6.4 `backend/runtime/adapters/openhands/adapter.py` — make only this B1 security correction

- Agent Server authorization headers and `OpenHandsRemoteWorkspace` receive only `server_api_key`.
- `OpenHandsLLM` receives only `llm_api_key` or an existing matching provider environment key.
- Delete every fallback that can assign the Agent Server key to the LLM.
- Apply the renamed URL/model/base URL fields.
- Do not change tool selection, system prompts, workspace directory, conversation lifecycle, event handling, result extraction, cancellation, retries, close/delete behavior, or artifacts in B1. Those are B4 work.

### 6.5 Remove deprecated configuration names

After all B1 call sites are migrated, remove these names from executable configuration and examples:

```text
OPENHANDS_SERVER_URL
OPENHANDS_API_KEY
OPENHANDS_TIMEOUT_SECONDS
OPENHANDS_DEFAULT_MODEL
```

Do not implement compatibility aliases. Search scripts, tests, control-center code, and documentation and update B1-relevant references. Historical specification text may retain old names only when clearly marked historical; do not rewrite unrelated frozen specifications.

### 6.6 `backend/apps/control_center/views.py` — modify only referenced settings

- Read the new Agent Server setting names.
- Preserve existing API response field names to avoid an unrelated control-center API change.
- Continue returning only boolean configured/not-configured indicators, never values.

### 6.7 `backend/apps/control_center/serializers.py` — inspect, no change expected

Preserve the public serializer contract unless a failing test proves a direct rename dependency.

### 6.8 Live scripts — modify configuration references only

Update:

- `backend/scripts/run_live_openrouter_test.py`
- `backend/scripts/verify_live_celery_openrouter_execution.py`

Use the new Agent Server URL name. Keep `OPENROUTER_API_KEY` as the model credential. Do not expand the scripts or run paid live tests without credentials already configured by the user.

## 7. Health and readiness implementation

### 7.1 `backend/apps/core/views.py` — modify

- Keep `HealthLiveView` external-service-free and HTTP 200.
- Keep `HealthReadyView` checking database, Redis, and Celery broker.
- Remove `simulated` readiness behavior in DEBUG and TESTING.
- On success, return `healthy` for each service.
- On failure, return `unhealthy` with a stable non-secret error code such as `database_unavailable`, `redis_unavailable`, or `celery_broker_unavailable`.
- Log the exception server-side without logging connection URLs or secrets.
- Return HTTP 503 if any required service is unhealthy.
- Preserve the top-level response shape (`status`, `timestamp`, `all_healthy`, `services`).
- Add short connection timeouts so the endpoint cannot hang indefinitely.

### 7.2 `backend/apps/core/urls.py` — inspect, preserve routes

Preserve `/health/live/`, `/health/ready/`, and the existing `/health/` readiness alias. Add no new endpoint.

### 7.3 `backend/apps/core/tests/test_health.py` — clean and expand

- Remove duplicate imports.
- Test liveness response without dependency access.
- Test readiness HTTP 200 with database, Redis, and Celery checks controlled as healthy.
- Test HTTP 503 separately for database failure, Redis failure, and Celery broker failure.
- Assert failed responses never contain thrown exception text, URL, password, API key, or environment value.
- Preserve request-ID middleware and exception-handler tests.
- Do not loosen assertions to allow both 200 and 503 for the same controlled case.

## 8. Tests affected by credential renaming

Update only fixtures, constructors, patches, and assertions affected by Section 6 in:

- `backend/runtime/tests/test_openhands_adapter.py`
- `backend/tests/integration/test_openhands_live.py`
- `backend/apps/generations/tests/test_execution_service.py`
- `backend/apps/control_center/tests/test_control_center_api.py`
- `backend/apps/control_center/tests/test_control_center_detail_api.py`
- `backend/apps/control_center/tests/test_control_center_actions_api.py` if it references old names

Add regression assertions proving:

1. Agent Server API keys are never supplied to `OpenHandsLLM`.
2. LLM provider API keys are never supplied to `OpenHandsRemoteWorkspace` or Agent Server authorization headers.
3. Runtime/control-center responses do not serialize either secret.

Do not refactor unrelated test organization.

## 9. Continuous integration

### 9.1 `.github/workflows/backend-ci.yml` — create

Create one backend workflow that:

- runs for pull requests and pushes affecting `backend/**`, this workflow, or backend documentation;
- uses `actions/checkout@v4`, `astral-sh/setup-uv@v6` with uv version `0.8.13`, and `actions/setup-python@v5` with Python `3.12`;
- starts PostgreSQL 16 and Redis 7 service containers with health checks;
- runs from `backend/`;
- runs `uv sync --frozen --extra dev`;
- verifies imports and versions of all four OpenHands packages;
- runs `uv run python manage.py check`;
- runs `uv run python manage.py makemigrations --check --dry-run`;
- runs `uv run pytest`;
- uses non-secret test environment values and never prints configured secrets.

Do not add deployment, release, frontend, WordPress, paid-provider, or live OpenHands Agent Server jobs.

## 10. Documentation

### 10.1 `README.md` — modify only inaccurate backend bootstrap information

- Change Python support to 3.12.
- Add concise verified backend setup commands using uv and Docker Compose.
- List liveness/readiness URLs.
- Document that live OpenHands/provider integration requires separate credentials without showing values.
- Do not rewrite the product vision or declare future features implemented.

### 10.2 `docs/OPENHANDS-INTEGRATION.md` — modify only B1 configuration/install sections

- Replace deprecated environment names with the approved names.
- State clearly that the Agent Server credential cannot be used as an LLM-provider credential.
- Do not rewrite the broader adapter architecture in B1.

### 10.3 `docs/reports/B1-BACKEND-BASELINE-REPORT.md` — create

Commit a truthful report using the exact report structure in `docs/ANTIGRAVITY-DEVELOPMENT-PROTOCOL.md`. Include the removal ledger and exact command outputs/counts. Do not write `passed` for a command that was not executed.

## 11. Files that must not change

Unless a B1 test-collection import is directly broken by a renamed setting, do not modify:

- `frontend/**`
- project, generation, account, realtime, or control-center domain models/migrations
- `backend/knowledge_base/**`
- storage implementation
- runtime interfaces
- `backend/runtime/adapters/mock_adapter.py`
- WordPress/product roadmap domain behavior
- existing phase/control-center specification documents other than the two documentation files explicitly allowed in Section 10

Never delete historical Django migrations.

## 12. Removal ledger rules

Classify each B1 candidate as `KEEP`, `REFACTOR`, `REPLACE`, `REMOVE`, or `DEFER`. At minimum, evaluate:

- `backend/requirements.txt`
- duplicate database configuration path in base settings
- duplicate media settings
- deprecated OpenHands setting names
- Agent Server key-to-LLM fallback
- health `simulated` fallback
- duplicate health-test imports
- stale Python 3.11 documentation

Delete only candidates explicitly required above or proven unused by repository-wide search. Uncertain or later-milestone code is `DEFER`, not permission to remove it.

## 13. Required verification commands

Run from `backend/` unless stated otherwise:

```bash
uv --version
python --version
uv lock --check
uv sync --frozen --extra dev
uv run python -c "import importlib.metadata as m; print({p: m.version(p) for p in ['openhands-sdk','openhands-tools','openhands-agent-server','openhands-workspace']})"
uv run python manage.py check
uv run python manage.py makemigrations --check --dry-run
uv run pytest
docker compose config
docker build -t tersuite-backend:b1 .
```

If Docker is unavailable, record those two Docker commands as not executed and do not fabricate results.

Also run repository searches proving deprecated names and `requirements.txt` installation references are gone from executable/current setup paths.

## 14. Exit criteria

- Every required file change matches this specification.
- Frozen installation works from clean state.
- All four OpenHands packages import at 1.42.1.
- Django system and migration checks pass.
- Backend tests complete with exact counts recorded.
- Credential-boundary regression tests pass.
- Health tests are deterministic and truthful.
- No secret is committed or serialized.
- CI expresses the same verified commands.
- Removal ledger is complete.
- No out-of-scope feature or refactor appears in the diff.
