"""Drafting Agent — generates legal documents using template RAG retrieval."""

import os

from google.adk.agents import Agent
from google.adk.tools.retrieval.vertex_ai_rag_retrieval import (
    VertexAiRagRetrieval,
)
from vertexai.preview import rag

from .prompt import DRAFTING_AGENT_INSTRUCTION

MODEL = "gemini-2.0-flash"

search_drafting_templates = VertexAiRagRetrieval(
    name="search_drafting_templates",
    description=(
        "Search the firm's drafting template library for standard clauses, "
        "contract templates, document formats, and prior drafting examples."
    ),
    rag_resources=[
        rag.RagResource(
            rag_corpus=os.environ.get("DRAFTING_RAG_CORPUS", ""),
        )
    ],
    similarity_top_k=10,
    vector_distance_threshold=0.6,
)

drafting_agent = Agent(
    model=MODEL,
    name="drafting_agent",
    description=(
        "Generates, refines, and reviews legal documents using the firm's "
        "template library and drafting standards."
    ),
    instruction=DRAFTING_AGENT_INSTRUCTION,
    output_key="draft_document",
    tools=[search_drafting_templates],
)
