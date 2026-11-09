"""Shared test fixtures."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from thehouse_genai.api.app import create_app
from thehouse_genai.infrastructure.config import Settings


@pytest.fixture()
def settings() -> Settings:
    """Deterministic settings that never read a developer `.env`."""

    return Settings(app_env="test", _env_file=None)


@pytest.fixture()
def client(settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(settings)) as test_client:
        yield test_client
