#!/usr/bin/env python3
"""README.forge CLI — Python port of tool.js. Stdlib only, Python 3.8+.

    python readme_forge.py octocat                      # classic layout to README.md
    python readme_forge.py octocat --preset showcase    # rich profile layout
    python readme_forge.py --config forge.config.json   # settings exported from tool.html
    python readme_forge.py octocat --workflows .github/workflows
    python readme_forge.py --selftest

Set GITHUB_TOKEN (or pass --token) to raise the API limit from 60/hr to 5000/hr.
"""

import argparse
import datetime
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

# Sections, same ids and defaults as tool.js

SECTIONS = [
    # id, on by default, needs workflow
    ("banner", False, None), ("header", True, None), ("typing", True, None),
    ("badges", True, None), ("connect", True, None), ("techstack", True, None),
    ("featured", True, None), ("stats", True, None), ("streak", True, None),
    ("activity", True, None), ("trophies", True, None), ("learning", True, None),
    ("quote", False, None),
    ("hero", False, None), ("about", False, None), ("profilestats", False, None),
    ("cards", False, None), ("contrib3d", False, "contrib3d"), ("chart", False, None),
    ("gitanimals", False, None), ("funzone", False, None), ("snake", False, "snake"),
    ("sponsors", False, None), ("footerwave", False, None),
]
SECTION_IDS = [s[0] for s in SECTIONS]

PRESETS = {
    "classic": [s[0] for s in SECTIONS if s[1]],
    "showcase": ["hero", "header", "about", "typing", "profilestats", "contrib3d", "cards",
                 "trophies", "chart", "techstack", "featured", "gitanimals", "funzone",
                 "connect", "snake", "sponsors", "footerwave"],
}

DEFAULT_HERO_GIF = "https://user-images.githubusercontent.com/74038190/212284158-e840e285-664b-44d7-b79b-e264b5e54825.gif"
DEFAULT_ABOUT_GIF = "https://user-images.githubusercontent.com/74038190/229223263-cf2e4b07-2615-4f87-9c38-e37600f8381a.gif"
DEFAULT_ACCENT_GIF = "https://raw.githubusercontent.com/innng/innng/master/assets/kyubey.gif"
DEFAULT_LEARNING = "I'm always exploring new technologies and expanding my skill set."

DEFAULT_OPTIONS = {
    "theme": "tokyonight",
    "typingLines": [], "bannerText": "", "learningText": "",
    "trophyRows": 1, "trophyCols": 7,
    "featuredLayout": "table", "featuredCount": 6,
    "showViews": True,
    "heroGif": "", "aboutGif": "", "headingGif": False,
    "working": "", "workingUrl": "", "collab": "", "askMe": "", "funFact": "",
    "footerText": "",
}

SOCIAL_KEYS = ["twitter", "linkedin", "email", "devto", "discord", "stackoverflow",
               "youtube", "website", "instagram", "facebook", "gitlab", "bitbucket"]

# Lookup tables

THEMES = {
    "tokyonight":  {"activity": "tokyo-night",    "trophy": "tokyonight", "summary": "tokyonight",  "accent": "7AA2F7"},
    "dracula":     {"activity": "dracula",        "trophy": "dracula",    "summary": "dracula",     "accent": "BD93F9"},
    "radical":     {"activity": "react-dark",     "trophy": "radical",    "summary": "radical",     "accent": "FE428E"},
    "onedark":     {"activity": "react-dark",     "trophy": "onedark",    "summary": "one_dark",    "accent": "E5C07B"},
    "gruvbox":     {"activity": "gruvbox",        "trophy": "gruvbox",    "summary": "gruvbox",     "accent": "FABD2F"},
    "nord":        {"activity": "nord",           "trophy": "nord",       "summary": "nord_dark",   "accent": "88C0D0"},
    "github_dark": {"activity": "github-compact", "trophy": "gitdimmed",  "summary": "github_dark", "accent": "58A6FF"},
    "default":     {"activity": "github",         "trophy": "flat",       "summary": "default",     "accent": "216E39"},
}


def widget_theme(theme_id, widget):
    if theme_id not in THEMES:
        theme_id = "tokyonight"
    return THEMES[theme_id].get(widget, theme_id)


# href None means no per-user URL exists so we emit an unlinked badge
SOCIALS_META = {
    "twitter":       {"label": "X",              "logo": "x",             "color": "000000", "strip": True, "href": lambda v: "https://x.com/" + v},
    "linkedin":      {"label": "LinkedIn",       "logo": "linkedin",      "color": "0A66C2", "strip": True, "href": lambda v: "https://www.linkedin.com/in/" + v},
    "email":         {"label": "Email",          "logo": "gmail",         "color": "EA4335", "href": lambda v: "mailto:" + v, "schemes": ["mailto"]},
    "devto":         {"label": "dev.to",         "logo": "devdotto",      "color": "0A0A0A", "strip": True, "href": lambda v: "https://dev.to/" + v},
    "discord":       {"label": "Discord",        "logo": "discord",       "color": "5865F2", "href": None},
    "stackoverflow": {"label": "Stack Overflow", "logo": "stackoverflow", "color": "F58025", "href": lambda v: "https://stackoverflow.com/users/" + v},
    "youtube":       {"label": "YouTube",        "logo": "youtube",       "color": "FF0000", "strip": True, "href": lambda v: "https://youtube.com/@" + v},
    "website":       {"label": "Website",        "logo": "googlechrome",  "color": "7C6AF7", "href": lambda v: v},
    "instagram":     {"label": "Instagram",      "logo": "instagram",     "color": "E4405F", "strip": True, "href": lambda v: "https://www.instagram.com/" + v},
    "facebook":      {"label": "Facebook",       "logo": "facebook",      "color": "1877F2", "strip": True, "href": lambda v: "https://www.facebook.com/" + v},
    "gitlab":        {"label": "GitLab",         "logo": "gitlab",        "color": "FC6D26", "strip": True, "href": lambda v: "https://gitlab.com/" + v},
    "bitbucket":     {"label": "Bitbucket",      "logo": "bitbucket",     "color": "0052CC", "strip": True, "href": lambda v: "https://bitbucket.org/" + v},
}

# language to logo lookup, keys normalized to lower with no spaces or dashes
LANG_META = {
    "javascript": ("javascript", "F7DF1E", "black"), "typescript": ("typescript", "3178C6", None),
    "python": ("python", "3776AB", None), "java": ("openjdk", "ED8B00", "black"),
    "c": ("c", "A8B9CC", "black"), "c++": ("cplusplus", "00599C", None),
    "c#": ("csharp", "239120", None), "f#": ("fsharp", "378BBA", None),
    "go": ("go", "00ADD8", None), "rust": ("rust", "000000", None), "ruby": ("ruby", "CC342D", None),
    "php": ("php", "777BB4", None), "swift": ("swift", "F05138", None), "kotlin": ("kotlin", "7F52FF", None),
    "dart": ("dart", "0175C2", None), "scala": ("scala", "DC322F", None), "elixir": ("elixir", "4B275F", None),
    "haskell": ("haskell", "5D4F85", None), "lua": ("lua", "2C2D72", None), "r": ("r", "276DC3", None),
    "julia": ("julia", "9558B2", None), "perl": ("perl", "39457E", None), "zig": ("zig", "F7A41D", "black"),
    "html": ("html5", "E34F26", None), "css": ("css3", "1572B6", None), "scss": ("sass", "CC6699", None),
    "sass": ("sass", "CC6699", None), "less": ("less", "1D365D", None),
    "shell": ("gnubash", "4EAA25", None), "bash": ("gnubash", "4EAA25", None),
    "powershell": ("powershell", "5391FE", None),
    "dockerfile": ("docker", "2496ED", None), "docker": ("docker", "2496ED", None),
    "cmake": ("cmake", "064F8C", None),
    "jupyternotebook": ("jupyter", "F37626", None), "jupyter": ("jupyter", "F37626", None),
    "vue": ("vuedotjs", "4FC08D", None), "vuejs": ("vuedotjs", "4FC08D", None),
    "svelte": ("svelte", "FF3E00", None), "astro": ("astro", "BC52EE", None),
    "vimscript": ("vim", "019733", None), "vim": ("vim", "019733", None),
    "emacslisp": ("gnuemacs", "7F5AB6", None), "clojure": ("clojure", "5881D8", None),
    "erlang": ("erlang", "A90533", None), "ocaml": ("ocaml", "EC6813", None),
    "solidity": ("solidity", "363636", None), "nix": ("nixos", "5277C3", None),
    "hcl": ("terraform", "7B42BC", None), "terraform": ("terraform", "7B42BC", None),
    "plpgsql": ("postgresql", "4169E1", None), "postgresql": ("postgresql", "4169E1", None),
    "tsql": ("microsoftsqlserver", "CC2927", None), "groovy": ("apachegroovy", "4298B8", None),
    "markdown": ("markdown", "000000", None), "mdx": ("mdx", "1B1F24", None),
    "tex": ("latex", "008080", None), "latex": ("latex", "008080", None),
    "blade": ("laravel", "FF2D20", None), "handlebars": ("handlebarsdotjs", "000000", None),
}
LANG_FALLBACK = (None, "05122A", None)


def norm_lang(s):
    return re.sub(r"[\s._-]", "", str(s or "").lower())


def lang_meta(lang):
    return LANG_META.get(norm_lang(lang), LANG_FALLBACK)


# Escaping helpers

HTML_MAP = {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}


def escape_html(s):
    return re.sub(r"[&<>\"']", lambda m: HTML_MAP[m.group(0)], "" if s is None else str(s))


def escape_attr(s):
    return re.sub(r"\r?\n", " ", escape_html(s))


def escape_md(s):
    s = re.sub(r"\r?\n", " ", "" if s is None else str(s))
    return re.sub(r"([\\`*_{}\[\]()#+\-.!|<>])", r"\\\1", s)


# prose variant, only neutralizes what breaks structure or injects HTML
def escape_md_text(s):
    s = ("" if s is None else str(s)).replace("\r\n", "\n")
    return re.sub(r"([\\`<>|\[\]])", r"\\\1", s)


def safe_url(s, schemes):
    """schemes are bare names, e.g. ["http", "https"]."""
    if not s:
        return ""
    raw = s if re.match(r"^[a-z][a-z0-9+.-]*:", s, re.I) else "https://" + s
    try:
        u = urllib.parse.urlsplit(raw)
    except ValueError:
        return ""
    if u.scheme.lower() not in schemes:
        return ""
    if u.scheme.lower() in ("http", "https"):
        if not u.netloc or re.search(r"[\s<>\"]", raw):
            return ""
        # match the WHATWG serializer: bare origin gains a trailing slash
        return urllib.parse.urlunsplit((u.scheme.lower(), u.netloc.lower(), u.path or "/", u.query, u.fragment))
    return raw if not re.search(r"[\s<>\"]", raw) else ""


def enc(s):
    """encodeURIComponent."""
    return urllib.parse.quote(str(s), safe="!~*'()")


def qs(pairs):
    """URLSearchParams.toString."""
    return urllib.parse.urlencode(pairs)


# URL builders

# query form, not path form, because path form splits on hyphens like Objective-C
def shield_badge(label, message, color, logo=None, logo_color=None):
    p = [("label", label), ("message", message), ("color", color), ("style", "for-the-badge")]
    if logo:
        p += [("logo", logo), ("logoColor", logo_color or "white")]
    return "https://img.shields.io/static/v1?" + qs(p)


def lang_badge(lang, m):
    slug, color, lc = m
    p = [("label", ""), ("message", lang), ("color", color), ("style", "flat")]
    if slug:
        p += [("logo", slug), ("logoColor", lc or "white")]
    return "https://img.shields.io/static/v1?" + qs(p)


def stats_url(login, theme):
    return ("https://github-readme-stats.vercel.app/api?username=" + enc(login)
            + "&show_icons=true&theme=" + theme + "&hide_border=true&count_private=true&include_all_commits=true")


def top_langs_url(login, theme):
    return ("https://github-readme-stats.vercel.app/api/top-langs/?username=" + enc(login)
            + "&layout=compact&theme=" + theme + "&hide_border=true&langs_count=8")


def donut_langs_url(login, theme):
    return ("https://github-readme-stats.vercel.app/api/top-langs/?username=" + enc(login)
            + "&layout=donut&theme=" + theme + "&hide_border=true&langs_count=8")


def pin_url(login, repo, theme):
    return ("https://github-readme-stats.vercel.app/api/pin/?username=" + enc(login)
            + "&repo=" + enc(repo) + "&theme=" + theme + "&hide_border=true")


def streak_url(login, theme):
    return "https://streak-stats.demolab.com?user=" + enc(login) + "&theme=" + theme + "&hide_border=true"


def trophy_url(login, theme, row, col):
    return ("https://github-profile-trophy.vercel.app/?username=" + enc(login)
            + "&theme=" + theme + "&no-frame=true&margin-w=8&row=" + str(row) + "&column=" + str(col))


def activity_url(login, theme):
    return ("https://github-readme-activity-graph.vercel.app/graph?username=" + enc(login)
            + "&theme=" + theme + "&hide_border=true&area=true&radius=8")


def views_url(login):
    return ("https://komarev.com/ghpvc/?username=" + enc(login)
            + "&label=Profile+Views&color=7C6AF7&style=for-the-badge")


# lines join on a literal semicolon, an encoded %3B renders as text instead
def typing_url(lines):
    joined = ";".join(enc(l.replace(";", "")) for l in lines)
    return ("https://readme-typing-svg.demolab.com?font=DM+Mono&size=24&duration=3200"
            "&pause=800&color=7C6AF7&center=true&vCenter=true&width=600&height=60&lines=" + joined)


def banner_url(text):
    return ("https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=12,24"
            "&height=180&section=header&fontSize=44&fontColor=ffffff&animation=fadeIn&text=" + enc(text))


def footer_wave_url(text):
    return ("https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=6,11,20"
            "&height=120&section=footer&fontSize=20&fontColor=ffffff&animation=twinkling&text=" + enc(text))


def summary_card_url(login, card, theme):
    return "https://github-profile-summary-cards.vercel.app/api/cards/" + card + "?username=" + enc(login) + "&theme=" + theme


def chart_url(login, accent):
    return "https://ghchart.rshah.org/" + accent + "/" + enc(login)


def git_animals_url(login):
    return "https://render.gitanimals.org/farms/" + enc(login)


# these two read from files a workflow commits into the profile repo
def contrib3d_url(login):
    l = enc(login)
    return "https://raw.githubusercontent.com/" + l + "/" + l + "/HEAD/profile-3d-contrib/profile-night-rainbow.svg"


def snake_url(login, dark):
    l = enc(login)
    return "https://raw.githubusercontent.com/" + l + "/" + l + "/output/github-snake" + ("-dark" if dark else "") + ".svg"


JOKES_URL = "https://readme-jokes.vercel.app/api"


def quote_card_url(theme):
    return "https://quotes-github-readme.vercel.app/api?type=horizontal&theme=" + theme


WORKFLOWS = {
    "snake": ("snake.yml", """name: Generate snake animation
on:
  schedule:
    - cron: "0 */12 * * *"
  workflow_dispatch:
  push:
    branches: [main]
permissions:
  contents: write
jobs:
  generate:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - uses: Platane/snk@v3
        with:
          github_user_name: ${{ github.repository_owner }}
          outputs: |
            dist/github-snake.svg
            dist/github-snake-dark.svg?palette=github-dark
      - uses: crazy-max/ghaction-github-pages@v4
        with:
          target_branch: output
          build_dir: dist
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
"""),
    "contrib3d": ("profile-3d-contrib.yml", """name: GitHub-Profile-3D-Contrib
on:
  schedule:
    - cron: "0 18 * * *"
  workflow_dispatch:
permissions:
  contents: write
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: yoshi389111/github-profile-3d-contrib@v0.9.3
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          USERNAME: ${{ github.repository_owner }}
      - name: Commit and push
        run: |
          git config user.name github-actions
          git config user.email github-actions@github.com
          git add -A .
          git commit -m "Update 3D contribution graph" || exit 0
          git push
"""),
}


def required_workflows(sections):
    return [WORKFLOWS[w] for sid, _, w in SECTIONS if w and sid in sections]


# GitHub API

USERNAME_RE = r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?"


def extract_username(url):
    url = re.sub(r"/+$", "", url.strip())
    m = re.match(r"^(?:https?://)?(?:www\.)?github\.com/(" + USERNAME_RE + ")", url, re.I)
    if m:
        return m.group(1)
    return url if re.fullmatch(USERNAME_RE, url) else None


class GitHub:
    def __init__(self, token=""):
        self.token = token
        self.remaining = None

    def get(self, path):
        req = urllib.request.Request("https://api.github.com" + path, headers={
            "Accept": "application/vnd.github+json", "User-Agent": "readme-forge",
            **({"Authorization": "Bearer " + self.token} if self.token else {}),
        })
        try:
            with urllib.request.urlopen(req, timeout=20) as res:
                self._rate(res.headers)
                return res.status, json.loads(res.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            self._rate(e.headers)
            return e.code, None

    def _rate(self, headers):
        rem = headers.get("x-ratelimit-remaining") if headers else None
        if rem is not None:
            self.remaining = int(rem)


def trim_repo(r):
    return {
        "id": r["id"], "name": r["name"], "full_name": r["full_name"], "html_url": r["html_url"],
        "description": r.get("description") or "", "stargazers_count": r.get("stargazers_count") or 0,
        "forks_count": r.get("forks_count") or 0, "language": r.get("language") or "",
        "fork": bool(r.get("fork")), "archived": bool(r.get("archived")),
    }


def aggregate_languages(gh, repos):
    """Returns (langs, source) with source one of bytes | mixed | primary."""
    targets = [r for r in repos if not r["fork"]][: 40 if gh.token else 20]
    counts = {}
    for r in targets:
        if r["language"]:
            counts[r["language"]] = counts.get(r["language"], 0) + 1

    # do not fire requests we know will 403
    budget = float("inf") if gh.remaining is None else gh.remaining
    nbytes, ok = {}, 0
    if targets and budget >= len(targets):
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda r: gh.get("/repos/" + r["full_name"] + "/languages"), targets))
        for status, body in results:
            if status != 200 or not isinstance(body, dict):
                continue
            ok += 1
            for lang, b in body.items():
                nbytes[lang] = nbytes.get(lang, 0) + b

    if ok == 0 or not nbytes:
        return counts, "primary"
    source = "bytes" if ok == len(targets) else "mixed"
    # anchor fallback weights to real bytes so they stay visible in the top cut
    floor = max(1, min(nbytes.values()) / 2)
    for lang, n in counts.items():
        nbytes.setdefault(lang, floor * n)
    return nbytes, source


def fetch_profile(username, token=""):
    gh = GitHub(token)
    status, user = gh.get("/users/" + username)
    if status != 200:
        if status == 404:
            raise SystemExit("User not found: " + username)
        if status == 401:
            raise SystemExit("Token rejected. Check GITHUB_TOKEN / --token.")
        if status in (403, 429):
            raise SystemExit("API rate limit reached." + ("" if token else " Set GITHUB_TOKEN to raise it to 5,000/hr."))
        raise SystemExit("GitHub API error: %s" % status)
    status, repos = gh.get("/users/" + username + "/repos?per_page=100&sort=updated")
    repos = [trim_repo(r) for r in repos] if status == 200 else []
    if status != 200:
        print("warning: repos could not be loaded (rate limit), stats will be incomplete", file=sys.stderr)
    langs, source = aggregate_languages(gh, repos)
    return user, repos, langs, source


# README generator

FOOTER = '<p align="center">Made with ❤️ by <a href="https://github.com/Antech-greyhat">Antech-greyhat</a></p>'


class Ctx:
    def __init__(self, user, repos, langs, lang_source, cfg):
        o = dict(DEFAULT_OPTIONS)
        o.update({k: v for k, v in (cfg.get("options") or {}).items() if k in DEFAULT_OPTIONS})
        self.o = o
        self.socials = {k: str((cfg.get("socials") or {}).get(k) or "") for k in SOCIAL_KEYS}
        custom = cfg.get("custom") or {}
        self.user = user
        self.login = user["login"]
        self.name = custom.get("name") or user.get("name") or user["login"]
        self.tagline = custom.get("tagline") or ""
        self.bio = custom.get("bio") if custom.get("bio") is not None else (user.get("bio") or "")
        self.location = custom.get("location") if custom.get("location") is not None else (user.get("location") or "")
        self.website = safe_url(custom.get("website") if custom.get("website") is not None else (user.get("blog") or ""),
                                ["http", "https"])
        # prefill socials from the API like the web UI does
        if not self.socials["twitter"] and user.get("twitter_username"):
            self.socials["twitter"] = user["twitter_username"]
        if not self.socials["email"] and user.get("email"):
            self.socials["email"] = user["email"]
        if not self.socials["website"] and user.get("blog"):
            self.socials["website"] = user["blog"]

        self.repos = repos
        self.lang_source = lang_source
        ranked = sorted(langs, key=lambda l: -langs[l])
        self.langs = cfg.get("langs") or ranked[:12]
        by_name = {r["name"]: r for r in repos}
        live = sorted([r for r in repos if not r["fork"] and not r["archived"]], key=lambda r: -r["stargazers_count"])
        self.featured = ([by_name[n] for n in cfg["featured"] if n in by_name] if cfg.get("featured") is not None
                         else live[:6])
        non_fork = [r for r in repos if not r["fork"]]
        self.totals = {
            "repos": user.get("public_repos") or 0,
            "stars": sum(r["stargazers_count"] for r in non_fork),
            "forks": sum(r["forks_count"] for r in non_fork),
            "followers": user.get("followers") or 0,
            # repos is capped at per_page=100 so sums undercount past that
            "capped": (user.get("public_repos") or 0) > len(repos),
        }
        if not o["typingLines"]:
            lines = []
            if user.get("bio"):
                lines.append(user["bio"][:60])
            if ranked:
                lines.append(ranked[0] + " Developer")
            lines.append("Always learning something new")
            o["typingLines"] = lines

    def wt(self, widget):
        return widget_theme(self.o["theme"], widget)

    def h2(self, title):
        if not self.o["headingGif"]:
            return "## " + title
        return "## " + title + ' <img height="32" src="' + DEFAULT_ACCENT_GIF + '" alt="" />'


def gif_url(v, fallback):
    return safe_url(v, ["https"]) if v else fallback


def r_banner(c):
    text = c.o["bannerText"] or c.name
    return ['<img src="' + escape_attr(banner_url(text)) + '" alt="banner" width="100%" />'] if text else []


def r_header(c):
    out = ["<h1 align=\"center\">Hi there 👋, I'm " + escape_html(c.name) + "</h1>"]
    if c.tagline:
        out.append('<h3 align="center">' + escape_html(c.tagline) + "</h3>")
    if c.bio:
        out += ["", '<p align="center">' + escape_html(c.bio) + "</p>"]
    meta = []
    if c.location:
        meta.append("📍 " + escape_md(c.location))
    if c.website:
        meta.append("🌐 [Website](" + c.website + ")")
    meta.append("📊 Public Repos: **%d**" % c.totals["repos"])
    meta.append("👥 Followers: **%d**" % c.totals["followers"])
    out += ["", '<p align="center">' + "  •  ".join(meta) + "</p>", "", "---"]
    return out


def r_typing(c):
    lines = [l.strip() for l in c.o["typingLines"] if l.strip()]
    if not lines:
        return []
    return ['<p align="center">',
            '  <a href="https://github.com/' + enc(c.login) + '">',
            '    <img src="' + escape_attr(typing_url(lines)) + '" alt="typing" />',
            "  </a>", "</p>"]


def r_badges(c):
    b = []
    if c.o["showViews"]:
        b.append('<img src="' + escape_attr(views_url(c.login)) + '" alt="Profile views" />')
    b.append('<img src="https://img.shields.io/github/followers/' + enc(c.login)
             + '?label=Followers&style=for-the-badge&color=7C6AF7&logo=github&logoColor=white" alt="Followers" />')
    star_label = "Stars (top 100 repos)" if c.totals["capped"] else "Total Stars"
    b.append('<img src="' + escape_attr(shield_badge(star_label, str(c.totals["stars"]), "F59E0B", "star", "white")) + '" alt="Stars" />')
    if c.totals["forks"]:
        fork_label = "Forks (top 100 repos)" if c.totals["capped"] else "Total Forks"
        b.append('<img src="' + escape_attr(shield_badge(fork_label, str(c.totals["forks"]), "22D3A0", "git", "white")) + '" alt="Forks" />')
    return ['<p align="center">'] + ["  " + x for x in b] + ["</p>"]


def r_connect(c):
    badges = ["[![GitHub](" + shield_badge("GitHub", c.login, "181717", "github")
              + ")](https://github.com/" + enc(c.login) + ")"]
    for k in SOCIAL_KEYS:
        v = c.socials[k].strip()
        m = SOCIALS_META[k]
        if m.get("strip"):
            v = v.lstrip("@")
        if not v:
            continue
        img = shield_badge(m["label"], v, m["color"], m["logo"])
        if not m["href"]:
            badges.append("![" + m["label"] + "](" + img + ")")
            continue
        href = safe_url(m["href"](v), m.get("schemes", ["http", "https"]))
        if href:
            badges.append("[![" + m["label"] + "](" + img + ")](" + href + ")")
    if len(badges) <= 1 and not c.website:
        return []
    return [c.h2("🔗 Connect with Me"), "", "\n".join(badges)]


def r_techstack(c):
    if not c.langs:
        return []
    note = {"primary": "<sub>Estimated from each repository's primary language.</sub>",
            "mixed": "<sub>Partially measured by bytes of code.</sub>"}.get(c.lang_source, "")
    out = [c.h2("⚡ Tech Stack"), "", '<p align="center">']
    out += ['  <img src="' + escape_attr(lang_badge(l, lang_meta(l))) + '" alt="' + escape_attr(l) + '" />' for l in c.langs]
    out.append("</p>")
    if note:
        out += ["", note]
    return out


def r_featured(c):
    if not c.featured:
        return []
    out = [c.h2("★ Featured Projects"), ""]
    if c.o["featuredLayout"] == "cards":
        out.append('<p align="center">')
        for r in c.featured:
            out.append('  <a href="' + escape_attr(safe_url(r["html_url"], ["https"])) + '">'
                       + '<img src="' + escape_attr(pin_url(c.login, r["name"], c.wt("stats"))) + '" alt="' + escape_attr(r["name"]) + '" /></a>')
        out.append("</p>")
        return out
    # escape_md is mandatory here, an unescaped pipe destroys the row
    out += ["| Project | Description | Stars | Forks | Language |", "| :--- | :--- | :---: | :---: | :--- |"]
    for r in c.featured:
        url = safe_url(r["html_url"], ["https"])
        link = "**[" + escape_md(r["name"]) + "](" + url + ")**" if url else "**" + escape_md(r["name"]) + "**"
        out.append("| " + link + " | " + (escape_md(r["description"]) if r["description"] else "—")
                   + " | %d | %d | " % (r["stargazers_count"], r["forks_count"])
                   + (escape_md(r["language"]) if r["language"] else "—") + " |")
    return out


def r_stats(c):
    return [c.h2("📊 GitHub Stats"), "", '<p align="center">',
            '  <img src="' + escape_attr(stats_url(c.login, c.wt("stats"))) + '" alt="stats" />',
            '  <img src="' + escape_attr(top_langs_url(c.login, c.wt("stats"))) + '" alt="top languages" />',
            "</p>"]


def r_streak(c):
    return [c.h2("🔥 Contribution Streak"), "", '<p align="center">',
            '  <img src="' + escape_attr(streak_url(c.login, c.wt("streak"))) + '" alt="streak" />', "</p>"]


def r_activity(c):
    return [c.h2("∿ Contribution Activity"), "", '<p align="center">',
            '  <img src="' + escape_attr(activity_url(c.login, c.wt("activity"))) + '" alt="activity graph" />', "</p>"]


def r_trophies(c):
    return [c.h2("🏆 Trophies"), "", '<p align="center">',
            '  <img src="' + escape_attr(trophy_url(c.login, c.wt("trophy"), c.o["trophyRows"], c.o["trophyCols"])) + '" alt="trophies" />',
            "</p>"]


def r_learning(c):
    return [c.h2("🌱 Currently Learning"), "", escape_md_text(c.o["learningText"] or DEFAULT_LEARNING)]


def r_quote(c):
    return [c.h2("💬 Dev Quote"), "",
            '> "Any fool can write code that a computer can understand. Good programmers write code that humans can understand." — Martin Fowler']


def r_hero(c):
    src = gif_url(c.o["heroGif"], DEFAULT_HERO_GIF)
    return ['<div align="center">', '  <img src="' + escape_attr(src) + '" width="100%" alt="" />', "</div>"] if src else []


def r_about(c):
    o = c.o

    def t(s):
        return escape_md_text(re.sub(r"\s*\n\s*", " ", str(s)))

    b = []
    if o["working"]:
        url = safe_url(o["workingUrl"], ["http", "https"])
        b.append("- 🔭 I’m currently working on **" + ("[" + t(o["working"]) + "](" + url + ")" if url else t(o["working"])) + "**")
    if o["learningText"]:
        b.append("- 🌱 I’m currently learning **" + t(o["learningText"]) + "**")
    if o["collab"]:
        b.append("- 👯 I’m looking to collaborate on **" + t(o["collab"]) + "**")
    if o["askMe"]:
        b.append("- 💬 Ask me about **" + t(o["askMe"]) + "**")
    if c.website:
        b.append("- 🏬 Pay a visit to my **[portfolio](" + c.website + ")**")
    if c.location:
        b.append("- 📍 Based in **" + t(c.location) + "**")
    email = re.sub(r"^mailto:", "", c.socials["email"], flags=re.I)
    mail = safe_url("mailto:" + email, ["mailto"]) if email else ""
    if mail:
        b.append("- 📫 How to reach me: **[" + t(email) + "](" + mail + ")**")
    if o["funFact"]:
        b.append("- ⚡ Fun fact: **" + t(o["funFact"]) + "**")
    if not b:
        return []
    out = [c.h2("👨‍💻 About Me"), ""]
    gif = safe_url(o["aboutGif"], ["https"]) if o["aboutGif"] else DEFAULT_ABOUT_GIF
    if gif:
        out += ['<img align="right" width="300" src="' + escape_attr(gif) + '" alt="" />', ""]
    out += b
    if gif:
        out += ["", '<br clear="right" />']
    return out


def r_profilestats(c):
    def cell(src, alt):
        return '      <td><img src="' + escape_attr(src) + '" alt="' + alt + '" /></td>'
    heads = ["👀 Views", "👤 Followers", "🌟 Stars", "✅ Awesome"]
    return (['<div align="center">', "", c.h2("📊 Profile Stats"), "", '<table align="center">', "  <tr>"]
            + ["    <td><b>" + h + "</b></td>" for h in heads]
            + ["  </tr>", "  <tr>",
               cell("https://komarev.com/ghpvc/?username=" + enc(c.login) + "&style=flat-square", "views"),
               cell("https://img.shields.io/github/followers/" + enc(c.login) + "?style=social", "followers"),
               cell("https://img.shields.io/github/stars/" + enc(c.login) + "?style=social", "stars"),
               cell("https://awesome.re/badge.svg", "awesome"),
               "  </tr>", "</table>", "", "</div>"])


def r_cards(c):
    st, sm = c.wt("stats"), c.wt("summary")
    return [c.h2("🖥️ GitHub Activity"), "", '<div align="center">',
            '  <img width="48%" src="' + escape_attr(stats_url(c.login, st)) + '" alt="stats" />',
            '  <img width="48%" src="' + escape_attr(streak_url(c.login, c.wt("streak"))) + '" alt="streak" />',
            "</div>", "", '<table align="center">', "  <tr>",
            '    <td width="33%"><img src="' + escape_attr(donut_langs_url(c.login, st)) + '" alt="top languages" /></td>',
            '    <td width="33%"><img src="' + escape_attr(summary_card_url(c.login, "stats", sm)) + '" alt="summary" /></td>',
            '    <td width="33%"><img src="' + escape_attr(summary_card_url(c.login, "productive-time", sm)) + '" alt="productive time" /></td>',
            "  </tr>", "</table>"]


def r_contrib3d(c):
    return ['<p align="center">', '  <img src="' + escape_attr(contrib3d_url(c.login)) + '" alt="3D contribution graph" />', "</p>"]


def r_chart(c):
    return ['<p align="center">', '  <img src="' + escape_attr(chart_url(c.login, c.wt("accent"))) + '" alt="contribution chart" />', "</p>"]


def r_gitanimals(c):
    return [c.h2("🐾 Git Animals"), "", '<p align="center">',
            '  <a href="https://www.gitanimals.org/"><img src="' + escape_attr(git_animals_url(c.login)) + '" width="600" alt="git animals farm" /></a>',
            "</p>"]


def r_funzone(c):
    return [c.h2("✨ Fun Zone"), "", '<p align="center">', '  <img src="' + JOKES_URL + '" alt="dev joke" />', "</p>", "",
            '<p align="center">', '  <img src="' + escape_attr(quote_card_url(c.wt("stats"))) + '" alt="dev quote" />', "</p>"]


def r_snake(c):
    return [c.h2("🐍 My Code Kingdom"), "", "<picture>",
            '  <source media="(prefers-color-scheme: dark)" srcset="' + escape_attr(snake_url(c.login, True)) + '" />',
            '  <source media="(prefers-color-scheme: light)" srcset="' + escape_attr(snake_url(c.login, False)) + '" />',
            '  <img alt="contribution snake" src="' + escape_attr(snake_url(c.login, False)) + '" />',
            "</picture>"]


def r_sponsors(c):
    href = "https://github.com/sponsors/" + enc(c.login)
    return [c.h2("☕ Fuel My Next Project"), "",
            "All my projects stay free and open source. If they help you, consider [sponsoring me on GitHub](" + href + ").", "",
            '<p align="center">',
            '  <a href="' + href + '"><img src="https://img.shields.io/badge/GitHub%20Sponsors-EA4AAA?style=for-the-badge&logo=githubsponsors&logoColor=white" alt="GitHub Sponsors" /></a>',
            "</p>"]


def r_footerwave(c):
    text = c.o["footerText"] or "Thanks for visiting my profile!"
    return ['<img src="' + escape_attr(footer_wave_url(text)) + '" width="100%" alt="" />', "",
            '<p align="center"><sub>' + escape_html(c.name) + " © %d • Crafted with ❤️</sub></p>" % datetime.date.today().year]


RENDERERS = {sid: globals()["r_" + sid] for sid in SECTION_IDS}


def generate(ctx, sections):
    lines = []
    for sid in sections:
        out = RENDERERS[sid](ctx)
        if out:
            lines += out + [""]
    lines += ["---", "", FOOTER]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip() + "\n"


# CLI

def resolve_sections(args, cfg):
    if args.sections:
        ids = [s.strip() for s in args.sections.split(",") if s.strip()]
    elif args.preset:
        ids = PRESETS[args.preset]
    elif cfg.get("sections"):
        ids = cfg["sections"]
    else:
        ids = PRESETS["classic"]
    unknown = [s for s in ids if s not in RENDERERS]
    if unknown:
        raise SystemExit("unknown section(s): " + ", ".join(unknown) + "\nknown: " + ", ".join(SECTION_IDS))
    return ids


def main(argv=None):
    p = argparse.ArgumentParser(description="Generate a GitHub profile README (Python port of README.forge).")
    p.add_argument("username", nargs="?", help="GitHub username or profile URL")
    p.add_argument("-o", "--output", default="README.md", help="output file, - for stdout (default README.md)")
    p.add_argument("-c", "--config", help="forge.config.json exported from tool.html")
    p.add_argument("--preset", choices=sorted(PRESETS), help="section layout preset")
    p.add_argument("--sections", help="comma-separated section ids, in order (overrides preset/config)")
    p.add_argument("--theme", choices=sorted(THEMES), help="widget theme")
    p.add_argument("--heading-gif", action="store_true", default=None, help="add the animated accent next to headings")
    p.add_argument("--workflows", metavar="DIR", help="write required GitHub Actions workflows into DIR")
    p.add_argument("--token", default=os.environ.get("GITHUB_TOKEN", ""), help="GitHub token (default $GITHUB_TOKEN)")
    p.add_argument("--list-sections", action="store_true", help="print section ids and exit")
    p.add_argument("--selftest", action="store_true", help="run built-in assertions and exit")
    args = p.parse_args(argv)

    if args.selftest:
        return 0 if selftest() else 1
    if args.list_sections:
        for sid, on, wf in SECTIONS:
            print("%-13s %s%s" % (sid, "default-on" if on else "", "  (needs workflow)" if wf else ""))
        return 0

    cfg = {}
    if args.config:
        with open(args.config, encoding="utf-8") as f:
            cfg = json.load(f)
    username = extract_username(args.username or cfg.get("username") or "")
    if not username:
        p.error("a valid GitHub username or URL is required (positional or in --config)")

    cfg.setdefault("options", {})
    if args.theme:
        cfg["options"]["theme"] = args.theme
    if args.heading_gif is not None:
        cfg["options"]["headingGif"] = True
    elif args.preset == "showcase" and "headingGif" not in cfg["options"]:
        cfg["options"]["headingGif"] = True
    sections = resolve_sections(args, cfg)

    user, repos, langs, source = fetch_profile(username, args.token)
    md = generate(Ctx(user, repos, langs, source, cfg), sections)

    if args.output == "-":
        sys.stdout.write(md)
    else:
        with open(args.output, "w", encoding="utf-8", newline="\n") as f:
            f.write(md)
        print("wrote " + args.output, file=sys.stderr)

    needed = required_workflows(sections)
    if needed and args.workflows:
        os.makedirs(args.workflows, exist_ok=True)
        for fname, yaml in needed:
            path = os.path.join(args.workflows, fname)
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(yaml)
            print("wrote " + path, file=sys.stderr)
    elif needed:
        print("note: %s need GitHub Actions in your profile repo; rerun with --workflows .github/workflows"
              % ", ".join(f for f, _ in needed), file=sys.stderr)
    return 0


# Self-test (--selftest)

def selftest():
    results = []

    def ok(name, cond):
        results.append((name, bool(cond)))

    ok("escape_html neutralizes tags", "<" not in escape_html("<img src=x onerror=alert(1)>"))
    ok("escape_html handles None", escape_html(None) == "")
    ok("escape_md escapes pipe", escape_md("a|b") == "a\\|b")
    ok("escape_md flattens newlines", "\n" not in escape_md("a\nb"))
    ok("escape_md_text keeps prose readable", escape_md_text("e.g. a-b") == "e.g. a-b")
    ok("escape_md_text escapes pipe", escape_md_text("a|b") == "a\\|b")

    ok("safe_url rejects javascript:", safe_url("javascript:alert(1)", ["http", "https"]) == "")
    ok("safe_url rejects data:", safe_url("data:text/html,x", ["http", "https"]) == "")
    ok("safe_url upgrades bare domain", safe_url("example.com", ["http", "https"]) == "https://example.com/")
    ok("safe_url allows mailto when asked", safe_url("mailto:a@b.com", ["mailto"]) != "")
    ok("safe_url blocks mailto by default", safe_url("mailto:a@b.com", ["http", "https"]) == "")

    ok("widget_theme maps activity", widget_theme("tokyonight", "activity") == "tokyo-night")
    ok("widget_theme maps trophy", widget_theme("github_dark", "trophy") == "gitdimmed")
    ok("widget_theme maps summary", widget_theme("nord", "summary") == "nord_dark")
    ok("widget_theme falls back", widget_theme("nonsense", "stats") == "tokyonight")

    q = urllib.parse.parse_qs(urllib.parse.urlsplit(shield_badge("Email", "a-b_c@x.com", "EA4335", "gmail")).query)
    ok("shield_badge preserves hyphens/underscores", q["message"] == ["a-b_c@x.com"])
    ok("shield_badge sets style", q["style"] == ["for-the-badge"])
    ok("typing_url joins on literal ;", typing_url(["a", "b"]).endswith("lines=a;b"))
    ok("typing_url strips inner ;", "%3B" not in typing_url(["a;b"]))
    ok("enc matches encodeURIComponent", enc("a b/c!'()*~") == "a%20b%2Fc!'()*~")

    ok("norm_lang folds spaces", norm_lang("Jupyter Notebook") == "jupyternotebook")
    ok("lang_meta finds C++", lang_meta("C++")[0] == "cplusplus")
    ok("lang_meta falls back without slug", lang_meta("Rich Text Format")[0] is None)
    ok("LANG_META keys are normalized", all(k == norm_lang(k) for k in LANG_META))

    ok("every section has a renderer", all(callable(RENDERERS.get(s)) for s in SECTION_IDS))
    ok("presets only name known sections", all(s in RENDERERS for p in PRESETS.values() for s in p))
    ok("snake_url dark variant", snake_url("a-b", True).endswith("/a-b/a-b/output/github-snake-dark.svg"))
    ok("contrib3d_url encodes login", "/a%20b/a%20b/" in contrib3d_url("a b"))
    ok("required_workflows picks snake", [f for f, _ in required_workflows(["snake", "header"])] == ["snake.yml"])
    ok("gif_url rejects javascript:", gif_url("javascript:alert(1)", "x") == "")

    user = {"login": "octocat", "name": "Octo|cat", "bio": "<b>hi</b>", "public_repos": 1, "followers": 2}
    repos = [{"id": 1, "name": "x", "full_name": "octocat/x", "html_url": "https://github.com/octocat/x",
              "description": "a|b", "stargazers_count": 3, "forks_count": 0, "language": "Python",
              "fork": False, "archived": False}]
    ctx = Ctx(user, repos, {"Python": 10}, "bytes", {"options": {"funFact": "x"}})
    md = generate(ctx, SECTION_IDS)
    ok("generate renders every section", md.count("## ") >= 15)
    ok("generate escapes bio html", "<b>hi</b>" not in md)
    ok("generate escapes table pipes", "a\\|b" in md)
    ok("heading gif off by default", "## 🏆 Trophies\n" in md)

    failed = [n for n, passed in results if not passed]
    for n, passed in results:
        print(("PASS " if passed else "FAIL ") + n)
    print(("%d of %d FAILED" % (len(failed), len(results))) if failed else "All %d passed" % len(results))
    return not failed


if __name__ == "__main__":
    sys.exit(main())
