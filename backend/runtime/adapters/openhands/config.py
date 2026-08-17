"""OpenHands Agent Server connection and execution settings."""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class OpenHandsServerConfig:
    """Configuration required to connect to OpenHands Agent Server and direct LLM provider."""

    server_url: str = "http://localhost:8010"
    server_api_key: Optional[str] = field(default=None, repr=False)
    server_timeout_seconds: int = 120
    server_verify_ssl: bool = True
    llm_default_model: str = "anthropic/claude-sonnet-4-5-20250929"
    llm_api_key: Optional[str] = field(default=None, repr=False)
    llm_base_url: Optional[str] = None
    max_retries: int = 3

    def __repr__(self) -> str:
        server_key_display = "***" if self.server_api_key else None
        llm_key_display = "***" if self.llm_api_key else None
        return (
            f"OpenHandsServerConfig("
            f"server_url={self.server_url!r}, "
            f"server_api_key={server_key_display!r}, "
            f"server_timeout_seconds={self.server_timeout_seconds!r}, "
            f"server_verify_ssl={self.server_verify_ssl!r}, "
            f"llm_default_model={self.llm_default_model!r}, "
            f"llm_api_key={llm_key_display!r}, "
            f"llm_base_url={self.llm_base_url!r}, "
            f"max_retries={self.max_retries!r})"
        )
