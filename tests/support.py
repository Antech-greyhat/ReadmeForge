"""Shared test helpers: recorded fixtures and a transport that serves them."""

from __future__ import annotations

import datetime
import json
from collections.abc import Mapping
from pathlib import Path

from readme_forge.github import Response

FIXTURES = Path(__file__).parent / "fixtures"
GOLDEN = Path(__file__).parent / "golden"
TODAY = datetime.date(2026, 1, 15)


class FixtureTransport:
    """Serves recorded API responses from tests/fixtures/github/<user>/."""

    def __init__(self, overrides: Mapping[str, Response] | None = None) -> None:
        self.root = FIXTURES / "github"
        self.overrides = dict(overrides or {})
        self.calls: list[str] = []
        self.headers_seen: list[Mapping[str, str]] = []

    def __call__(self, url: str, headers: Mapping[str, str], timeout: float) -> Response:
        path = url.removeprefix("https://api.github.com")
        self.calls.append(path)
        self.headers_seen.append(headers)
        if path in self.overrides:
            return self.overrides[path]
        parts = path.split("?")[0].strip("/").split("/")
        if parts[0] == "users" and len(parts) == 2:
            file = self.root / parts[1] / "user.json"
        elif parts[0] == "users" and parts[2] == "repos":
            file = self.root / parts[1] / "repos.json"
        else:
            file = self.root / parts[1] / "languages" / f"{parts[2]}.json"
        if not file.exists():
            return Response(404, {}, b"")
        return Response(200, {}, file.read_bytes())


def load_json(relative: str) -> object:
    return json.loads((FIXTURES / relative).read_text(encoding="utf-8"))
