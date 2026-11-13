"""Typed runtime configuration.

Configuration is loaded from environment variables and an optional local `.env`.
Invalid values raise a clear validation error at startup; secrets use `SecretStr`.
"""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Annotated, Any, Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings.

    The provider block (`genai_provider`, `genai_api_key`, `genai_model`,
    `genai_timeout_seconds`, `genai_max_input_chars`) is validated since spec 002.
    In G02 only the `fake` provider is accepted and no external call is ever made; the
    real provider and its credential are consumed by spec 011 behind the same port.
    Never log `genai_api_key`.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "thehouse-genai"
    app_env: Literal["local", "test", "staging", "production"] = "local"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    cors_origins: Annotated[list[str], NoDecode] = Field(default_factory=list)
    max_request_bytes: int = Field(default=65_536, ge=1_024, le=10_485_760)

    # Future spec 002 configuration. Never log `genai_api_key`.
    genai_provider: str | None = None
    genai_api_key: SecretStr | None = None
    genai_model: str | None = None
    genai_timeout_seconds: float = Field(default=15.0, gt=0, le=120)
    genai_max_input_chars: int = Field(default=4_000, ge=1, le=100_000)

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors_origins(cls, value: Any) -> list[str]:
        if value is None or value == "":
            return []
        if isinstance(value, str):
            raw = value.strip()
            if raw.startswith("["):
                parsed = json.loads(raw)
                if not isinstance(parsed, list):
                    raise ValueError("CORS_ORIGINS must be a JSON list or comma-separated values")
                return [str(origin).strip() for origin in parsed if str(origin).strip()]
            return [origin.strip() for origin in raw.split(",") if origin.strip()]
        if isinstance(value, (list, tuple)):
            return [str(origin).strip() for origin in value if str(origin).strip()]
        raise ValueError("CORS_ORIGINS must be a JSON list or comma-separated values")

    @field_validator("cors_origins")
    @classmethod
    def _validate_cors_origins(cls, value: list[str]) -> list[str]:
        if "*" in value:
            raise ValueError("wildcard CORS origin is not allowed; configure explicit origins")
        normalized: list[str] = []
        for origin in value:
            if not origin.startswith(("http://", "https://")):
                raise ValueError(f"invalid CORS origin: {origin!r}")
            normalized.append(origin.rstrip("/"))
        return normalized


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings instance, loaded once."""

    return Settings()
