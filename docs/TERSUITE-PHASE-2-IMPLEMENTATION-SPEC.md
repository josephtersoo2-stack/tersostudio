# Tersuite AI Studio — Phase 2 Implementation Specification

## Phase

PHASE 2 — PROJECT, GENERATION, AGENT RUN, WORKSPACE & ARTIFACT DOMAIN

---

# 1. Purpose

Phase 1 is officially frozen.

Phase 1 established and verified:

- Django foundation
- Django REST Framework
- PostgreSQL
- Redis
- Celery
- Django Channels
- Authentication foundation
- Tersuite Agent Runtime abstraction
- Mock Agent Runtime
- Official OpenHands SDK integration
- Official OpenHands Agent Server integration
- Runtime failure classification
- PostgreSQL-backed tests
- OpenHands adapter architecture

Do NOT modify Phase 1 architecture unless a real defect is discovered during Phase 2.

Do NOT redesign the OpenHands integration.

Do NOT add a second agent runtime.

Do NOT implement future-phase AI intelligence yet.

---

# 2. Phase 2 Objective

The objective of Phase 2 is to create the durable domain model and APIs that allow Tersuite to manage:

```text
Project
    ↓
Generation
    ↓
Generation Steps
    ↓
Agent Runs
    ↓
Workspace
    ↓
Artifacts
```
