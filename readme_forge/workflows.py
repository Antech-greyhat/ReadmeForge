"""GitHub Actions workflows for sections that embed files generated inside the profile repo."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from .sections import SECTIONS


@dataclass(frozen=True)
class Workflow:
    file: str
    title: str
    yaml: str


WORKFLOWS: dict[str, Workflow] = {
    "snake": Workflow(
        "snake.yml",
        "Contribution Snake",
        """\
name: Generate snake animation
on:
  schedule:
    - cron: "0 */12 * * *"
  workflow_dispatch:
  push:
    branches: [main]
permissions:
  contents: write
jobs:
  generate:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - uses: Platane/snk@v3
        with:
          github_user_name: ${{ github.repository_owner }}
          outputs: |
            dist/github-snake.svg
            dist/github-snake-dark.svg?palette=github-dark
      - uses: crazy-max/ghaction-github-pages@v4
        with:
          target_branch: output
          build_dir: dist
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
""",
    ),
    "contrib3d": Workflow(
        "profile-3d-contrib.yml",
        "3D Contributions",
        """\
name: GitHub-Profile-3D-Contrib
on:
  schedule:
    - cron: "0 18 * * *"
  workflow_dispatch:
permissions:
  contents: write
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: yoshi389111/github-profile-3d-contrib@v0.9.3
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          USERNAME: ${{ github.repository_owner }}
      - name: Commit and push
        run: |
          git config user.name github-actions
          git config user.email github-actions@github.com
          git add -A .
          git commit -m "Update 3D contribution graph" || exit 0
          git push
""",
    ),
}


def required_workflows(section_ids: Iterable[str]) -> list[Workflow]:
    wanted = set(section_ids)
    return [WORKFLOWS[s.workflow] for s in SECTIONS if s.workflow and s.id in wanted]


def write_workflows(directory: str | Path, workflows: Iterable[Workflow]) -> list[Path]:
    target = Path(directory)
    target.mkdir(parents=True, exist_ok=True)
    written = []
    for workflow in workflows:
        path = target / workflow.file
        path.write_text(workflow.yaml, encoding="utf-8", newline="\n")
        written.append(path)
    return written
