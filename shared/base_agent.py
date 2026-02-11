"""Base agent abstract class for the DailyAgentGarden framework.

All agents must inherit from BaseAgent and implement its abstract methods.
Provides standardized logging, error handling, and lifecycle management.
"""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class AgentContext:
    """Context passed to agents during query processing.

    Attributes:
        session_id: Unique identifier for the current session.
        client_id: Identifier for the client project.
        metadata: Arbitrary key-value pairs for agent-specific context.
    """

    session_id: str
    client_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResponse:
    """Standardized response returned by all agents.

    Attributes:
        content: The main response content.
        sources: List of source references used to generate the response.
        metadata: Additional response metadata (token counts, latency, etc.).
        success: Whether the agent completed successfully.
        error: Error message if success is False.
    """

    content: str
    sources: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    success: bool = True
    error: str | None = None


@dataclass
class ToolDefinition:
    """Definition of a tool available to an agent.

    Attributes:
        name: Tool identifier used in function calling.
        description: Human-readable description of what the tool does.
        parameters: JSON Schema describing the tool's parameters.
    """

    name: str
    description: str
    parameters: dict[str, Any] = field(default_factory=dict)


class BaseAgent(ABC):
    """Abstract base class for all agents in the framework.

    Subclasses must implement:
        - process_query: Core logic for handling a user query.
        - get_tools: Returns tool definitions available to the agent.

    Provides built-in interaction logging and error handling.

    Example::

        class MyAgent(BaseAgent):
            def __init__(self):
                super().__init__(agent_name="my_agent")

            async def process_query(self, query, context):
                return AgentResponse(content="Hello")

            def get_tools(self):
                return []
    """

    def __init__(self, agent_name: str) -> None:
        self.agent_name = agent_name
        self.logger = logging.getLogger(f"agents.{agent_name}")

    @abstractmethod
    async def process_query(
        self, query: str, context: AgentContext
    ) -> AgentResponse:
        """Process a user query and return a response.

        Args:
            query: The user's input query string.
            context: Contextual information for processing.

        Returns:
            AgentResponse with the result of processing.
        """

    @abstractmethod
    def get_tools(self) -> list[ToolDefinition]:
        """Return the list of tools available to this agent.

        Returns:
            List of ToolDefinition objects describing callable tools.
        """

    def log_interaction(
        self,
        query: str,
        response: AgentResponse,
        duration_ms: float,
    ) -> None:
        """Log details of an agent interaction.

        Args:
            query: The original query string.
            response: The agent's response.
            duration_ms: Processing time in milliseconds.
        """
        self.logger.info(
            "interaction",
            extra={
                "agent": self.agent_name,
                "query_length": len(query),
                "success": response.success,
                "duration_ms": round(duration_ms, 2),
                "source_count": len(response.sources),
            },
        )
        if not response.success:
            self.logger.warning(
                "agent returned error: %s",
                response.error,
                extra={"agent": self.agent_name},
            )

    async def run(self, query: str, context: AgentContext) -> AgentResponse:
        """Execute the agent with logging and error handling.

        This is the primary entry point for running an agent. It wraps
        process_query with timing, logging, and exception handling.

        Args:
            query: The user's input query string.
            context: Contextual information for processing.

        Returns:
            AgentResponse with the result or error details.
        """
        start = time.perf_counter()
        try:
            response = await self.process_query(query, context)
        except Exception as exc:
            duration_ms = (time.perf_counter() - start) * 1000
            self.logger.exception("unhandled error in %s", self.agent_name)
            response = AgentResponse(
                content="",
                success=False,
                error=str(exc),
            )
            self.log_interaction(query, response, duration_ms)
            return response

        duration_ms = (time.perf_counter() - start) * 1000
        self.log_interaction(query, response, duration_ms)
        return response
