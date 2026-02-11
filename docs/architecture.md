# Architecture

## Purpose

DailyAgentGarden is a reusable multi-agent framework designed for building and deploying client-specific AI agents. It provides shared infrastructure so that each new client project inherits production-ready tooling — RAG pipelines, observability, configuration management — without duplicating effort.

## Tech Stack

| Layer | Technology |
|---|---|
| **AI / LLM** | Google Vertex AI ADK (Gemini models) |
| **Agent Framework** | Google ADK `Agent` / `LlmAgent` / `AgentTool` |
| **Backend API** | FastAPI + Uvicorn |
| **Frontend** | React |
| **Infrastructure** | Google Cloud Run, Cloud Storage, Vertex AI RAG Engine |
| **Configuration** | Pydantic Settings + python-dotenv |
| **Testing** | pytest + pytest-asyncio |

## Core Principles

### Modularity
Every agent lives in its own directory with a self-contained configuration, agent definition, prompts, and tests. Agents communicate only through the orchestrator via `AgentTool` — never directly with each other.

### Native ADK Composition
Agents are built using Google ADK's `Agent` and `LlmAgent` classes directly, enabling use of `AgentTool` for sub-agent orchestration. This provides built-in model invocation, tool execution, session management, and event streaming without custom wrappers.

### Shared RAG
Each agent has its own RAG corpus configured via environment variables (`KNOWLEDGE_RAG_CORPUS`, `DRAFTING_RAG_CORPUS`, `RESEARCH_RAG_CORPUS`), allowing each agent to ground responses in different data sources using `VertexAiRagRetrieval`.

### Client-Specific Configs
Each client deployment gets its own environment configuration. The base framework provides sensible defaults; client configs override only what differs.

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
│         Orchestrator (LlmAgent)             │
│    Prompt-driven intent routing             │
│    tools=[AgentTool x 3]                    │
└───┬──────────┬──────────┬───────────────────┘
    │          │          │
┌───▼───┐ ┌───▼────┐ ┌───▼──────┐
│Knowl. │ │Draft   │ │Research  │  ← Specialist agents (ADK Agent)
│Agent  │ │Agent   │ │Agent     │
│RAG    │ │RAG     │ │Search+RAG│
└───────┘ └────────┘ └──────────┘
```

## Agent Composition Pattern

The orchestrator uses `AgentTool` wrappers to delegate to sub-agents:

```python
from google.adk.agents import LlmAgent
from google.adk.tools.agent_tool import AgentTool

orchestrator = LlmAgent(
    name="orchestrator",
    model="gemini-2.0-flash",
    instruction=ORCHESTRATOR_INSTRUCTION,
    tools=[
        AgentTool(agent=knowledge_agent),
        AgentTool(agent=drafting_agent),
        AgentTool(agent=research_agent),
    ],
)
```

Each sub-agent defines its own tools (RAG retrieval, web search) and `output_key` for structured output passing.

## Agent Pattern Structure

Each agent follows a standard layout:

```
agents/<agent_name>/
├── __init__.py       # Env setup + exports agent instance
├── agent.py          # ADK Agent definition with tools
├── prompt.py         # Instruction prompt constant
├── config.yaml       # Agent metadata
└── tests/
    └── test_agent.py
```

See [agent_patterns.md](agent_patterns.md) for detailed conventions.

## Data Flow

1. **Request** arrives at the FastAPI gateway (or `adk web` / `adk run`).
2. **Orchestrator** classifies intent via its prompt and selects specialist agent(s) via `AgentTool`.
3. **Specialist agent** retrieves relevant context via `VertexAiRagRetrieval` and/or `google_search`.
4. **Vertex AI** generates a grounded response.
5. **Response** is returned through the orchestrator to the client.

## Configuration Hierarchy

```
.env                          # Environment secrets (never committed)
shared/config/base_config.py  # Framework defaults (Settings class)
agents/<name>/config.yaml     # Agent metadata
```

Settings are resolved bottom-up: agent config overrides base config, which overrides environment defaults.
