# Google ADK Patterns

Code patterns for working with Google Vertex AI in DailyAgentGarden.

## Agent Initialization

Initialize the Vertex AI SDK once at startup:

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

Call this during application startup (e.g., in a FastAPI lifespan handler):

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_vertex_ai()
    yield


app = FastAPI(lifespan=lifespan)
```

## Generative Model Usage

### Basic Generation

```python
from vertexai.generative_models import GenerativeModel, GenerationConfig

model = GenerativeModel(
    model_name="gemini-2.0-flash",
    generation_config=GenerationConfig(
        temperature=0.3,
        max_output_tokens=2048,
        top_k=40,
        top_p=0.95,
    ),
    system_instruction="You are a helpful research assistant.",
)

response = model.generate_content("Summarize the key findings.")
print(response.text)
```

### Async Generation

```python
response = await model.generate_content_async("Summarize the key findings.")
```

## RAG Grounding Configuration

### Using Vertex AI Search as a Grounding Source

```python
from vertexai.generative_models import GenerativeModel, Tool
from vertexai.preview.generative_models import grounding

# Create a grounding tool backed by a Vertex AI Search datastore
grounding_tool = Tool.from_retrieval(
    retrieval=grounding.Retrieval(
        source=grounding.VertexAISearch(
            datastore=f"projects/{PROJECT_ID}/locations/global"
                      f"/collections/default_collection"
                      f"/dataStores/{DATASTORE_ID}",
        ),
    )
)

model = GenerativeModel(
    model_name="gemini-2.0-flash",
    tools=[grounding_tool],
)

response = model.generate_content("What is our refund policy?")
```

### Per-Agent RAG Configuration

Each agent defines its RAG sources in `rag_config.py`:

```python
from dataclasses import dataclass


@dataclass
class RAGConfig:
    datastore_id: str
    collection: str = "default_collection"
    similarity_top_k: int = 10
    vector_distance_threshold: float = 0.7


# Agent-specific configuration
DEFAULT_CONFIG = RAGConfig(
    datastore_id="knowledge-base-v2",
    similarity_top_k=5,
)
```

## Tool Definition Patterns (Function Calling)

### Declaring Tools

Define tools as Python functions with type annotations. Vertex AI infers the schema:

```python
from vertexai.generative_models import FunctionDeclaration, Tool

search_func = FunctionDeclaration(
    name="search_documents",
    description="Search internal documents for relevant information.",
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query.",
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results to return.",
            },
        },
        "required": ["query"],
    },
)

create_draft_func = FunctionDeclaration(
    name="create_draft",
    description="Create a draft document with the given content.",
    parameters={
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Document title.",
            },
            "body": {
                "type": "string",
                "description": "Document body content.",
            },
            "format": {
                "type": "string",
                "enum": ["markdown", "plain", "html"],
                "description": "Output format.",
            },
        },
        "required": ["title", "body"],
    },
)

tools = Tool(function_declarations=[search_func, create_draft_func])
```

### Handling Function Calls

```python
from vertexai.generative_models import GenerativeModel, Part

model = GenerativeModel(
    model_name="gemini-2.0-flash",
    tools=[tools],
)

response = model.generate_content("Find documents about Q4 revenue.")

# Check if the model wants to call a function
for candidate in response.candidates:
    for part in candidate.content.parts:
        if fn := part.function_call:
            name = fn.name
            args = dict(fn.args)

            # Execute the function
            result = execute_tool(name, args)

            # Send the result back to the model
            follow_up = model.generate_content(
                [
                    Part.from_text("Find documents about Q4 revenue."),
                    response.candidates[0].content,
                    Part.from_function_response(
                        name=name,
                        response={"result": result},
                    ),
                ]
            )
```

### Mapping BaseAgent Tools to Vertex AI

Convert `ToolDefinition` objects from `get_tools()` into Vertex AI declarations:

```python
from shared.base_agent import ToolDefinition
from vertexai.generative_models import FunctionDeclaration, Tool


def to_vertex_tools(definitions: list[ToolDefinition]) -> Tool:
    """Convert BaseAgent tool definitions to a Vertex AI Tool."""
    declarations = [
        FunctionDeclaration(
            name=td.name,
            description=td.description,
            parameters=td.parameters,
        )
        for td in definitions
    ]
    return Tool(function_declarations=declarations)
```

## Chat Sessions (Multi-Turn)

```python
model = GenerativeModel(model_name="gemini-2.0-flash")
chat = model.start_chat()

response1 = chat.send_message("What are the key metrics for Q4?")
print(response1.text)

response2 = chat.send_message("Compare those with Q3.")
print(response2.text)
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
