from __future__ import annotations

import socket

import pytest

from readme_forge.github import GitHubClient, Profile, TTLCache, fetch_profile
from tests.support import FixtureTransport


@pytest.fixture(autouse=True)
def no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*args: object, **kwargs: object) -> None:
        raise RuntimeError("tests must not open network connections")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)


@pytest.fixture
def transport() -> FixtureTransport:
    return FixtureTransport()


@pytest.fixture
def client(transport: FixtureTransport) -> GitHubClient:
    return GitHubClient(transport=transport, cache=TTLCache(ttl=60))


@pytest.fixture
def profile(client: GitHubClient) -> Profile:
    return fetch_profile(client, "octocat")
