"""Tests for the Knowledge Agent structure, tools, and prompt."""

from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def _set_env(monkeypatch):
    """Set required environment variables for agent import."""
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")
    monkeypatch.setenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    monkeypatch.setenv("GOOGLE_GENAI_USE_VERTEXAI", "TRUE")
    monkeypatch.setenv("KNOWLEDGE_RAG_CORPUS", "projects/test/locations/us-central1/ragCorpora/123")


class TestKnowledgeAgentStructure:
    """Verify the knowledge agent is correctly configured."""

    def test_agent_name(self):
        from agents.knowledge_agent.agent import knowledge_agent

        assert knowledge_agent.name == "knowledge_agent"

    def test_agent_model(self):
        from agents.knowledge_agent.agent import knowledge_agent

        assert knowledge_agent.model == "gemini-2.0-flash"

    def test_agent_has_output_key(self):
        from agents.knowledge_agent.agent import knowledge_agent

        assert knowledge_agent.output_key == "knowledge_results"

    def test_agent_has_one_tool(self):
        from agents.knowledge_agent.agent import knowledge_agent

        assert len(knowledge_agent.tools) == 1

    def test_tool_is_rag_retrieval(self):
        from agents.knowledge_agent.agent import search_firm_knowledge_base

        assert search_firm_knowledge_base.name == "search_firm_knowledge_base"

    def test_agent_description_set(self):
        from agents.knowledge_agent.agent import knowledge_agent

        assert knowledge_agent.description
        assert "knowledge base" in knowledge_agent.description


class TestKnowledgeAgentPrompt:
    """Verify the prompt contains required instruction elements."""

    def test_prompt_mentions_knowledge_base(self):
        from agents.knowledge_agent.prompt import KNOWLEDGE_AGENT_INSTRUCTION

        assert "knowledge base" in KNOWLEDGE_AGENT_INSTRUCTION.lower()

    def test_prompt_mentions_citation_format(self):
        from agents.knowledge_agent.prompt import KNOWLEDGE_AGENT_INSTRUCTION

        assert "References:" in KNOWLEDGE_AGENT_INSTRUCTION

    def test_prompt_mentions_tool_name(self):
        from agents.knowledge_agent.prompt import KNOWLEDGE_AGENT_INSTRUCTION

        assert "search_firm_knowledge_base" in KNOWLEDGE_AGENT_INSTRUCTION

    def test_prompt_mentions_retrieval(self):
        from agents.knowledge_agent.prompt import KNOWLEDGE_AGENT_INSTRUCTION

        assert "retriev" in KNOWLEDGE_AGENT_INSTRUCTION.lower()


class TestKnowledgeAgentExports:
    """Verify the package exports correctly."""

    def test_package_exports_agent(self):
        from agents.knowledge_agent import knowledge_agent

        assert knowledge_agent.name == "knowledge_agent"
