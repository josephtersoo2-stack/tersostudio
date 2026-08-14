# OPENHANDS-INTEGRATION.md — Tersuite AI Studio OpenHands Protocol & Architecture

## 1. Architectural Strategy & Decoupled Boundary

**Tersuite AI Studio** uses the **OpenHands Software Agent SDK & Agent Server (v1.42.1)** as its execution engine for executing agent conversations, managing bash/python tools, and orchestrating sandboxed workspaces.

Per the engineering rules in [AGENTS.md](file:///c:/xampp/htdocs/tersostudio%20new/AGENTS.md) and [docs/TERSUITE-IMPLEMENTATION-ROADMAP.md](file:///c:/xampp/htdocs/tersostudio%20new/docs/TERSUITE-IMPLEMENTATION-ROADMAP.md):

> **Core Decoupling Rule**: The Django business, generation, and intelligence layers must never import or depend directly on OpenHands SDK internals. All agent interactions must go through the `TersuiteAgentRuntime` abstraction layer.

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
                                │   OpenHands Agent Server    │
                                │   (FastAPI on Port 8010)    │
                                └─────────────────────────────┘
```

---

## 2. Pinned Ecosystem & Version Matrix

| Component | Pinned Version | Verification Environment |
|---|---|---|
| **Python** | `3.12.14` | Supported runtime across local venv & Docker |
| **Django** | `5.1.15` | Core Backend Framework |
| **Django REST Framework** | `3.17.2` | REST API Layer |
| **Django Channels** | `4.3.2` | WebSockets & Event Streaming |
| **Daphne** | `4.2.3` | ASGI Server |
| **Celery** | `5.6.3` | Asynchronous Background Task Worker |
| **Redis** | `8.1.0` | Cache, Celery Broker, Channel Layer |
| **psycopg** | `3.3.4` / `3.3.4-binary` | PostgreSQL Native Driver |
| **openhands-sdk** | `1.42.1` | Pinned OpenHands Software Agent SDK |
| **openhands-tools** | `1.42.1` | Pinned OpenHands Tools |
| **httpx** | `0.28.1` | HTTP & WebSocket Client for Adapter |

---

## 3. Network Topology & Service Ports

| Service | Port | Target URL | Description |
|---|---|---|---|
| **Tersuite Django (Daphne)** | `8000` | `http://localhost:8000` | Django REST API & WebSockets |
| **OpenHands Agent Server** | `8010` | `http://localhost:8010` | Remote Agent Server REST/WS API |
| **PostgreSQL 16** | `5432` | `postgresql://tersuite:...@localhost:5432/tersuite_db` | Primary relational database |
| **Redis 7** | `6379` | `redis://localhost:6379/0` | Cache & Channel layer |

---

## 4. OpenHands v1.42.1 Protocol Specification

The `OpenHandsAgentRuntime` adapter conforms strictly to the `openhands-sdk` v1.42.1 `RemoteConversation` protocol:

### 4.1. Conversation Creation
- **Endpoint**: `POST /api/conversations`
- **Payload**:
  ```json
  {
    "model": "anthropic/claude-sonnet-4-5-20250929",
    "system_prompt": "You are a WordPress Architect...",
    "tools": ["terminal", "file_editor"],
    "max_iterations": 30
  }
  ```
- **Response**: `{"conversation_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6"}`
- **Failure Policy**: If the server is unreachable, raises `AdapterConnectionError`. **Never fabricates synthetic conversation IDs.**

### 4.2. User Message Submission
- **Endpoint**: `POST /api/conversations/{conversation_id}/events`
- **Payload**:
  ```json
  {
    "type": "message",
    "role": "user",
    "content": "Create database schema migration for affiliate referrals.",
    "context": {}
  }
  ```

### 4.3. Run Triggering & Execution
- **Endpoint**: `POST /api/conversations/{conversation_id}/run`
- **State Check**: `GET /api/conversations/{conversation_id}`
- **Returns**: `TaskResult`
  - `success: bool`
  - `execution_status: ExecutionStatus` (`SUCCESS`, `AGENT_FAILED`, `INFRASTRUCTURE_UNAVAILABLE`, `TIMEOUT`, `CANCELLED`)
  - `failure_category: FailureCategory` (`NONE`, `NETWORK_CONNECTION`, `MODEL_ERROR`, `TOOL_ERROR`, `TIMEOUT`, `AGENT_FATAL`)
  - `output: str`
  - `artifacts: List[str]`
  - `token_usage: Dict[str, int]`
- **Failure Policy**: Sets `execution_status = INFRASTRUCTURE_UNAVAILABLE` on network errors. **Never claims success on unreachable servers.**

### 4.4. Event Streaming & Historical Synchronization
- **Live Streaming**: WebSocket endpoint `/sockets/events/{conversation_id}`
- **Historical Search**: `GET /api/conversations/{conversation_id}/events/search`
- **Normalization**:
  - OpenHands `ActionEvent` / `action` $\rightarrow$ `EventType.AGENT_TOOL_STARTED`
  - OpenHands `ObservationEvent` / `observation` $\rightarrow$ `EventType.AGENT_TOOL_FINISHED`
  - OpenHands `MessageEvent` / `thought` $\rightarrow$ `EventType.AGENT_THINKING`
  - OpenHands `InterruptEvent` $\rightarrow$ `EventType.GENERATION_CANCELLED`
  - OpenHands `AgentErrorEvent` / `error` $\rightarrow$ `EventType.AGENT_FAILED`

### 4.5. Interruption / Cancellation
- **Endpoint**: `POST /api/conversations/{conversation_id}/interrupt`

---

## 5. Phase 1 Boundaries & Known Limitations

1. **In-Memory Session State**:
   - In Phase 1, `OpenHandsAgentRuntime` and `MockAgentRuntime` maintain session mapping in-memory (`self._sessions`).
   - Durable multi-worker persistence in PostgreSQL (`generations.Generation` and `agents.AgentRun`) is scheduled for **Phase 2**.
2. **Workspace Isolation**:
   - Phase 1 defines the minimal `WorkspaceInterface` and connects to `RemoteWorkspace`.
   - Automated multi-container Docker WordPress sandbox QA (WP Core, PHP 8.x, MySQL, WP-CLI) is scheduled for **Phase 12**.
3. **Multi-Agent Orchestration**:
   - Multi-agent coordinator pipelines, planner graph deconstruction, and domain specialist delegation are scheduled for **Phases 9 & 10**.
