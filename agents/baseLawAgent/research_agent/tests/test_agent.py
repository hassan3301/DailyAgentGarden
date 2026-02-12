"""Tests for the Research Agent structure, tools, and prompt."""

import pytest


@pytest.fixture(autouse=True)
def _set_env(monkeypatch):
    """Set required environment variables for agent import."""
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")
    monkeypatch.setenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    monkeypatch.setenv("GOOGLE_GENAI_USE_VERTEXAI", "TRUE")
    monkeypatch.setenv("RESEARCH_RAG_CORPUS", "projects/test/locations/us-central1/ragCorpora/789")


class TestResearchAgentStructure:
    """Verify the research agent is correctly configured."""

    def test_agent_name(self):
        from agents.research_agent.agent import research_agent

        assert research_agent.name == "research_agent"

    def test_agent_model(self):
        from agents.research_agent.agent import research_agent

        assert research_agent.model == "gemini-2.0-flash"

    def test_agent_has_output_key(self):
        from agents.research_agent.agent import research_agent

        assert research_agent.output_key == "research_results"

    def test_agent_has_two_tools(self):
        from agents.research_agent.agent import research_agent

        assert len(research_agent.tools) == 2

    def test_has_google_search_tool(self):
        from agents.research_agent.agent import research_agent

        tool_names = [
            getattr(t, "name", None) or getattr(t, "__name__", None)
            for t in research_agent.tools
        ]
        assert "google_search" in tool_names

    def test_has_rag_retrieval_tool(self):
        from agents.research_agent.agent import search_research_corpus

        assert search_research_corpus.name == "search_research_corpus"

    def test_agent_description_set(self):
        from agents.research_agent.agent import research_agent

        assert research_agent.description
        assert "research" in research_agent.description.lower()


class TestResearchAgentPrompt:
    """Verify the prompt contains required instruction elements."""

    def test_prompt_mentions_research(self):
        from agents.research_agent.prompt import RESEARCH_AGENT_INSTRUCTION

        assert "research" in RESEARCH_AGENT_INSTRUCTION.lower()

    def test_prompt_mentions_case_law(self):
        from agents.research_agent.prompt import RESEARCH_AGENT_INSTRUCTION

        assert "Case Law" in RESEARCH_AGENT_INSTRUCTION

    def test_prompt_mentions_statutes(self):
        from agents.research_agent.prompt import RESEARCH_AGENT_INSTRUCTION

        assert "Statutes" in RESEARCH_AGENT_INSTRUCTION

    def test_prompt_mentions_google_search(self):
        from agents.research_agent.prompt import RESEARCH_AGENT_INSTRUCTION

        assert "google_search" in RESEARCH_AGENT_INSTRUCTION

    def test_prompt_mentions_rag_tool(self):
        from agents.research_agent.prompt import RESEARCH_AGENT_INSTRUCTION

        assert "search_research_corpus" in RESEARCH_AGENT_INSTRUCTION

    def test_prompt_has_structured_output_sections(self):
        from agents.research_agent.prompt import RESEARCH_AGENT_INSTRUCTION

        assert "Research Summary" in RESEARCH_AGENT_INSTRUCTION
        assert "Key Issues" in RESEARCH_AGENT_INSTRUCTION
        assert "Analysis" in RESEARCH_AGENT_INSTRUCTION


class TestResearchAgentExports:
    """Verify the package exports correctly."""

    def test_package_exports_agent(self):
        from agents.research_agent import research_agent

        assert research_agent.name == "research_agent"
