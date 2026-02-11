"""Research Agent package — legal research via web search and RAG."""

import os

from dotenv import load_dotenv

load_dotenv()

os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "TRUE")

from .agent import research_agent  # noqa: E402

__all__ = ["research_agent"]
