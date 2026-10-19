"""Minimal GitHub REST client and the profile data the renderers need.

Stdlib only so the CLI installs without dependencies. The transport is injectable,
which is how the tests run against recorded fixtures without touching the network.
"""

from __future__ import annotations

import datetime
import json
import re
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any

API_ROOT = "https://api.github.com"
USERNAME_PATTERN = r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?"
_USERNAME_RE = re.compile(USERNAME_PATTERN)
_PROFILE_URL_RE = re.compile(
    r"^(?:https?://)?(?:www\.)?github\.com/(" + USERNAME_PATTERN + ")", re.I
)


def extract_username(value: str) -> str | None:
    """Accept a bare username or a github.com profile URL."""
    value = re.sub(r"/+$", "", (value or "").strip())
    match = _PROFILE_URL_RE.match(value)
    if match:
        return match.group(1)
    return value if _USERNAME_RE.fullmatch(value) else None


class GitHubError(Exception):
    """A GitHub failure with a message that is safe to show to end users."""

    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


class UserNotFound(GitHubError):
    pass


class Unauthorized(GitHubError):
    pass


class RateLimited(GitHubError):
    pass


@dataclass(frozen=True)
class Response:
    status: int
    headers: Mapping[str, str]
    body: bytes


Transport = Callable[[str, Mapping[str, str], float], Response]


def urllib_transport(url: str, headers: Mapping[str, str], timeout: float) -> Response:
    request = urllib.request.Request(url, headers=dict(headers))
    try:
        with urllib.request.urlopen(request, timeout=timeout) as res:
            return Response(res.status, _lower_keys(res.headers), res.read())
    except urllib.error.HTTPError as exc:
        return Response(exc.code, _lower_keys(exc.headers), b"")
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        reason = getattr(exc, "reason", exc)
        raise GitHubError(f"Could not reach GitHub: {reason}") from None


def _lower_keys(headers: Any) -> dict[str, str]:
    return {k.lower(): v for k, v in headers.items()} if headers else {}


@dataclass
class RateLimit:
    remaining: int | None = None
    limit: int | None = None
    reset: int | None = None


class TTLCache:
    """Thread-safe in-memory cache. Per process, so serverless instances do not share it."""

    def __init__(
        self, ttl: float, max_entries: int = 2048, clock: Callable[[], float] = time.monotonic
    ) -> None:
        self.ttl = ttl
        self.max_entries = max_entries
        self._clock = clock
        self._data: dict[Any, tuple[float, Any]] = {}
        self._lock = threading.Lock()

    def get(self, key: Any) -> Any | None:
        with self._lock:
            hit = self._data.get(key)
            if hit is None:
                return None
            if self._clock() >= hit[0]:
                del self._data[key]
                return None
            return hit[1]

    def set(self, key: Any, value: Any) -> None:
        if self.ttl <= 0:
            return
        with self._lock:
            self._data.pop(key, None)
            while len(self._data) >= self.max_entries:
                del self._data[next(iter(self._data))]
            self._data[key] = (self._clock() + self.ttl, value)


class GitHubClient:
    def __init__(
        self,
        token: str = "",
        *,
        timeout: float = 10.0,
        cache: TTLCache | None = None,
        transport: Transport = urllib_transport,
    ) -> None:
        self._token = token
        self.timeout = timeout
        self.cache = cache if cache is not None else TTLCache(ttl=300)
        self.rate = RateLimit()
        self._transport = transport

    def __repr__(self) -> str:
        return f"GitHubClient(authenticated={self.authenticated})"

    @property
    def authenticated(self) -> bool:
        return bool(self._token)

    def get(self, username: str, endpoint: str, path: str) -> tuple[int, Any]:
        """GET path, caching successful bodies under (username, endpoint)."""
        key = (username.lower(), endpoint, self.authenticated)
        cached = self.cache.get(key)
        if cached is not None:
            return 200, cached
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "readme-forge"}
        if self._token:
            headers["Authorization"] = "Bearer " + self._token
        res = self._transport(API_ROOT + path, headers, self.timeout)
        self._record_rate(res.headers)
        if res.status != 200:
            return res.status, None
        try:
            body = json.loads(res.body.decode("utf-8"))
        except ValueError:
            raise GitHubError("GitHub returned a response that is not JSON", res.status) from None
        self.cache.set(key, body)
        return 200, body

    def _record_rate(self, headers: Mapping[str, str]) -> None:
        def as_int(name: str) -> int | None:
            value = headers.get(name)
            return int(value) if value is not None and value.isdigit() else None

        remaining = as_int("x-ratelimit-remaining")
        if remaining is not None:
            self.rate = RateLimit(
                remaining, as_int("x-ratelimit-limit"), as_int("x-ratelimit-reset")
            )

    def error_for(self, status: int, username: str) -> GitHubError:
        if status == 404:
            return UserNotFound(f"GitHub user not found: {username}", status)
        if status == 401:
            return Unauthorized("GitHub rejected the token (401). Check GITHUB_TOKEN.", status)
        if status == 429 or (status == 403 and self.rate.remaining == 0):
            hint = "" if self.authenticated else " Set GITHUB_TOKEN to raise it to 5,000/hour."
            return RateLimited(f"GitHub API rate limit reached{self._reset_hint()}.{hint}", status)
        if status == 403:
            return GitHubError("GitHub refused the request (403).", status)
        return GitHubError(f"GitHub API error: {status}", status)

    def _reset_hint(self) -> str:
        if not self.rate.reset:
            return ""
        reset = datetime.datetime.fromtimestamp(self.rate.reset, tz=datetime.timezone.utc)
        return reset.strftime(", resets at %H:%M UTC")


@dataclass(frozen=True)
class User:
    login: str
    name: str = ""
    bio: str = ""
    location: str = ""
    blog: str = ""
    twitter_username: str = ""
    email: str = ""
    avatar_url: str = ""
    public_repos: int = 0
    followers: int = 0

    @classmethod
    def from_api(cls, data: Mapping[str, Any]) -> User:
        return cls(
            login=data["login"],
            name=data.get("name") or "",
            bio=data.get("bio") or "",
            location=data.get("location") or "",
            blog=data.get("blog") or "",
            twitter_username=data.get("twitter_username") or "",
            email=data.get("email") or "",
            avatar_url=data.get("avatar_url") or "",
            public_repos=data.get("public_repos") or 0,
            followers=data.get("followers") or 0,
        )


@dataclass(frozen=True)
class Repo:
    id: int
    name: str
    full_name: str
    html_url: str
    description: str = ""
    stargazers_count: int = 0
    forks_count: int = 0
    language: str = ""
    fork: bool = False
    archived: bool = False

    @classmethod
    def from_api(cls, data: Mapping[str, Any]) -> Repo:
        return cls(
            id=data["id"],
            name=data["name"],
            full_name=data["full_name"],
            html_url=data["html_url"],
            description=data.get("description") or "",
            stargazers_count=data.get("stargazers_count") or 0,
            forks_count=data.get("forks_count") or 0,
            language=data.get("language") or "",
            fork=bool(data.get("fork")),
            archived=bool(data.get("archived")),
        )


@dataclass(frozen=True)
class Profile:
    user: User
    repos: tuple[Repo, ...]
    # Language name to weight: bytes of code, or repo counts when bytes were unavailable.
    languages: dict[str, float] = field(default_factory=dict)
    # "bytes", "mixed" or "primary", which the Tech Stack section discloses.
    lang_source: str = "primary"
    repos_complete: bool = True

    @property
    def ranked_languages(self) -> list[str]:
        return sorted(self.languages, key=lambda lang: -self.languages[lang])


def aggregate_languages(
    client: GitHubClient, username: str, repos: tuple[Repo, ...]
) -> tuple[dict[str, float], str]:
    targets = [r for r in repos if not r.fork][: 40 if client.authenticated else 20]
    counts: dict[str, float] = {}
    for repo in targets:
        if repo.language:
            counts[repo.language] = counts.get(repo.language, 0) + 1

    def fetch(repo: Repo) -> tuple[int, Any]:
        try:
            return client.get(
                username, "languages/" + repo.name, f"/repos/{repo.full_name}/languages"
            )
        except GitHubError:
            return 0, None

    # Skip the fan-out when the remaining quota cannot cover it; it would only 403.
    budget = float("inf") if client.rate.remaining is None else client.rate.remaining
    totals: dict[str, float] = {}
    ok = 0
    if targets and budget >= len(targets):
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(fetch, targets))
        for status, body in results:
            if status != 200 or not isinstance(body, dict):
                continue
            ok += 1
            for lang, size in body.items():
                totals[lang] = totals.get(lang, 0) + size

    if ok == 0 or not totals:
        return counts, "primary"
    source = "bytes" if ok == len(targets) else "mixed"
    # Weight count-only languages against real bytes so they can still make the top cut.
    floor = max(1, min(totals.values()) / 2)
    for lang, n in counts.items():
        totals.setdefault(lang, floor * n)
    return totals, source


def fetch_profile(client: GitHubClient, username: str) -> Profile:
    status, user = client.get(username, "user", "/users/" + username)
    if status != 200:
        raise client.error_for(status, username)
    status, repos_data = client.get(
        username, "repos", f"/users/{username}/repos?per_page=100&sort=updated"
    )
    complete = status == 200 and isinstance(repos_data, list)
    repos = tuple(Repo.from_api(r) for r in repos_data) if complete else ()
    languages, source = aggregate_languages(client, username, repos)
    return Profile(User.from_api(user), repos, languages, source, complete)
