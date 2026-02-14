"""
Configuration file for Veloce Agent
Store your environment-specific settings here
"""

import os

# Veloce API Configuration
VELOCE_API_BASE = "https://api.posveloce.com"

# Default Location ID - Set this to your Pur & Simple location
# You can get this from the Veloce dashboard or API
DEFAULT_LOCATION_ID = os.getenv("VELOCE_LOCATION_ID", "")

# Veloce API Credentials
# IMPORTANT: Never commit these to git
# Set these as environment variables or use a secrets manager
VELOCE_EMAIL = os.getenv("VELOCE_EMAIL", "")
VELOCE_PASSWORD = os.getenv("VELOCE_PASSWORD", "")

# Gemini Model Configuration
GEMINI_MODEL = "gemini-2.0-flash"

# Session Configuration
SESSION_APP_NAME = "veloce_restaurant_agent"
DEFAULT_USER_ID = "manager_001"  # Can be customized per manager
