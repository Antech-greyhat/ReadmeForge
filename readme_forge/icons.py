"""Bundled Tabler outline icons for the "local" heading icon style.

The SVGs ship inside the package (MIT, see icons/LICENSE) and are recoloured to the
theme accent when written, because an SVG loaded through <img> ignores currentColor.
"""

from __future__ import annotations

from collections.abc import Iterable
from importlib import resources
from pathlib import Path


def bundled_icon(name: str) -> str:
    return resources.files("readme_forge").joinpath("icons", f"{name}.svg").read_text("utf-8")


def bundled_licence() -> str:
    return resources.files("readme_forge").joinpath("icons", "LICENSE").read_text("utf-8")


def recolor(svg: str, accent: str) -> str:
    return svg.replace('stroke="currentColor"', f'stroke="#{accent}"')


def write_icons(assets_dir: str | Path, names: Iterable[str], accent: str) -> list[Path]:
    """Write recoloured icons to <assets_dir>/icons/ and return the paths written."""
    target = Path(assets_dir) / "icons"
    target.mkdir(parents=True, exist_ok=True)
    written = []
    for name in dict.fromkeys(names):
        path = target / f"{name}.svg"
        path.write_text(recolor(bundled_icon(name), accent), encoding="utf-8", newline="\n")
        written.append(path)
    return written
