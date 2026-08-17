# OPENHANDS-INTEGRATION.md — Tersuite AI Studio OpenHands Architecture & Integration Guide

## 1. Architectural Overview & Single Execution Path

**Tersuite AI Studio** uses the official **OpenHands Software Agent SDK & Agent Server (v1.42.1)** as its execution engine for executing agent conversations, managing bash/python tools, and orchestrating sandboxed workspaces.

Per the non-negotiable engineering rules in [AGENTS.md](../AGENTS.md) and [TERSUITE-IMPLEMENTATION-ROADMAP.md](TERSUITE-IMPLEMENTATION-ROADMAP.md):

> **Core Decoupling Rule**: The Django business, generation, and intelligence layers must never import or depend directly on OpenHands internals. All agent interactions must go through the `TersuiteAgentRuntime` abstraction layer.

> **Single Execution Path Rule**: The production adapter (`OpenHandsAgentRuntime`) has exactly **one** execution path: through the official OpenHands SDK `RemoteConversation`. There is no secondary homemade REST fallback or retry loop. If SDK execution fails, the failure is strictly classified (`FailureCategory`), error details are preserved, and a failed `TaskResult` is returned.

---

### Component Distinctions & Architecture

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
                                               │ (Sole Execution Path)
                                               ▼
                                ┌─────────────────────────────┐
                                │ Official OpenHands SDK      │
                                │    RemoteConversation       │
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
   - Provides official abstractions for conversation lifecycle: `send_message()`, `run()`, `interrupt()`, `close()`, and `state.events`.

2. **Official OpenHands Agent Server (`openhands-agent-server==1.42.1`)**:
   - The official FastAPI-based agent execution server provided by the OpenHands project.
   - Runs as a standalone service (`python -m openhands.agent_server --host 127.0.0.1 --port 8010`).
   - Hosts endpoints for `/api/conversations`, `/sockets/events/{id}`, file system tools, tmux bash runners, and subagents.
   - **Tersuite never substitutes a custom or synthetic replacement server for this official package.**

3. **Tersuite Agent Runtime Adapter (`backend/runtime/adapters/openhands/adapter.py`)**:
   - The decoupled adapter implementing `TersuiteAgentRuntime`.
   - Bridges Tersuite domain objects (`SessionConfig`, `TaskResult`, `NormalizedEvent`) to the official OpenHands SDK `RemoteConversation` and `RemoteWorkspace`.
   - Strictly uses the official SDK for conversation lifecycle, event streaming, and stats access.
   - **No fallback to handwritten HTTP REST protocols.**

4. **Mock Adapter (`backend/runtime/adapters/mock/`)**:
   - In-memory deterministic mock implementation used for fast, deterministic unit and regression tests without requiring network dependencies or external LLM API tokens.

5. **Real Integration Tests vs. Mock Tests**:
   - **Mock Unit Tests** (`backend/runtime/tests/test_mock_adapter.py`, `backend/runtime/tests/test_openhands_adapter.py`): Test domain contracts, event serialization, error propagation, and failure categories with zero external dependencies.
   - **Real Integration Tests** (`backend/tests/integration/test_openhands_live.py`): Test the live chain against the actual running `openhands-agent-server` with real LLM credentials, verifying real tool execution, real file generation, and real event streaming.

---

## 2. Pinned Ecosystem & Version Matrix

| Component | Pinned Version / Line | Role / Environment |
|---|---|---|
| **Python** | `3.12` | Supported Python 3.12 minor line (e.g. 3.12.11 in Docker, 3.12.14 in local runtime) |
| **uv** | `0.8.13` | Deterministic package manager & lock engine |
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
| **psycopg** | `3.3.4` | PostgreSQL native driver (both psycopg and psycopg-binary resolve to 3.3.4) |
| **PostgreSQL** | `16` | Relational database (PostgreSQL 16 major line via postgres:16-alpine) |

---

## 3. Strict Credential Separation & Configuration Settings

Tersuite strictly segregates Agent Server infrastructure credentials from LLM provider API credentials:

| Configuration Setting | Type | Role & Boundary |
|---|---|---|
| `OPENHANDS_AGENT_SERVER_URL` | String | URL of the official OpenHands Agent Server (e.g. `http://localhost:8010`) |
| `OPENHANDS_AGENT_SERVER_API_KEY` | SecretStr | Secret token for Agent Server workspace authentication. Unwrapped with `.get_secret_value()` solely for `OpenHandsRemoteWorkspace.api_key`. |
| `OPENHANDS_AGENT_SERVER_TIMEOUT_SECONDS` | Integer | Read timeout for Agent Server calls. Passed to `RemoteWorkspace(..., read_timeout=...)`. |
| `OPENHANDS_AGENT_SERVER_VERIFY_SSL` | Boolean | TLS verification flag. In B1, `server_verify_ssl=True` is mandatory; disabling it raises a configuration error. |
| `LLM_DEFAULT_MODEL` | String | Default model identifier (e.g. `anthropic/claude-sonnet-4-5-20250929`). |
| `OPENROUTER_API_KEY` | SecretStr | Direct provider API key for `openrouter/` models. Passed as `SecretStr` to `OpenHandsLLM.api_key`. |
| `OPENROUTER_BASE_URL` | String | Provider routing URL for OpenRouter models. |

> **Security Rule**: The Agent Server API key must **never** be supplied to `OpenHandsLLM`, and model provider API keys must **never** be supplied to `OpenHandsRemoteWorkspace` or Agent Server authorization headers. Agent Server credentials are unwrapped only for `OpenHandsRemoteWorkspace.api_key`, while provider credentials are provided as `SecretStr` directly to `OpenHandsLLM.api_key`.

---

## 4. Launching the Official OpenHands Agent Server

The official OpenHands Agent Server is started with:

```powershell
# In backend virtual environment
uv run python -m openhands.agent_server --host 127.0.0.1 --port 8010
```

Verify health & OpenAPI metadata:
```powershell
uv run python -c "import httpx; resp = httpx.get('http://127.0.0.1:8010/openapi.json'); print(resp.json()['info'])"
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

---

## 6. Live Event Streaming Architecture

Tersuite does NOT wait for `conv.run()` to finish before observing events.

```
OpenHands Agent Server (WebSocket /sockets/events/{id})
                    │
                    ▼
   OpenHands SDK WebSocketCallbackClient
                    │ (synchronous event callback)
                    ▼
     OpenHandsAgentRuntime (live_event_callback)
                    │ (normalizes Event -> NormalizedEvent)
                    ▼
         ExecutionService (stream_event)
                    │
                    ▼
     GenerationEventPublisher (channel_layer.group_send)
                    │
                    ▼
   Django Channels Group `events_<generation_id>`
                    │
                    ▼
       Connected WebSocket Frontend Clients
```

Key guarantees:
- `RemoteConversation` is instantiated with `callbacks=[live_event_callback]`.
- As the agent acts, thinks, or invokes tools, events are dispatched immediately.
- `GenerationEventPublisher` acts as the single producer choke point for Channels broadcasting.
- Event broadcasting errors are logged and tolerated without crashing the active agent execution.

---

## 7. Failure Classification & Retry Taxonomy

Errors during execution are strictly classified without homemade retry loops:

| Category (`FailureCategory`) | Source / Condition | Default Retryable | Handled In |
|---|---|---|---|
| `NETWORK_CONNECTION` | `httpx.ConnectError`, `WebSocketConnectionError`, network drop | `True` | Infrastructure / connection layer |
| `TIMEOUT` | Execution duration exceeds timeout threshold | `True` | Runtime timeout guard |
| `MODEL_ERROR` | LLM rate limit (429), provider overloaded (500/503), context window | `True` (rate-limited) / `False` (bad request) | Model provider bridge |
| `TOOL_ERROR` | Command/tool execution failure, syntax error | `False` | Agent tool feedback loop |
| `AGENT_FATAL` | Unrecoverable loop, agent failure | `False` | Agent / Orchestration |

- `AgentRun.error_details` retains `{"error": ..., "retryable": ..., ...}`.
- Failures transition `Generation` to `FAILED` through `GenerationStateMachine.transition()`, recording `failure_category` in the generation state and metadata history.
