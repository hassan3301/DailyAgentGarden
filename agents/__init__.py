"""DailyAgentGarden agents package.

Re-exports root_agent from the orchestrator for use with `adk web` / `adk run`.
"""

from agents.orchestrator import root_agent

__all__ = ["root_agent"]
