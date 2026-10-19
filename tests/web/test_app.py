import io
import json
import zipfile

import pytest

pytest.importorskip("flask")

from readme_forge.github import GitHubClient, Response
from readme_forge.web.app import create_app
from tests.support import FIXTURES, GOLDEN, FixtureTransport, load_json


def make_app(transport=None, token="", **settings):
    app = create_app({"TESTING": True, "MODE": "local", "GITHUB_TOKEN": token, **settings})
    app.extensions["github"] = GitHubClient(token, transport=transport or FixtureTransport())
    return app


@pytest.fixture
def transport():
    return FixtureTransport()


@pytest.fixture
def client(transport):
    return make_app(transport).test_client()


def test_index_renders_controls_without_token_field(client):
    res = client.get("/")
    body = res.get_data(as_text=True)
    assert res.status_code == 200
    assert 'data-section="snake"' in body
    assert 'type="password"' not in body
    assert "GITHUB_TOKEN" in body


def test_public_mode_hides_local_only_ui(transport):
    body = make_app(transport, MODE="public").test_client().get("/").get_data(as_text=True)
    assert "GITHUB_TOKEN" not in body


def test_security_headers(client):
    headers = client.get("/").headers
    csp = headers["Content-Security-Policy"]
    assert "script-src 'self'" in csp
    assert "img-src 'self' https: data:" in csp
    assert "https://fonts.googleapis.com" in csp
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["Referrer-Policy"] == "no-referrer"


def test_static_assets_are_served(client):
    assert client.get("/static/js/app.js").status_code == 200
    assert client.get("/static/css/app.css").status_code == 200
    assert client.get("/static/img/favicon.svg").status_code == 200


def test_profile_returns_fragments_and_defaults(client):
    res = client.post("/api/profile", json={"username": "https://github.com/octocat"})
    data = res.get_json()
    assert res.status_code == 200
    assert data["login"] == "octocat"
    assert 'value="Spoon-Knife"' in data["html"]["repos"]
    assert "linguist" not in data["html"]["repos"]
    assert data["defaults"]["custom"]["name"] == "The Octocat"
    assert data["defaults"]["featured"][0] == "Spoon-Knife"


def test_profile_escapes_api_data(transport):
    user = json.loads((FIXTURES / "github" / "octocat" / "user.json").read_text("utf-8"))
    user["bio"] = "<script>alert(1)</script>"
    transport.overrides["/users/octocat"] = Response(200, {}, json.dumps(user).encode())
    data = make_app(transport).test_client().post("/api/profile", json={"username": "octocat"})
    card = data.get_json()["html"]["card"]
    assert "<script>" not in card
    assert "&lt;script&gt;" in card


@pytest.mark.parametrize(
    ("body", "status"),
    [
        ({"username": "not a user!"}, 400),
        ({"username": ""}, 400),
        ({"username": "ghost-user-xyz"}, 404),
    ],
)
def test_profile_rejects_bad_usernames(client, body, status):
    res = client.post("/api/profile", json=body)
    assert res.status_code == status
    assert res.get_json()["error"]


def test_profile_reports_rate_limit(transport):
    transport.overrides["/users/octocat"] = Response(429, {}, b"")
    res = make_app(transport).test_client().post("/api/profile", json={"username": "octocat"})
    assert res.status_code == 429
    assert "rate limit" in res.get_json()["error"]


@pytest.mark.parametrize("path", ["/api/profile", "/api/generate", "/api/config/validate"])
def test_api_rejects_non_json(client, path):
    res = client.post(path, data="username=octocat", content_type="text/plain")
    assert res.status_code == 400
    assert res.get_json()["error"]


@pytest.mark.parametrize("path", ["/api/profile", "/api/generate", "/api/config/validate"])
def test_api_rejects_oversized_bodies(client, path):
    res = client.post(path, data=json.dumps({"x": "a" * 70_000}), content_type="application/json")
    assert res.status_code == 413
    assert "64 KB" in res.get_json()["error"]


def test_api_routes_are_post_only(client):
    assert client.get("/api/generate").status_code == 405


def test_generate_matches_cli_output(client):
    res = client.post("/api/generate", json={"username": "octocat"})
    data = res.get_json()
    assert res.status_code == 200
    assert data["markdown"] == (GOLDEN / "classic.md").read_text(encoding="utf-8")
    assert data["workflowCount"] == 0


def test_generate_sanitises_preview_and_lists_workflows(client):
    data = client.post("/api/generate", json=load_json("configs/full.json")).get_json()
    assert "<script" not in data["html"]
    assert "onerror=" not in data["html"].replace("onerror=alert(1)&gt;", "")
    assert [w["file"] for w in data["workflows"]] == ["profile-3d-contrib.yml", "snake.yml"]
    assert "Platane/snk" in data["workflowsText"]


@pytest.mark.parametrize(
    ("body", "message"),
    [
        ({"username": "octocat", "sections": ["header", "evil"]}, "unknown section"),
        ({"username": "octocat", "options": {"theme": "x"}}, "options.theme"),
        ({"sections": ["header"]}, "Fetch a profile first"),
        ({"username": "octocat", "instances": {"stats": "javascript:alert(1)"}}, "instance"),
    ],
)
def test_generate_rejects_invalid_settings(client, body, message):
    res = client.post("/api/generate", json=body)
    assert res.status_code == 400
    assert message in " ".join(res.get_json()["errors"])


def test_generate_never_uses_a_client_supplied_token(transport):
    app = make_app(transport)
    app.test_client().post("/api/generate", json={"username": "octocat", "token": "ghp_x"})
    assert all("Authorization" not in h for h in transport.headers_seen)


def test_server_token_is_used_but_not_stored_in_config(transport):
    app = create_app({"TESTING": True, "GITHUB_TOKEN": "ghp_server"})
    assert "GITHUB_TOKEN" not in app.config
    assert app.extensions["github"].authenticated


def test_local_icons_preview_from_server(client):
    body = {"username": "octocat", "sections": ["stats"], "options": {"iconStyle": "local"}}
    data = client.post("/api/generate", json=body).get_json()
    assert "./assets/icons/chart-bar.svg" in data["markdown"]
    assert 'src="/icons/tokyonight/chart-bar.svg"' in data["html"]


def test_validate_config(client):
    res = client.post("/api/config/validate", json=load_json("configs/full.json"))
    data = res.get_json()
    assert data["valid"] is True
    assert data["config"]["options"]["theme"] == "dracula"


def test_validate_config_reports_all_errors(client):
    res = client.post("/api/config/validate", json={"sections": ["x"], "options": {"theme": "y"}})
    assert res.status_code == 400
    assert len(res.get_json()["errors"]) == 2


def test_icon_route(client):
    res = client.get("/icons/dracula/trophy.svg")
    assert res.status_code == 200
    assert res.mimetype == "image/svg+xml"
    assert 'stroke="#BD93F9"' in res.get_data(as_text=True)


@pytest.mark.parametrize("path", ["/icons/dracula/etc.svg", "/icons/nope/trophy.svg"])
def test_icon_route_rejects_unknown(client, path):
    assert client.get(path).status_code == 404


def test_icon_bundle(client):
    res = client.get("/icons/nord.zip")
    names = zipfile.ZipFile(io.BytesIO(res.data)).namelist()
    assert "assets/icons/trophy.svg" in names
    assert "assets/icons/LICENSE" in names


def test_rate_limit_applies_per_ip(transport):
    app = make_app(transport, RATELIMIT_PROFILE="2/minute")
    web = app.test_client()
    codes = [web.post("/api/profile", json={"username": "octocat"}).status_code for _ in range(3)]
    assert codes == [200, 200, 429]
    other = web.post(
        "/api/profile", json={"username": "octocat"}, environ_base={"REMOTE_ADDR": "10.0.0.9"}
    )
    assert other.status_code == 200


def test_public_mode_has_stricter_limits(transport):
    app = make_app(transport, MODE="public")
    assert app.config["RATELIMIT_PROFILE"] == "6/minute;60/hour"


def test_invalid_mode_is_rejected():
    with pytest.raises(ValueError, match="READMEFORGE_MODE"):
        create_app({"MODE": "prod"})


def test_trusted_proxy_uses_forwarded_ip(transport):
    app = make_app(transport, RATELIMIT_PROFILE="1/minute", TRUSTED_PROXIES=1)
    web = app.test_client()

    def call(ip):
        return web.post(
            "/api/profile", json={"username": "octocat"}, headers={"X-Forwarded-For": ip}
        ).status_code

    assert [call("1.1.1.1"), call("1.1.1.1"), call("2.2.2.2")] == [200, 429, 200]
