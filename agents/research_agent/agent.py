"""Research Agent — conducts legal research via web search and RAG retrieval."""

import os

from google.adk.agents import Agent
from google.adk.tools import google_search
from google.adk.tools.retrieval.vertex_ai_rag_retrieval import (
    VertexAiRagRetrieval,
)
from vertexai.preview import rag

from .prompt import RESEARCH_AGENT_INSTRUCTION

MODEL = "gemini-2.0-flash"

search_research_corpus = VertexAiRagRetrieval(
    name="search_research_corpus",
    description=(
        "Search the firm's internal research corpus for prior research memos, "
        "case analyses, legal briefs, and compiled legal research."
    ),
    rag_resources=[
        rag.RagResource(
            rag_corpus=os.environ.get("RESEARCH_RAG_CORPUS", ""),
        )
    ],
    similarity_top_k=10,
    vector_distance_threshold=0.6,
)

research_agent = Agent(
    model=MODEL,
    name="research_agent",
    description=(
        "Conducts legal research using web search and the firm's internal "
        "research corpus to provide comprehensive, well-sourced analysis."
    ),
    instruction=RESEARCH_AGENT_INSTRUCTION,
    output_key="research_results",
    tools=[google_search, search_research_corpus],
)
