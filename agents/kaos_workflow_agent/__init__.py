"""kaos_workflow_agent package.

Centralizes environment setup and re-exports root_agent for use with
`adk web` / `adk run`.
"""

import os

from dotenv import load_dotenv

load_dotenv()

# Derive project ID from default credentials if not already set.
try:
    import google.auth

    _credentials, _project = google.auth.default()
    if _project:
        os.environ.setdefault("GOOGLE_CLOUD_PROJECT", _project)
except Exception:
    pass

os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "us-east5")
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "TRUE")

from .agent import root_agent  # noqa: E402

__all__ = ["root_agent"]
