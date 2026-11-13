"""Shared test fixtures."""

from __future__ import annotations

import socket
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from thehouse_genai.api.app import create_app
from thehouse_genai.infrastructure.config import Settings

_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "::1", "localhost"})


def _host_of(address: object) -> str:
    """Extract the host of a socket address."""

    if isinstance(address, tuple) and address:
        return str(address[0])
    if isinstance(address, bytes):
        return address.decode(errors="replace")
    return str(address)


def _is_loopback(address: object) -> bool:
    """Return whether an address stays on the loopback interface."""

    host = _host_of(address).strip().lower()
    if host.startswith("127."):
        return True
    return host in _LOOPBACK_HOSTS


@pytest.fixture(autouse=True)
def block_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reject any network access that leaves the machine.

    Sockets can still be created: `asyncio.run` needs `socketpair`, which on Windows
    connects to 127.0.0.1. Only connections and DNS resolutions towards a non-loopback
    address are rejected, before any real traffic is attempted.
    """

    original_connect = socket.socket.connect
    original_connect_ex = socket.socket.connect_ex
    original_create_connection = socket.create_connection
    original_getaddrinfo = socket.getaddrinfo

    def connect(self: socket.socket, address: Any) -> None:
        if not _is_loopback(address):
            raise RuntimeError(
                f"network access is forbidden in tests: {_host_of(address)}"
            )
        original_connect(self, address)

    def connect_ex(self: socket.socket, address: Any) -> int:
        if not _is_loopback(address):
            raise RuntimeError(
                f"network access is forbidden in tests: {_host_of(address)}"
            )
        return original_connect_ex(self, address)

    def create_connection(address: Any, *args: Any, **kwargs: Any) -> socket.socket:
        if not _is_loopback(address):
            raise RuntimeError(
                f"network access is forbidden in tests: {_host_of(address)}"
            )
        return original_create_connection(address, *args, **kwargs)

    def getaddrinfo(host: str, port: Any, *args: Any, **kwargs: Any) -> list[Any]:
        if not _is_loopback(host):
            raise RuntimeError(f"network access is forbidden in tests: {host}")
        return original_getaddrinfo(host, port, *args, **kwargs)

    monkeypatch.setattr(socket.socket, "connect", connect)
    monkeypatch.setattr(socket.socket, "connect_ex", connect_ex)
    monkeypatch.setattr(socket, "create_connection", create_connection)
    monkeypatch.setattr(socket, "getaddrinfo", getaddrinfo)


@pytest.fixture()
def settings() -> Settings:
    """Deterministic settings that never read a developer `.env`."""

    return Settings(app_env="test", _env_file=None)


@pytest.fixture()
def client(settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(settings)) as test_client:
        yield test_client
