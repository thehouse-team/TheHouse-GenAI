"""Typed runtime configuration.

Configuration is loaded from environment variables and an optional local `.env`.
Invalid values raise a clear validation error at startup; secrets use `SecretStr`.
"""

from __future__ import annotations

import json
from decimal import Decimal
from functools import lru_cache
from typing import Annotated, Any, Literal, Self

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings.

    The provider block (`genai_provider`, `genai_api_key`, `genai_model`,
    `genai_timeout_seconds`, `genai_max_input_chars`) is validated since spec 002.
    Since spec 011 the `gemini` provider is accepted by the configuration and
    requires a credential and a model id; the factory still builds only the `fake`
    provider until its own block closes, so a `gemini` configuration fails fast
    instead of calling anything. Never log `genai_api_key`.

    Since spec 003, `service_key` holds the service-to-service credential as a
    `SecretStr`; it is never logged nor serialized. Since spec 005,
    `service_key_previous` holds the outgoing key during rotation and is treated the
    same way.
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

    # Process-local rate limiting (spec 005). The state is per process: with several
    # replicas the effective limit is N times the configured one; see spec 005.
    rate_limit_enabled: bool = Field(
        default=True,
        validation_alias="GENAI_RATE_LIMIT_ENABLED",
    )
    rate_limit_requests: int = Field(
        default=60,
        ge=1,
        le=100_000,
        validation_alias="GENAI_RATE_LIMIT_REQUESTS",
    )
    rate_limit_window_seconds: int = Field(
        default=60,
        ge=1,
        le=86_400,
        validation_alias="GENAI_RATE_LIMIT_WINDOW_SECONDS",
    )
    rate_limit_max_clients: int = Field(
        default=1_000,
        ge=1,
        le=1_000_000,
        validation_alias="GENAI_RATE_LIMIT_MAX_CLIENTS",
    )

    # Daily provider budget (spec 007). Disabled by default: activation is a deployment
    # decision of G10. Token limits of None mean "no limit"; rates are per million tokens.
    budget_enabled: bool = Field(
        default=False,
        validation_alias="GENAI_BUDGET_ENABLED",
    )
    daily_call_limit: int = Field(
        default=400,
        ge=1,
        validation_alias="GENAI_DAILY_CALL_LIMIT",
    )
    daily_input_token_limit: int | None = Field(
        default=None,
        ge=0,
        validation_alias="GENAI_DAILY_INPUT_TOKEN_LIMIT",
    )
    daily_output_token_limit: int | None = Field(
        default=None,
        ge=0,
        validation_alias="GENAI_DAILY_OUTPUT_TOKEN_LIMIT",
    )
    cost_input_per_million: Decimal = Field(
        default=Decimal("0"),
        ge=0,
        validation_alias="GENAI_COST_INPUT_PER_MILLION",
    )
    cost_output_per_million: Decimal = Field(
        default=Decimal("0"),
        ge=0,
        validation_alias="GENAI_COST_OUTPUT_PER_MILLION",
    )

    # Service-to-service authentication for the generative endpoints (spec 003,
    # rotation added in 005). Only the GENAI_ prefixed variables are read from the
    # environment; the field names are mapped below for explicit construction.
    # Never log either credential.
    service_key: SecretStr | None = Field(
        default=None,
        validation_alias="GENAI_SERVICE_KEY",
    )
    service_key_previous: SecretStr | None = Field(
        default=None,
        validation_alias="GENAI_SERVICE_KEY_PREVIOUS",
    )

    # Separate credential for internal diagnostic endpoints (spec 007, decision 2).
    # Only the GENAI_ prefixed variable is read; never log or serialize it.
    metrics_key: SecretStr | None = Field(
        default=None,
        validation_alias="GENAI_METRICS_KEY",
    )

    # Provider configuration (spec 002, extended by spec 011). "gemini" is accepted
    # by the configuration and requires a credential and a model id; the factory
    # still builds only "fake" until its own block closes.
    # Never log `genai_api_key`.
    genai_provider: Literal["fake", "gemini"] | None = None
    genai_api_key: SecretStr | None = None
    genai_model: str | None = None
    genai_timeout_seconds: float = Field(default=15.0, gt=0, le=120)
    genai_max_input_chars: int = Field(default=4_000, ge=1, le=100_000)

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

    @field_validator("genai_api_key", mode="before")
    @classmethod
    def _normalize_genai_api_key(cls, value: Any) -> Any:
        """Treat a blank credential as unset instead of an empty secret."""

        if value is None:
            return None
        if isinstance(value, SecretStr):
            text = value.get_secret_value()
        elif isinstance(value, str):
            text = value
        else:
            return value
        if not text.strip():
            return None
        return SecretStr(text)

    @field_validator("genai_model", mode="before")
    @classmethod
    def _normalize_genai_model(cls, value: Any) -> Any:
        """Trim the model id and treat a blank value as unset."""

        if value is None:
            return None
        if not isinstance(value, str):
            return value
        candidate = value.strip()
        if not candidate:
            return None
        return candidate

    @model_validator(mode="before")
    @classmethod
    def _accept_aliased_kwargs(cls, data: Any) -> Any:
        """Map field names to their `GENAI_` aliases for explicit construction.

        Only the `GENAI_`-prefixed variables are valid environment sources; field names
        are accepted here so tests and explicit construction can still use them.
        """

        if not isinstance(data, dict):
            return data
        mapped = dict(data)
        aliases: dict[str, str] = {
            "service_key": "GENAI_SERVICE_KEY",
            "service_key_previous": "GENAI_SERVICE_KEY_PREVIOUS",
            "metrics_key": "GENAI_METRICS_KEY",
        }
        for field_name in (
            "rate_limit_enabled",
            "rate_limit_requests",
            "rate_limit_window_seconds",
            "rate_limit_max_clients",
            "budget_enabled",
            "daily_call_limit",
            "daily_input_token_limit",
            "daily_output_token_limit",
            "cost_input_per_million",
            "cost_output_per_million",
        ):
            aliases[field_name] = f"GENAI_{field_name.upper()}"
        for field_name, env_name in aliases.items():
            if field_name in mapped and env_name not in mapped:
                mapped[env_name] = mapped[field_name]
        return mapped

    @field_validator("service_key", "service_key_previous", "metrics_key", mode="before")
    @classmethod
    def _normalize_service_keys(cls, value: Any) -> Any:
        """Treat a blank service key as unset instead of an empty secret."""

        if value is None:
            return None
        if isinstance(value, SecretStr):
            text = value.get_secret_value()
        elif isinstance(value, str):
            text = value
        else:
            return value
        if not text.strip():
            return None
        return SecretStr(text)

    @model_validator(mode="after")
    def _require_gemini_credentials(self) -> Self:
        """Require a credential and a model id when the real provider is selected.

        The messages never carry the credential value, so a misconfigured start-up
        cannot expose the secret.
        """

        if self.genai_provider != "gemini":
            return self
        if self.genai_api_key is None:
            raise ValueError("GENAI_API_KEY is required when GENAI_PROVIDER is 'gemini'")
        if self.genai_model is None:
            raise ValueError("GENAI_MODEL is required when GENAI_PROVIDER is 'gemini'")
        return self

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
