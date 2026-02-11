# Agent Patterns

Standard conventions for creating and organizing agents in DailyAgentGarden.

## Folder Structure

Every agent must follow this layout:

```
agents/<agent_name>/
├── __init__.py        # Env setup + exports agent instance
├── agent.py           # ADK Agent/LlmAgent definition with tools
├── prompt.py          # Instruction prompt constant
├── config.yaml        # Agent metadata (model, temperature, tools)
└── tests/
    ├── __init__.py
    └── test_agent.py
```

### File Responsibilities

| File | Purpose |
|---|---|
| `__init__.py` | Loads `.env`, sets `GOOGLE_GENAI_USE_VERTEXAI`, re-exports the agent instance |
| `agent.py` | Defines the ADK `Agent` or `LlmAgent` with model, instruction, tools, and `output_key` |
| `prompt.py` | System instruction as a module-level constant (e.g., `KNOWLEDGE_AGENT_INSTRUCTION`) |
| `config.yaml` | Agent metadata: name, model, temperature, max tokens, tool list, output_key |
| `tests/` | Structural tests verifying agent name, tool count, prompt content, exports |

## Naming Conventions

- **Directory names**: `snake_case` (e.g., `drafting_agent`, `knowledge_agent`)
- **Agent instance**: `snake_case` matching the directory (e.g., `knowledge_agent`, `drafting_agent`)
- **Agent name string**: Same as directory name, passed to `name=` parameter
- **Prompt constant**: `UPPER_SNAKE_CASE` (e.g., `KNOWLEDGE_AGENT_INSTRUCTION`)
- **Test files**: `test_agent.py`

## Using Google ADK Agent

All specialist agents use `google.adk.agents.Agent` directly:

```python
from google.adk.agents import Agent
from google.adk.tools.retrieval.vertex_ai_rag_retrieval import VertexAiRagRetrieval
from vertexai.preview import rag

from .prompt import MY_AGENT_INSTRUCTION

search_tool = VertexAiRagRetrieval(
    name="search_my_corpus",
    description="Search for relevant documents.",
    rag_resources=[rag.RagResource(rag_corpus=os.environ.get("MY_RAG_CORPUS", ""))],
    similarity_top_k=10,
    vector_distance_threshold=0.6,
)

my_agent = Agent(
    model="gemini-2.0-flash",
    name="my_agent",
    description="What this agent does.",
    instruction=MY_AGENT_INSTRUCTION,
    output_key="my_output",
    tools=[search_tool],
)
```

### Key Parameters

| Parameter | Purpose |
|---|---|
| `model` | Gemini model ID (e.g., `gemini-2.0-flash`) |
| `name` | Unique agent identifier, matches directory name |
| `description` | Used by `AgentTool` to help the orchestrator decide when to invoke |
| `instruction` | System prompt from `prompt.py` |
| `output_key` | Key under which the agent's output is stored in session state |
| `tools` | List of ADK tools (`VertexAiRagRetrieval`, `google_search`, etc.) |

## Using LlmAgent for Orchestration

The orchestrator uses `LlmAgent` with `AgentTool` wrappers:

```python
from google.adk.agents import LlmAgent
from google.adk.tools.agent_tool import AgentTool

orchestrator = LlmAgent(
    name="orchestrator",
    model="gemini-2.0-flash",
    description="Routes queries to specialist agents.",
    instruction=ORCHESTRATOR_INSTRUCTION,
    tools=[
        AgentTool(agent=knowledge_agent),
        AgentTool(agent=drafting_agent),
        AgentTool(agent=research_agent),
    ],
)
```

## Package __init__.py Pattern

Every agent package follows this pattern:

```python
import os
from dotenv import load_dotenv

load_dotenv()
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "TRUE")

from .agent import my_agent  # noqa: E402
__all__ = ["my_agent"]
```

## config.yaml Schema

```yaml
agent_name: research_agent
model: gemini-2.0-flash
temperature: 0.3
max_output_tokens: 2048
description: Conducts legal research using web search and internal corpus
type: adk_agent
tools:
  - google_search
  - search_research_corpus (VertexAiRagRetrieval)
output_key: research_results
```

## Prompt Management

Keep prompts in `prompt.py` as module-level constants:

```python
RESEARCH_AGENT_INSTRUCTION = """
You are a Legal Research Assistant...

## Workflow
1. Analyze the request
2. Search internal corpus
3. Search the web
4. Synthesize findings
"""
```

## Testing

Each agent's `tests/` directory should include tests for:

- **Structure**: Agent name, model, output_key, description
- **Tools**: Correct tool count and tool names
- **Prompt**: Contains required keywords, references tool names, has structured sections
- **Exports**: Package `__init__.py` correctly exports the agent instance

Use the shared `adk_env` fixture from `tests/conftest.py` for environment setup.

## Legacy: BaseAgent ABC

The `shared/base_agent.py` file defines a `BaseAgent` ABC that is retained for backward compatibility but is **not used** by the current ADK-native agents. The ADK `Agent`/`LlmAgent` classes handle model invocation, tool execution, session management, and event streaming natively.
