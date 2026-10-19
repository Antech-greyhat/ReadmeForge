"""Escapers for the three contexts a README value can land in: HTML, Markdown and URLs.

Every value that comes from the GitHub API or from the user goes through one of these
before it reaches the output, so a hostile bio or repo name cannot inject markup.
"""

from __future__ import annotations

import re
import urllib.parse
from collections.abc import Iterable, Sequence

_HTML_MAP = {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}
_UNSAFE_URL_CHARS = re.compile(r"[\s<>\"]")
_SCHEME = re.compile(r"^[a-z][a-z0-9+.-]*:", re.I)


def escape_html(value: object) -> str:
    return re.sub(r"[&<>\"']", lambda m: _HTML_MAP[m.group(0)], "" if value is None else str(value))


def escape_attr(value: object) -> str:
    return re.sub(r"\r?\n", " ", escape_html(value))


def escape_md(value: object) -> str:
    """Escape for inline Markdown such as table cells, where newlines would break the row."""
    text = re.sub(r"\r?\n", " ", "" if value is None else str(value))
    return re.sub(r"([\\`*_{}\[\]()#+\-.!|<>])", r"\\\1", text)


def escape_md_text(value: object) -> str:
    """Escape prose: only what breaks structure or injects HTML, so punctuation stays readable."""
    text = ("" if value is None else str(value)).replace("\r\n", "\n")
    return re.sub(r"([\\`<>|\[\]])", r"\\\1", text)


def safe_url(value: str | None, schemes: Sequence[str]) -> str:
    """Return a normalised URL if its scheme is allowed, otherwise an empty string.

    Bare domains are upgraded to https. The result matches what the browser's URL
    serialiser produced in the original web UI, so outputs stay byte-identical.
    """
    if not value:
        return ""
    raw = value if _SCHEME.match(value) else "https://" + value
    try:
        parts = urllib.parse.urlsplit(raw)
    except ValueError:
        return ""
    scheme = parts.scheme.lower()
    if scheme not in schemes:
        return ""
    if _UNSAFE_URL_CHARS.search(raw):
        return ""
    if scheme in ("http", "https"):
        if not parts.netloc:
            return ""
        return urllib.parse.urlunsplit(
            (scheme, parts.netloc.lower(), parts.path or "/", parts.query, parts.fragment)
        )
    return raw


def enc(value: object) -> str:
    """Same character set as JavaScript's encodeURIComponent."""
    return urllib.parse.quote(str(value), safe="!~*'()")


def qs(pairs: Iterable[tuple[str, str]]) -> str:
    """Same output as JavaScript's URLSearchParams.toString()."""
    return urllib.parse.urlencode(list(pairs))
