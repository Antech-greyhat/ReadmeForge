import subprocess
import sys
from pathlib import Path

import pytest

from readme_forge import cli
from readme_forge.github import GitHubClient, Response
from tests.support import GOLDEN, FixtureTransport

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def transport(monkeypatch):
    fake = FixtureTransport()
    monkeypatch.setattr(cli, "GitHubClient", lambda token: GitHubClient(token, transport=fake))
    for name in ("STATS", "STREAK", "TROPHY", "ACTIVITY", "SUMMARY"):
        monkeypatch.delenv(f"READMEFORGE_INSTANCE_{name}", raising=False)
    return fake


def run(*argv: str) -> int:
    return cli.main(list(argv))


def test_writes_classic_readme(tmp_path, transport):
    out = tmp_path / "README.md"
    assert run("octocat", "-o", str(out)) == 0
    assert out.read_text(encoding="utf-8") == (GOLDEN / "classic.md").read_text(encoding="utf-8")


def test_stdout_output(transport, capsys):
    assert run("github.com/octocat", "-o", "-", "--sections", "header") == 0
    assert capsys.readouterr().out.startswith('<h1 align="center">')


def test_workflows_are_written(tmp_path, transport):
    wf = tmp_path / "wf"
    run("octocat", "-o", str(tmp_path / "R.md"), "--sections", "snake", "--workflows", str(wf))
    assert (wf / "snake.yml").read_text(encoding="utf-8").startswith("name: Generate snake")


def test_missing_workflows_produce_a_note(tmp_path, transport, capsys):
    run("octocat", "-o", str(tmp_path / "R.md"), "--sections", "contrib3d")
    assert "profile-3d-contrib.yml" in capsys.readouterr().err


def test_no_credit(transport, capsys):
    run("octocat", "-o", "-", "--sections", "quote", "--no-credit")
    assert "Antech-greyhat" not in capsys.readouterr().out


def test_instance_flag(transport, capsys):
    run("octocat", "-o", "-", "--sections", "stats", "--instance", "stats=https://s.example.com")
    out = capsys.readouterr().out
    assert "https://s.example.com/api?username=octocat" in out
    assert "vercel.app" not in out


def test_instance_flag_beats_env_and_config(tmp_path, transport, capsys, monkeypatch):
    monkeypatch.setenv("READMEFORGE_INSTANCE_STATS", "https://env.example.com")
    config = tmp_path / "c.json"
    config.write_text('{"instances": {"stats": "https://cfg.example.com"}}', encoding="utf-8")
    run("octocat", "-c", str(config), "-o", "-", "--sections", "stats")
    assert "https://cfg.example.com/api" in capsys.readouterr().out
    run("octocat", "-c", str(config), "-o", "-", "--sections", "stats",
        "--instance", "stats=https://cli.example.com")  # fmt: skip
    assert "https://cli.example.com/api" in capsys.readouterr().out


def test_env_instance(transport, capsys, monkeypatch):
    monkeypatch.setenv("READMEFORGE_INSTANCE_TROPHY", "https://t.example.com")
    run("octocat", "-o", "-", "--sections", "trophies")
    assert "https://t.example.com/?username=octocat" in capsys.readouterr().out


@pytest.mark.parametrize(
    "argv",
    [
        ["--instance", "stats=http://insecure.example.com"],
        ["--instance", "nope=https://x.example.com"],
        ["--sections", "header,nope"],
        ["--config", "does-not-exist.json"],
    ],
)
def test_bad_input_exits_with_usage_error(transport, capsys, argv):
    assert run("octocat", "-o", "-", *argv) == 2
    assert capsys.readouterr().err.startswith("error:")


def test_missing_username(transport, capsys):
    assert run("-o", "-") == 2
    assert "username" in capsys.readouterr().err


def test_unknown_user(transport, capsys):
    assert run("ghost-user-xyz", "-o", "-") == 1
    assert "not found" in capsys.readouterr().err


def test_token_is_not_echoed_on_failure(transport, capsys):
    transport.overrides["/users/octocat"] = Response(401, {}, b"")
    assert run("octocat", "-o", "-", "--token", "ghp_topsecret") == 1
    captured = capsys.readouterr()
    assert "ghp_topsecret" not in captured.err + captured.out


def test_local_icons_written_and_referenced(tmp_path, transport):
    out = tmp_path / "profile" / "README.md"
    out.parent.mkdir()
    assets = tmp_path / "profile" / "assets"
    run("octocat", "-o", str(out), "--sections", "stats,trophies", "--icons", "local",
        "--theme", "dracula", "--assets", str(assets))  # fmt: skip
    md = out.read_text(encoding="utf-8")
    assert '<img src="./assets/icons/chart-bar.svg"' in md
    svg = (assets / "icons" / "trophy.svg").read_text(encoding="utf-8")
    assert 'stroke="#BD93F9"' in svg
    assert "currentColor" not in svg


def test_local_icons_without_assets_dir_warn(transport, capsys):
    run("octocat", "-o", "-", "--sections", "stats", "--icons", "local")
    assert "--assets" in capsys.readouterr().err


def test_iconify_flag(transport, capsys):
    run("octocat", "-o", "-", "--sections", "stats", "--icons", "iconify")
    assert "api.iconify.design/tabler/chart-bar.svg" in capsys.readouterr().out


def test_showcase_heading_gif_can_be_disabled(transport, capsys):
    run("octocat", "-o", "-", "--preset", "showcase", "--no-heading-gif")
    assert "kyubey.gif" not in capsys.readouterr().out


def test_list_sections(capsys):
    assert run("--list-sections") == 0
    assert "snake" in capsys.readouterr().out


def test_serve_help():
    with pytest.raises(SystemExit) as info:
        run("serve", "--help")
    assert info.value.code == 0


def test_legacy_script_still_runs():
    result = subprocess.run(
        [sys.executable, "readme_forge.py", "--list-sections"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.startswith("banner")
