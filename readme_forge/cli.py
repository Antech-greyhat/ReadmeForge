"""Command-line entry point: `readme-forge USERNAME` and `readme-forge serve`."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path

from . import __version__
from .config import ICON_STYLES, Config, ConfigError, parse_config, read_config_file
from .github import GitHubClient, GitHubError, Profile, extract_username, fetch_profile
from .icons import write_icons
from .sections import (
    LOCAL_ICON_BASE,
    PRESETS,
    SECTION_IDS,
    SECTIONS,
    build_context,
    generate,
    heading_icons,
)
from .themes import THEMES, widget_theme
from .urls import INSTANCE_ENV_PREFIX, INSTANCE_NAMES, instances_from_env, with_instances
from .workflows import required_workflows, write_workflows


def _instance_arg(value: str) -> tuple[str, str]:
    name, sep, url = value.partition("=")
    if not sep or not name or not url:
        raise argparse.ArgumentTypeError("expected NAME=URL")
    return name.strip(), url.strip()


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="readme-forge",
        description="Generate a GitHub profile README. Run `readme-forge serve` for the web UI.",
        epilog=(
            f"Widget instances ({', '.join(INSTANCE_NAMES)}) can also be set with "
            f"{INSTANCE_ENV_PREFIX}<NAME> environment variables. "
            "Set GITHUB_TOKEN to raise the API limit from 60 to 5,000 requests per hour."
        ),
    )
    p.add_argument("username", nargs="?", help="GitHub username or profile URL")
    p.add_argument("-o", "--output", default="README.md", help="output file, - for stdout")
    p.add_argument("-c", "--config", help="forge.config.json exported from the web UI")
    p.add_argument("--preset", choices=sorted(PRESETS), help="section layout preset")
    p.add_argument("--sections", help="comma-separated section ids in order")
    p.add_argument("--theme", choices=sorted(THEMES), help="widget theme")
    p.add_argument(
        "--heading-gif",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="animated accent next to headings (default on for the showcase preset)",
    )
    p.add_argument("--icons", choices=ICON_STYLES, help="heading icon style (default emoji)")
    p.add_argument("--assets", metavar="DIR", help="write local heading icons into DIR/icons")
    p.add_argument(
        "--instance",
        action="append",
        type=_instance_arg,
        default=[],
        metavar="NAME=URL",
        help="self-hosted widget base URL, repeatable",
    )
    p.add_argument("--no-credit", action="store_true", help="omit the README.forge credit footer")
    p.add_argument("--workflows", metavar="DIR", help="write required GitHub Actions into DIR")
    p.add_argument("--token", help="GitHub token (default: $GITHUB_TOKEN)")
    p.add_argument("--list-sections", action="store_true", help="print section ids and exit")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return p


def build_serve_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="readme-forge serve", description="Run the web UI.")
    p.add_argument("--host", default="127.0.0.1", help="interface to bind (default 127.0.0.1)")
    p.add_argument("--port", type=int, default=5000, help="port (default 5000)")
    return p


def resolve_config(args: argparse.Namespace) -> Config:
    raw = read_config_file(args.config) if args.config else {}
    try:
        env_instances = instances_from_env(os.environ)
    except ValueError as exc:
        raise ConfigError([f"environment: {exc}"]) from None
    config = parse_config(raw, instances=env_instances)
    try:
        instances = with_instances(config.instances, dict(args.instance))
    except ValueError as exc:
        raise ConfigError([str(exc)]) from None

    username = extract_username(args.username) if args.username else config.username
    if not username:
        raise ConfigError(["a valid GitHub username or profile URL is required"])

    if args.sections:
        sections = tuple(s.strip() for s in args.sections.split(",") if s.strip())
        unknown = [s for s in sections if s not in SECTION_IDS]
        if unknown:
            raise ConfigError(
                [f"unknown section(s): {', '.join(unknown)}; known: {', '.join(SECTION_IDS)}"]
            )
    elif args.preset:
        sections = PRESETS[args.preset]
    else:
        sections = config.section_ids

    options = config.options
    if args.theme:
        options = replace(options, theme=args.theme)
    if args.icons:
        options = replace(options, icon_style=args.icons)
    if args.no_credit:
        options = replace(options, credit=False)
    raw_options = raw.get("options") if isinstance(raw, dict) else None
    if args.heading_gif is not None:
        options = replace(options, heading_gif=args.heading_gif)
    elif args.preset == "showcase" and "headingGif" not in (raw_options or {}):
        options = replace(options, heading_gif=True)
    return replace(
        config, username=username, sections=sections, options=options, instances=instances
    )


def _icon_base(output: str, assets: str | None) -> str:
    """Path from the README to the icons, so the links resolve wherever the files land."""
    if not assets:
        return LOCAL_ICON_BASE
    readme_dir = Path.cwd() if output == "-" else Path(output).resolve().parent
    rel = os.path.relpath(Path(assets).resolve() / "icons", readme_dir)
    return "./" + Path(rel).as_posix()


def _write(path: str | Path, text: str) -> None:
    Path(path).write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {path}", file=sys.stderr)


def run(args: argparse.Namespace) -> int:
    config = resolve_config(args)
    token = args.token if args.token is not None else os.environ.get("GITHUB_TOKEN", "")
    client = GitHubClient(token)
    profile: Profile = fetch_profile(client, config.username)
    if not profile.repos_complete:
        print(
            "warning: repositories could not be loaded, stats will be incomplete", file=sys.stderr
        )

    ctx = build_context(profile, config, icon_base=_icon_base(args.output, args.assets))
    markdown = generate(ctx, config.section_ids)
    if args.output == "-":
        sys.stdout.write(markdown)
    else:
        _write(args.output, markdown)

    workflows = required_workflows(config.section_ids)
    if workflows and args.workflows:
        for path in write_workflows(args.workflows, workflows):
            print(f"wrote {path}", file=sys.stderr)
    elif workflows:
        files = ", ".join(w.file for w in workflows)
        print(
            f"note: {files} must run in your profile repo; "
            "rerun with --workflows .github/workflows",
            file=sys.stderr,
        )

    if config.options.icon_style == "local":
        if args.assets:
            accent = widget_theme(config.options.theme, "accent")
            for path in write_icons(args.assets, heading_icons(config.section_ids), accent):
                print(f"wrote {path}", file=sys.stderr)
        else:
            print(
                "note: local icons need their SVG files; rerun with --assets assets",
                file=sys.stderr,
            )
    return 0


def serve(argv: Sequence[str]) -> int:
    args = build_serve_parser().parse_args(argv)
    try:
        from .web.app import create_app
    except ImportError:
        print(
            'error: the web UI needs extra packages: pip install "readme-forge[web]"',
            file=sys.stderr,
        )
        return 1
    create_app().run(host=args.host, port=args.port)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ["serve"]:
        return serve(argv[1:])

    parser = build_parser()
    args = parser.parse_args(argv)
    if args.list_sections:
        for spec in SECTIONS:
            flags = "default-on" if spec.default_on else ""
            needs = "  (needs workflow)" if spec.workflow else ""
            print(f"{spec.id:<13} {flags}{needs}")
        return 0
    try:
        return run(args)
    except ConfigError as exc:
        for error in exc.errors:
            print(f"error: {error}", file=sys.stderr)
        return 2
    except GitHubError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
