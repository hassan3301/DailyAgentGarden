# DailyAgentGarden

Reusable multi-agent framework for building client-specific AI agents using Google Vertex AI ADK, FastAPI, and React.

## Project Overview

DailyAgentGarden provides a modular foundation for deploying specialized AI agents that share common infrastructure — RAG pipelines, configuration management, and a standardized agent interface — while remaining independently configurable per client.

**Core agents:**

| Agent | Purpose |
|---|---|
| **Orchestrator** | Routes queries to the appropriate specialist agent |
| **Drafting Agent** | Generates and refines written content |
| **Research Agent** | Searches and synthesizes information from multiple sources |
| **Knowledge Agent** | Answers questions grounded in a client's knowledge base |

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
# Edit .env with your GCP project details

# Run tests
pytest

# Start the API server
uvicorn shared.api:app --reload
```

## Creating a New Agent

1. Create a directory under `agents/`:

```
agents/my_agent/
├── __init__.py
├── config.yaml      # Agent-specific settings
├── handler.py       # Agent implementation (extends BaseAgent)
├── prompts.py       # Prompt templates
├── rag_config.py    # RAG grounding configuration
└── tests/
    └── test_handler.py
```

2. Implement the agent by subclassing `BaseAgent`:

```python
from shared.base_agent import AgentContext, AgentResponse, BaseAgent, ToolDefinition


class MyAgent(BaseAgent):
    def __init__(self):
        super().__init__(agent_name="my_agent")

    async def process_query(self, query: str, context: AgentContext) -> AgentResponse:
        # Your agent logic here
        return AgentResponse(content="response")

    def get_tools(self) -> list[ToolDefinition]:
        return []
```

3. Register the agent in the orchestrator's routing config.

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

- [Architecture](docs/architecture.md) — system design and principles
- [Agent Patterns](docs/agent_patterns.md) — folder structure and conventions
- [Google ADK Patterns](docs/google_adk_patterns.md) — Vertex AI code examples
