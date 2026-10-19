"""Flask application factory for the README.forge web UI."""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any

from flask import Flask, Response, jsonify
from werkzeug.exceptions import HTTPException
from werkzeug.middleware.proxy_fix import ProxyFix

from ..github import GitHubClient, TTLCache
from ..urls import instances_from_env
from .extensions import limiter
from .views import bp

MODES = ("local", "public")

# Public deployments share one GitHub token between every visitor, so profile lookups
# (up to 42 API calls each) are throttled harder than README regeneration.
RATE_LIMITS = {
    "local": {"profile": "30/minute", "api": "120/minute"},
    "public": {"profile": "6/minute;60/hour", "api": "60/minute;600/hour"},
}

CONTENT_SECURITY_POLICY = "; ".join(
    [
        "default-src 'none'",
        "script-src 'self'",
        "style-src 'self' https://fonts.googleapis.com",
        "font-src https://fonts.gstatic.com",
        "img-src 'self' https: data:",
        "connect-src 'self'",
        "base-uri 'none'",
        "form-action 'none'",
        "frame-ancestors 'none'",
    ]
)


def _settings_from_env(environ: Mapping[str, str]) -> dict[str, Any]:
    mode = environ.get("READMEFORGE_MODE", "local")
    return {
        "MODE": mode,
        "GITHUB_TOKEN": environ.get("GITHUB_TOKEN", ""),
        "CACHE_TTL": int(environ.get("READMEFORGE_CACHE_TTL", "600")),
        "TRUSTED_PROXIES": int(environ.get("READMEFORGE_TRUSTED_PROXIES", "0")),
        "RATELIMIT_STORAGE_URI": environ.get("READMEFORGE_RATELIMIT_STORAGE", "memory://"),
    }


def create_app(settings: Mapping[str, Any] | None = None) -> Flask:
    """Build the app. settings override values read from the environment, mainly for tests."""
    app = Flask(__name__)
    app.config.update(_settings_from_env(os.environ))
    app.config.update(MAX_CONTENT_LENGTH=64 * 1024, JSON_SORT_KEYS=False)
    app.config.update(settings or {})

    mode = app.config["MODE"]
    if mode not in MODES:
        raise ValueError(f"READMEFORGE_MODE must be one of {', '.join(MODES)}, got {mode!r}")
    for name, limit in RATE_LIMITS[mode].items():
        app.config.setdefault(f"RATELIMIT_{name.upper()}", limit)

    proxies = app.config["TRUSTED_PROXIES"]
    if proxies:
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=proxies, x_proto=proxies)  # type: ignore[method-assign]

    app.extensions["github"] = GitHubClient(
        app.config.pop("GITHUB_TOKEN"), cache=TTLCache(ttl=app.config["CACHE_TTL"])
    )
    app.extensions["instances"] = instances_from_env(os.environ)

    limiter.init_app(app)
    app.register_blueprint(bp)
    app.after_request(_security_headers)
    app.register_error_handler(HTTPException, _http_error)
    return app


def _security_headers(response: Response) -> Response:
    response.headers["Content-Security-Policy"] = CONTENT_SECURITY_POLICY
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Frame-Options"] = "DENY"
    return response


def _http_error(exc: HTTPException) -> tuple[Response, int]:
    messages = {
        413: "Request body is larger than 64 KB.",
        429: "Too many requests, slow down and try again shortly.",
    }
    message = messages.get(exc.code or 500, exc.description or exc.name)
    return jsonify(error=message), exc.code or 500
