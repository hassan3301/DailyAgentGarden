"""Drafting Agent package — generates legal documents via template RAG."""

import os

from dotenv import load_dotenv

load_dotenv()

os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "TRUE")

from .agent import drafting_agent  # noqa: E402

__all__ = ["drafting_agent"]
