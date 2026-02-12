"""Research Agent — conducts legal research via web search and RAG retrieval."""

import os

from google.adk.agents import Agent
from google.adk.tools import google_search

from baseLawAgent.shared_libraries.rag_tools import create_rag_retrieval_tool

from .prompt import RESEARCH_AGENT_INSTRUCTION

MODEL = os.environ.get("VERTEX_AI_MODEL", "gemini-2.0-flash")

search_research_corpus = create_rag_retrieval_tool(
    name="search_research_corpus",
    description=(
        "Search the firm's internal research corpus for prior research memos, "
        "case analyses, legal briefs, and compiled legal research."
    ),
    corpus_env_var="RESEARCH_RAG_CORPUS",
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
