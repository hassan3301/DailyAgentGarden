# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run the agent locally with ADK web UI (requires GCP auth)
adk web baseLawAgent

# Run with ADK CLI
adk run baseLawAgent

# Run all tests
pytest

# Run a single agent's tests
pytest baseLawAgent/knowledge_agent/tests/test_agent.py

# Run a single test class or method
pytest baseLawAgent/tests/test_agent.py::TestOrchestratorStructure::test_agent_name

# Install dependencies
pip install -r requirements.txt

# Set up RAG corpora in Vertex AI (requires GCP auth)
python -m baseLawAgent.shared_libraries.prepare_corpus_and_data

# Authenticate with GCP
gcloud auth application-default login
```

## Architecture

This is a legal AI multi-agent system built on **Google ADK** (Agent Development Kit) with **Vertex AI**.

### Orchestrator Pattern

`baseLawAgent/agent.py` defines the `root_agent` (an `LlmAgent`) that routes queries to three specialist sub-agents via `AgentTool` wrappers. The orchestrator never answers legal questions directly — it delegates based on intent keywords in its prompt (`baseLawAgent/prompt.py`).

### Sub-Agents

Each sub-agent lives in its own package (`knowledge_agent/`, `drafting_agent/`, `research_agent/`) with the same structure: `agent.py` (definition + tools), `prompt.py` (instructions), `config.yaml` (metadata), `tests/`.

- **knowledge_agent** — RAG search over firm knowledge base. Output key: `knowledge_results`
- **drafting_agent** — RAG search over templates, then generates legal documents. Output key: `draft_document`
- **research_agent** — `google_search` + RAG search over research corpus. Output key: `research_results`

### Centralized Environment Setup

`baseLawAgent/__init__.py` is the single place that calls `load_dotenv()`, derives GCP project from `google.auth.default()`, and sets defaults for `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`, and `GOOGLE_GENAI_USE_VERTEXAI`. Sub-agent `__init__.py` files only re-export their agent — no env setup.

### RAG Tool Factory

`baseLawAgent/shared_libraries/rag_tools.py` provides `create_rag_retrieval_tool()` — a factory that all three sub-agents use instead of constructing `VertexAiRagRetrieval` directly. It takes a `corpus_env_var` string (e.g. `"KNOWLEDGE_RAG_CORPUS"`) and reads the corpus resource name from that env var at construction time.

### Key Environment Variables (in `.env`)

- `GOOGLE_CLOUD_PROJECT` — GCP project ID
- `VERTEX_AI_MODEL` — model name, defaults to `gemini-2.0-flash`
- `KNOWLEDGE_RAG_CORPUS`, `DRAFTING_RAG_CORPUS`, `RESEARCH_RAG_CORPUS` — Vertex AI RAG corpus resource names (format: `projects/{project}/locations/{location}/ragCorpora/{id}`)

### Conventions

- The model is always read from `os.environ.get("VERTEX_AI_MODEL", "gemini-2.0-flash")`, never hardcoded.
- ADK expects `root_agent` exported from the top-level package `__init__.py`.
- Tests use `monkeypatch.setenv` fixtures to set env vars — they test agent structure/wiring, not live LLM calls.
- Prompt instructions live in `prompt.py` files, separate from agent definitions.

## Reference Agents

The `references/adk-samples/` directory contains Google's official ADK sample agents (Python, Go, Java, TypeScript). Use these as reference for ADK patterns — especially `references/adk-samples/python/agents/RAG/` for RAG patterns.
