"""Tests for the Kaos Workflow Agent structure, tools, and prompt."""

import pytest


@pytest.fixture(autouse=True)
def _set_env(monkeypatch):
    """Set required environment variables for agent import."""
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")
    monkeypatch.setenv("GOOGLE_CLOUD_LOCATION", "us-east5")
    monkeypatch.setenv("GOOGLE_GENAI_USE_VERTEXAI", "TRUE")
    monkeypatch.setenv(
        "KAOS_RAG_CORPUS",
        "projects/test/locations/us-east5/ragCorpora/123",
    )


class TestAgentStructure:
    """Verify the agent is correctly configured."""

    def test_agent_name(self):
        from kaos_workflow_agent.agent import root_agent

        assert root_agent.name == "kaos_workflow_agent"

    def test_agent_model(self):
        from kaos_workflow_agent.agent import root_agent
        from kaos_workflow_agent.config import GEMINI_MODEL

        assert root_agent.model == GEMINI_MODEL

    def test_agent_has_one_tool(self):
        from kaos_workflow_agent.agent import root_agent

        assert len(root_agent.tools) == 1

    def test_tool_name(self):
        from kaos_workflow_agent.agent import search_kaos_workflows

        assert search_kaos_workflows.name == "search_kaos_workflows"

    def test_agent_description_set(self):
        from kaos_workflow_agent.agent import root_agent

        assert root_agent.description
        assert "Kaos Group" in root_agent.description

    def test_instruction_is_set(self):
        from kaos_workflow_agent.agent import root_agent

        assert root_agent.instruction


class TestPrompt:
    """Verify the prompt contains required instruction elements."""

    def test_prompt_mentions_ghl(self):
        from kaos_workflow_agent.prompt import SYSTEM_INSTRUCTION

        assert "GHL" in SYSTEM_INSTRUCTION

    def test_prompt_mentions_pipeline(self):
        from kaos_workflow_agent.prompt import SYSTEM_INSTRUCTION

        assert "pipeline" in SYSTEM_INSTRUCTION.lower()

    def test_prompt_mentions_automated(self):
        from kaos_workflow_agent.prompt import SYSTEM_INSTRUCTION

        assert "automated" in SYSTEM_INSTRUCTION.lower()

    def test_prompt_mentions_manual(self):
        from kaos_workflow_agent.prompt import SYSTEM_INSTRUCTION

        assert "manual" in SYSTEM_INSTRUCTION.lower()

    def test_prompt_mentions_workflow(self):
        from kaos_workflow_agent.prompt import SYSTEM_INSTRUCTION

        assert "workflow" in SYSTEM_INSTRUCTION.lower()

    def test_prompt_mentions_tool_name(self):
        from kaos_workflow_agent.prompt import SYSTEM_INSTRUCTION

        assert "search_kaos_workflows" in SYSTEM_INSTRUCTION


class TestExports:
    """Verify the package exports correctly."""

    def test_package_exports_root_agent(self):
        from kaos_workflow_agent import root_agent

        assert root_agent.name == "kaos_workflow_agent"
