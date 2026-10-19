<div align="center">

# README.forge

Generate a GitHub profile README from a username, in the terminal or in your browser.

[![CI](https://github.com/Antech-greyhat/ReadmeForge/actions/workflows/ci.yml/badge.svg)](https://github.com/Antech-greyhat/ReadmeForge/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](pyproject.toml)
[![Flask](https://img.shields.io/badge/Flask-3-000000?logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-7C6AF7)](LICENSE)
[![GitHub Stars](https://img.shields.io/github/stars/Antech-greyhat/ReadmeForge?style=social)](https://github.com/Antech-greyhat/ReadmeForge)

</div>

README.forge reads a public GitHub profile and builds a README with a header, typing
banner, badges, tech stack, featured projects, stats cards, trophies, 3D contributions,
a contribution snake and more. One Python engine powers both the command-line tool and
the web UI, so they always produce the same output.

## Features

- **24 sections** in any order, with two presets: `classic` and `showcase`.
- **8 widget themes**, mapped to each widget family's own theme names.
- **Heading icons**: emoji, Tabler icons through Iconify, or Tabler SVGs committed to
  your profile repo.
- **Self-hostable widgets**: point stats, streak, trophy, activity and summary cards at
  your own instances when the shared ones are rate-limited.
- **Workflow generator** for the sections that need a GitHub Action (snake, 3D graph).
- **Safe output**: every API and user value is escaped for its context, and links only
  allow safe URL schemes.
- **Stdlib-only CLI**: the core needs nothing beyond Python 3.10.

## Install

```bash
pipx install git+https://github.com/Antech-greyhat/ReadmeForge
```

For the web UI, include the `web` extra:

```bash
pipx install "readme-forge[web] @ git+https://github.com/Antech-greyhat/ReadmeForge"
```

## Command line

```bash
readme-forge octocat                                   # classic layout -> README.md
readme-forge octocat --preset showcase --workflows .github/workflows
readme-forge --config forge.config.json                # settings exported from the web UI
readme-forge octocat --sections hero,about,cards,snake -o -   # custom order, to stdout
readme-forge octocat --icons local --assets assets     # Tabler icons stored in your repo
readme-forge octocat --instance stats=https://stats.example.com --no-credit
readme-forge --list-sections
```

Set `GITHUB_TOKEN` to raise the GitHub API limit from 60 to 5,000 requests per hour. A
classic token with no scopes is enough. `readme-forge --help` lists every option.

`python readme_forge.py ...` from a clone still works and runs the same CLI.

### Options worth knowing

| Option | Config key | Effect |
| --- | --- | --- |
| `--theme NAME` | `options.theme` | Widget theme: `tokyonight`, `dracula`, `radical`, `onedark`, `gruvbox`, `nord`, `github_dark`, `default`. |
| `--icons STYLE` | `options.iconStyle` | `emoji` (default), `iconify` or `local`. `local` writes SVGs into `--assets DIR/icons` and links them relatively. |
| `--instance NAME=URL` | `instances.NAME` | Widget base URL for `stats`, `streak`, `trophy`, `activity` or `summary`. HTTPS only. Also settable with `READMEFORGE_INSTANCE_<NAME>`. |
| `--no-credit` | `options.credit` | Leave out the "Made with ❤️ by Antech-greyhat" footer. |
| `--heading-gif` / `--no-heading-gif` | `options.headingGif` | Animated accent next to headings. On by default for `showcase`. |
| `--workflows DIR` | | Write the GitHub Actions that the snake and 3D sections need. |

Precedence for widget instances: command line, then config file, then environment, then
the public defaults.

## Web UI

```bash
readme-forge serve                  # http://127.0.0.1:5000
readme-forge serve --host 0.0.0.0 --port 8080
```

The UI covers section toggles and ordering, presets, the About Me fields, socials, the
featured-repo picker, themes, live preview, copy and download, config import and export,
the Workflows tab and the server's remaining GitHub quota. Everything is generated and
sanitised on the server. The page never asks for a token: the server uses its own
`GITHUB_TOKEN`.

## Deployment

`wsgi.py` exposes the app for gunicorn and defaults to public mode, which tightens rate
limits. See [docs/deployment.md](docs/deployment.md) for Render, Vercel and the full list
of environment variables.

## Profile sections that need a workflow

| Section | Action | Output |
| --- | --- | --- |
| Contribution Snake | `Platane/snk` | `output` branch: `github-snake.svg`, `github-snake-dark.svg` |
| 3D Contributions | `yoshi389111/github-profile-3d-contrib` | `profile-3d-contrib/profile-night-rainbow.svg` |

Add the files from `--workflows` or the Workflows tab to `.github/workflows/` in your
`<username>/<username>` repository, then run each once from the Actions tab.

## Project structure

```
readme_forge/
  cli.py          command line and `serve`
  config.py       forge.config.json loading and validation
  github.py       GitHub API client, TTL cache, language aggregation
  sections.py     the 24 section renderers and generate()
  urls.py         widget URL builders and self-hosted instances
  escaping.py     HTML, Markdown and URL escaping
  themes.py       widget theme mapping
  languages.py    language badge metadata
  socials.py      social link badges
  icons.py        bundled Tabler icons for the local icon style
  workflows.py    GitHub Actions for snake and 3D sections
  icons/          Tabler outline SVGs (MIT)
  web/            Flask app: app factory, routes, preview sanitiser, templates, static
tests/            pytest suite, recorded API fixtures and golden READMEs
docs/             deployment guide
wsgi.py           production entry point
readme_forge.py   compatibility shim for `python readme_forge.py`
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). A new section is one Python function and a test.

## License

MIT, see [LICENSE](LICENSE). Bundled Tabler icons are MIT licensed, see
`readme_forge/icons/LICENSE`.

Built by [Antony Mwendwa](https://github.com/Antech-greyhat). If the tool saves you time,
a star helps other developers find it.
