"""Kaos Group GHL Workflow Assistant — single LlmAgent with RAG retrieval."""

from google.adk.agents import LlmAgent

from baseLawAgent.shared_libraries.rag_tools import create_rag_retrieval_tool

from .config import GEMINI_MODEL
from .prompt import SYSTEM_INSTRUCTION

search_kaos_workflows = create_rag_retrieval_tool(
    name="search_kaos_workflows",
    description=(
        "Search Kaos Group's GHL workflow documentation for process steps, "
        "pipeline stages, custom fields, email/SMS templates, and automation details."
    ),
    corpus_env_var="KAOS_RAG_CORPUS",
    similarity_top_k=10,
    vector_distance_threshold=0.5,
)

root_agent = LlmAgent(
    name="kaos_workflow_agent",
    model=GEMINI_MODEL,
    description=(
        "Internal operations assistant for Kaos Group. Answers process "
        "questions about GHL workflows using RAG retrieval."
    ),
    instruction=SYSTEM_INSTRUCTION,
    tools=[search_kaos_workflows],
)
