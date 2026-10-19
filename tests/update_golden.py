"""Regenerate tests/golden/*.md after an intentional output change.

    python -m tests.update_golden

Review the resulting diff line by line: every change lands in users' READMEs.
"""

from readme_forge.cli import build_parser, resolve_config
from readme_forge.github import GitHubClient, fetch_profile
from readme_forge.sections import build_context, generate
from tests.support import GOLDEN, TODAY, FixtureTransport
from tests.test_golden import CASES


def main() -> None:
    for name, argv in CASES.items():
        config = resolve_config(build_parser().parse_args(argv))
        profile = fetch_profile(GitHubClient(transport=FixtureTransport()), config.username)
        markdown = generate(build_context(profile, config, today=TODAY), config.section_ids)
        path = GOLDEN / f"{name}.md"
        path.write_text(markdown, encoding="utf-8", newline="\n")
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
