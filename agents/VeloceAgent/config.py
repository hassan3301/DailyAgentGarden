"""
Configuration for Veloce Agent
"""

import os

# Veloce API base URL
VELOCE_API_BASE = "https://api.posveloce.com"

# Gemini model used by the agent
GEMINI_MODEL = os.getenv("VERTEX_AI_MODEL", "gemini-2.5-flash")
