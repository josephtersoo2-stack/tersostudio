# Tersuite AI Studio — Phase 1 Implementation Audit & Correction Instructions

## Purpose

This document is a **correction specification for the Phase 1 implementation that has just been completed**.

Do not treat this as a new project roadmap. The master roadmap already exists at:

`docs/TERSUITE-IMPLEMENTATION-ROADMAP.md`

Do not rewrite the roadmap.

Do not start Phase 2.

Your job is to take the existing Phase 1 implementation, understand what was done correctly and incorrectly, and make the implementation trustworthy enough for us to formally freeze Phase 1.

The current GitHub commit being reviewed is:

`8eb7b76b738267f4e927b6bcaa54fc8028f872f8`

Repository:

`https://github.com/josephtersoo2-stack/tersostudio`

---

# 1. What Phase 1 Did Correctly

The Phase 1 implementation is a good foundation. Do not throw it away.

The following architectural decisions are correct and should be preserved.

## 1.1 Django foundation

The project correctly established:

- Django
- Django REST Framework
- PostgreSQL configuration
- Redis
- Celery
- Django Channels
- modular settings
- environment configuration
- structured logging
- health endpoints
- testing infrastructure

Keep these foundations.

## 1.2 Application boundaries

The foundational applications are appropriately separated:

```text
apps/
├── core/
├── accounts/
└── realtime/
```

This is appropriate for Phase 1.

Do not prematurely create every future application from the roadmap.

## 1.3 Custom User model

The custom email-based User model with UUID identity is appropriate.

Keep:

- email login
- UUID primary key
- password hashing
- basic permissions foundation
- basic authentication endpoints

Do not expand this phase into full organizations, subscriptions, billing, or enterprise RBAC.

## 1.4 Health endpoints

The implementation correctly separated:

```text
/api/v1/health/live/
/api/v1/health/ready/
```

Keep this separation.

Liveness means the process is alive.

Readiness reports the health of dependencies such as:

- PostgreSQL
- Redis
- Celery

without blocking the HTTP request waiting for a worker job to run.

## 1.5 Runtime abstraction

This is one of the most important things the implementation got right.

The architecture is:

```text
Tersuite Django
      ↓
TersuiteAgentRuntime
      ↓
Adapter
      ↓
OpenHands
```

The rest of Django should not import OpenHands internals directly.

Keep the OpenHands-specific implementation inside the runtime adapter boundary.

## 1.6 Mock runtime

The deterministic mock runtime is a good Phase 1 decision.

It allows the Tersuite runtime contracts to be tested without requiring a live OpenHands server.

Keep it.

But keep a strict distinction between:

```text
Mock execution
```

and:

```text
Real OpenHands execution
```

A mock test must never be presented as proof that OpenHands integration works.

## 1.7 Realtime event normalization

Creating a Tersuite-owned normalized event model is also correct.

The intended architecture is:

```text
OpenHands event
      ↓
Tersuite adapter
      ↓
Tersuite NormalizedEvent
      ↓
Channels
      ↓
Client
```

Keep this ownership boundary.

---

# 2. The Main Problem: Phase 1 Was Reported as More Complete Than It Actually Is

The previous Phase 1 report said:

> "All Phase 1 objectives and mandatory corrections have been implemented, tested, committed, and pushed."

That statement is too strong.

The Django foundation is substantially implemented and tested.

However, the **real OpenHands integration has not been sufficiently verified**, and some parts of the adapter currently simulate successful execution instead of requiring real execution.

Therefore:

```text
Django Foundation       = substantially complete
Runtime abstraction     = substantially complete
Mock runtime            = complete enough for Phase 1
Real OpenHands adapter  = needs correction and verification
PostgreSQL verification = not yet proven by the reported test run
```

Do not repeat the previous "Phase 1 complete" claim until these issues are fixed.

---

# 3. Error #1 — The Reported Test Run Used SQLite

## What happened

The reported test command was:

```powershell
$env:TEST_USE_SQLITE="1"; pytest
```

This explicitly switched the Django test configuration to in-memory SQLite.

The repository's test settings contain the SQLite override:

```python
if os.getenv("TEST_USE_SQLITE", "0") == "1":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    }
```

Therefore:

```text
30 passed
```

proves that the suite passed under SQLite.

It does NOT prove PostgreSQL compatibility.

## Why this matters

Tersuite's actual production database is PostgreSQL.

PostgreSQL-specific behavior can differ from SQLite in:

- UUID handling
- constraints
- indexes
- JSON behavior
- transactions
- SQL behavior
- concurrency
- connection behavior
- migrations

A passing SQLite test suite can therefore hide PostgreSQL defects.

## What was right

The project did correctly configure PostgreSQL as the primary test database.

The problem is that the final verification command bypassed it.

## Required correction

Run the test suite with PostgreSQL actually running:

```powershell
pytest
```

without:

```powershell
$env:TEST_USE_SQLITE="1"
```

Verify that the test database is actually PostgreSQL.

Record:

```text
Python version
PostgreSQL version
Django version
psycopg version
```

The final report must explicitly say:

```text
PostgreSQL-backed tests: PASS
```

only if they actually ran against PostgreSQL.

If PostgreSQL is not available, report the environmental blocker. Do not substitute SQLite and claim PostgreSQL passed.

## Implementation guidance

Keep SQLite only as an explicit optional local fallback if useful.

Do not make it the authoritative integration test database.

---

# 4. Error #2 — OpenHands Was Not Actually Installed in the Tested Python Environment

## What happened

The dependency file contains:

```text
openhands-sdk>=1.40.0; python_version >= "3.12"
openhands-tools>=1.40.0; python_version >= "3.12"
```

The project metadata says:

```text
requires-python = ">=3.11"
```

The previous test environment reported:

```text
Python 3.11.9
```

Therefore the OpenHands dependencies were conditionally skipped.

This creates a critical verification problem:

```text
Python 3.11
     ↓
OpenHands package condition says >=3.12
     ↓
OpenHands is not installed
     ↓
Tests still pass
     ↓
Phase 1 is reported as OpenHands-integrated
```

That is not sufficient.

## What was right

The developer correctly tried to prevent an incompatible OpenHands installation.

The problem is the overall project Python version was not reconciled with that decision.

## Required correction

Choose the actual Python version we are going to support for Tersuite.

Because OpenHands is a core engine of this project, the supported Python environment must be compatible with the selected OpenHands SDK/server stack.

Then make these consistent:

```text
pyproject.toml
requirements/constraints
Dockerfile
docker-compose
local development environment
documentation
```

Do not leave the project saying:

```text
Python >= 3.11
```

while the actual OpenHands dependency only exists for:

```text
Python >= 3.12
```

if Python 3.12 is the environment we actually require.

## Required evidence

The final report must show that the OpenHands packages were actually installed in the environment used for verification.

---

# 5. Error #3 — The OpenHands Adapter Appears to Guess the Agent Server API

This is the most important implementation issue.

The current adapter manually uses HTTP requests such as:

```python
self._client.post("/api/conversations", ...)
self._client.post(f"/api/conversations/{id}/messages", ...)
self._client.get(f"/api/conversations/{id}/events")
self._client.post(f"/api/conversations/{id}/cancel")
```

It also assumes payload fields such as:

```python
{
    "model": ...,
    "system_prompt": ...,
    "tools": ...,
    "max_iterations": ...
}
```

and responses such as:

```python
data.get("conversation_id")
data.get("response")
```

The issue is not that HTTP adapters are inherently wrong.

The issue is that these paths and fields must come from the **actual OpenHands version we are installing**, not from assumptions.

## Why this matters

OpenHands is an actively evolving project.

The SDK and Agent Server have explicit implementations for:

- Agent
- Conversation
- RemoteConversation
- Task
- Delegate
- Workspace
- events
- Agent Server APIs

We already inspected those source areas.

Tersuite must integrate with the real contract.

## What was right

Creating an adapter was the correct architectural decision.

## What was wrong

The adapter appears to define its own interpretation of the OpenHands API before proving that the current OpenHands API actually works that way.

## Required correction

Before modifying the adapter:

1. Select the OpenHands version.
2. Inspect that exact version's source.
3. Inspect the actual Agent Server API implementation.
4. Determine the real session/conversation creation mechanism.
5. Determine the real task/message execution mechanism.
6. Determine the actual event transport.
7. Determine the real cancellation mechanism.
8. Determine the real workspace mechanism.
9. Build the adapter against those actual interfaces.

Prefer the official SDK abstractions where they provide the needed behavior.

If REST is required, use the actual Agent Server API contract.

Do not invent endpoint paths or payload schemas.

---

# 6. Error #4 — The Adapter Can Report SUCCESS When OpenHands Is Unreachable

This is a serious correctness issue.

The current adapter contains fallback behavior equivalent to:

```python
except httpx.RequestError:
    output = f"Executed task locally (server unreachable): {prompt}"
    success = True
```

This must be removed.

## Why this is dangerous

Tersuite will eventually use the result to determine:

- generation state
- artifacts
- billing
- credits
- agent success
- test status
- user-visible completion

If OpenHands never executed the task, Tersuite must never claim it did.

Otherwise we could get:

```text
OpenHands is down
      ↓
Tersuite says SUCCESS
      ↓
User receives "completed"
      ↓
No real code was generated
```

That is unacceptable.

## Required behavior

Use a real failure:

```text
OpenHands unavailable
        ↓
AdapterConnectionError
        ↓
execution = failed
        ↓
diagnostic recorded
```

The failure should contain enough information to identify:

```text
component
operation
error
retryable status
```

## Rule

There must be **no fake success** anywhere in the real OpenHands adapter.

---

# 7. Error #5 — Session Creation Also Falls Back to Fake Detached Conversations

The current adapter attempts to create a session and, when communication fails, generates something equivalent to:

```text
conv-detached-...
```

and continues.

This makes the system look like a remote conversation exists when it does not.

That is misleading.

## Required behavior

If the real OpenHands server cannot create the session:

```text
create_session()
       ↓
OpenHands unavailable
       ↓
raise/return connection failure
```

Do not create a synthetic OpenHands conversation ID and continue as though the remote session exists.

A Tersuite-local session ID may still exist, but it must be marked appropriately, such as:

```text
INITIALIZATION_FAILED
```

rather than:

```text
ACTIVE
```

---

# 8. Error #6 — The Current Event Streaming Is Not Really Live Streaming

The current implementation of `stream_events()` essentially iterates through an in-memory event list.

That is event replay, not true live streaming.

## What was right

The idea of exposing:

```text
stream_events()
```

from the runtime abstraction is correct.

## What needs correction

Clearly distinguish:

```text
get_historical_events()
```

from:

```text
subscribe_to_live_events()
```

At Phase 1, it is acceptable to implement only the simplest verified behavior.

But do not document cached event iteration as production live streaming.

The eventual pipeline is:

```text
OpenHands
      ↓
real events
      ↓
Tersuite runtime
      ↓
NormalizedEvent
      ↓
Redis / Channels
      ↓
client
```

That belongs primarily to Phase 4.

---

# 9. Error #7 — Runtime Sessions Are Process-Local Only

The current adapter uses an in-memory dictionary similar to:

```python
self._sessions = {}
```

## What was right

This is acceptable as a Phase 1 prototype.

## What is important

It must be explicitly documented as temporary.

It will not survive:

- Django restart
- worker restart
- process replacement
- multiple application workers
- horizontal scaling

That is not a Phase 1 blocker if we document the limitation.

## Required correction

Make sure:

```text
Tersuite session ID
```

and:

```text
OpenHands conversation ID
```

are distinct.

The durable generation/session records will be implemented later in the Tersuite database.

Do not build the entire durable generation persistence system now.

---

# 10. Error #8 — OpenHands and Django Are Configured on the Same Default Port

The current OpenHands configuration defaults to:

```text
http://localhost:8000
```

while Django is also expected to use port 8000.

That is ambiguous and will create conflicts in local development.

## Required correction

Make the topology explicit.

For example:

```text
Tersuite Django
http://localhost:8000

OpenHands Agent Server
http://localhost:8010
```

or use Docker service names.

The actual values must come from environment configuration.

The two services must not silently point to the same address.

---

# 11. Error #9 — Dependencies Are Described as "Pinned" but Aren't

The requirements currently use:

```text
openhands-sdk>=1.40.0
openhands-tools>=1.40.0
```

A minimum version is not a pinned dependency.

This matters because reproducibility is very important for an AI runtime that is evolving quickly.

## Required correction

Use either:

```text
package==version
```

or a proper constraints/lock mechanism.

The final report must state the exact OpenHands versions used for testing.

---

# 12. Error #10 — The Adapter Currently Mixes Real Infrastructure Failure With Successful Execution Semantics

This is related to the fake-success problem but deserves a separate architectural fix.

An adapter must distinguish:

```text
Task accepted
Task running
Task completed
Task failed
Infrastructure unavailable
Authentication failed
Request invalid
Timeout
Cancelled
```

It should not simply map everything into:

```text
success=True/False
```

too early.

## Required approach

At the runtime boundary, preserve enough state to tell Tersuite:

```text
Execution status
Failure reason
Retryable
Provider/runtime error
Agent result
Artifacts
```

Do not collapse infrastructure errors into normal agent output.

---

# 13. Error #11 — The Integration Tests Currently Test the Translation Layer, Not the Real OpenHands Runtime

The existing tests for:

```text
runtime/tests/test_openhands_adapter.py
```

are useful.

Keep them.

But understand what they prove:

```text
Tersuite adapter
      ↓
payload translation
      ↓
mocked/controlled response
```

They do not prove:

```text
Tersuite
      ↓
actual OpenHands Server
      ↓
actual agent
      ↓
actual task
      ↓
actual event/result
```

## Required correction

Keep the current unit tests.

Add a clearly separated real integration/smoke test.

It may be environment-dependent.

For example:

```text
tests/
└── integration/
    └── test_openhands_live.py
```

This test should only run when the real OpenHands service is available.

If it cannot run locally, report:

```text
NOT RUN — OpenHands Agent Server unavailable
```

Do not turn that into a false pass.

---

# 14. Do Not Add Future-Phase Functionality

While fixing Phase 1, do not begin building:

- WordPress knowledge ingestion
- professional plugin extraction
- feature discovery
- product specification UI
- full Coordinator
- full Planner
- specialist domain agents
- WordPress sandbox
- QA engine
- security engine
- billing
- credits
- subscriptions
- WordPress client plugin

Those remain future phases.

The current goal is:

> Make the foundation and OpenHands runtime boundary trustworthy.

---

# 15. Exact Implementation Strategy

Use this sequence.

## Step A — Inspect actual OpenHands

Inspect:

```text
OpenHands/software-agent-sdk
```

and the relevant Agent Server/workspace source.

Determine the real APIs.

## Step B — Select compatible versions

Choose:

```text
Python
OpenHands SDK
OpenHands Tools
OpenHands Workspace
OpenHands Agent Server
```

as a tested combination.

## Step C — Update environment

Make:

```text
pyproject.toml
requirements/constraints
Dockerfile
docker-compose
.env.example
```

consistent.

## Step D — Correct the adapter

Keep the existing Tersuite abstraction.

Replace guessed/fake OpenHands behavior with real integration.

## Step E — Remove fake success

Any OpenHands communication failure must produce a real failure.

## Step F — Clarify session state

Keep process-local state only as a temporary Phase 1 limitation.

## Step G — Correct service URLs

Django and OpenHands must have distinct addresses.

## Step H — Run PostgreSQL tests

Use actual PostgreSQL.

## Step I — Run real OpenHands smoke test

Use the actual selected OpenHands runtime.

## Step J — Document the integration

Update:

```text
docs/OPENHANDS-INTEGRATION.md
```

with what actually exists.

## Step K — Commit and push

Create a focused corrective commit.

Do not modify unrelated future-phase work.

---

# 16. Definition of Done for This Correction

Phase 1 may be recommended for freeze only when:

### Django

- Django starts.
- PostgreSQL works.
- Redis works.
- Celery is configured.
- Channels is configured.
- Authentication foundation works.
- Health endpoints work.
- Logging works.

### Runtime

- Runtime interfaces work.
- Mock adapter works.
- OpenHands adapter follows the same contracts.
- OpenHands-specific dependencies remain isolated.

### OpenHands

- Actual compatible version selected.
- Actual compatible Python version selected.
- OpenHands packages actually installed.
- Actual OpenHands API inspected.
- No guessed endpoint contract remains.
- No fake-success fallback remains.
- Session failure is reported correctly.
- Task failure is reported correctly.
- Events are normalized correctly.
- Live vs historical event semantics are documented.

### Database

- PostgreSQL-backed test suite passes.

### Verification

- Unit tests pass.
- Integration tests pass where environment allows.
- Real OpenHands smoke test passes OR is explicitly reported as environment-dependent and not run.

### Git

- Working tree clean.
- Corrective commit created.
- Commit pushed to GitHub.
- Commit SHA reported.

---

# 17. Final Report Required From Antigravity

At the end, report:

```text
Repository:
Branch:
Commit SHA:

Python version:
Django version:
PostgreSQL version:
Redis version:
Celery version:

OpenHands SDK version:
OpenHands Tools version:
OpenHands Agent Server version:
```

Then report:

```text
PostgreSQL tests: PASS / FAIL
Unit tests: PASS / FAIL
Runtime tests: PASS / FAIL
OpenHands adapter tests: PASS / FAIL
Real OpenHands smoke test: PASS / FAIL / NOT RUN
```

For `NOT RUN`, explain why.

Also include:

- exact OpenHands API/SDK contract used
- session creation mechanism
- task execution mechanism
- event mechanism
- cancellation mechanism
- workspace mechanism
- known limitations

Do not claim Phase 1 is frozen until these corrections have been verified.

---

# 18. Important Final Instruction

Do not simply make the test suite green.

We are building the foundation for a production AI software-generation platform.

A test that passes using SQLite is not equivalent to a PostgreSQL test.

A mocked HTTP response is not equivalent to a real OpenHands execution.

A fabricated success response is not an acceptable fallback.

A cached event list is not equivalent to live event streaming.

The goal of this correction is to make the Phase 1 implementation **truthful, reproducible, and technically trustworthy**.

Do the work carefully, run the real tests, commit the corrections, push them to GitHub, and STOP.

Do not begin Phase 2.
