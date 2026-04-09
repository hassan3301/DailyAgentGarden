"""
Insight Session Agent — AI Discovery Interview Agent

Conducts guided discovery interviews to identify AI opportunities
in professional services firms.
"""

from google.adk.agents import LlmAgent
from .config import GEMINI_MODEL
from .prompt import SYSTEM_INSTRUCTION
from .tools import update_session_progress, generate_insight_report


def _init_session_state(callback_context):
    """Initialize session state for tracking interview progress."""
    state = callback_context.state

    if "covered_topics" in state:
        return

    state["covered_topics"] = []
    state["topic_findings"] = {}


root_agent = LlmAgent(
    name="InsightSessionAgent",
    model=GEMINI_MODEL,
    instruction=SYSTEM_INSTRUCTION,
    description="AI Discovery Interview Agent that conducts guided insight sessions to identify AI opportunities in professional services firms.",
    before_agent_callback=_init_session_state,
    tools=[
        update_session_progress,
        generate_insight_report,
    ],
)
