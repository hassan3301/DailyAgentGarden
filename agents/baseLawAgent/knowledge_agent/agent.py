"""Knowledge Agent — searches the firm's internal knowledge base using RAG."""

import os

from google.adk.agents import Agent

from baseLawAgent.shared_libraries.rag_tools import create_rag_retrieval_tool

from .prompt import KNOWLEDGE_AGENT_INSTRUCTION

MODEL = os.environ.get("VERTEX_AI_MODEL", "gemini-2.0-flash")

search_firm_knowledge_base = create_rag_retrieval_tool(
    name="search_firm_knowledge_base",
    description=(
        "Search the firm's internal knowledge base for past work product, "
        "legal precedents, clause libraries, templates, and internal memoranda."
    ),
    corpus_env_var="KNOWLEDGE_RAG_CORPUS",
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
