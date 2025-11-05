"""Configuration management"""

import os
from typing import Optional
from dotenv import load_dotenv
from pydantic import BaseModel, Field


class Config(BaseModel):
    """Application configuration"""

    # API settings
    api_key: str = Field(description="AIMusicAPI.ai API key")
    base_url: str = Field(
        default="https://api.aimusicapi.ai/v1",
        description="API base URL"
    )
    timeout: int = Field(default=30, description="Request timeout in seconds")

    # FSM settings
    poll_interval: int = Field(
        default=5,
        description="Seconds between status polls"
    )
    max_retries: int = Field(
        default=60,
        description="Maximum polling attempts (60 * 5s = 5 minutes)"
    )

    # Output settings
    output_dir: str = Field(
        default="./output",
        description="Directory for downloaded files"
    )
    auto_download: bool = Field(
        default=True,
        description="Automatically download generated files"
    )

    # Logging settings
    log_level: str = Field(
        default="INFO",
        description="Logging level"
    )
    log_file: Optional[str] = Field(
        default=None,
        description="Log file path (None for console only)"
    )


def load_config(env_file: str = ".env") -> Config:
    """
    Load configuration from environment variables

    Args:
        env_file: Path to .env file

    Returns:
        Config object

    Raises:
        ValueError: If required settings are missing
    """
    # Load .env file
    load_dotenv(env_file)

    # Get required API key
    api_key = os.getenv("AIMUSIC_API_KEY")
    if not api_key:
        raise ValueError("AIMUSIC_API_KEY environment variable is required")

    # Create config
    config = Config(
        api_key=api_key,
        base_url=os.getenv("AIMUSIC_BASE_URL", "https://api.aimusicapi.ai/v1"),
        timeout=int(os.getenv("AIMUSIC_TIMEOUT", "30")),
        poll_interval=int(os.getenv("POLL_INTERVAL", "5")),
        max_retries=int(os.getenv("MAX_RETRIES", "60")),
        output_dir=os.getenv("OUTPUT_DIR", "./output"),
        auto_download=os.getenv("AUTO_DOWNLOAD", "true").lower() == "true",
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        log_file=os.getenv("LOG_FILE")
    )

    return config
