"""Loading and validating forge.config.json.

The format is the one the original web UI exported, so old exports keep working:
camelCase option keys, unknown keys ignored. Values are type-checked here so the
renderers can trust them, which matters once configs arrive over HTTP.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

from .github import extract_username
from .sections import PRESETS, SECTION_IDS
from .socials import SOCIAL_KEYS
from .themes import DEFAULT_THEME, THEMES
from .urls import INSTANCE_NAMES, Instances, with_instances

MAX_TEXT = 2000
MAX_ITEMS = 100

FEATURED_LAYOUTS = ("table", "cards")
ICON_STYLES = ("emoji", "iconify", "local")


class ConfigError(ValueError):
    def __init__(self, errors: list[str]) -> None:
        super().__init__("; ".join(errors))
        self.errors = errors


@dataclass(frozen=True)
class Options:
    theme: str = DEFAULT_THEME
    typing_lines: tuple[str, ...] = ()
    banner_text: str = ""
    learning_text: str = ""
    trophy_rows: int = 1
    trophy_cols: int = 7
    featured_layout: str = "table"
    featured_count: int = 6
    show_views: bool = True
    hero_gif: str = ""
    about_gif: str = ""
    heading_gif: bool = False
    working: str = ""
    working_url: str = ""
    collab: str = ""
    ask_me: str = ""
    fun_fact: str = ""
    footer_text: str = ""
    credit: bool = True
    icon_style: str = "emoji"


# JSON key in forge.config.json -> Options attribute.
OPTION_KEYS: dict[str, str] = {
    "theme": "theme",
    "typingLines": "typing_lines",
    "bannerText": "banner_text",
    "learningText": "learning_text",
    "trophyRows": "trophy_rows",
    "trophyCols": "trophy_cols",
    "featuredLayout": "featured_layout",
    "featuredCount": "featured_count",
    "showViews": "show_views",
    "heroGif": "hero_gif",
    "aboutGif": "about_gif",
    "headingGif": "heading_gif",
    "working": "working",
    "workingUrl": "working_url",
    "collab": "collab",
    "askMe": "ask_me",
    "funFact": "fun_fact",
    "footerText": "footer_text",
    "credit": "credit",
    "iconStyle": "icon_style",
}

_CHOICES: dict[str, tuple[str, ...]] = {
    "theme": tuple(THEMES),
    "featured_layout": FEATURED_LAYOUTS,
    "icon_style": ICON_STYLES,
}
_RANGES: dict[str, tuple[int, int]] = {
    "trophy_rows": (1, 6),
    "trophy_cols": (1, 7),
    "featured_count": (1, 30),
}

CUSTOM_KEYS = ("name", "tagline", "bio", "location", "website")


@dataclass(frozen=True)
class Config:
    username: str = ""
    # None means "not chosen", which falls back to the classic preset.
    sections: tuple[str, ...] | None = None
    options: Options = field(default_factory=Options)
    socials: Mapping[str, str] = field(default_factory=lambda: dict.fromkeys(SOCIAL_KEYS, ""))
    # None keeps the value from the GitHub profile; "" deliberately clears it.
    custom: Mapping[str, str | None] = field(default_factory=lambda: dict.fromkeys(CUSTOM_KEYS))
    featured: tuple[str, ...] | None = None
    langs: tuple[str, ...] | None = None
    instances: Instances = field(default_factory=Instances)

    @property
    def section_ids(self) -> tuple[str, ...]:
        return self.sections if self.sections is not None else tuple(PRESETS["classic"])


class _Checker:
    def __init__(self) -> None:
        self.errors: list[str] = []

    def text(self, where: str, value: Any, *, optional: bool = False) -> str | None:
        if value is None:
            return None if optional else ""
        if not isinstance(value, str):
            self.errors.append(f"{where} must be a string")
            return None if optional else ""
        if len(value) > MAX_TEXT:
            self.errors.append(f"{where} is longer than {MAX_TEXT} characters")
            return value[:MAX_TEXT]
        return value

    def text_list(self, where: str, value: Any) -> tuple[str, ...] | None:
        if value is None:
            return None
        if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
            self.errors.append(f"{where} must be a list of strings")
            return None
        if len(value) > MAX_ITEMS:
            self.errors.append(f"{where} has more than {MAX_ITEMS} items")
        return tuple(self.text(f"{where}[{i}]", v) or "" for i, v in enumerate(value[:MAX_ITEMS]))

    def mapping(self, where: str, value: Any) -> Mapping[str, Any]:
        if value is None:
            return {}
        if not isinstance(value, Mapping):
            self.errors.append(f"{where} must be an object")
            return {}
        return value


def _parse_options(check: _Checker, raw: Mapping[str, Any]) -> Options:
    defaults = Options()
    values: dict[str, Any] = {}
    for key, attr in OPTION_KEYS.items():
        if key not in raw or raw[key] is None:
            continue
        value = raw[key]
        default = getattr(defaults, attr)
        where = f"options.{key}"
        if isinstance(default, bool):
            if not isinstance(value, bool):
                check.errors.append(f"{where} must be true or false")
                continue
        elif isinstance(default, int):
            if isinstance(value, float) and value.is_integer():
                value = int(value)
            if not isinstance(value, int) or isinstance(value, bool):
                check.errors.append(f"{where} must be a whole number")
                continue
            low, high = _RANGES[attr]
            if not low <= value <= high:
                check.errors.append(f"{where} must be between {low} and {high}")
                continue
        elif isinstance(default, tuple):
            value = check.text_list(where, value)
            if value is None:
                continue
        else:
            value = check.text(where, value)
        if attr in _CHOICES and value not in _CHOICES[attr]:
            check.errors.append(f"{where} must be one of {', '.join(_CHOICES[attr])}")
            continue
        values[attr] = value
    return replace(defaults, **values)


def parse_config(data: Any, *, instances: Instances | None = None) -> Config:
    """Validate a decoded forge.config.json.

    instances is the base the config's own "instances" key is layered on, typically
    the defaults overridden by environment variables. Raises ConfigError with every
    problem found, not just the first.
    """
    check = _Checker()
    if not isinstance(data, Mapping):
        raise ConfigError(["config must be a JSON object"])

    username = ""
    raw_user = check.text("username", data.get("username"))
    if raw_user:
        username = extract_username(raw_user) or ""
        if not username:
            check.errors.append("username is not a valid GitHub username or profile URL")

    sections = check.text_list("sections", data.get("sections"))
    if sections is not None:
        unknown = [s for s in sections if s not in SECTION_IDS]
        if unknown:
            check.errors.append("unknown section(s): " + ", ".join(unknown))
        if len(set(sections)) != len(sections):
            check.errors.append("sections must not repeat")

    options = _parse_options(check, check.mapping("options", data.get("options")))

    raw_socials = check.mapping("socials", data.get("socials"))
    socials = {k: check.text(f"socials.{k}", raw_socials.get(k)) or "" for k in SOCIAL_KEYS}

    raw_custom = check.mapping("custom", data.get("custom"))
    custom = {k: check.text(f"custom.{k}", raw_custom.get(k), optional=True) for k in CUSTOM_KEYS}

    resolved = instances or Instances()
    raw_instances = check.mapping("instances", data.get("instances"))
    try:
        resolved = with_instances(resolved, {k: v for k, v in raw_instances.items() if v})
    except ValueError as exc:
        check.errors.append(str(exc))

    config = Config(
        username=username,
        sections=sections,
        options=options,
        socials=socials,
        custom=custom,
        featured=check.text_list("featured", data.get("featured")),
        langs=check.text_list("langs", data.get("langs")),
        instances=resolved,
    )
    if check.errors:
        raise ConfigError(check.errors)
    return config


def read_config_file(path: str | Path) -> Any:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError as exc:
        raise ConfigError([f"cannot read {path}: {exc.strerror}"]) from None
    except ValueError as exc:
        raise ConfigError([f"{path} is not valid JSON: {exc}"]) from None


def load_config(path: str | Path, *, instances: Instances | None = None) -> Config:
    return parse_config(read_config_file(path), instances=instances)


def config_to_dict(config: Config) -> dict[str, Any]:
    """Serialise back to the forge.config.json format."""
    options = {key: getattr(config.options, attr) for key, attr in OPTION_KEYS.items()}
    options["typingLines"] = list(config.options.typing_lines)
    defaults = Instances()
    data: dict[str, Any] = {
        "username": config.username,
        "sections": list(config.section_ids),
        "socials": dict(config.socials),
        "options": options,
        "custom": {k: v for k, v in config.custom.items() if v is not None},
        "featured": None if config.featured is None else list(config.featured),
        "langs": None if config.langs is None else list(config.langs),
        "instances": {
            name: getattr(config.instances, name)
            for name in INSTANCE_NAMES
            if getattr(config.instances, name) != getattr(defaults, name)
        },
    }
    return {k: v for k, v in data.items() if v is not None}
