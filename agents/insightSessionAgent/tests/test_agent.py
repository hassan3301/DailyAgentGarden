"""
Structural tests for the Insight Session Agent
"""

import pytest
from unittest.mock import MagicMock


class TestAgentStructure:
    """Test that the agent is wired up correctly."""

    def test_root_agent_export(self):
        from insightSessionAgent import root_agent
        assert root_agent is not None

    def test_agent_name(self):
        from insightSessionAgent import root_agent
        assert root_agent.name == "InsightSessionAgent"

    def test_agent_has_tools(self):
        from insightSessionAgent import root_agent
        tool_names = [t.__name__ if callable(t) else t.name for t in root_agent.tools]
        assert "update_session_progress" in tool_names
        assert "generate_insight_report" in tool_names

    def test_agent_has_two_tools(self):
        from insightSessionAgent import root_agent
        assert len(root_agent.tools) == 2

    def test_agent_has_instruction(self):
        from insightSessionAgent import root_agent
        assert root_agent.instruction is not None
        assert len(root_agent.instruction) > 100

    def test_agent_has_before_callback(self):
        from insightSessionAgent import root_agent
        assert root_agent.before_agent_callback is not None

    def test_model_configured(self):
        from insightSessionAgent import root_agent
        assert root_agent.model is not None


class TestTools:
    """Test tool functions directly."""

    def _make_tool_context(self, state=None):
        ctx = MagicMock()
        ctx.state = state if state is not None else {}
        return ctx

    def test_update_progress_valid_topic(self):
        from insightSessionAgent.tools import update_session_progress

        ctx = self._make_tool_context()
        result = update_session_progress(
            "firm_overview", "Small firm with 5 lawyers.", ctx
        )
        assert result["status"] == "success"
        assert result["topics_covered"] == 1
        assert ctx.state["covered_topics"] == ["firm_overview"]
        assert ctx.state["topic_findings"]["firm_overview"] == "Small firm with 5 lawyers."

    def test_update_progress_invalid_topic(self):
        from insightSessionAgent.tools import update_session_progress

        ctx = self._make_tool_context()
        result = update_session_progress("invalid_topic", "Some summary.", ctx)
        assert result["status"] == "error"

    def test_update_progress_tracks_remaining(self):
        from insightSessionAgent.tools import update_session_progress

        ctx = self._make_tool_context()
        update_session_progress("firm_overview", "Summary 1.", ctx)
        result = update_session_progress("workflows", "Summary 2.", ctx)
        assert result["topics_covered"] == 2
        assert result["topics_total"] == 7
        assert len(result["remaining_topics"]) == 5

    def test_update_progress_no_duplicates(self):
        from insightSessionAgent.tools import update_session_progress

        ctx = self._make_tool_context()
        update_session_progress("firm_overview", "First summary.", ctx)
        update_session_progress("firm_overview", "Updated summary.", ctx)
        assert ctx.state["covered_topics"].count("firm_overview") == 1
        assert ctx.state["topic_findings"]["firm_overview"] == "Updated summary."

    def test_generate_report_incomplete(self):
        from insightSessionAgent.tools import generate_insight_report

        ctx = self._make_tool_context({"covered_topics": ["firm_overview"], "topic_findings": {}})
        result = generate_insight_report(ctx)
        assert result["status"] == "incomplete"

    def test_generate_report_all_topics_covered(self):
        from insightSessionAgent.tools import (
            generate_insight_report,
            TOPIC_AREAS,
        )

        findings = {t: f"Findings for {t}" for t in TOPIC_AREAS}
        ctx = self._make_tool_context({
            "covered_topics": list(TOPIC_AREAS.keys()),
            "topic_findings": findings,
        })
        result = generate_insight_report(ctx)
        assert result["status"] == "success"
        assert "report" in result
        assert "Executive Summary" in result["report"]
        assert "AI Opportunities" in result["report"]
        assert "Recommended Next Steps" in result["report"]

    def test_generate_report_includes_findings(self):
        from insightSessionAgent.tools import (
            generate_insight_report,
            TOPIC_AREAS,
        )

        findings = {t: f"Specific findings about {t}" for t in TOPIC_AREAS}
        ctx = self._make_tool_context({
            "covered_topics": list(TOPIC_AREAS.keys()),
            "topic_findings": findings,
        })
        result = generate_insight_report(ctx)
        for topic_id in TOPIC_AREAS:
            assert f"Specific findings about {topic_id}" in result["report"]


class TestSessionInit:
    """Test the before_agent_callback."""

    def test_init_creates_state(self):
        from insightSessionAgent.agent import _init_session_state

        ctx = MagicMock()
        ctx.state = {}
        _init_session_state(ctx)
        assert ctx.state["covered_topics"] == []
        assert ctx.state["topic_findings"] == {}

    def test_init_does_not_overwrite(self):
        from insightSessionAgent.agent import _init_session_state

        ctx = MagicMock()
        ctx.state = {"covered_topics": ["firm_overview"], "topic_findings": {"firm_overview": "test"}}
        _init_session_state(ctx)
        assert ctx.state["covered_topics"] == ["firm_overview"]
