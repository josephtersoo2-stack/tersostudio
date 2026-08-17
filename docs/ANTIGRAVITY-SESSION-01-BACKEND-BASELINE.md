# Antigravity Execution Prompt — Session 01: B1 Backend Baseline

Copy only the prompt below into Google Antigravity.

---

You are implementing Session 01 for the existing Tersuite repository. Execute the approved B1 specification exactly. You are an implementer, not a product designer or architect.

## Mandatory reading order

Read these files completely before editing:

1. `AGENTS.md`
2. `docs/TERSUITE-IMPLEMENTATION-ROADMAP.md`
3. `docs/ANTIGRAVITY-DEVELOPMENT-PROTOCOL.md`
4. `docs/B1-BACKEND-BASELINE-PHASE-SPEC.md`
5. `docs/B1-BACKEND-BASELINE-DETAILED-IMPLEMENTATION.md`

Then inspect every existing repository file referenced by the detailed implementation specification.

## Non-invention rule

Do not invent or add any feature, behavior, architecture, abstraction, dependency, endpoint, setting, file, service, agent role, fallback, or user experience that is not explicitly required by the two B1 specifications.

Do not make an independent design decision where the specification is silent or incompatible with the repository. Stop and report the exact ambiguity, conflict, dependency-resolution failure, or repository mismatch. Wait for a correction specification.

Do not use “best judgment,” “reasonable improvement,” or opportunistic cleanup as permission to expand scope.

## Execution requirements

1. Create a dedicated branch from the current approved base commit.
2. Record the base commit SHA before editing.
3. Inspect first; do not rewrite the repository.
4. Implement every requirement in `docs/B1-BACKEND-BASELINE-DETAILED-IMPLEMENTATION.md` exactly, file by file.
5. Preserve all files and behaviors that the specification protects.
6. Remove only the obsolete B1 items explicitly required or proven dead under the removal-ledger rules.
7. Never delete historical Django migrations.
8. Never commit or display credentials.
9. Do not weaken, skip, replace, or falsify tests.
10. Do not run paid live-provider tests unless credentials were already supplied through the environment and the detailed specification requires the run; B1 does not require paid calls.
11. Run every required verification command that the environment supports.
12. If a required command cannot run, report it as not executed with the exact reason.
13. Create and complete `docs/reports/B1-BACKEND-BASELINE-REPORT.md`.
14. Review the final diff for scope violations, secrets, debug code, orphan imports, obsolete fallbacks, duplicate configuration, and unreported deletions.
15. Commit and push the completed work to the dedicated branch.

## Stop conditions

Stop without inventing a solution if:

- the existing direct dependency versions do not resolve under uv 0.8.13;
- a required file or contract conflicts with the detailed specification;
- complying would require an out-of-scope product or OpenHands runtime redesign;
- a deletion cannot be proven safe;
- credentials or external authority are required but unavailable;
- required repository state differs materially from the specification.

When stopped, do not commit a partial workaround as completed. Report the blocker and the smallest decision needed from the reviewer.

## Final response

Return:

- session name;
- base commit SHA;
- branch;
- pushed commit SHA;
- objective status: completed or blocked;
- every changed, created, and removed file with reason;
- migrations or `none`;
- exact commands and passed/failed/skipped counts;
- removal ledger;
- exit-criteria evidence;
- unresolved failures;
- scope deviations or `none`;
- security and compatibility notes;
- link/path to `docs/reports/B1-BACKEND-BASELINE-REPORT.md`.

Do not claim completion unless every B1 exit criterion is satisfied. The pushed GitHub commit will be independently inspected before approval.
