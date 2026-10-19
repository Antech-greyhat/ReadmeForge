import pytest

from readme_forge.github import (
    GitHubClient,
    GitHubError,
    RateLimited,
    Response,
    TTLCache,
    Unauthorized,
    UserNotFound,
    extract_username,
    fetch_profile,
)
from tests.support import FixtureTransport

TOKEN = "ghp_secret_value_never_printed"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("octocat", "octocat"),
        ("https://github.com/octocat", "octocat"),
        ("github.com/octocat/Hello-World/", "octocat"),
        ("www.github.com/a-b", "a-b"),
        ("-bad", None),
        ("bad--", None),
        ("a" * 40, None),
        ("https://gitlab.com/octocat", None),
        ("", None),
    ],
)
def test_extract_username(value, expected):
    assert extract_username(value) == expected


def test_fetch_profile_reads_user_repos_and_languages(profile):
    assert profile.user.login == "octocat"
    assert len(profile.repos) == 8
    assert profile.lang_source == "bytes"
    assert profile.ranked_languages[0] == "CSS"


def test_fork_languages_are_not_fetched(client, transport):
    fetch_profile(client, "octocat")
    assert not any("linguist" in call for call in transport.calls)


def test_responses_are_cached_per_user_and_endpoint(client, transport):
    fetch_profile(client, "octocat")
    first = len(transport.calls)
    fetch_profile(client, "OctoCat")
    assert len(transport.calls) == first


def test_cache_expires():
    now = [0.0]
    cache = TTLCache(ttl=10, clock=lambda: now[0])
    cache.set("k", 1)
    assert cache.get("k") == 1
    now[0] = 10.0
    assert cache.get("k") is None


def test_cache_evicts_oldest_when_full():
    cache = TTLCache(ttl=10, max_entries=2)
    for key in "abc":
        cache.set(key, key)
    assert cache.get("a") is None
    assert cache.get("c") == "c"


def test_errors_are_not_cached(transport):
    transport.overrides["/users/octocat"] = Response(500, {}, b"")
    client = GitHubClient(transport=transport)
    with pytest.raises(GitHubError):
        fetch_profile(client, "octocat")
    del transport.overrides["/users/octocat"]
    assert fetch_profile(client, "octocat").user.login == "octocat"


@pytest.mark.parametrize(
    ("status", "headers", "error", "message"),
    [
        (404, {}, UserNotFound, "not found: octocat"),
        (401, {}, Unauthorized, "rejected the token"),
        (403, {"x-ratelimit-remaining": "0", "x-ratelimit-reset": "0"}, RateLimited, "rate limit"),
        (429, {}, RateLimited, "rate limit"),
        (403, {"x-ratelimit-remaining": "10"}, GitHubError, "refused"),
        (502, {}, GitHubError, "502"),
    ],
)
def test_status_errors_have_clear_messages(status, headers, error, message):
    transport = FixtureTransport({"/users/octocat": Response(status, headers, b"")})
    with pytest.raises(error, match=message) as info:
        fetch_profile(GitHubClient(TOKEN, transport=transport), "octocat")
    assert TOKEN not in str(info.value)


def test_rate_limit_hint_suggests_token_when_anonymous():
    transport = FixtureTransport({"/users/octocat": Response(429, {}, b"")})
    with pytest.raises(RateLimited, match="GITHUB_TOKEN"):
        fetch_profile(GitHubClient(transport=transport), "octocat")


def test_rate_limit_is_recorded():
    transport = FixtureTransport()
    client = GitHubClient(transport=transport)
    transport.overrides["/users/octocat"] = Response(
        200, {"x-ratelimit-remaining": "41", "x-ratelimit-limit": "60"}, b'{"login": "octocat"}'
    )
    fetch_profile(client, "octocat")
    assert client.rate.limit == 60


def test_language_fan_out_skipped_when_quota_is_low():
    transport = FixtureTransport()
    transport.overrides["/users/octocat/repos?per_page=100&sort=updated"] = Response(
        200,
        {"x-ratelimit-remaining": "1"},
        (transport.root / "octocat" / "repos.json").read_bytes(),
    )
    profile = fetch_profile(GitHubClient(transport=transport), "octocat")
    assert profile.lang_source == "primary"
    assert not any("/languages" in call for call in transport.calls)


def test_missing_repos_mark_profile_incomplete():
    transport = FixtureTransport(
        {"/users/octocat/repos?per_page=100&sort=updated": Response(403, {}, b"")}
    )
    profile = fetch_profile(GitHubClient(transport=transport), "octocat")
    assert profile.repos == ()
    assert not profile.repos_complete


def test_network_failure_on_languages_degrades_gracefully():
    class Flaky(FixtureTransport):
        def __call__(self, url, headers, timeout):
            if url.endswith("/languages"):
                raise GitHubError("Could not reach GitHub: timed out")
            return super().__call__(url, headers, timeout)

    profile = fetch_profile(GitHubClient(transport=Flaky()), "octocat")
    assert profile.lang_source == "primary"


def test_token_is_sent_but_never_shown():
    transport = FixtureTransport()
    client = GitHubClient(TOKEN, transport=transport)
    fetch_profile(client, "octocat")
    assert transport.headers_seen[0]["Authorization"] == "Bearer " + TOKEN
    assert TOKEN not in repr(client)
    assert TOKEN not in str(vars(client).get("rate"))


def test_timeout_is_passed_to_transport():
    seen = []

    def transport(url, headers, timeout):
        seen.append(timeout)
        return Response(404, {}, b"")

    with pytest.raises(UserNotFound):
        fetch_profile(GitHubClient(transport=transport, timeout=3), "octocat")
    assert seen == [3]
