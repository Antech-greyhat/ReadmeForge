# Contributing

Bug reports and pull requests are welcome.

## Setup

```bash
git clone https://github.com/Antech-greyhat/ReadmeForge
cd ReadmeForge
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

Run the checks CI runs:

```bash
ruff check .
ruff format --check .
pytest
```

Tests never touch the network. GitHub responses come from `tests/fixtures/github/`, and a
socket guard in `tests/conftest.py` fails any test that tries to connect.

## Adding a section

A section is one Python function plus a test.

1. Add a `SectionSpec` to `SECTIONS` in `readme_forge/sections.py`. Set `workflow=` if the
   section embeds files that a GitHub Action generates.
2. Write `r_<id>(ctx: Context) -> list[str]`. Return Markdown lines, or `[]` to skip the
   section. Keep it pure: read only from `ctx`.
3. If it has a heading, add a `Heading` entry with an emoji, a title and a
   [Tabler](https://tabler.io/icons) icon name. Copy the outline SVG into
   `readme_forge/icons/`.
4. Escape everything that comes from the user or the API: `escape_html` and `escape_attr`
   in HTML, `escape_md` in table cells, `escape_md_text` in prose, and `safe_url` for
   every link.
5. Add a test in `tests/test_sections.py`.

The web UI picks the section up automatically.

## Output changes

`tests/golden/` holds full READMEs generated from recorded API data. If you change
output on purpose, regenerate them and review the diff line by line, because the same
change lands in every user's README:

```bash
python -m tests.update_golden
git diff tests/golden
```

## Code style

- Python 3.10+, type hints, `ruff` with a line length of 100.
- Small modules and pure functions. The core and the CLI stay stdlib-only, and web
  dependencies stay inside `readme_forge/web/`.
- Comments explain why, not what. No decorative banners.
- The web UI's JavaScript only handles UI behaviour. No frameworks, bundlers or npm.

## Commits and pull requests

Use [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`,
`refactor:`, `test:`, `docs:`, `chore:`) with an imperative subject of 72 characters or
fewer. The body should explain why the change is needed.
