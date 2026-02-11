"""Knowledge Agent package — retrieves firm knowledge via RAG."""

import os

from dotenv import load_dotenv

load_dotenv()

# Ensure Vertex AI backend is configured
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "TRUE")

from .agent import knowledge_agent  # noqa: E402

__all__ = ["knowledge_agent"]
