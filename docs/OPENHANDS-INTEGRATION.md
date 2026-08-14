# OPENHANDS-INTEGRATION.md — Tersuite AI Studio OpenHands Architecture & Integration Guide

## 1. Architectural Overview & Component Distinctions

**Tersuite AI Studio** uses the official **OpenHands Software Agent SDK & Agent Server (v1.42.1)** as its execution engine for executing agent conversations, managing bash/python tools, and orchestrating sandboxed workspaces.

Per the non-negotiable engineering rules in [AGENTS.md](file:///c:/xampp/htdocs/tersostudio%20new/AGENTS.md) and [docs/TERSUITE-IMPLEMENTATION-ROADMAP.md](file:///c:/xampp/htdocs/tersostudio%20new/docs/TERSUITE-IMPLEMENTATION-ROADMAP.md):

> **Core Decoupling Rule**: The Django business, generation, and intelligence layers must never import or depend directly on OpenHands internals. All agent interactions must go through the `TersuiteAgentRuntime` abstraction layer.

---

### Component Distinctions

```
┌─────────────────────────────────────────────────────────────┐
│                 Tersuite Django Application                 │
│         (Accounts, Generations, Realtime, Knowledge)        │
└──────────────────────────────┬──────────────────────────────┘
                               │ (calls abstract interfaces)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│          TersuiteAgentRuntime Abstract Interface            │
│         (runtime.interfaces: SessionConfig, TaskResult)     │
└──────────────────────────────┬──────────────────────────────┘
                               │
               ┌───────────────┴───────────────┐
               ▼                               ▼
┌─────────────────────────────┐ ┌─────────────────────────────┐
│      MockAgentRuntime       │ │    OpenHandsAgentRuntime    │
│  (Deterministic Unit Tests) │ │ (Production Adapter Bridge) │
└─────────────────────────────┘ └──────────────┬──────────────┘
                                               │ (SDK / REST / WS)
                                               ▼
                                ┌─────────────────────────────┐
                                │ OpenHands RemoteConversation│
                                │   (openhands-sdk v1.42.1)   │
                                └──────────────┬──────────────┘
                                               │
                                               ▼
                                ┌─────────────────────────────┐
                                │ Official OpenHands Agent    │
                                │ Server (openhands-agent-    │
                                │   server v1.42.1 on 8010)   │
                                └─────────────────────────────┘
```

1. **OpenHands Software Agent SDK (`openhands-sdk==1.42.1`)**:
   - The core agent framework defining `Agent`, `LLM`, `Conversation`, `RemoteConversation`, `RemoteWorkspace`, `Tool`, and event models.
   - Provides client-side abstractions for communicating with remote OpenHands servers over HTTP and WebSocket.

2. **Official OpenHands Agent Server (`openhands-agent-server==1.42.1`)**:
   - The official FastAPI-based agent execution server provided by the OpenHands project.
   - Runs as a standalone service (`python -m openhands.agent_server --host 127.0.0.1 --port 8010`).
   - Hosts endpoints for `/api/conversations`, `/sockets/events/{id}`, file system tools, tmux bash runners, and subagents.
   - **Tersuite never substitutes a custom or synthetic replacement server for this official package.**

3. **Tersuite Agent Runtime Adapter (`backend/runtime/adapters/openhands/adapter.py`)**:
   - The decoupled adapter implementing `TersuiteAgentRuntime`.
   - Bridges Tersuite domain objects (`SessionConfig`, `TaskResult`, `NormalizedEvent`) to the official OpenHands SDK `RemoteConversation` and `RemoteWorkspace`.
   - OpenHands owns its protocol; Tersuite owns the domain abstraction boundary.

4. **Mock Adapter (`backend/runtime/adapters/mock/`)**:
   - In-memory deterministic mock implementation used for fast, deterministic unit and regression tests without requiring network dependencies or external LLM API tokens.

5. **Real Integration Tests vs. Mock Tests**:
   - **Mock Unit Tests** (`backend/runtime/tests/test_mock_adapter.py`, `backend/runtime/tests/test_openhands_adapter.py`): Test domain contracts, event serialization, error propagation, and failure categories with zero external dependencies.
   - **Real Integration Tests** (`backend/tests/integration/test_openhands_live.py`): Test the live chain against the actual running `openhands-agent-server` with real LLM credentials, verifying real tool execution, real file generation, and real event streaming.

---

## 2. Pinned Ecosystem & Version Matrix

| Component | Pinned Version | Role / Environment |
|---|---|---|
| **Python** | `3.12.14` | CPython 3.12 64-bit runtime |
| **openhands-sdk** | `1.42.1` | Pinned OpenHands Software Agent SDK |
| **openhands-agent-server** | `1.42.1` | Official OpenHands Agent Server |
| **openhands-tools** | `1.42.1` | Pinned OpenHands Tools |
| **openhands-workspace** | `1.42.1` | Pinned OpenHands Workspace management |
| **Django** | `5.1.15` | Core Backend Framework |
| **Django REST Framework** | `3.17.2` | REST API Layer |
| **Django Channels** | `4.3.2` | WebSockets & Event Streaming |
| **Daphne** | `4.2.3` | ASGI Server |
| **Celery** | `5.6.3` | Asynchronous Background Task Worker |
| **Redis** | `8.1.0` | Cache, Celery Broker, Channel Layer |
| **psycopg** | `3.3.4` / `3.3.4-binary` | PostgreSQL 16 Native Driver |
| **PostgreSQL** | `16.6` | Relational Database |

---

## 3. Network Topology & Service Ports

| Service | Port | Target URL | Description |
|---|---|---|---|
| **Tersuite Django (Daphne)** | `8000` | `http://localhost:8000` | Django REST API & WebSockets |
| **Official OpenHands Agent Server** | `8010` | `http://localhost:8010` | Official OpenHands Agent Server |
| **PostgreSQL 16** | `5432` | `postgresql://tersuite:...@localhost:5432/tersuite_db` | Primary relational database |
| **Redis 7** | `6379` | `redis://localhost:6379/0` | Cache & Channel layer |

---

## 4. Launching the Official OpenHands Agent Server

The official OpenHands Agent Server is started with:

```powershell
# In backend virtual environment
.\.venv\Scripts\python.exe -m openhands.agent_server --host 127.0.0.1 --port 8010
```

Verify health & OpenAPI metadata:
```powershell
.\.venv\Scripts\python.exe -c "import httpx; resp = httpx.get('http://127.0.0.1:8010/openapi.json'); print(resp.json()['info'])"
# Expected output: {'title': 'OpenHands Agent Server', 'version': '1.42.1'}
```

---

## 5. Event Stream Normalization Contract

All agent actions, thoughts, and outputs are normalized into `NormalizedEvent` records and streamed over Django Channels:

```json
{
  "generation_id": "gen-a1b2c3d4",
  "agent_run_id": "run-e5f6g7h8",
  "timestamp": "2026-08-14T23:55:00.000000Z",
  "event_type": "agent.tool_started",
  "payload": {
    "tool": "file_editor",
    "command": "write",
    "path": "plugin.php"
  }
}
```

Standard Event Types:
- `agent.started`: Session or subagent execution begins.
- `agent.thinking`: LLM thought or reasoning output.
- `agent.tool_started`: Tool/action invocation requested.
- `agent.tool_finished`: Tool observation returned.
- `agent.completed`: Task completed successfully.
- `agent.failed`: Execution failed with fatal error.
- `generation.cancelled`: Execution cancelled by user or coordinator.
