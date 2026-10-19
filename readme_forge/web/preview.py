"""Server-side README preview: Markdown to HTML, then an allowlist sanitiser.

The engine already escapes everything it emits, so this is the second line of defence:
if an escaping bug ever lets markup through, nh3 still strips scripts and handlers
before the preview reaches the browser.
"""

from __future__ import annotations

import nh3
from markdown_it import MarkdownIt

_markdown = MarkdownIt("commonmark", {"html": True}).enable(["table", "strikethrough"])

# Tags README sections emit directly, plus those Markdown itself produces.
ALLOWED_TAGS = {
    "a", "b", "blockquote", "br", "code", "del", "div", "em", "h1", "h2", "h3", "hr", "img",
    "li", "ol", "p", "picture", "pre", "source", "strong", "sub", "table", "tbody", "td", "th",
    "thead", "tr", "ul",
}  # fmt: skip

ALLOWED_ATTRIBUTES = {
    "*": {"align"},
    "a": {"href", "title"},
    "img": {"src", "alt", "width", "height", "title"},
    "source": {"srcset", "media"},
    "td": {"width"},
    "th": {"width"},
    "br": {"clear"},
}

ALLOWED_SCHEMES = {"http", "https", "mailto"}


def render_preview(markdown: str) -> str:
    return nh3.clean(
        _markdown.render(markdown),
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        url_schemes=ALLOWED_SCHEMES,
        link_rel="noopener noreferrer",
    )
