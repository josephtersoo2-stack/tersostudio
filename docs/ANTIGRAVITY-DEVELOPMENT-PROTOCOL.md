# Tersuite — Google Antigravity Development Protocol

## 1. Purpose

Google Antigravity is the implementation assistant. Tersuite's repository contracts remain the source of truth. Work is delivered in bounded sessions, uploaded to GitHub, and independently verified against the actual commit before approval.

## 2. Authority order

For every session, Antigravity must apply instructions in this order:

1. The session-specific implementation instruction
2. `AGENTS.md`
3. `docs/TERSUITE-IMPLEMENTATION-ROADMAP.md`
4. Applicable architecture, data, API, event, runtime, testing, and security contracts in `docs/`
5. Existing tests and established code conventions

If two authoritative documents conflict, stop and report the conflict. Do not silently choose one.

## 3. Session scope

Each session must define objective, allowed paths, required reading, required changes, prohibited changes, migrations/data compatibility rules, required tests, exit criteria, and report format.

Antigravity must inspect the current implementation before editing. Existing correct work must be preserved. Unrelated user changes must not be reverted.

## 4. Engineering requirements

- Use a dedicated feature or correction branch.
- Keep changes limited to the approved session scope.
- Prefer public package APIs over implementation internals.
- Do not fabricate unavailable integrations or passing results.
- Add or update tests for every behavior change.
- Keep migrations backward-compatible and reviewable.
- Never serialize credentials, secrets, raw environment values, or private prompts.
- Do not mark a future roadmap phase complete.
- Do not create synthetic success fallbacks for real runtime failures.
- Do not weaken tests to make an implementation pass.
- Do not replace a deterministic rule with LLM judgment.

## 5. Required Antigravity report

Every report must use this structure:

```text
Session:
Branch:
Commit SHA:

Objective completed:

Files changed:
- path — reason

Migrations:
- migration or "none"

Tests and commands:
- exact command
- passed / failed / skipped counts

Exit criteria evidence:
- criterion — evidence

Unresolved failures:
- item or "none"

Scope deviations:
- item or "none"

Security/compatibility notes:

Documentation updated:
```

## 6. Independent GitHub review

The reviewer must not approve from the report alone. Review includes:

1. Resolve the reported commit SHA in the expected repository.
2. Inspect the diff and file list.
3. Check for unrelated or destructive changes.
4. Compare implementation with session instructions and authoritative contracts.
5. Inspect migrations and backwards compatibility.
6. Inspect tests for real behavioral coverage.
7. Run or independently validate relevant checks where possible.
8. Check security, tenant isolation, idempotency, error handling, and secret handling.
9. Confirm documentation accurately describes limitations.
10. Approve, partially approve with non-blocking notes, or reject with a correction prompt.

## 7. Correction prompt format

When a session fails review, the next prompt must contain:

```text
Correction session for: <commit>

Verified findings:
1. <file/symbol> — <actual problem> — <required behavior>

Required corrections:
1. <bounded implementation instruction>

Do not change:
- <protected areas>

Required tests:
- <specific tests>

Exit criteria:
- <observable proof>
```

The correction session must repair verified findings only. It must not continue to the next roadmap milestone.

## 8. Freeze rule

A session is not frozen because code was committed. Freeze requires all blocking findings resolved, required tests passing, truthful documentation, actual GitHub commit verification, and satisfied milestone exit criteria.

## 9. Starting and stopping rules

- Start with backend milestone B1.
- Work in dependency order.
- Stop when a session exit criterion fails and report the blocker.
- Do not hide environment or dependency failures behind mocks.
- Mocks remain valid only for explicitly isolated unit tests and development modes.
- Real-integration milestones require real integration evidence.
