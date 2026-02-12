"""Shared RAG tool factory for baseLawAgent sub-agents."""

import os

from google.adk.tools.retrieval.vertex_ai_rag_retrieval import (
    VertexAiRagRetrieval,
)
from vertexai.preview import rag


def create_rag_retrieval_tool(
    name: str,
    description: str,
    corpus_env_var: str,
    similarity_top_k: int = 10,
    vector_distance_threshold: float = 0.6,
) -> VertexAiRagRetrieval:
    """Create a configured VertexAiRagRetrieval tool.

    Args:
        name: Tool name (e.g. "search_firm_knowledge_base").
        description: Human-readable description of what the tool searches.
        corpus_env_var: Name of the environment variable holding the RAG corpus
            resource name (e.g. "KNOWLEDGE_RAG_CORPUS").
        similarity_top_k: Number of top results to return.
        vector_distance_threshold: Minimum similarity score for results.

    Returns:
        A configured VertexAiRagRetrieval tool instance.
    """
    return VertexAiRagRetrieval(
        name=name,
        description=description,
        rag_resources=[
            rag.RagResource(
                rag_corpus=os.environ.get(corpus_env_var, ""),
            )
        ],
        similarity_top_k=similarity_top_k,
        vector_distance_threshold=vector_distance_threshold,
    )
