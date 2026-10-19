from dataclasses import replace

import pytest

from readme_forge.config import Config, Options, parse_config
from readme_forge.github import Profile, Repo, User
from readme_forge.sections import (
    HEADINGS,
    PRESETS,
    RENDERERS,
    SECTION_IDS,
    SECTIONS,
    build_context,
    generate,
    heading,
    heading_icons,
)
from tests.support import TODAY

TRICKY = Profile(
    user=User(login="octocat", name="Octo|cat", bio="<b>hi</b>", public_repos=1, followers=2),
    repos=(
        Repo(
            id=1,
            name="x",
            full_name="octocat/x",
            html_url="https://github.com/octocat/x",
            description="a|b",
            stargazers_count=3,
            language="Python",
        ),
    ),
    languages={"Python": 10},
    lang_source="bytes",
)


def render(config: Config, sections=SECTION_IDS, profile: Profile = TRICKY) -> str:
    return generate(build_context(profile, config, today=TODAY), sections)


def with_options(**kwargs) -> Config:
    return Config(options=replace(Options(), **kwargs))


def test_every_section_has_a_renderer():
    assert all(callable(RENDERERS.get(s)) for s in SECTION_IDS)


def test_no_orphan_renderers():
    assert set(RENDERERS) == set(SECTION_IDS)


def test_presets_only_name_known_sections():
    assert all(s in SECTION_IDS for preset in PRESETS.values() for s in preset)


def test_every_heading_belongs_to_a_section():
    assert set(HEADINGS) <= set(SECTION_IDS)


def test_classic_preset_is_the_default_on_sections():
    assert PRESETS["classic"] == tuple(s.id for s in SECTIONS if s.default_on)


def test_generate_renders_every_section():
    assert render(with_options(fun_fact="x")).count("## ") >= 15


def test_generate_escapes_bio_html():
    assert "<b>hi</b>" not in render(Config())


def test_generate_escapes_table_pipes():
    assert "a\\|b" in render(Config())


def test_heading_gif_off_by_default():
    assert "## 🏆 Trophies\n" in render(Config())


def test_heading_gif_on():
    ctx = build_context(TRICKY, with_options(heading_gif=True), today=TODAY)
    assert heading(ctx, "trophies").startswith("## 🏆 Trophies <img")


def test_user_gif_rejects_javascript():
    md = render(with_options(hero_gif="javascript:alert(1)"), ["hero"])
    assert "javascript" not in md


def test_user_gif_falls_back_when_blank():
    assert "user-images.githubusercontent.com" in render(Config(), ["hero"])


def test_credit_footer_on_by_default():
    assert render(Config(), ["quote"]).endswith("Antech-greyhat</a></p>\n")


def test_credit_footer_can_be_disabled():
    md = render(with_options(credit=False), ["quote"])
    assert "Antech-greyhat" not in md
    assert not md.rstrip().endswith("---")


def test_iconify_headings_use_theme_accent():
    md = render(with_options(icon_style="iconify", theme="dracula"), ["trophies"])
    assert md.startswith(
        '## <img src="https://api.iconify.design/tabler/trophy.svg?color=%23BD93F9&amp;height=24"'
        ' alt="" height="24" /> Trophies'
    )


def test_local_headings_reference_assets_dir():
    ctx = build_context(TRICKY, with_options(icon_style="local"), today=TODAY)
    assert generate(ctx, ["trophies"]).startswith(
        '## <img src="./assets/icons/trophy.svg" alt="" height="24" /> Trophies'
    )


def test_heading_icons_lists_only_sections_with_headings():
    assert heading_icons(["header", "stats", "snake"]) == ["chart-bar", "grid-dots"]


def test_instances_reach_every_widget():
    config = parse_config(
        {
            "instances": {
                "stats": "https://s.example.com",
                "streak": "https://k.example.com",
                "trophy": "https://t.example.com",
                "activity": "https://a.example.com",
                "summary": "https://m.example.com",
            },
            "options": {"featuredLayout": "cards"},
        }
    )
    md = render(config, ["featured", "stats", "streak", "activity", "trophies", "cards"])
    assert "vercel.app" not in md
    assert "demolab.com" not in md
    for host in "sktam":
        assert f"https://{host}.example.com" in md


def test_header_meta_is_html_not_markdown():
    profile = replace(TRICKY, user=replace(TRICKY.user, location="St. Louis", blog="example.com"))
    md = render(Config(), ["header"], profile)
    assert "**" not in md
    assert "St. Louis" in md
    assert '<a href="https://example.com/">Website</a>' in md


def test_featured_count_limits_default_selection():
    repos = tuple(
        replace(TRICKY.repos[0], id=i, name=f"r{i}", stargazers_count=i) for i in range(10)
    )
    md = render(with_options(featured_count=2), ["featured"], replace(TRICKY, repos=repos))
    assert "r9" in md and "r8" in md and "r7" not in md


@pytest.mark.parametrize("section", SECTION_IDS)
def test_each_section_renders_alone(section):
    assert render(with_options(fun_fact="x"), [section]).endswith("\n")
