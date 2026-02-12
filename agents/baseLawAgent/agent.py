"""Orchestrator Agent — routes queries to specialist agents via AgentTool."""

import os

from google.adk.agents import LlmAgent
from google.adk.tools.agent_tool import AgentTool

from baseLawAgent.knowledge_agent.agent import knowledge_agent
from baseLawAgent.drafting_agent.agent import drafting_agent
from baseLawAgent.research_agent.agent import research_agent

from .prompt import ORCHESTRATOR_INSTRUCTION

MODEL = os.environ.get("VERTEX_AI_MODEL", "gemini-2.0-flash")

orchestrator = LlmAgent(
    name="orchestrator",
    model=MODEL,
    description=(
        "Routes legal queries to the appropriate specialist agent: "
        "knowledge, drafting, or research."
    ),
    instruction=ORCHESTRATOR_INSTRUCTION,
    tools=[
        AgentTool(agent=knowledge_agent),
        AgentTool(agent=drafting_agent),
        AgentTool(agent=research_agent),
    ],
)

root_agent = orchestrator
