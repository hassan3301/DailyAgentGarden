"""Shared pytest fixtures for DailyAgentGarden tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from shared.base_agent import AgentContext, AgentResponse


@pytest.fixture
def agent_context() -> AgentContext:
    """Provide a default AgentContext for tests."""
    return AgentContext(
        session_id="test-session-001",
        client_id="test-client",
        metadata={"env": "test"},
    )


@pytest.fixture
def sample_response() -> AgentResponse:
    """Provide a successful AgentResponse for assertions."""
    return AgentResponse(
        content="Test response content",
        sources=["https://example.com/doc1"],
        metadata={"tokens": 42},
        success=True,
    )


@pytest.fixture
def error_response() -> AgentResponse:
    """Provide a failed AgentResponse for error-path tests."""
    return AgentResponse(
        content="",
        success=False,
        error="something went wrong",
    )


@pytest.fixture
def mock_vertex_model() -> MagicMock:
    """Provide a mocked Vertex AI GenerativeModel.

    The mock supports both sync and async generate_content calls.
    """
    model = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "mocked model response"
    mock_response.candidates = []

    model.generate_content.return_value = mock_response
    model.generate_content_async = AsyncMock(return_value=mock_response)
    return model


@pytest.fixture(autouse=True)
def _reset_settings_cache() -> None:
    """Clear the cached settings between tests so env overrides take effect."""
    from shared.config.base_config import get_settings

    get_settings.cache_clear()
