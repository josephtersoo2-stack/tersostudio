# Tersuite — Google Antigravity Development Protocol

## 1. Purpose & Operating Model

Google Antigravity is the implementation assistant, not an autonomous architect or requirements author. Tersuite's repository contracts, roadmap, and specifications remain the sole source of truth. Work is delivered in bounded, milestone-driven sessions, uploaded to GitHub, and independently verified against the actual commit before approval.

Antigravity must stop and request clarification or instruction instead of inventing unspecified architectural decisions, models, routes, or behaviors.

---

## 2. Mandatory Three-Document Workflow

Every roadmap milestone must strictly follow the three-document authoring and execution process before implementation:

1. **Phase Specification (`docs/<MILESTONE>-PHASE-SPEC.md`)**: Defines business objectives, architectural contracts, domain boundaries, security requirements, and acceptance criteria.
2. **Detailed Implementation Specification (`docs/<MILESTONE>-DETAILED-IMPLEMENTATION.md`)**: Contains file-by-file instructions, exact symbol definitions, removal ledgers, test assertions, and step-by-step verification commands.
3. **Execution-Only Prompt (`docs/ANTIGRAVITY-SESSION-<XX>-<NAME>.md`)**: The prompt executed by Antigravity to perform the implementation, referencing the governing specifications without inventing alternative paths.

---

## 3. Authority Order

For every session, Antigravity must apply instructions in this strict order:

1. The session-specific implementation prompt (`docs/ANTIGRAVITY-SESSION-...`)
2. `AGENTS.md`
3. `docs/TERSUITE-IMPLEMENTATION-ROADMAP.md`
4. Applicable phase and detailed implementation specifications in `docs/`
5. Applicable architecture, data, API, event, runtime, testing, and security contracts in `docs/`
6. Existing tests and established code conventions

If two authoritative documents conflict, stop and report the conflict. Do not silently choose one.

---

## 4. Session Scope & Code Preservation

Each session must define objective, allowed paths, required reading, required changes, prohibited changes, migrations/data compatibility rules, required tests, exit criteria, and report format.

Antigravity must inspect the current implementation before editing. Existing correct work must be preserved. Unrelated user changes must not be reverted.

---

## 5. Engineering, Deletion, and Code Quality Rules

- **Use Dedicated Branches**: Deliver work on a dedicated feature (`feature/<milestone>`) or correction branch.
- **Strict Scope Boundaries**: Keep changes limited to the approved session scope.
- **Public APIs First**: Prefer public package APIs over implementation internals.
- **Truthful Results**: Do not fabricate unavailable integrations or passing results.
- **Test Coverage**: Add or update tests for every behavior change.
- **Historical Migration Preservation**: Never rewrite or delete historical database migrations; keep all migrations backward-compatible.
- **Pre-Deletion Checks**: Before deleting any file, function, class, route, or setting, perform comprehensive repository searches for static references, dynamic lookups, template usages, and configuration registrations.
- **Prohibition on Technical Debt**: No orphan imports, unused dependencies, duplicate adapters, dead flags, or obsolete simulated fallbacks are allowed.
- **Credential Protection**: Never serialize credentials, secrets, raw environment values, or private prompts.
- **No Scope Jumping**: Do not mark a future roadmap phase complete.
- **No Synthetic Fallbacks**: Do not create synthetic success fallbacks for real runtime failures.
- **No Weakened Tests**: Do not weaken tests or delete valid assertions to make an implementation pass.
- **Deterministic Logic**: Do not replace deterministic business rules with LLM judgment.

---

## 6. Required Antigravity Report

Every session must produce an authoritative evidence report at `docs/reports/<MILESTONE>-REPORT.md` using this exact structure:

```text
Session:
Branch:
Commit SHA:

Objective completed:

Files changed:
- path — reason

Removal ledger:
- item — classification (KEEP, REFACTOR, REPLACE, REMOVE, DEFER) — reason/replacement

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

Every report must list all created, modified, restored, and removed files, symbols, routes, settings, and dependencies.

---

## 7. Independent GitHub Review

The reviewer must not approve from the report alone. Review includes:

1. Resolve the reported commit SHA in the expected repository.
2. Inspect the diff and complete file list.
3. Check for unrelated or destructive changes.
4. Compare implementation with session instructions and authoritative contracts.
5. Inspect migrations, historical migration preservation, and backwards compatibility.
6. Inspect tests for real behavioral coverage and absence of weakened assertions.
7. Perform independent review of removals and newly orphaned references.
8. Run or independently validate relevant checks where possible.
9. Check security, tenant isolation, idempotency, error handling, and secret handling.
10. Confirm documentation accurately describes limitations.
11. Approve, partially approve with non-blocking notes, or reject with a correction prompt.

---

## 8. Correction Prompt Format

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

---

## 9. Freeze Rule

A session is not frozen because code was committed. Freeze requires all blocking findings resolved, required tests passing, truthful documentation, actual GitHub commit verification, and satisfied milestone exit criteria.

---

## 10. Starting and Stopping Rules

- Start with backend milestone B1.
- Work in dependency order.
- Stop when a session exit criterion fails and report the blocker.
- Do not hide environment or dependency failures behind mocks.
- Mocks remain valid only for explicitly isolated unit tests and development modes.
- Real-integration milestones require real integration evidence.
