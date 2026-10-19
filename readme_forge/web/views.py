"""Routes. All README generation happens here; the browser only collects settings."""

from __future__ import annotations

import io
import zipfile
from dataclasses import asdict
from typing import Any

from flask import (
    Blueprint,
    Response,
    abort,
    current_app,
    jsonify,
    render_template,
    request,
    send_file,
    url_for,
)

from .. import __version__
from ..config import ICON_STYLES, ConfigError, config_to_dict, parse_config
from ..github import (
    GitHubClient,
    GitHubError,
    Profile,
    RateLimited,
    Unauthorized,
    UserNotFound,
    extract_username,
    fetch_profile,
)
from ..icons import bundled_icon, bundled_licence, recolor
from ..sections import HEADINGS, PRESETS, SECTIONS, build_context, generate
from ..socials import SOCIALS
from ..themes import THEMES
from ..urls import INSTANCE_NAMES, Instances
from ..workflows import Workflow, required_workflows
from .extensions import limiter
from .preview import render_preview

bp = Blueprint("web", __name__)

HEADING_ICONS = frozenset(h.icon for h in HEADINGS.values())


def _limit(name: str) -> Any:
    return limiter.limit(lambda: current_app.config[f"RATELIMIT_{name.upper()}"])


def _client() -> GitHubClient:
    return current_app.extensions["github"]


def _json_body() -> dict[str, Any]:
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        abort(400, description="Expected a JSON object.")
    return data


def _error(message: str | list[str], status: int) -> tuple[Response, int]:
    errors = message if isinstance(message, list) else [message]
    return jsonify(error=errors[0], errors=errors), status


def _github_error(exc: GitHubError) -> tuple[Response, int]:
    if isinstance(exc, UserNotFound):
        return _error(str(exc), 404)
    if isinstance(exc, RateLimited):
        return _error(str(exc), 429)
    if isinstance(exc, Unauthorized):
        current_app.logger.error("GitHub rejected the server's GITHUB_TOKEN")
        return _error("The server's GitHub token was rejected.", 502)
    return _error(str(exc), 502)


def _rate_limit() -> dict[str, int | None]:
    return asdict(_client().rate)


@bp.get("/")
def index() -> str:
    return render_template(
        "index.html",
        sections=SECTIONS,
        presets=PRESETS,
        themes=THEMES.values(),
        socials=SOCIALS,
        icon_styles=ICON_STYLES,
        instances=Instances(),
        instance_names=INSTANCE_NAMES,
        public=current_app.config["MODE"] == "public",
        token_configured=_client().authenticated,
        version=__version__,
    )


def _defaults(profile: Profile) -> dict[str, Any]:
    """Prefill values for a freshly fetched profile, mirroring the CLI's fallbacks."""
    user = profile.user
    live = sorted(
        (r for r in profile.repos if not r.fork and not r.archived),
        key=lambda r: -r.stargazers_count,
    )
    return {
        "custom": {
            "name": user.name or user.login,
            "bio": user.bio,
            "location": user.location,
            "website": user.blog,
        },
        "socials": {"twitter": user.twitter_username, "email": user.email, "website": user.blog},
        "featured": [r.name for r in live[:6]],
        "langs": profile.ranked_languages[:12],
    }


@bp.post("/api/profile")
@_limit("profile")
def profile() -> tuple[Response, int] | Response:
    username = extract_username(str(_json_body().get("username", "")))
    if not username:
        return _error("Enter a valid GitHub username or profile URL.", 400)
    try:
        data = fetch_profile(_client(), username)
    except GitHubError as exc:
        return _github_error(exc)

    repos = sorted(
        (r for r in data.repos if not r.fork and not r.archived),
        key=lambda r: -r.stargazers_count,
    )
    languages = data.ranked_languages[:24]
    return jsonify(
        login=data.user.login,
        defaults=_defaults(data),
        warning=None if data.repos_complete else "Repositories could not be loaded.",
        html={
            "card": render_template("fragments/profile_card.html", user=data.user),
            "repos": render_template("fragments/repo_list.html", repos=repos),
            "langs": render_template("fragments/lang_tags.html", languages=languages),
        },
        rateLimit=_rate_limit(),
    )


def _parse(data: dict[str, Any]):
    return parse_config(data, instances=current_app.extensions["instances"])


@bp.post("/api/generate")
@_limit("api")
def generate_readme() -> tuple[Response, int] | Response:
    try:
        config = _parse(_json_body())
    except ConfigError as exc:
        return _error(exc.errors, 400)
    if not config.username:
        return _error("Fetch a profile first.", 400)
    try:
        data = fetch_profile(_client(), config.username)
    except GitHubError as exc:
        return _github_error(exc)

    markdown = generate(build_context(data, config), config.section_ids)
    preview = markdown
    if config.options.icon_style == "local":
        # The README points at ./assets/icons, which only exists in the user's repo.
        base = url_for("web.index") + "icons/" + config.options.theme
        preview = generate(build_context(data, config, icon_base=base), config.section_ids)
    workflows = required_workflows(config.section_ids)
    return jsonify(
        markdown=markdown,
        html=render_preview(preview),
        workflows=[asdict(w) for w in workflows],
        workflowCount=len(workflows),
        workflowsText=_workflows_text(workflows),
        rateLimit=_rate_limit(),
    )


def _workflows_text(workflows: list[Workflow]) -> str:
    if not workflows:
        return (
            "No enabled section needs a GitHub Action.\n"
            "Contribution Snake and 3D Contributions render files a workflow commits "
            "to your profile repo."
        )
    files = "\n---\n\n".join(
        f"# .github/workflows/{w.file}  ({w.title})\n{w.yaml}" for w in workflows
    )
    return (
        "Add these files to your <username>/<username> profile repository, then run each once\n"
        "from the Actions tab so the images exist before your README links to them.\n\n" + files
    )


@bp.post("/api/config/validate")
@_limit("api")
def validate_config() -> tuple[Response, int] | Response:
    try:
        config = _parse(_json_body())
    except ConfigError as exc:
        return jsonify(valid=False, error=exc.errors[0], errors=exc.errors), 400
    return jsonify(valid=True, config=config_to_dict(config))


def _icon_svg(theme: str, name: str) -> str:
    if theme not in THEMES or name not in HEADING_ICONS:
        abort(404)
    return recolor(bundled_icon(name), THEMES[theme].accent)


@bp.get("/icons/<theme>/<name>.svg")
def icon(theme: str, name: str) -> Response:
    response = Response(_icon_svg(theme, name), mimetype="image/svg+xml")
    response.cache_control.max_age = 86400
    return response


@bp.get("/icons/<theme>.zip")
def icon_bundle(theme: str) -> Response:
    """Every heading icon recoloured for one theme, for users of the local icon style."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(HEADING_ICONS):
            archive.writestr(f"assets/icons/{name}.svg", _icon_svg(theme, name))
        archive.writestr("assets/icons/LICENSE", bundled_licence())
    buffer.seek(0)
    return send_file(buffer, "application/zip", as_attachment=True, download_name="icons.zip")
