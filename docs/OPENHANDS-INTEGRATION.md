# OPENHANDS-INTEGRATION.md — Tersuite AI Studio Agent Runtime & OpenHands Architecture

## 1. Architectural Strategy & Boundary Principle

**Tersuite AI Studio** uses the **OpenHands Software Agent SDK & Agent Server** as its low-level execution engine for executing agent conversations, running bash/python tools, and managing sandboxed workspaces.

However, per the non-negotiable architectural rules in [AGENTS.md](file:///c:/xampp/htdocs/tersostudio%20new/AGENTS.md) and [docs/TERSUITE-IMPLEMENTATION-ROADMAP.md](file:///c:/xampp/htdocs/tersostudio%20new/docs/TERSUITE-IMPLEMENTATION-ROADMAP.md):

> **Core Decoupling Rule**: The Django business and intelligence layers must never import or depend directly on OpenHands SDK internals. All communication with OpenHands must remain strictly behind the `TersuiteAgentRuntime` abstraction layer.

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
                                               │ (HTTP / WebSocket)
                                               ▼
                                ┌─────────────────────────────┐
                                │   OpenHands Agent Server    │
                                │   (FastAPI on Port 8010)    │
                                └──────────────┬──────────────┘
                                               │
                                               ▼
                                ┌─────────────────────────────┐
                                │   OpenHands Software SDK    │
                                │    (Agent, LLM, Tools)      │
                                └─────────────────────────────┘
```

---

## 2. Pinned Ecosystem & Version Matrix

| Component | Pinned Version | Environment Requirement |
|---|---|---|
| **Python** | `3.12+` | Production Runtime & Containers |
| **Django** | `5.1.15` | Core Backend Framework |
| **Django REST Framework** | `3.17.2` | REST API Layer |
| **Django Channels** | `4.3.2` | WebSockets & Event Streaming |
| **Daphne** | `4.2.3` | ASGI Server |
| **Celery** | `5.6.3` | Asynchronous Background Worker |
| **Redis** | `8.1.0` | Cache, Celery Broker, Channel Layer |
| **psycopg** | `3.3.4` | PostgreSQL Native Driver |
| **openhands-sdk** | `1.42.1` | Pinned OpenHands Software Agent SDK |
| **openhands-tools** | `1.42.1` | Pinned OpenHands Execution Tools |
| **httpx** | `0.28.1` | Async/Sync HTTP Client for Adapter |

---

## 3. Network Topology & Service Port Allocations

To prevent port collisions during local and containerized development:

| Service | Host Port | Container / Internal URL | Description |
|---|---|---|---|
| **Tersuite Django (Daphne)** | `8000` | `http://localhost:8000` | Django REST API & WebSockets |
| **OpenHands Agent Server** | `8010` | `http://localhost:8010` | Remote OpenHands Agent Server API |
| **PostgreSQL 16** | `5432` | `postgresql://tersuite:...@db:5432/tersuite_db` | Primary relational database |
| **Redis 7** | `6379` | `redis://localhost:6379/0` | Cache & Channel layer |

---

## 4. Agent Runtime Lifecycle & API Contract

The `TersuiteAgentRuntime` interface mandates the following execution lifecycle:

### 4.1. Session Creation (`create_session`)
- **Tersuite Input**: `SessionConfig(generation_id, agent_run_id, model, system_prompt, tools, max_iterations, timeout_seconds)`
- **OpenHands REST Call**: `POST /api/conversations`
- **Request Payload**:
  ```json
  {
    "model": "anthropic/claude-sonnet-4-5-20250929",
    "system_prompt": "You are a WordPress Architect...",
    "tools": ["terminal", "file_editor"],
    "max_iterations": 30
  }
  ```
- **Response**: Returns `conversation_id`.
- **Failure Policy**: If the server is unreachable or returns a non-2xx status code, raises `AdapterConnectionError`. **Never fabricates synthetic conversation IDs.**

### 4.2. Task Execution (`send_task`)
- **Tersuite Input**: `session_id`, `prompt`, `context`
- **OpenHands REST Call**: `POST /api/conversations/{conversation_id}/messages`
- **Request Payload**:
  ```json
  {
    "content": "Create database schema migration for affiliate referrals.",
    "context": {}
  }
  ```
- **Returns**: `TaskResult`
  - `success: bool`
  - `execution_status: ExecutionStatus` (`SUCCESS`, `AGENT_FAILED`, `INFRASTRUCTURE_UNAVAILABLE`, `TIMEOUT`, `CANCELLED`)
  - `failure_category: FailureCategory` (`NONE`, `NETWORK_CONNECTION`, `MODEL_ERROR`, `TOOL_ERROR`, `TIMEOUT`, `AGENT_FATAL`)
  - `output: str`
  - `artifacts: List[str]`
  - `token_usage: Dict[str, int]`
- **Failure Policy**: If network connection fails, sets `execution_status = INFRASTRUCTURE_UNAVAILABLE` and `retryable = True`. **Never claims success on unreachable servers.**

### 4.3. Event Observation & Streaming
- **Historical Events (`get_historical_events` / `observe_events`)**: Queries recorded session events from the in-memory session log and synchronizes remote events from `GET /api/conversations/{conversation_id}/events`.
- **Live Subscription (`subscribe_events`)**: Asynchronous generator yielding `NormalizedEvent` objects in real time.
- **Normalization Mapping**:
  - OpenHands `agent_action` $\rightarrow$ Tersuite `agent.tool_started`
  - OpenHands `agent_observation` $\rightarrow$ Tersuite `agent.tool_finished`
  - OpenHands `thought` $\rightarrow$ Tersuite `agent.thinking`
  - OpenHands `error` $\rightarrow$ Tersuite `system.error` / `agent.failed`

### 4.4. Cancellation & Teardown
- **Cancellation (`cancel_execution`)**: Sends `POST /api/conversations/{conversation_id}/cancel`, sets session status to `CANCELLED`, and logs `generation.cancelled` event.
- **Session Cleanup (`close_session`)**: Sends `POST /api/conversations/{conversation_id}/close` and cleans up adapter session mappings.

---

## 5. Phase 1 Boundaries & Known Limitations

1. **In-Memory Session State**:
   - In Phase 1, `OpenHandsAgentRuntime` and `MockAgentRuntime` maintain session mapping in-memory (`self._sessions`).
   - Durable multi-worker persistence in PostgreSQL (`generations.Generation` and `agents.AgentRun`) is scheduled for **Phase 2**.
2. **Workspace Isolation**:
   - Phase 1 defines the minimal `WorkspaceInterface`.
   - Automated multi-container Docker sandbox provisioning (WordPress Core, PHP 8.x, MySQL, WP-CLI) is scheduled for **Phase 12**.
3. **Multi-Agent Orchestration**:
   - Multi-agent coordinator pipelines, planner graph deconstruction, and domain specialist delegation are scheduled for **Phases 9 & 10**.
