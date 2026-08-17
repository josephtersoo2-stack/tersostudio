"""OpenHands Agent Server connection and execution settings."""
from dataclasses import dataclass
from typing import Optional

from pydantic import SecretStr


@dataclass
class OpenHandsServerConfig:
    """Configuration required to connect to OpenHands Agent Server and direct LLM provider."""

    server_url: str = "http://localhost:8010"
    server_api_key: Optional[SecretStr] = None
    server_timeout_seconds: int = 120
    server_verify_ssl: bool = True
    llm_default_model: str = "anthropic/claude-sonnet-4-5-20250929"
    llm_api_key: Optional[SecretStr] = None
    llm_base_url: Optional[str] = None
    max_retries: int = 3

    def __post_init__(self) -> None:
        if isinstance(self.server_api_key, str):
            self.server_api_key = SecretStr(self.server_api_key)
        if isinstance(self.llm_api_key, str):
            self.llm_api_key = SecretStr(self.llm_api_key)
        if self.server_verify_ssl is False:
            raise ValueError(
                "Disabling TLS verification (server_verify_ssl=False) is not supported in B1."
            )
