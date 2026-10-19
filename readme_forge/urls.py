"""Builders for every image and link URL a README embeds.

The five self-hostable widget families take their base URL from Instances, so users can
point them at their own deployments when the shared public ones are rate-limited.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, fields, replace

from .escaping import enc, qs, safe_url
from .languages import LangMeta


@dataclass(frozen=True)
class Instances:
    stats: str = "https://github-readme-stats.vercel.app"
    streak: str = "https://streak-stats.demolab.com"
    trophy: str = "https://github-profile-trophy.vercel.app"
    activity: str = "https://github-readme-activity-graph.vercel.app"
    summary: str = "https://github-profile-summary-cards.vercel.app"

    def to_dict(self) -> dict[str, str]:
        return {f.name: getattr(self, f.name) for f in fields(self)}


INSTANCE_NAMES: tuple[str, ...] = tuple(f.name for f in fields(Instances))
INSTANCE_ENV_PREFIX = "READMEFORGE_INSTANCE_"


def normalize_instance_url(url: str) -> str:
    """Validate a widget base URL. Only https is accepted because GitHub's image proxy needs it."""
    clean = safe_url(url.strip(), ["https"]) if isinstance(url, str) else ""
    if not clean or "?" in clean or "#" in clean:
        raise ValueError(f"{url!r} is not an https base URL without query or fragment")
    return clean.rstrip("/")


def with_instances(base: Instances, overrides: Mapping[str, str]) -> Instances:
    """Apply name->URL overrides on top of base, raising ValueError on bad names or URLs."""
    changes = {}
    for name, url in overrides.items():
        if name not in INSTANCE_NAMES:
            raise ValueError(
                f"unknown instance {name!r}, expected one of {', '.join(INSTANCE_NAMES)}"
            )
        try:
            changes[name] = normalize_instance_url(url)
        except ValueError as exc:
            raise ValueError(f"instance {name}: {exc}") from None
    return replace(base, **changes)


def instances_from_env(environ: Mapping[str, str]) -> Instances:
    overrides = {
        name: environ[INSTANCE_ENV_PREFIX + name.upper()]
        for name in INSTANCE_NAMES
        if environ.get(INSTANCE_ENV_PREFIX + name.upper())
    }
    return with_instances(Instances(), overrides)


def shield_badge(
    label: str, message: str, color: str, logo: str | None = None, logo_color: str | None = None
) -> str:
    # Query form rather than path form: the path form splits messages on hyphens.
    params = [("label", label), ("message", message), ("color", color), ("style", "for-the-badge")]
    if logo:
        params += [("logo", logo), ("logoColor", logo_color or "white")]
    return "https://img.shields.io/static/v1?" + qs(params)


def lang_badge(lang: str, meta: LangMeta) -> str:
    params = [("label", ""), ("message", lang), ("color", meta.color), ("style", "flat")]
    if meta.slug:
        params += [("logo", meta.slug), ("logoColor", meta.logo_color or "white")]
    return "https://img.shields.io/static/v1?" + qs(params)


def stats_url(base: str, login: str, theme: str) -> str:
    return (
        f"{base}/api?username={enc(login)}&show_icons=true&theme={theme}"
        "&hide_border=true&count_private=true&include_all_commits=true"
    )


def top_langs_url(base: str, login: str, theme: str, layout: str = "compact") -> str:
    return (
        f"{base}/api/top-langs/?username={enc(login)}&layout={layout}&theme={theme}"
        "&hide_border=true&langs_count=8"
    )


def pin_url(base: str, login: str, repo: str, theme: str) -> str:
    return f"{base}/api/pin/?username={enc(login)}&repo={enc(repo)}&theme={theme}&hide_border=true"


def streak_url(base: str, login: str, theme: str) -> str:
    return f"{base}?user={enc(login)}&theme={theme}&hide_border=true"


def trophy_url(base: str, login: str, theme: str, rows: int, cols: int) -> str:
    return (
        f"{base}/?username={enc(login)}&theme={theme}&no-frame=true&margin-w=8"
        f"&row={rows}&column={cols}"
    )


def activity_url(base: str, login: str, theme: str) -> str:
    return f"{base}/graph?username={enc(login)}&theme={theme}&hide_border=true&area=true&radius=8"


def summary_card_url(base: str, login: str, card: str, theme: str) -> str:
    return f"{base}/api/cards/{card}?username={enc(login)}&theme={theme}"


def views_url(login: str) -> str:
    return (
        f"https://komarev.com/ghpvc/?username={enc(login)}"
        "&label=Profile+Views&color=7C6AF7&style=for-the-badge"
    )


def views_compact_url(login: str) -> str:
    return f"https://komarev.com/ghpvc/?username={enc(login)}&style=flat-square"


def followers_badge_url(login: str) -> str:
    return f"https://img.shields.io/github/followers/{enc(login)}?style=social"


def followers_count_url(login: str) -> str:
    return (
        f"https://img.shields.io/github/followers/{enc(login)}"
        "?label=Followers&style=for-the-badge&color=7C6AF7&logo=github&logoColor=white"
    )


def stars_badge_url(login: str) -> str:
    return f"https://img.shields.io/github/stars/{enc(login)}?style=social"


def typing_url(lines: list[str]) -> str:
    # Lines join on a literal semicolon; an encoded %3B would render as text.
    joined = ";".join(enc(line.replace(";", "")) for line in lines)
    return (
        "https://readme-typing-svg.demolab.com?font=DM+Mono&size=24&duration=3200"
        "&pause=800&color=7C6AF7&center=true&vCenter=true&width=600&height=60&lines=" + joined
    )


def banner_url(text: str) -> str:
    return (
        "https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=12,24"
        "&height=180&section=header&fontSize=44&fontColor=ffffff&animation=fadeIn&text=" + enc(text)
    )


def footer_wave_url(text: str) -> str:
    return (
        "https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=6,11,20"
        "&height=120&section=footer&fontSize=20&fontColor=ffffff&animation=twinkling&text="
        + enc(text)
    )


def chart_url(login: str, accent: str) -> str:
    return f"https://ghchart.rshah.org/{accent}/{enc(login)}"


def git_animals_url(login: str) -> str:
    return f"https://render.gitanimals.org/farms/{enc(login)}"


# These two read files that a workflow commits into the user's profile repository.
def contrib3d_url(login: str) -> str:
    user = enc(login)
    return f"https://raw.githubusercontent.com/{user}/{user}/HEAD/profile-3d-contrib/profile-night-rainbow.svg"


def snake_url(login: str, dark: bool) -> str:
    user = enc(login)
    suffix = "-dark" if dark else ""
    return f"https://raw.githubusercontent.com/{user}/{user}/output/github-snake{suffix}.svg"


JOKES_URL = "https://readme-jokes.vercel.app/api"
AWESOME_BADGE_URL = "https://awesome.re/badge.svg"
SPONSORS_BADGE_URL = (
    "https://img.shields.io/badge/GitHub%20Sponsors-EA4AAA"
    "?style=for-the-badge&logo=githubsponsors&logoColor=white"
)


def sponsors_url(login: str) -> str:
    return f"https://github.com/sponsors/{enc(login)}"


def profile_url(login: str) -> str:
    return f"https://github.com/{enc(login)}"


def quote_card_url(theme: str) -> str:
    return f"https://quotes-github-readme.vercel.app/api?type=horizontal&theme={theme}"


def iconify_url(icon: str, accent: str) -> str:
    return f"https://api.iconify.design/tabler/{icon}.svg?color=%23{accent}&height=24"
