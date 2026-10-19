import re
from pathlib import Path

import pytest

tomllib = pytest.importorskip("tomllib")

ROOT = Path(__file__).resolve().parent.parent


def _names(requirements: list[str]) -> set[str]:
    return {re.split(r"[<>=\[ ]", r, maxsplit=1)[0].lower() for r in requirements}


def test_requirements_txt_matches_deploy_extra():
    extras = tomllib.loads((ROOT / "pyproject.toml").read_text("utf-8"))["project"][
        "optional-dependencies"
    ]
    expected = (_names(extras["web"]) | _names(extras["deploy"])) - {"readme-forge"}
    lines = (ROOT / "requirements.txt").read_text("utf-8").splitlines()
    pinned = [line for line in lines if line and not line.startswith("#")]
    assert _names(pinned) == expected
