"""Drafting Agent — generates legal documents using template RAG retrieval."""

import os

from google.adk.agents import Agent

from baseLawAgent.shared_libraries.rag_tools import create_rag_retrieval_tool

from .prompt import DRAFTING_AGENT_INSTRUCTION

MODEL = os.environ.get("VERTEX_AI_MODEL", "gemini-2.0-flash")

search_drafting_templates = create_rag_retrieval_tool(
    name="search_drafting_templates",
    description=(
        "Search the firm's drafting template library for standard clauses, "
        "contract templates, document formats, and prior drafting examples."
    ),
    corpus_env_var="DRAFTING_RAG_CORPUS",
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
