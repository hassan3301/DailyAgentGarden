# Architecture

## Purpose

DailyAgentGarden is a reusable multi-agent framework designed for building and deploying client-specific AI agents. It provides shared infrastructure so that each new client project inherits production-ready tooling — RAG pipelines, observability, configuration management — without duplicating effort.

## Tech Stack

| Layer | Technology |
|---|---|
| **AI / LLM** | Google Vertex AI ADK (Gemini models) |
| **Backend API** | FastAPI + Uvicorn |
| **Frontend** | React |
| **Infrastructure** | Google Cloud Run, Cloud Storage, Vertex AI Search |
| **Configuration** | Pydantic Settings + python-dotenv |
| **Testing** | pytest + pytest-asyncio |

## Core Principles

### Modularity
Every agent lives in its own directory with a self-contained configuration, handler, prompts, and tests. Agents communicate only through the orchestrator — never directly with each other.

### Shared RAG
A common RAG grounding layer is configured per-agent through `rag_config.py`. This allows each agent to ground its responses in different data sources while reusing the same retrieval infrastructure.

### Client-Specific Configs
Each client deployment gets its own `config.yaml` overlays. The base framework provides sensible defaults; client configs override only what differs.

## System Architecture

```
┌─────────────────────────────────────────────┐
│                   React UI                  │
└──────────────────────┬──────────────────────┘
                       │ HTTP / WebSocket
┌──────────────────────▼──────────────────────┐
│               FastAPI Gateway               │
│          (auth, rate limiting, CORS)        │
└──────────────────────┬──────────────────────┘
                       │
┌──────────────────────▼──────────────────────┐
│              Orchestrator Agent              │
│         (intent detection, routing)         │
└───┬──────────┬──────────┬───────────────────┘
    │          │          │
┌───▼───┐ ┌───▼────┐ ┌───▼──────┐
│Draft  │ │Research│ │Knowledge │  ← Specialist agents
│Agent  │ │Agent   │ │Agent     │
└───┬───┘ └───┬────┘ └───┬──────┘
    │         │           │
┌───▼─────────▼───────────▼──────┐
│     Shared RAG / Grounding     │
│   (Vertex AI Search, GCS)      │
└────────────────────────────────┘
```

## Agent Pattern Structure

Each agent follows a standard layout:

```
agents/<agent_name>/
├── __init__.py
├── config.yaml       # Agent-specific settings
├── handler.py        # BaseAgent subclass
├── prompts.py        # Prompt templates
├── rag_config.py     # RAG data source configuration
└── tests/
    └── test_handler.py
```

See [agent_patterns.md](agent_patterns.md) for detailed conventions.

## Data Flow

1. **Request** arrives at the FastAPI gateway.
2. **Orchestrator** classifies intent and selects a specialist agent.
3. **Specialist agent** retrieves relevant context via RAG grounding.
4. **Vertex AI** generates a grounded response.
5. **Response** is returned through the gateway to the client.

## Configuration Hierarchy

```
.env                          # Environment secrets (never committed)
shared/config/base_config.py  # Framework defaults
agents/<name>/config.yaml     # Agent-specific overrides
```

Settings are resolved bottom-up: agent config overrides base config, which overrides environment defaults.
