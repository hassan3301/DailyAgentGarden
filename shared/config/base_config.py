"""Environment configuration for the DailyAgentGarden framework.

Loads settings from environment variables (via .env file) and exposes
them as a validated Pydantic settings object.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

# Load .env from project root
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_PROJECT_ROOT / ".env")

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Attributes:
        google_cloud_project: GCP project ID.
        google_cloud_location: GCP region for Vertex AI resources.
        vertex_ai_model: Default model name for Vertex AI inference.
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        environment: Deployment environment name.
    """

    google_cloud_project: str = Field(
        default="", alias="GOOGLE_CLOUD_PROJECT"
    )
    google_cloud_location: str = Field(
        default="us-central1", alias="GOOGLE_CLOUD_LOCATION"
    )
    vertex_ai_model: str = Field(
        default="gemini-2.0-flash", alias="VERTEX_AI_MODEL"
    )
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    environment: str = Field(default="development", alias="ENVIRONMENT")

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings.

    Settings are loaded once and reused for the lifetime of the process.
    """
    settings = Settings()
    logger.info(
        "loaded settings: project=%s location=%s env=%s",
        settings.google_cloud_project,
        settings.google_cloud_location,
        settings.environment,
    )
    return settings


def configure_logging(level: str | None = None) -> None:
    """Configure root logger with a standard format.

    Args:
        level: Override log level. Defaults to the value from settings.
    """
    effective_level = level or get_settings().log_level
    logging.basicConfig(
        level=effective_level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
