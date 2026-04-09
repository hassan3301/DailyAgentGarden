"""
Configuration for Insight Session Agent
"""

import os

GEMINI_MODEL = os.getenv("VERTEX_AI_MODEL", "gemini-2.5-flash")
