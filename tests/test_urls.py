import re
import urllib.parse

import pytest

from readme_forge import urls
from readme_forge.languages import LANG_META, lang_meta, norm_lang
from readme_forge.themes import THEMES, widget_theme
from readme_forge.urls import Instances, instances_from_env, with_instances


def test_widget_theme_maps_activity():
    assert widget_theme("tokyonight", "activity") == "tokyo-night"


def test_widget_theme_maps_trophy():
    assert widget_theme("github_dark", "trophy") == "gitdimmed"


def test_widget_theme_maps_summary():
    assert widget_theme("nord", "summary") == "nord_dark"


def test_widget_theme_maps_accent_to_bare_hex():
    assert re.fullmatch(r"[0-9A-F]{6}", widget_theme("dracula", "accent"))


def test_widget_theme_falls_back():
    assert widget_theme("nonsense", "stats") == "tokyonight"


def test_every_theme_has_a_hex_accent():
    assert all(re.fullmatch(r"[0-9A-F]{6}", t.accent) for t in THEMES.values())


def test_shield_badge_preserves_hyphens_and_underscores():
    query = urllib.parse.parse_qs(
        urllib.parse.urlsplit(urls.shield_badge("Email", "a-b_c@x.com", "EA4335", "gmail")).query
    )
    assert query["message"] == ["a-b_c@x.com"]
    assert query["style"] == ["for-the-badge"]


def test_typing_url_joins_on_literal_semicolon():
    assert urls.typing_url(["a", "b"]).endswith("lines=a;b")


def test_typing_url_strips_inner_semicolons():
    assert "%3B" not in urls.typing_url(["a;b"])


def test_norm_lang_folds_spaces():
    assert norm_lang("Jupyter Notebook") == "jupyternotebook"


@pytest.mark.parametrize(
    ("lang", "slug"), [("C++", "cplusplus"), ("C#", "csharp"), ("Jupyter Notebook", "jupyter")]
)
def test_lang_meta_finds_slug(lang, slug):
    assert lang_meta(lang).slug == slug


def test_lang_meta_falls_back_without_slug():
    assert lang_meta("Rich Text Format").slug is None


def test_lang_meta_keys_are_normalized():
    assert all(key == norm_lang(key) for key in LANG_META)


def test_lang_meta_colors_are_hex():
    assert all(re.fullmatch(r"[0-9A-Fa-f]{6}", m.color) for m in LANG_META.values())


def test_snake_url_dark_variant():
    assert urls.snake_url("a-b", True).endswith("/a-b/a-b/output/github-snake-dark.svg")


def test_contrib3d_url_encodes_login():
    assert "/a%20b/a%20b/" in urls.contrib3d_url("a b")


def test_footer_wave_url_encodes_text():
    assert urls.footer_wave_url("a&b").endswith("text=a%26b")


def test_iconify_url_uses_accent():
    assert urls.iconify_url("star", "BD93F9") == (
        "https://api.iconify.design/tabler/star.svg?color=%23BD93F9&height=24"
    )


def test_instance_override_changes_only_that_family():
    inst = with_instances(Instances(), {"stats": "https://stats.example.com/"})
    assert inst.stats == "https://stats.example.com"
    assert inst.streak == Instances().streak
    assert urls.stats_url(inst.stats, "me", "dark").startswith("https://stats.example.com/api?")


def test_instance_override_keeps_subpath():
    inst = with_instances(Instances(), {"streak": "https://example.com/streak"})
    assert urls.streak_url(inst.streak, "me", "dark").startswith(
        "https://example.com/streak?user=me"
    )


@pytest.mark.parametrize(
    "url",
    ["http://stats.example.com", "javascript:alert(1)", "", "https://x.com/?a=1", "ftp://x.com"],
)
def test_instance_rejects_non_https(url):
    with pytest.raises(ValueError):
        with_instances(Instances(), {"stats": url})


def test_instance_rejects_unknown_name():
    with pytest.raises(ValueError, match="unknown instance"):
        with_instances(Instances(), {"nope": "https://x.com"})


def test_instances_from_env():
    inst = instances_from_env({"READMEFORGE_INSTANCE_TROPHY": "https://trophy.example.com"})
    assert inst.trophy == "https://trophy.example.com"
    assert inst.stats == Instances().stats
