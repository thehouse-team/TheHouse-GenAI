"""Typed runtime configuration.

Configuration is loaded from environment variables and an optional local .env.
Invalid values raise a clear validation error at startup; secrets use SecretStr.
"""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Annotated, Any, Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings.

    The provider block is validated at startup. ake is always available for tests;
    gemini is the authorized real provider for smart-match explanation. Never log
    credentials or service secrets.
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

    # Provider configuration. Never log secrets.
    genai_provider: Literal["fake", "gemini"] | None = None
    genai_api_key: SecretStr | None = None
    gemini_api_key: SecretStr | None = None
    genai_model: str | None = None
    genai_timeout_seconds: float = Field(default=15.0, gt=0, le=120)
    genai_max_input_chars: int = Field(default=4_000, ge=1, le=100_000)
    genai_max_output_tokens: int = Field(default=256, ge=1, le=2_048)
    genai_max_output_chars: int = Field(default=1_200, ge=1, le=10_000)
    genai_max_retries: int = Field(default=2, ge=0, le=3)

    # Service-to-service auth for generative endpoints.
    service_api_key: SecretStr | None = None

    @field_validator("genai_provider", mode="before")
    @classmethod
    def _normalize_genai_provider(cls, value: Any) -> str | None:
        """Normalize the provider name and treat an empty value as unset."""

        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("GENAI_PROVIDER must be a string")
        candidate = value.strip().lower()
        if not candidate:
            return None
        return candidate

    @field_validator("genai_api_key", "gemini_api_key", "service_api_key", mode="before")
    @classmethod
    def _empty_secret_to_none(cls, value: Any) -> Any:
        """Normalize empty secrets to None for simpler validation."""

        if isinstance(value, str) and value.strip() == "":
            return None
        return value

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

    def resolved_api_key(self) -> SecretStr | None:
        """Return the configured provider credential without exposing it."""

        if self.genai_api_key is not None:
            return self.genai_api_key
        return self.gemini_api_key

    def resolved_model(self) -> str:
        """Return the configured model or the safe default for the provider."""

        if self.genai_model and self.genai_model.strip():
            return self.genai_model.strip()
        if self.genai_provider == "gemini":
            return "gemini-2.5-flash-lite"
        return "fake-model"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings instance, loaded once."""

    return Settings()
