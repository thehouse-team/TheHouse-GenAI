"""Configuration validation tests."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from thehouse_genai.infrastructure.config import Settings


def test_defaults_are_valid(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "APP_ENV",
        "LOG_LEVEL",
        "CORS_ORIGINS",
        "MAX_REQUEST_BYTES",
        "GENAI_TIMEOUT_SECONDS",
        "GENAI_MAX_INPUT_CHARS",
    ):
        monkeypatch.delenv(name, raising=False)

    settings = Settings(_env_file=None)

    assert settings.app_env == "local"
    assert settings.log_level == "INFO"
    assert settings.cors_origins == []
    assert settings.genai_timeout_seconds == 15
    assert settings.genai_max_input_chars == 4_000


def test_reads_environment_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("GENAI_TIMEOUT_SECONDS", "30")
    monkeypatch.setenv("GENAI_MAX_INPUT_CHARS", "1200")
    monkeypatch.setenv("CORS_ORIGINS", "https://app.thehouse.test,https://admin.thehouse.test")

    settings = Settings(_env_file=None)

    assert settings.genai_timeout_seconds == 30
    assert settings.genai_max_input_chars == 1200
    assert settings.cors_origins == [
        "https://app.thehouse.test",
        "https://admin.thehouse.test",
    ]


def test_accepts_json_cors_origins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", '["https://app.thehouse.test"]')

    settings = Settings(_env_file=None)

    assert settings.cors_origins == ["https://app.thehouse.test"]


@pytest.mark.parametrize(
    "overrides",
    [
        {"genai_timeout_seconds": 0},
        {"genai_timeout_seconds": -1},
        {"genai_max_input_chars": 0},
        {"max_request_bytes": 0},
        {"app_env": "unknown"},
        {"log_level": "VERBOSE"},
    ],
)
def test_invalid_configuration_fails(overrides: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **overrides)


def test_wildcard_cors_is_rejected() -> None:
    with pytest.raises(ValidationError, match="wildcard CORS"):
        Settings(_env_file=None, cors_origins=["*"])


def test_non_http_cors_origin_is_rejected() -> None:
    with pytest.raises(ValidationError, match="invalid CORS origin"):
        Settings(_env_file=None, cors_origins=["file:///tmp/app"])


def test_api_key_is_not_exposed_in_repr() -> None:
    settings = Settings(_env_file=None, genai_api_key="super-secret-value")

    assert "super-secret-value" not in repr(settings)
    assert settings.genai_api_key is not None
    assert settings.genai_api_key.get_secret_value() == "super-secret-value"


def test_genai_provider_defaults_to_none() -> None:
    settings = Settings(_env_file=None)

    assert settings.genai_provider is None


def test_genai_provider_accepts_fake() -> None:
    settings = Settings(_env_file=None, genai_provider="fake")

    assert settings.genai_provider == "fake"


def test_genai_provider_empty_string_is_none() -> None:
    settings = Settings(_env_file=None, genai_provider="")

    assert settings.genai_provider is None


@pytest.mark.parametrize("value", ["FAKE", " fake ", "fake "])
def test_genai_provider_is_normalized(value: str) -> None:
    settings = Settings(_env_file=None, genai_provider=value)

    assert settings.genai_provider == "fake"


@pytest.mark.parametrize("value", ["GEMINI", " gemini "])
def test_genai_provider_accepts_normalized_gemini(value: str) -> None:
    settings = Settings(
        _env_file=None,
        genai_provider=value,
        genai_api_key="test-key",
        genai_model="gemini-3.8-flash",
    )

    assert settings.genai_provider == "gemini"


@pytest.mark.parametrize("value", ["openai", "azure", "unknown"])
def test_genai_provider_rejects_unsupported_value(value: str) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, genai_provider=value)


def test_gemini_without_api_key_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, genai_provider="gemini", genai_model="gemini-3.8-flash")


def test_gemini_without_model_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, genai_provider="gemini", genai_api_key="test-key")


def test_gemini_with_credentials_is_accepted() -> None:
    settings = Settings(
        _env_file=None,
        genai_provider="gemini",
        genai_api_key="test-key",
        genai_model="gemini-3.8-flash",
    )

    assert settings.genai_provider == "gemini"
    assert settings.genai_api_key is not None
    assert settings.genai_api_key.get_secret_value() == "test-key"
    assert settings.genai_model == "gemini-3.8-flash"


def test_missing_credential_error_does_not_leak_the_key() -> None:
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            _env_file=None,
            genai_provider="gemini",
            genai_api_key="super-secret-key",
            genai_model="",
        )

    message = str(exc_info.value)
    assert "super-secret-key" not in message
    assert "GENAI_MODEL" in message


def test_missing_api_key_error_names_the_variable() -> None:
    with pytest.raises(ValidationError, match="GENAI_API_KEY"):
        Settings(_env_file=None, genai_provider="gemini", genai_model="gemini-3.8-flash")


def test_empty_api_key_is_none() -> None:
    settings = Settings(_env_file=None, genai_api_key="")

    assert settings.genai_api_key is None


def test_blank_api_key_is_none() -> None:
    settings = Settings(_env_file=None, genai_api_key="   ")

    assert settings.genai_api_key is None


def test_blank_model_is_none() -> None:
    settings = Settings(_env_file=None, genai_model="   ")

    assert settings.genai_model is None


def test_empty_model_is_none() -> None:
    settings = Settings(_env_file=None, genai_model="")

    assert settings.genai_model is None


def test_model_is_trimmed() -> None:
    settings = Settings(_env_file=None, genai_model="  gemini-3.8-flash  ")

    assert settings.genai_model == "gemini-3.8-flash"


def test_service_key_defaults_to_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GENAI_SERVICE_KEY", raising=False)

    settings = Settings(_env_file=None)

    assert settings.service_key is None


@pytest.mark.parametrize("value", ["", "   "])
def test_blank_service_key_is_none(value: str) -> None:
    settings = Settings(_env_file=None, service_key=value)

    assert settings.service_key is None


def test_reads_service_key_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GENAI_SERVICE_KEY", "test-service-key")

    settings = Settings(_env_file=None)

    assert settings.service_key is not None
    assert settings.service_key.get_secret_value() == "test-service-key"


def test_service_key_is_not_exposed_in_repr() -> None:
    settings = Settings(_env_file=None, service_key="super-secret-service-key")

    assert "super-secret-service-key" not in repr(settings)
    assert settings.service_key is not None
    assert settings.service_key.get_secret_value() == "super-secret-service-key"
