# Antigravity Session 01 — Reproducible Backend Baseline

Copy the implementation instruction below into Google Antigravity for the first coding session.

---

## Implementation instruction

You are working on the existing Tersuite AI Studio repository. This is a correction and verification session, not a rewrite.

### Objective

Establish a truthful, reproducible backend foundation for roadmap milestone B1. Inspect the existing backend first, preserve correct work, correct only foundation defects within this scope, and provide evidence that a clean environment can install and run the backend test baseline.

### Required reading

Read completely before editing:

1. `AGENTS.md`
2. `docs/TERSUITE-IMPLEMENTATION-ROADMAP.md`
3. `docs/ANTIGRAVITY-DEVELOPMENT-PROTOCOL.md`
4. `docs/TERSUITE-PHASE-1-CORRECTION-SPEC.md`
5. `docs/TERSUITE-PHASE-2-IMPLEMENTATION-SPEC.md`
6. `docs/OPENHANDS-INTEGRATION.md`
7. Backend dependency files, settings, Docker files, test configuration, and CI configuration

If these documents conflict, report the conflict before implementing the affected behavior.

### Scope

This session may change only backend foundation, dependency, environment, test-bootstrap, health-check, and directly related documentation files.

Required work:

1. Inventory the actual Python and service requirements used by the repository.
2. Select and document one supported Python version compatible with the pinned OpenHands release and the rest of the backend.
3. Replace non-reproducible dependency installation with a committed, compatible lock or constraints workflow. Do not claim that direct top-level pins alone are a full lock.
4. Ensure the selected OpenHands SDK, tools, workspace, and Agent Server packages can be installed together in the verified environment.
5. Keep Agent Server credentials separate from LLM provider credentials in configuration names and documentation. Do not refactor the OpenHands adapter in this session unless a minimal import/bootstrap change is required for the backend to start.
6. Validate Django settings for PostgreSQL, Redis, Celery, and Channels without exposing credentials.
7. Verify or correct backend health/readiness endpoints so they distinguish application health from unavailable required services where the existing contract expects this.
8. Establish exact documented commands for installation, migrations, lint/static checks if configured, and tests.
9. Run the backend test suite and classify every remaining failure. Fix only failures caused by B1 foundation work or an obvious existing baseline defect that blocks test collection/startup.
10. Update documentation truthfully with verified commands, versions, failures, and limitations.

### Explicitly out of scope

Do not implement or redesign feature discovery, specifications, planning, multi-agent orchestration, component registries, blueprints, self-learning, WordPress sandbox, WordPress client, frontend, billing, theme creation, or broad OpenHands adapter behavior beyond installation and startup blockers.

Do not delete existing Phase 5 or control-center functionality. Do not mark it frozen or complete.

### Safety requirements

- Preserve unrelated repository changes.
- Do not commit `.env` files or credentials.
- Do not use Agent Server API keys as model-provider fallbacks.
- Do not weaken or skip tests to obtain a green result.
- Do not replace real package installation with test-only stubs.
- Keep development/test mocks clearly separated from production configuration.

### Required tests and evidence

At minimum, report and where applicable run:

1. Clean dependency resolution/install command
2. `python --version` from the verified environment
3. Imports and versions for all four pinned OpenHands packages
4. Django system check
5. Migration consistency check
6. Backend test suite with passed/failed/skipped totals
7. Health/readiness endpoint tests
8. Secret-serialization regression tests if configuration code changes

If Docker or required services are unavailable, do not fabricate results. Report exactly what was and was not verified.

### Exit criteria

The session is successful only if:

- dependency installation is reproducible from committed files;
- the selected Python version is explicit and compatible;
- the OpenHands packages install and import together;
- Django starts and passes its system check;
- migrations are consistent;
- backend tests run to completion;
- remaining failures are documented with root-cause classification;
- no credential is committed or serialized;
- no future milestone functionality was added.

### Git and report requirements

Work on a dedicated branch. Commit and push the completed scoped changes. Return the exact report format required by `docs/ANTIGRAVITY-DEVELOPMENT-PROTOCOL.md`, including branch, commit SHA, every changed file, migrations, exact commands, test counts, unresolved failures, and deviations.
