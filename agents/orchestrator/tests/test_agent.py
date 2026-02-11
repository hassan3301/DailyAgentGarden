"""Tests for the Orchestrator Agent structure, tools, and prompt."""

import pytest


@pytest.fixture(autouse=True)
def _set_env(monkeypatch):
    """Set required environment variables for agent import."""
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")
    monkeypatch.setenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    monkeypatch.setenv("GOOGLE_GENAI_USE_VERTEXAI", "TRUE")
    monkeypatch.setenv("KNOWLEDGE_RAG_CORPUS", "projects/test/locations/us-central1/ragCorpora/123")
    monkeypatch.setenv("DRAFTING_RAG_CORPUS", "projects/test/locations/us-central1/ragCorpora/456")
    monkeypatch.setenv("RESEARCH_RAG_CORPUS", "projects/test/locations/us-central1/ragCorpora/789")


class TestOrchestratorStructure:
    """Verify the orchestrator is correctly configured."""

    def test_agent_name(self):
        from agents.orchestrator.agent import orchestrator

        assert orchestrator.name == "orchestrator"

    def test_agent_model(self):
        from agents.orchestrator.agent import orchestrator

        assert orchestrator.model == "gemini-2.0-flash"

    def test_has_three_tools(self):
        from agents.orchestrator.agent import orchestrator

        assert len(orchestrator.tools) == 3

    def test_root_agent_is_orchestrator(self):
        from agents.orchestrator.agent import root_agent, orchestrator

        assert root_agent is orchestrator

    def test_agent_description_set(self):
        from agents.orchestrator.agent import orchestrator

        assert orchestrator.description
        assert "Routes" in orchestrator.description


class TestOrchestratorSubAgents:
    """Verify all sub-agents are wired via AgentTool."""

    def test_knowledge_agent_present(self):
        from agents.orchestrator.agent import orchestrator

        agent_names = [t.agent.name for t in orchestrator.tools]
        assert "knowledge_agent" in agent_names

    def test_drafting_agent_present(self):
        from agents.orchestrator.agent import orchestrator

        agent_names = [t.agent.name for t in orchestrator.tools]
        assert "drafting_agent" in agent_names

    def test_research_agent_present(self):
        from agents.orchestrator.agent import orchestrator

        agent_names = [t.agent.name for t in orchestrator.tools]
        assert "research_agent" in agent_names


class TestOrchestratorPrompt:
    """Verify the prompt references all agents and routing rules."""

    def test_prompt_references_knowledge_agent(self):
        from agents.orchestrator.prompt import ORCHESTRATOR_INSTRUCTION

        assert "knowledge_agent" in ORCHESTRATOR_INSTRUCTION

    def test_prompt_references_drafting_agent(self):
        from agents.orchestrator.prompt import ORCHESTRATOR_INSTRUCTION

        assert "drafting_agent" in ORCHESTRATOR_INSTRUCTION

    def test_prompt_references_research_agent(self):
        from agents.orchestrator.prompt import ORCHESTRATOR_INSTRUCTION

        assert "research_agent" in ORCHESTRATOR_INSTRUCTION

    def test_prompt_has_routing_rules(self):
        from agents.orchestrator.prompt import ORCHESTRATOR_INSTRUCTION

        assert "Routing Rules" in ORCHESTRATOR_INSTRUCTION

    def test_prompt_supports_multi_agent(self):
        from agents.orchestrator.prompt import ORCHESTRATOR_INSTRUCTION

        assert "Multi-Agent" in ORCHESTRATOR_INSTRUCTION


class TestOrchestratorExports:
    """Verify the package exports correctly."""

    def test_package_exports_root_agent(self):
        from agents.orchestrator import root_agent

        assert root_agent.name == "orchestrator"
