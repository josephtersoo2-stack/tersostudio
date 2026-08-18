# B2 Correction 03 — Runtime Scope Restoration and Final Evidence

## 1. Identity

- Milestone: B2
- Branch: `feature/b2-core-domains`
- B2 baseline SHA: `b651815cf380174f8df347a8d754a287f4e9a8bb`
- Previous B2 code SHA: `0150f31f111474076d9358dac3f4c7c14bc7f069`
- Previous evidence SHA: `c5b9000ec2a3d0cb18b1eeae922aafbdf87729d0`
- Correction 03 code SHA: `b79073263d646f19f21012b35552470904bd8a68`
- Code CI run: [https://github.com/josephtersoo2-stack/tersostudio/actions/runs/32114260215](https://github.com/josephtersoo2-stack/tersostudio/actions/runs/32114260215)

## 2. Reason for Correction

The frozen B2 specification excludes calling OpenHands, creating OpenHands
conversations, and changing runtime adapters.

The previous B2 diff contained changes to the OpenHands runtime adapter and
its unit-test harness. Those changes were removed from B2.

## 3. Exact Files Restored

- `backend/runtime/adapters/openhands/adapter.py`
- `backend/runtime/tests/test_openhands_adapter.py`

Both files were restored directly from:

`b651815cf380174f8df347a8d754a287f4e9a8bb`

## 4. Runtime Equality Proof

Commands:

`git diff --exit-code b651815cf380174f8df347a8d754a287f4e9a8bb...HEAD -- backend/runtime/adapters/openhands/adapter.py`

Result: exit 0 / no diff.

`git diff --exit-code b651815cf380174f8df347a8d754a287f4e9a8bb...HEAD -- backend/runtime/tests/test_openhands_adapter.py`

Result: exit 0 / no diff.

`git diff --name-only b651815cf380174f8df347a8d754a287f4e9a8bb...HEAD -- backend/runtime`

Result: empty.

Therefore the B2 branch contains no runtime implementation/test delta relative
to the frozen B1 baseline.

## 5. Historical Migration Integrity

Record exit-0/no-diff checks for:

- accounts `0001_initial.py`: exit 0 / no diff
- projects `0001_initial.py`: exit 0 / no diff
- generations `0001_initial.py`: exit 0 / no diff

## 6. Verification Results

- Django `manage.py check`: System check identified no issues (0 silenced).
- `makemigrations --check --dry-run`: No changes detected
- MigrationExecutor tests: 2 passed (forward backfill, slug collision, metadata preservation, and reverse unmarked personal org survival)
- Full pytest: 234 passed, 1 skipped (0 failed)
- Skipped test: `tests/integration/test_openhands_live.py:91` (live OpenHands integration test skipped: no LLM API key found in CI environment)
- Docker Compose config: PASS (verified in CI)
- Docker build: PASS (verified in CI)
- Docker tag: `tersuite-backend:b2`

## 7. Documentation Corrections

- Removed B2 runtime-adapter accomplishment claim.
- Explicitly documented that the B1 runtime boundary is unchanged.
- Corrected the skipped integration-test reason to match GitHub CI evidence.
- Updated final B2 commit and CI evidence.

## 8. Scope Statement

Correction 03 does not modify B2 domain behavior, migrations, API contracts,
tenant authorization, frontend code, WordPress code, orchestration, or agent
execution architecture.

## 9. Final Status

`READY FOR INDEPENDENT B2 FREEZE VERIFICATION`
