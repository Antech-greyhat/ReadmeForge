"""Widget themes.

Each widget family names its themes differently, so one README theme maps to a
separate value per family. Stats and streak cards accept the theme id as is.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    id: str
    label: str
    activity: str
    trophy: str
    summary: str
    accent: str


DEFAULT_THEME = "tokyonight"

THEMES: dict[str, Theme] = {
    t.id: t
    for t in (
        Theme("tokyonight", "Tokyo Night", "tokyo-night", "tokyonight", "tokyonight", "7AA2F7"),
        Theme("dracula", "Dracula", "dracula", "dracula", "dracula", "BD93F9"),
        Theme("radical", "Radical", "react-dark", "radical", "radical", "FE428E"),
        Theme("onedark", "One Dark", "react-dark", "onedark", "one_dark", "E5C07B"),
        Theme("gruvbox", "Gruvbox", "gruvbox", "gruvbox", "gruvbox", "FABD2F"),
        Theme("nord", "Nord", "nord", "nord", "nord_dark", "88C0D0"),
        Theme("github_dark", "GitHub Dark", "github-compact", "gitdimmed", "github_dark", "58A6FF"),
        Theme("default", "Light", "github", "flat", "default", "216E39"),
    )
}

_MAPPED_WIDGETS = ("activity", "trophy", "summary", "accent")


def widget_theme(theme_id: str, widget: str) -> str:
    theme = THEMES.get(theme_id) or THEMES[DEFAULT_THEME]
    if widget in _MAPPED_WIDGETS:
        return getattr(theme, widget)
    return theme.id
