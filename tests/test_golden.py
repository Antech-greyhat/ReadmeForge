"""Recorded API responses in, expected README out.

The expected files were produced by the pre-package readme_forge.py, so these tests pin
the engine's output byte for byte across refactors.
"""

import pytest

from readme_forge.cli import build_parser, resolve_config
from readme_forge.github import GitHubClient, fetch_profile
from readme_forge.sections import build_context, generate
from tests.support import FIXTURES, GOLDEN, TODAY

CASES = {
    "classic": ["octocat"],
    "showcase": ["octocat", "--preset", "showcase"],
    "full": ["--config", str(FIXTURES / "configs" / "full.json")],
}


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for name in ("STATS", "STREAK", "TROPHY", "ACTIVITY", "SUMMARY"):
        monkeypatch.delenv(f"READMEFORGE_INSTANCE_{name}", raising=False)


@pytest.mark.parametrize("name", CASES)
def test_output_matches_golden(name: str, client: GitHubClient) -> None:
    config = resolve_config(build_parser().parse_args(CASES[name]))
    ctx = build_context(fetch_profile(client, config.username), config, today=TODAY)
    expected = (GOLDEN / f"{name}.md").read_text(encoding="utf-8")
    assert generate(ctx, config.section_ids) == expected
