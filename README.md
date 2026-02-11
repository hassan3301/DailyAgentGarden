# DailyAgentGarden

Reusable multi-agent framework for building client-specific AI agents using Google Vertex AI ADK, FastAPI, and React.

## Project Overview

DailyAgentGarden provides a modular foundation for deploying specialized AI agents that share common infrastructure — RAG pipelines, configuration management, and a standardized agent interface — while remaining independently configurable per client.

**Core agents:**

| Agent | Purpose |
|---|---|
| **Orchestrator** | Routes queries to the appropriate specialist agent |
| **Drafting Agent** | Generates and refines legal documents using template RAG |
| **Research Agent** | Conducts legal research via web search and internal corpus |
| **Knowledge Agent** | Searches the firm's internal knowledge base for precedents and clauses |

## Quick Start

```bash
# Clone and set up
git clone <repo-url> && cd DailyAgentGarden
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# Install dependencies
pip install -r requirements.txt
pip install -e ".[dev]"

# Configure environment
cp .env.example .env
# Edit .env with your GCP project details and RAG corpus IDs

# Run structural tests
pytest

# Run with ADK web UI (requires GCP credentials)
adk web agents

# Run with ADK CLI
adk run agents
```

## Architecture

The system uses Google ADK's native `Agent` / `LlmAgent` classes with `AgentTool` for sub-agent composition:

```
User Query
    │
    ▼
┌──────────────────────────────────┐
│  Orchestrator (LlmAgent)         │
│  - Prompt-driven intent routing  │
│  - Multi-agent invocation        │
│  tools=[                         │
│    AgentTool(knowledge_agent),   │
│    AgentTool(drafting_agent),    │
│    AgentTool(research_agent),    │
│  ]                               │
└──┬──────────┬──────────┬─────────┘
   │          │          │
   ▼          ▼          ▼
Knowledge   Drafting   Research
Agent       Agent      Agent
(Agent)     (Agent)    (Agent)
RAG tool    RAG tool   google_search + RAG tool
```

## Creating a New Agent

1. Create a directory under `agents/`:

```
agents/my_agent/
├── __init__.py      # Env setup + exports agent instance
├── agent.py         # ADK Agent definition with tools
├── prompt.py        # Instruction prompt
├── config.yaml      # Agent metadata
└── tests/
    └── test_agent.py
```

2. Define the agent using Google ADK:

```python
# agents/my_agent/agent.py
from google.adk.agents import Agent
from .prompt import MY_AGENT_INSTRUCTION

my_agent = Agent(
    model="gemini-2.0-flash",
    name="my_agent",
    description="What this agent does",
    instruction=MY_AGENT_INSTRUCTION,
    output_key="my_output",
    tools=[...],
)
```

3. Export from `__init__.py`:

```python
# agents/my_agent/__init__.py
import os
from dotenv import load_dotenv

load_dotenv()
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "TRUE")

from .agent import my_agent
__all__ = ["my_agent"]
```

4. Wire it into the orchestrator via `AgentTool`:

```python
from google.adk.tools.agent_tool import AgentTool
from agents.my_agent.agent import my_agent

# Add to orchestrator tools list
AgentTool(agent=my_agent)
```

See [docs/agent_patterns.md](docs/agent_patterns.md) for full conventions.

## Deployment

1. Authenticate with GCP: `gcloud auth application-default login`
2. Set your project: `gcloud config set project <PROJECT_ID>`
3. Build and deploy:

```bash
# Build container
docker build -t daily-agent-garden .

# Deploy to Cloud Run
gcloud run deploy daily-agent-garden \
    --image daily-agent-garden \
    --region us-central1 \
    --allow-unauthenticated
```

## Documentation

- [Architecture](docs/architecture.md) — system design and ADK agent composition
- [Agent Patterns](docs/agent_patterns.md) — folder structure and conventions
- [Google ADK Patterns](docs/google_adk_patterns.md) — ADK Agent, AgentTool, and InMemoryRunner patterns
