"""Section renderers and the README generator.

Each renderer is a pure function from a Context to a list of Markdown lines; an empty
list opts the section out. Adding a section means adding a SectionSpec, a renderer
named r_<id> and a test.
"""

from __future__ import annotations

import datetime
import re
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING

from . import urls
from .escaping import escape_attr, escape_html, escape_md, escape_md_text, safe_url
from .github import Profile, Repo
from .languages import lang_meta
from .socials import SOCIAL_KEYS, SOCIALS
from .themes import widget_theme

if TYPE_CHECKING:
    from .config import Config, Options


@dataclass(frozen=True)
class SectionSpec:
    id: str
    label: str
    default_on: bool = False
    # Key into workflows.WORKFLOWS for sections that embed files a GitHub Action produces.
    workflow: str | None = None


SECTIONS: tuple[SectionSpec, ...] = (
    SectionSpec("banner", "Banner Header"),
    SectionSpec("header", "Introduction", True),
    SectionSpec("typing", "Animated Typing", True),
    SectionSpec("badges", "Profile Badges", True),
    SectionSpec("connect", "Connect with Me", True),
    SectionSpec("techstack", "Tech Stack", True),
    SectionSpec("featured", "Featured Projects", True),
    SectionSpec("stats", "GitHub Stats", True),
    SectionSpec("streak", "Streak Stats", True),
    SectionSpec("activity", "Activity Graph", True),
    SectionSpec("trophies", "Trophies", True),
    SectionSpec("learning", "Currently Learning", True),
    SectionSpec("quote", "Dev Quote"),
    SectionSpec("hero", "Hero GIF"),
    SectionSpec("about", "About Me (bullets)"),
    SectionSpec("profilestats", "Profile Stats Table"),
    SectionSpec("cards", "Stats Card Grid"),
    SectionSpec("contrib3d", "3D Contributions", workflow="contrib3d"),
    SectionSpec("chart", "Contribution Chart"),
    SectionSpec("gitanimals", "Git Animals Farm"),
    SectionSpec("funzone", "Fun Zone"),
    SectionSpec("snake", "Contribution Snake", workflow="snake"),
    SectionSpec("sponsors", "Sponsor Me"),
    SectionSpec("footerwave", "Footer Wave"),
)
SECTION_IDS: tuple[str, ...] = tuple(s.id for s in SECTIONS)

PRESETS: dict[str, tuple[str, ...]] = {
    "classic": tuple(s.id for s in SECTIONS if s.default_on),
    "showcase": (
        "hero", "header", "about", "typing", "profilestats", "contrib3d", "cards", "trophies",
        "chart", "techstack", "featured", "gitanimals", "funzone", "connect", "snake",
        "sponsors", "footerwave",
    ),
}  # fmt: skip


@dataclass(frozen=True)
class Heading:
    emoji: str
    title: str
    # Tabler icon name, used by both the iconify and the local icon styles.
    icon: str


HEADINGS: dict[str, Heading] = {
    "connect": Heading("🔗", "Connect with Me", "link"),
    "techstack": Heading("⚡", "Tech Stack", "bolt"),
    "featured": Heading("★", "Featured Projects", "star"),
    "stats": Heading("📊", "GitHub Stats", "chart-bar"),
    "streak": Heading("🔥", "Contribution Streak", "flame"),
    "activity": Heading("∿", "Contribution Activity", "activity"),
    "trophies": Heading("🏆", "Trophies", "trophy"),
    "learning": Heading("🌱", "Currently Learning", "plant"),
    "quote": Heading("💬", "Dev Quote", "quote"),
    "about": Heading("👨‍💻", "About Me", "user-code"),
    "profilestats": Heading("📊", "Profile Stats", "chart-dots"),
    "cards": Heading("🖥️", "GitHub Activity", "device-desktop-analytics"),
    "gitanimals": Heading("🐾", "Git Animals", "paw"),
    "funzone": Heading("✨", "Fun Zone", "sparkles"),
    "snake": Heading("🐍", "My Code Kingdom", "grid-dots"),
    "sponsors": Heading("☕", "Fuel My Next Project", "coffee"),
}

LOCAL_ICON_BASE = "./assets/icons"

DEFAULT_HERO_GIF = "https://user-images.githubusercontent.com/74038190/212284158-e840e285-664b-44d7-b79b-e264b5e54825.gif"
DEFAULT_ABOUT_GIF = "https://user-images.githubusercontent.com/74038190/229223263-cf2e4b07-2615-4f87-9c38-e37600f8381a.gif"
ACCENT_GIF = "https://raw.githubusercontent.com/innng/innng/master/assets/kyubey.gif"
DEFAULT_LEARNING = "I'm always exploring new technologies and expanding my skill set."
DEFAULT_FOOTER_TEXT = "Thanks for visiting my profile!"
FOWLER_QUOTE = (
    '> "Any fool can write code that a computer can understand. '
    'Good programmers write code that humans can understand." — Martin Fowler'
)
CREDIT = (
    '<p align="center">Made with ❤️ by '
    '<a href="https://github.com/Antech-greyhat">Antech-greyhat</a></p>'
)


@dataclass(frozen=True)
class Totals:
    repos: int
    stars: int
    forks: int
    followers: int
    # The repo list is capped at 100, so sums undercount past that and say so.
    capped: bool


@dataclass(frozen=True)
class Context:
    login: str
    name: str
    tagline: str
    bio: str
    location: str
    website: str
    socials: Mapping[str, str]
    typing_lines: tuple[str, ...]
    langs: tuple[str, ...]
    lang_source: str
    featured: tuple[Repo, ...]
    totals: Totals
    options: Options
    instances: urls.Instances
    year: int
    icon_base: str = LOCAL_ICON_BASE

    def wt(self, widget: str) -> str:
        return widget_theme(self.options.theme, widget)


def build_context(
    profile: Profile,
    config: Config,
    *,
    today: datetime.date | None = None,
    icon_base: str = LOCAL_ICON_BASE,
) -> Context:
    user, repos, custom = profile.user, profile.repos, config.custom

    def custom_or(key: str, fallback: str) -> str:
        value = custom.get(key)
        return fallback if value is None else value

    socials = {k: config.socials.get(k, "") for k in SOCIAL_KEYS}
    if not socials["twitter"] and user.twitter_username:
        socials["twitter"] = user.twitter_username
    if not socials["email"] and user.email:
        socials["email"] = user.email
    if not socials["website"] and user.blog:
        socials["website"] = user.blog

    ranked = profile.ranked_languages
    typing_lines = config.options.typing_lines
    if not typing_lines:
        defaults = [user.bio[:60]] if user.bio else []
        if ranked:
            defaults.append(ranked[0] + " Developer")
        typing_lines = (*defaults, "Always learning something new")

    by_name = {r.name: r for r in repos}
    if config.featured is not None:
        featured = tuple(by_name[n] for n in config.featured if n in by_name)
    else:
        live = sorted(
            (r for r in repos if not r.fork and not r.archived), key=lambda r: -r.stargazers_count
        )
        featured = tuple(live[: config.options.featured_count])

    own = [r for r in repos if not r.fork]
    return Context(
        login=user.login,
        name=custom.get("name") or user.name or user.login,
        tagline=custom.get("tagline") or "",
        bio=custom_or("bio", user.bio),
        location=custom_or("location", user.location),
        website=safe_url(custom_or("website", user.blog), ["http", "https"]),
        socials=socials,
        typing_lines=typing_lines,
        langs=tuple(config.langs or ranked[:12]),
        lang_source=profile.lang_source,
        featured=featured,
        totals=Totals(
            repos=user.public_repos,
            stars=sum(r.stargazers_count for r in own),
            forks=sum(r.forks_count for r in own),
            followers=user.followers,
            capped=user.public_repos > len(repos),
        ),
        options=config.options,
        instances=config.instances,
        year=(today or datetime.date.today()).year,
        icon_base=icon_base,
    )


def heading(ctx: Context, section_id: str) -> str:
    spec = HEADINGS[section_id]
    style = ctx.options.icon_style
    if style == "iconify":
        src = urls.iconify_url(spec.icon, ctx.wt("accent"))
        lead = f'<img src="{escape_attr(src)}" alt="" height="24" />'
    elif style == "local":
        lead = f'<img src="{escape_attr(ctx.icon_base)}/{spec.icon}.svg" alt="" height="24" />'
    else:
        lead = spec.emoji
    line = f"## {lead} {spec.title}"
    if ctx.options.heading_gif:
        line += f' <img height="32" src="{ACCENT_GIF}" alt="" />'
    return line


def heading_icons(section_ids: Iterable[str]) -> list[str]:
    return [HEADINGS[s].icon for s in section_ids if s in HEADINGS]


def _img(src: str, alt: str, extra: str = "") -> str:
    return f'<img {extra}src="{escape_attr(src)}" alt="{alt}" />'


def _centered(*lines: str) -> list[str]:
    return ['<p align="center">', *(f"  {line}" for line in lines), "</p>"]


def r_banner(ctx: Context) -> list[str]:
    text = ctx.options.banner_text or ctx.name
    if not text:
        return []
    return [f'<img src="{escape_attr(urls.banner_url(text))}" alt="banner" width="100%" />']


def r_header(ctx: Context) -> list[str]:
    out = [f'<h1 align="center">Hi there 👋, I\'m {escape_html(ctx.name)}</h1>']
    if ctx.tagline:
        out.append(f'<h3 align="center">{escape_html(ctx.tagline)}</h3>')
    if ctx.bio:
        out += ["", f'<p align="center">{escape_html(ctx.bio)}</p>']
    # This line sits inside an HTML block, where GitHub does not parse Markdown.
    meta = []
    if ctx.location:
        meta.append("📍 " + escape_html(ctx.location))
    if ctx.website:
        meta.append(f'🌐 <a href="{escape_attr(ctx.website)}">Website</a>')
    meta.append(f"📊 Public Repos: <b>{ctx.totals.repos}</b>")
    meta.append(f"👥 Followers: <b>{ctx.totals.followers}</b>")
    return [*out, "", '<p align="center">' + "  •  ".join(meta) + "</p>", "", "---"]


def r_typing(ctx: Context) -> list[str]:
    lines = [line.strip() for line in ctx.typing_lines if line.strip()]
    if not lines:
        return []
    return [
        '<p align="center">',
        f'  <a href="{urls.profile_url(ctx.login)}">',
        f"    {_img(urls.typing_url(lines), 'typing')}",
        "  </a>",
        "</p>",
    ]


def r_badges(ctx: Context) -> list[str]:
    badges = []
    if ctx.options.show_views:
        badges.append(_img(urls.views_url(ctx.login), "Profile views"))
    badges.append(f'<img src="{urls.followers_count_url(ctx.login)}" alt="Followers" />')
    capped = ctx.totals.capped
    star_label = "Stars (top 100 repos)" if capped else "Total Stars"
    badges.append(
        _img(urls.shield_badge(star_label, str(ctx.totals.stars), "F59E0B", "star"), "Stars")
    )
    if ctx.totals.forks:
        fork_label = "Forks (top 100 repos)" if capped else "Total Forks"
        badges.append(
            _img(urls.shield_badge(fork_label, str(ctx.totals.forks), "22D3A0", "git"), "Forks")
        )
    return _centered(*badges)


def r_connect(ctx: Context) -> list[str]:
    badges = [
        f"[![GitHub]({urls.shield_badge('GitHub', ctx.login, '181717', 'github')})]"
        f"({urls.profile_url(ctx.login)})"
    ]
    for key in SOCIAL_KEYS:
        social = SOCIALS[key]
        handle = ctx.socials[key].strip()
        if social.strip_at:
            handle = handle.lstrip("@")
        if not handle:
            continue
        img = urls.shield_badge(social.label, handle, social.color, social.logo)
        link = social.link(handle)
        if link is None:
            badges.append(f"![{social.label}]({img})")
            continue
        href = safe_url(link, social.schemes)
        if href:
            badges.append(f"[![{social.label}]({img})]({href})")
    if len(badges) <= 1 and not ctx.website:
        return []
    return [heading(ctx, "connect"), "", "\n".join(badges)]


_LANG_NOTES = {
    "primary": "<sub>Estimated from each repository's primary language.</sub>",
    "mixed": "<sub>Partially measured by bytes of code.</sub>",
}


def r_techstack(ctx: Context) -> list[str]:
    if not ctx.langs:
        return []
    badges = [_img(urls.lang_badge(lang, lang_meta(lang)), escape_attr(lang)) for lang in ctx.langs]
    out = [heading(ctx, "techstack"), "", *_centered(*badges)]
    note = _LANG_NOTES.get(ctx.lang_source)
    if note:
        out += ["", note]
    return out


def r_featured(ctx: Context) -> list[str]:
    if not ctx.featured:
        return []
    out = [heading(ctx, "featured"), ""]
    if ctx.options.featured_layout == "cards":
        cards = []
        for repo in ctx.featured:
            pin = urls.pin_url(ctx.instances.stats, ctx.login, repo.name, ctx.wt("stats"))
            card = _img(pin, escape_attr(repo.name))
            href = safe_url(repo.html_url, ["https"])
            cards.append(f'<a href="{escape_attr(href)}">{card}</a>' if href else card)
        return out + _centered(*cards)
    # escape_md is mandatory in table cells: an unescaped pipe would split the row.
    out += [
        "| Project | Description | Stars | Forks | Language |",
        "| :--- | :--- | :---: | :---: | :--- |",
    ]
    for repo in ctx.featured:
        url = safe_url(repo.html_url, ["https"])
        name = escape_md(repo.name)
        link = f"**[{name}]({url})**" if url else f"**{name}**"
        description = escape_md(repo.description) if repo.description else "—"
        language = escape_md(repo.language) if repo.language else "—"
        out.append(
            f"| {link} | {description} | {repo.stargazers_count} | {repo.forks_count} "
            f"| {language} |"
        )
    return out


def r_stats(ctx: Context) -> list[str]:
    base, theme = ctx.instances.stats, ctx.wt("stats")
    return [
        heading(ctx, "stats"),
        "",
        *_centered(
            _img(urls.stats_url(base, ctx.login, theme), "stats"),
            _img(urls.top_langs_url(base, ctx.login, theme), "top languages"),
        ),
    ]


def r_streak(ctx: Context) -> list[str]:
    src = urls.streak_url(ctx.instances.streak, ctx.login, ctx.wt("streak"))
    return [heading(ctx, "streak"), "", *_centered(_img(src, "streak"))]


def r_activity(ctx: Context) -> list[str]:
    src = urls.activity_url(ctx.instances.activity, ctx.login, ctx.wt("activity"))
    return [heading(ctx, "activity"), "", *_centered(_img(src, "activity graph"))]


def r_trophies(ctx: Context) -> list[str]:
    o = ctx.options
    src = urls.trophy_url(
        ctx.instances.trophy, ctx.login, ctx.wt("trophy"), o.trophy_rows, o.trophy_cols
    )
    return [heading(ctx, "trophies"), "", *_centered(_img(src, "trophies"))]


def r_learning(ctx: Context) -> list[str]:
    text = ctx.options.learning_text or DEFAULT_LEARNING
    return [heading(ctx, "learning"), "", escape_md_text(text)]


def r_quote(ctx: Context) -> list[str]:
    return [heading(ctx, "quote"), "", FOWLER_QUOTE]


def _user_gif(value: str, fallback: str) -> str:
    """User-supplied image URL; blank falls back, anything that is not https is dropped."""
    return safe_url(value, ["https"]) if value else fallback


def r_hero(ctx: Context) -> list[str]:
    src = _user_gif(ctx.options.hero_gif, DEFAULT_HERO_GIF)
    if not src:
        return []
    return [
        '<div align="center">',
        f'  <img src="{escape_attr(src)}" width="100%" alt="" />',
        "</div>",
    ]


def r_about(ctx: Context) -> list[str]:
    o = ctx.options

    def text(value: str) -> str:
        return escape_md_text(re.sub(r"\s*\n\s*", " ", value))

    bullets = []
    if o.working:
        url = safe_url(o.working_url, ["http", "https"])
        work = f"[{text(o.working)}]({url})" if url else text(o.working)
        bullets.append(f"- 🔭 I’m currently working on **{work}**")
    if o.learning_text:
        bullets.append(f"- 🌱 I’m currently learning **{text(o.learning_text)}**")
    if o.collab:
        bullets.append(f"- 👯 I’m looking to collaborate on **{text(o.collab)}**")
    if o.ask_me:
        bullets.append(f"- 💬 Ask me about **{text(o.ask_me)}**")
    if ctx.website:
        bullets.append(f"- 🏬 Pay a visit to my **[portfolio]({ctx.website})**")
    if ctx.location:
        bullets.append(f"- 📍 Based in **{text(ctx.location)}**")
    email = re.sub(r"^mailto:", "", ctx.socials["email"], flags=re.I)
    mail = safe_url("mailto:" + email, ["mailto"]) if email else ""
    if mail:
        bullets.append(f"- 📫 How to reach me: **[{text(email)}]({mail})**")
    if o.fun_fact:
        bullets.append(f"- ⚡ Fun fact: **{text(o.fun_fact)}**")
    if not bullets:
        return []

    out = [heading(ctx, "about"), ""]
    gif = _user_gif(o.about_gif, DEFAULT_ABOUT_GIF)
    if gif:
        out += [f'<img align="right" width="300" src="{escape_attr(gif)}" alt="" />', ""]
    out += bullets
    if gif:
        out += ["", '<br clear="right" />']
    return out


def r_profilestats(ctx: Context) -> list[str]:
    def cell(src: str, alt: str) -> str:
        return f"      <td>{_img(src, alt)}</td>"

    heads = ["👀 Views", "👤 Followers", "🌟 Stars", "✅ Awesome"]
    return [
        '<div align="center">',
        "",
        heading(ctx, "profilestats"),
        "",
        '<table align="center">',
        "  <tr>",
        *(f"    <td><b>{h}</b></td>" for h in heads),
        "  </tr>",
        "  <tr>",
        cell(urls.views_compact_url(ctx.login), "views"),
        cell(urls.followers_badge_url(ctx.login), "followers"),
        cell(urls.stars_badge_url(ctx.login), "stars"),
        cell(urls.AWESOME_BADGE_URL, "awesome"),
        "  </tr>",
        "</table>",
        "",
        "</div>",
    ]


def r_cards(ctx: Context) -> list[str]:
    inst, login = ctx.instances, ctx.login
    stats_theme, summary_theme = ctx.wt("stats"), ctx.wt("summary")

    def cell(src: str, alt: str) -> str:
        return f'    <td width="33%">{_img(src, alt)}</td>'

    return [
        heading(ctx, "cards"),
        "",
        '<div align="center">',
        "  " + _img(urls.stats_url(inst.stats, login, stats_theme), "stats", 'width="48%" '),
        "  "
        + _img(urls.streak_url(inst.streak, login, ctx.wt("streak")), "streak", 'width="48%" '),
        "</div>",
        "",
        '<table align="center">',
        "  <tr>",
        cell(urls.top_langs_url(inst.stats, login, stats_theme, "donut"), "top languages"),
        cell(urls.summary_card_url(inst.summary, login, "stats", summary_theme), "summary"),
        cell(
            urls.summary_card_url(inst.summary, login, "productive-time", summary_theme),
            "productive time",
        ),
        "  </tr>",
        "</table>",
    ]


def r_contrib3d(ctx: Context) -> list[str]:
    return _centered(_img(urls.contrib3d_url(ctx.login), "3D contribution graph"))


def r_chart(ctx: Context) -> list[str]:
    return _centered(_img(urls.chart_url(ctx.login, ctx.wt("accent")), "contribution chart"))


def r_gitanimals(ctx: Context) -> list[str]:
    src = escape_attr(urls.git_animals_url(ctx.login))
    farm = f'<img src="{src}" width="600" alt="git animals farm" />'
    return [
        heading(ctx, "gitanimals"),
        "",
        *_centered(f'<a href="https://www.gitanimals.org/">{farm}</a>'),
    ]


def r_funzone(ctx: Context) -> list[str]:
    return [
        heading(ctx, "funzone"),
        "",
        *_centered(f'<img src="{urls.JOKES_URL}" alt="dev joke" />'),
        "",
        *_centered(_img(urls.quote_card_url(ctx.wt("stats")), "dev quote")),
    ]


def r_snake(ctx: Context) -> list[str]:
    dark, light = urls.snake_url(ctx.login, True), urls.snake_url(ctx.login, False)
    return [
        heading(ctx, "snake"),
        "",
        "<picture>",
        f'  <source media="(prefers-color-scheme: dark)" srcset="{escape_attr(dark)}" />',
        f'  <source media="(prefers-color-scheme: light)" srcset="{escape_attr(light)}" />',
        f'  <img alt="contribution snake" src="{escape_attr(light)}" />',
        "</picture>",
    ]


def r_sponsors(ctx: Context) -> list[str]:
    href = urls.sponsors_url(ctx.login)
    badge = f'<img src="{urls.SPONSORS_BADGE_URL}" alt="GitHub Sponsors" />'
    return [
        heading(ctx, "sponsors"),
        "",
        "All my projects stay free and open source. If they help you, consider "
        f"[sponsoring me on GitHub]({href}).",
        "",
        *_centered(f'<a href="{href}">{badge}</a>'),
    ]


def r_footerwave(ctx: Context) -> list[str]:
    text = ctx.options.footer_text or DEFAULT_FOOTER_TEXT
    return [
        f'<img src="{escape_attr(urls.footer_wave_url(text))}" width="100%" alt="" />',
        "",
        f'<p align="center"><sub>{escape_html(ctx.name)} © {ctx.year} • Crafted with ❤️</sub></p>',
    ]


Renderer = Callable[[Context], list[str]]
RENDERERS: dict[str, Renderer] = {sid: globals()["r_" + sid] for sid in SECTION_IDS}


def generate(ctx: Context, section_ids: Iterable[str]) -> str:
    lines: list[str] = []
    for sid in section_ids:
        out = RENDERERS[sid](ctx)
        if out:
            lines += [*out, ""]
    if ctx.options.credit:
        lines += ["---", "", CREDIT]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip() + "\n"
