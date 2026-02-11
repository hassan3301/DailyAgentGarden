"""Orchestrator package — top-level agent that routes to specialists."""

import os

from dotenv import load_dotenv

load_dotenv()

os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "TRUE")

from .agent import root_agent  # noqa: E402

__all__ = ["root_agent"]
