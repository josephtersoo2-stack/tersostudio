"""OpenHands Agent Server connection and execution settings."""
from dataclasses import dataclass
from typing import Optional


@dataclass
class OpenHandsServerConfig:
    """Configuration required to connect to OpenHands Agent Server."""

    server_url: str = "http://localhost:8000"
    api_key: Optional[str] = None
    default_model: str = "anthropic/claude-sonnet-4-5-20250929"
    timeout_seconds: int = 120
    max_retries: int = 3
    verify_ssl: bool = True
