# Google ADK Patterns

Code patterns for working with Google ADK and Vertex AI in DailyAgentGarden.

## ADK Agent Definition

Define agents using `google.adk.agents.Agent`:

```python
from google.adk.agents import Agent

my_agent = Agent(
    model="gemini-2.0-flash",
    name="my_agent",
    description="Brief description for AgentTool routing",
    instruction="System prompt with workflow and guidelines",
    output_key="my_output",
    tools=[...],
)
```

### Agent vs LlmAgent

- **`Agent`**: Standard agent with tools. Use for specialist agents (knowledge, drafting, research).
- **`LlmAgent`**: Equivalent to `Agent` (they are aliases in ADK). Use for the orchestrator to make the intent clear.

## AgentTool for Sub-Agent Composition

Wrap sub-agents as tools for the orchestrator:

```python
from google.adk.agents import LlmAgent
from google.adk.tools.agent_tool import AgentTool

from agents.knowledge_agent.agent import knowledge_agent
from agents.drafting_agent.agent import drafting_agent

orchestrator = LlmAgent(
    name="orchestrator",
    model="gemini-2.0-flash",
    instruction=ORCHESTRATOR_INSTRUCTION,
    tools=[
        AgentTool(agent=knowledge_agent),
        AgentTool(agent=drafting_agent),
    ],
)
```

`AgentTool` uses the sub-agent's `name` and `description` to help the orchestrator's LLM decide when to invoke each sub-agent.

## output_key for Structured State

Use `output_key` to store agent output in the session state:

```python
knowledge_agent = Agent(
    model="gemini-2.0-flash",
    name="knowledge_agent",
    output_key="knowledge_results",  # Stored in session state
    ...
)
```

When the orchestrator invokes this agent via `AgentTool`, the output is stored under `knowledge_results` in the session state and can be referenced by subsequent agent invocations.

## VertexAiRagRetrieval Tool

Use ADK's built-in RAG retrieval tool:

```python
import os
from google.adk.tools.retrieval.vertex_ai_rag_retrieval import VertexAiRagRetrieval
from vertexai.preview import rag

search_tool = VertexAiRagRetrieval(
    name="search_firm_knowledge_base",
    description="Search the firm's knowledge base for relevant documents.",
    rag_resources=[
        rag.RagResource(
            rag_corpus=os.environ.get("KNOWLEDGE_RAG_CORPUS", ""),
        )
    ],
    similarity_top_k=10,
    vector_distance_threshold=0.6,
)
```

### Configuration

| Parameter | Description |
|---|---|
| `name` | Tool name referenced in the agent's prompt |
| `description` | Helps the LLM decide when to use this tool |
| `rag_resources` | List of `RagResource` with corpus resource names |
| `similarity_top_k` | Number of top results to retrieve |
| `vector_distance_threshold` | Minimum similarity score (0.0–1.0) |

## google_search Tool

Use ADK's built-in Google Search tool:

```python
from google.adk.tools import google_search

research_agent = Agent(
    model="gemini-2.0-flash",
    name="research_agent",
    tools=[google_search, search_rag_tool],
)
```

## InMemoryRunner for Testing

Use `InMemoryRunner` for programmatic agent execution:

```python
from google.adk.runners import InMemoryRunner
from google.genai import types

from agents import root_agent

runner = InMemoryRunner(agent=root_agent, app_name="legal_assistant")

# Create a session
session = await runner.session_service.create_session(
    app_name="legal_assistant",
    user_id="test-user",
)

# Send a message
content = types.Content(
    role="user",
    parts=[types.Part.from_text("Research non-compete enforceability in California")],
)

async for event in runner.run_async(
    user_id="test-user",
    session_id=session.id,
    new_message=content,
):
    if event.content and event.content.parts:
        print(event.content.parts[0].text)
```

## Environment Setup

### Required Environment Variables

```bash
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_GENAI_USE_VERTEXAI=TRUE

# RAG corpus resource names
KNOWLEDGE_RAG_CORPUS=projects/{project}/locations/{location}/ragCorpora/{id}
DRAFTING_RAG_CORPUS=projects/{project}/locations/{location}/ragCorpora/{id}
RESEARCH_RAG_CORPUS=projects/{project}/locations/{location}/ragCorpora/{id}
```

### Package __init__.py Pattern

Each agent package loads env and sets the Vertex AI backend:

```python
import os
from dotenv import load_dotenv

load_dotenv()
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "TRUE")

from .agent import my_agent  # noqa: E402
__all__ = ["my_agent"]
```

## Agent Initialization (Legacy)

For direct Vertex AI SDK usage outside of ADK agents:

```python
import vertexai
from google.cloud import aiplatform
from shared.config.base_config import get_settings


def init_vertex_ai() -> None:
    """Initialize Vertex AI SDK with project settings."""
    settings = get_settings()
    vertexai.init(
        project=settings.google_cloud_project,
        location=settings.google_cloud_location,
    )
    aiplatform.init(
        project=settings.google_cloud_project,
        location=settings.google_cloud_location,
    )
```

## Error Handling

```python
from google.api_core import exceptions, retry

@retry.Retry(
    predicate=retry.if_exception_type(
        exceptions.ResourceExhausted,
        exceptions.ServiceUnavailable,
    ),
    initial=1.0,
    maximum=60.0,
    multiplier=2.0,
)
async def generate_with_retry(model, prompt: str) -> str:
    response = await model.generate_content_async(prompt)
    return response.text
```

## Running with ADK CLI

```bash
# Web UI
adk web agents

# CLI mode
adk run agents

# The entry point is agents/__init__.py which exports root_agent
```
