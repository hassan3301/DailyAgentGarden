"""
Configuration for QBO Bookkeeping Agent
"""

import os

# Gemini model used by the agent
GEMINI_MODEL = os.getenv("VERTEX_AI_MODEL", "gemini-2.5-flash")

# --- QBO API constants ---
QB_CLIENT_ID = os.getenv("QB_CLIENT_ID", "")
QB_CLIENT_SECRET = os.getenv("QB_CLIENT_SECRET", "")
QB_ENV = os.getenv("QB_ENV", "sandbox").strip().lower()

# Intuit OAuth token endpoint (same for sandbox and production)
TOKEN_URL = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"

# Accounting API base per environment (includes /v3/company)
if QB_ENV == "production":
    QBO_API_BASE = "https://quickbooks.api.intuit.com/v3/company"
else:
    QBO_API_BASE = "https://sandbox-quickbooks.api.intuit.com/v3/company"

# QuickBooks minor version
MINOR_VERSION = os.getenv("QB_MINOR_VERSION", "75")

# Postgres connection (for token storage via qbo_connection table)
DATABASE_URL = os.getenv("DATABASE_URL", "")
