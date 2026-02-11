"""Knowledge Agent — searches the firm's internal knowledge base using RAG."""

import os

from google.adk.agents import Agent
from google.adk.tools.retrieval.vertex_ai_rag_retrieval import (
    VertexAiRagRetrieval,
)
from vertexai.preview import rag

from .prompt import KNOWLEDGE_AGENT_INSTRUCTION

MODEL = "gemini-2.0-flash"

search_firm_knowledge_base = VertexAiRagRetrieval(
    name="search_firm_knowledge_base",
    description=(
        "Search the firm's internal knowledge base for past work product, "
        "legal precedents, clause libraries, templates, and internal memoranda."
    ),
    rag_resources=[
        rag.RagResource(
            rag_corpus=os.environ.get("KNOWLEDGE_RAG_CORPUS", ""),
        )
    ],
    similarity_top_k=10,
    vector_distance_threshold=0.6,
)

knowledge_agent = Agent(
    model=MODEL,
    name="knowledge_agent",
    description=(
        "Searches the firm's internal knowledge base for past work product, "
        "legal precedents, clause libraries, and internal memoranda."
    ),
    instruction=KNOWLEDGE_AGENT_INSTRUCTION,
    output_key="knowledge_results",
    tools=[search_firm_knowledge_base],
)
