"""Tests for the Drafting Agent structure, tools, and prompt."""

import pytest


@pytest.fixture(autouse=True)
def _set_env(monkeypatch):
    """Set required environment variables for agent import."""
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")
    monkeypatch.setenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    monkeypatch.setenv("GOOGLE_GENAI_USE_VERTEXAI", "TRUE")
    monkeypatch.setenv("DRAFTING_RAG_CORPUS", "projects/test/locations/us-central1/ragCorpora/456")


class TestDraftingAgentStructure:
    """Verify the drafting agent is correctly configured."""

    def test_agent_name(self):
        from agents.drafting_agent.agent import drafting_agent

        assert drafting_agent.name == "drafting_agent"

    def test_agent_model(self):
        from agents.drafting_agent.agent import drafting_agent

        assert drafting_agent.model == "gemini-2.0-flash"

    def test_agent_has_output_key(self):
        from agents.drafting_agent.agent import drafting_agent

        assert drafting_agent.output_key == "draft_document"

    def test_agent_has_one_tool(self):
        from agents.drafting_agent.agent import drafting_agent

        assert len(drafting_agent.tools) == 1

    def test_tool_is_rag_retrieval(self):
        from agents.drafting_agent.agent import search_drafting_templates

        assert search_drafting_templates.name == "search_drafting_templates"

    def test_agent_description_set(self):
        from agents.drafting_agent.agent import drafting_agent

        assert drafting_agent.description
        assert "legal documents" in drafting_agent.description


class TestDraftingAgentPrompt:
    """Verify the prompt contains required instruction elements."""

    def test_prompt_mentions_drafting(self):
        from agents.drafting_agent.prompt import DRAFTING_AGENT_INSTRUCTION

        assert "draft" in DRAFTING_AGENT_INSTRUCTION.lower()

    def test_prompt_mentions_review_needed_marker(self):
        from agents.drafting_agent.prompt import DRAFTING_AGENT_INSTRUCTION

        assert "[REVIEW NEEDED]" in DRAFTING_AGENT_INSTRUCTION

    def test_prompt_mentions_tool_name(self):
        from agents.drafting_agent.prompt import DRAFTING_AGENT_INSTRUCTION

        assert "search_drafting_templates" in DRAFTING_AGENT_INSTRUCTION

    def test_prompt_mentions_template(self):
        from agents.drafting_agent.prompt import DRAFTING_AGENT_INSTRUCTION

        assert "template" in DRAFTING_AGENT_INSTRUCTION.lower()


class TestDraftingAgentExports:
    """Verify the package exports correctly."""

    def test_package_exports_agent(self):
        from agents.drafting_agent import drafting_agent

        assert drafting_agent.name == "drafting_agent"
