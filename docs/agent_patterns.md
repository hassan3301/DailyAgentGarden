# Agent Patterns

Standard conventions for creating and organizing agents in DailyAgentGarden.

## Folder Structure

Every agent must follow this layout:

```
agents/<agent_name>/
├── __init__.py        # Exports the agent class
├── config.yaml        # Agent-specific configuration
├── handler.py         # Agent implementation (BaseAgent subclass)
├── prompts.py         # Prompt templates and system instructions
├── rag_config.py      # RAG grounding data source configuration
└── tests/
    ├── __init__.py
    └── test_handler.py
```

### File Responsibilities

| File | Purpose |
|---|---|
| `__init__.py` | Re-exports the handler class for clean imports |
| `config.yaml` | Model parameters, temperature, top-k, max tokens, feature flags |
| `handler.py` | Subclass of `BaseAgent` — implements `process_query` and `get_tools` |
| `prompts.py` | System prompt, few-shot examples, template strings |
| `rag_config.py` | Vertex AI Search datastore IDs, grounding parameters |
| `tests/` | Unit and integration tests specific to this agent |

## Naming Conventions

- **Directory names**: `snake_case` (e.g., `drafting_agent`, `knowledge_agent`)
- **Handler class**: `PascalCase` matching the directory (e.g., `DraftingAgent`, `KnowledgeAgent`)
- **Agent name string**: Same as directory name, passed to `super().__init__(agent_name="...")`
- **Test files**: `test_<module>.py` (e.g., `test_handler.py`)

## Inheriting from BaseAgent

All agents extend `shared.base_agent.BaseAgent`:

```python
from shared.base_agent import (
    AgentContext,
    AgentResponse,
    BaseAgent,
    ToolDefinition,
)


class ResearchAgent(BaseAgent):
    """Searches and synthesizes information from multiple sources."""

    def __init__(self) -> None:
        super().__init__(agent_name="research_agent")

    async def process_query(
        self, query: str, context: AgentContext
    ) -> AgentResponse:
        # 1. Retrieve grounded context via RAG
        # 2. Build prompt from prompts.py templates
        # 3. Call Vertex AI for generation
        # 4. Return structured response
        return AgentResponse(
            content="synthesized answer",
            sources=["https://example.com/doc1"],
        )

    def get_tools(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name="web_search",
                description="Search the web for current information",
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"}
                    },
                    "required": ["query"],
                },
            ),
        ]
```

### Required Methods

| Method | Description |
|---|---|
| `process_query(query, context)` | Core logic — receives the user query and context, returns an `AgentResponse` |
| `get_tools()` | Returns `list[ToolDefinition]` describing tools for Vertex AI function calling |

### Built-in Methods (inherited)

| Method | Description |
|---|---|
| `run(query, context)` | Entry point — wraps `process_query` with timing, logging, and error handling |
| `log_interaction(query, response, duration_ms)` | Structured logging of each interaction |

## config.yaml Schema

```yaml
agent_name: research_agent
model: gemini-2.0-flash
temperature: 0.3
max_output_tokens: 2048
top_k: 40
top_p: 0.95

# Feature flags
enable_grounding: true
enable_citations: true

# Client overrides (optional)
client_overrides:
  acme_corp:
    temperature: 0.1
    max_output_tokens: 4096
```

## Prompt Management

Keep prompts in `prompts.py` as constants or template functions:

```python
SYSTEM_PROMPT = """You are a research assistant. Ground your answers
in the provided sources and cite them explicitly."""


def build_query_prompt(query: str, context_docs: list[str]) -> str:
    docs = "\n---\n".join(context_docs)
    return f"Sources:\n{docs}\n\nQuestion: {query}"
```

## Testing

Each agent's `tests/` directory should include:

- **Unit tests** for `process_query` logic with mocked Vertex AI calls
- **Tool tests** verifying `get_tools` returns valid definitions
- **Prompt tests** ensuring templates render correctly

Use the shared fixtures from `tests/conftest.py` for common setup.
