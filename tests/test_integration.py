"""Integration tests for the multi-agent legal assistant system.

These tests require a live GCP environment with configured RAG corpora.
Run with: pytest -m integration
"""

from __future__ import annotations

import pytest

# Mark the entire module as integration tests
pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def _set_env(monkeypatch):
    """Set environment variables for integration tests."""
    monkeypatch.setenv("GOOGLE_GENAI_USE_VERTEXAI", "TRUE")


class TestAgentWiring:
    """Verify that all agents can be imported and are wired correctly."""

    def test_root_agent_importable(self):
        from agents.baseLawAgent import root_agent

        assert root_agent.name == "orchestrator"

    def test_orchestrator_has_all_sub_agents(self):
        from agents.baseLawAgent import root_agent

        agent_names = [t.agent.name for t in root_agent.tools]
        assert set(agent_names) == {"knowledge_agent", "drafting_agent", "research_agent"}

    def test_knowledge_agent_has_rag_tool(self):
        from agents.knowledge_agent.agent import knowledge_agent

        assert len(knowledge_agent.tools) == 1
        assert knowledge_agent.tools[0].name == "search_firm_knowledge_base"

    def test_drafting_agent_has_rag_tool(self):
        from agents.drafting_agent.agent import drafting_agent

        assert len(drafting_agent.tools) == 1
        assert drafting_agent.tools[0].name == "search_drafting_templates"

    def test_research_agent_has_two_tools(self):
        from agents.research_agent.agent import research_agent

        assert len(research_agent.tools) == 2


class TestInMemoryRunner:
    """Integration tests using ADK InMemoryRunner.

    These require live GCP credentials and configured RAG corpora.
    """

    @pytest.mark.asyncio
    async def test_runner_can_be_created(self):
        """Verify the InMemoryRunner can instantiate with our root agent."""
        from google.adk.runners import InMemoryRunner

        from agents.baseLawAgent import root_agent

        runner = InMemoryRunner(agent=root_agent, app_name="test_legal_assistant")
        assert runner is not None
