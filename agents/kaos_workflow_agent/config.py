"""Configuration constants for kaos_workflow_agent."""

import os

GEMINI_MODEL = os.getenv("VERTEX_AI_MODEL", "gemini-2.5-flash")
