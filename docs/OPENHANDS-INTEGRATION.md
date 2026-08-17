# OpenHands SDK & Agent Server Integration Specification

## 1. Overview & Architecture

Tersuite AI Studio integrates the official **OpenHands Software Agent SDK (v1.42.1)** and **OpenHands Agent Server (v1.42.1)** as its programmatic agent execution engine.

Tersuite acts as the durable workflow coordinator (Django / PostgreSQL), maintaining state, models, lifecycle steps, and audit records, while delegating conversation and tool execution to the OpenHands runtime engine.

---

## 2. Pinned Package Baseline

The backend environment requires and pins the following OpenHands 1.42.1 packages:

```toml
openhands-sdk = "1.42.1"
openhands-tools = "1.42.1"
openhands-agent-server = "1.42.1"
openhands-workspace = "1.42.1"
```

---

## 3. Strict Credential Separation

Tersuite enforces strict separation between **Agent Server infrastructure credentials** and **LLM model provider credentials**:

| Configuration Name | Role | Usage |
|---|---|---|
| `OPENHANDS_AGENT_SERVER_URL` | Agent Server Host URL | Used by `OpenHandsRemoteWorkspace` and connection probes |
| `OPENHANDS_AGENT_SERVER_API_KEY` | Server Authentication | Passed solely to Agent Server HTTP headers / workspace |
| `OPENHANDS_AGENT_SERVER_TIMEOUT_SECONDS` | Request Timeout | Configures HTTP client timeouts for server calls |
| `OPENHANDS_AGENT_SERVER_VERIFY_SSL` | TLS Verification | Boolean flag for SSL validation |
| `LLM_DEFAULT_MODEL` | Default Model Slug | Configures default model for `OpenHandsLLM` (e.g. `anthropic/claude-sonnet-4-5-20250929`) |
| `OPENROUTER_API_KEY` | OpenRouter Provider Key | Passed exclusively to `OpenHandsLLM` / LiteLLM provider |
| `OPENROUTER_BASE_URL` | Provider Routing URL | Passed exclusively to `OpenHandsLLM` / LiteLLM provider |

> **Security Rule**: The Agent Server API key must **never** be supplied to `OpenHandsLLM`, and model provider API keys must **never** be supplied to `OpenHandsRemoteWorkspace` or Agent Server authorization headers.

---

## 4. Execution Lifecycle

```
Generation (BUILDING)
  ↓
GenerationStep (PENDING)
  ↓
ExecutionService.create_and_dispatch()
  ↓
AgentRun (QUEUED)
  ↓
OpenHandsAgentRuntime.create_session()
  ↓
OpenHands SDK RemoteConversation (port 8010)
  ↓
WebSocket Live Event Stream (Normalizer)
  ↓
AgentRun (COMPLETED / FAILED)
```

---

## 5. Verification Commands

```bash
# Verify OpenHands packages installation
uv run python -c "import importlib.metadata as m; print({p: m.version(p) for p in ['openhands-sdk','openhands-tools','openhands-agent-server','openhands-workspace']})"

# Run OpenHands adapter unit & regression tests
uv run pytest runtime/tests/
```
