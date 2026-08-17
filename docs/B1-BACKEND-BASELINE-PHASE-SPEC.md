# B1 — Reproducible Backend Baseline Phase Specification

## 1. Phase identity

- Roadmap milestone: `B1`
- Product area: backend foundation
- Implementation order: first backend implementation phase after architecture re-baselining
- Status before execution: specified, not implemented, not approved
- Implementer: Google Antigravity
- Reviewer: independent review of the pushed GitHub commit

## 2. Purpose

Create a reproducible, secure, and testable backend foundation on which all later Tersuite domains will be built. This phase corrects the environment, dependency, service bootstrap, credential-boundary, health-check, and backend continuous-integration baseline. It does not build product workflows or new user-facing features.

## 3. Outcomes

At the end of B1:

1. The backend uses Python 3.12 from an explicit version file and container image.
2. Direct and transitive Python dependencies are represented by `backend/pyproject.toml` and a committed `backend/uv.lock`.
3. A clean machine can install with `uv sync --frozen --extra dev`.
4. Production/container installation uses the same frozen lock and excludes development dependencies.
5. The four OpenHands 1.42.1 packages resolve and import in one environment.
6. Agent Server credentials and model-provider credentials are separate in settings, runtime configuration, tests, scripts, and operational status code.
7. PostgreSQL, Redis, Celery, and Channels configuration is explicit and testable.
8. Liveness and readiness endpoints report truthful status and never claim simulated dependencies are ready.
9. Django checks, migration checks, and the backend test suite run from documented commands.
10. GitHub Actions reproduces the backend verification with PostgreSQL and Redis services.
11. Proven obsolete B1 files, settings, imports, dependencies, and fallbacks are removed and recorded.

## 4. Fixed technical decisions

These decisions are approved and are not choices for Antigravity:

- Python line: `3.12`
- Dependency manager and lock: `uv`, with `uv==0.8.13` used by documented local/bootstrap and container workflows
- Dependency source of truth: `backend/pyproject.toml`
- Frozen resolution: `backend/uv.lock`
- Existing direct dependency versions: retain exactly as currently declared unless the resolver proves them incompatible
- OpenHands packages: `openhands-sdk`, `openhands-tools`, `openhands-agent-server`, and `openhands-workspace`, all at `1.42.1`
- Database: PostgreSQL
- Cache, Channels transport, and Celery broker/result transport: Redis
- Web protocol server: Daphne/ASGI
- Test runner: pytest with pytest-django
- B1 CI: GitHub Actions with PostgreSQL and Redis service containers

If the declared dependency set cannot resolve, Antigravity must stop, preserve the resolver evidence, and report the exact conflict. It must not choose alternative versions on its own.

## 5. Credential boundary

The following meanings are fixed:

- `OPENHANDS_AGENT_SERVER_URL`: Agent Server location
- `OPENHANDS_AGENT_SERVER_API_KEY`: authentication only for Agent Server/remote workspace requests
- `OPENHANDS_AGENT_SERVER_TIMEOUT_SECONDS`: Agent Server connection/request timeout
- `OPENHANDS_AGENT_SERVER_VERIFY_SSL`: Agent Server TLS verification
- `LLM_DEFAULT_MODEL`: default model identifier
- Provider keys such as `OPENROUTER_API_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`, and `GROQ_API_KEY`: model-provider authentication only
- Provider base URLs such as `OPENROUTER_BASE_URL`: model-provider routing only

An Agent Server key must never be used as an LLM key, and an LLM key must never be sent to Agent Server. No API response, log, exception, committed file, test snapshot, or report may contain a raw secret.

## 6. Health contract

### Liveness

`GET /health/live/` proves only that the Django web process can respond. It returns HTTP 200 without querying external services.

### Readiness

`GET /health/ready/` and the existing `GET /health/` alias check required backend dependencies:

- PostgreSQL query succeeds;
- Redis ping succeeds;
- Celery broker connection succeeds.

Readiness returns HTTP 200 only when all required checks succeed. Otherwise it returns HTTP 503. Development and test modes must not convert a failed dependency into `simulated` success. Responses may identify the failed service but must not return credentials, connection URLs, or raw exception messages.

## 7. In scope

- Python version declaration
- Python dependency source-of-truth cleanup and lock generation
- Docker dependency installation and backend service bootstrap
- safe example environment file
- Django foundation settings cleanup
- minimal runtime configuration changes needed to enforce the credential boundary
- all direct call sites/tests/scripts affected by those configuration names
- liveness/readiness behavior and tests
- backend GitHub Actions verification
- backend setup and verification documentation
- evidence-based removal of superseded B1 code and files

## 8. Out of scope

- OpenHands agent tool selection, prompts, conversation lifecycle, workspace isolation, event extraction, artifact collection, cancellation, or nested delegation
- project discovery, specifications, implementation plans, approvals, work packages, or multi-agent coordination
- WordPress intelligence, blueprints, component registry, sandbox, packaging, delivery, activation, or rollback
- frontend and WordPress client work
- billing, usage metering, themes, or enterprise administration
- redesign of existing control-center features

No out-of-scope code may be added, deleted, renamed, or refactored merely to make the repository look cleaner.

## 9. Completion gate

B1 is complete only after:

1. Antigravity implements the separate detailed implementation specification exactly.
2. Antigravity pushes a dedicated branch and reports its commit SHA.
3. The actual GitHub diff is independently inspected.
4. All B1 exit criteria and tests are verified.
5. Any blocking review finding is corrected in a separate correction session.

A report or commit alone does not approve the phase.
