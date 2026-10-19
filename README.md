<div align="center">

![README.forge](https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=12,24&height=200&section=header&text=README.forge&fontSize=80&fontColor=ffffff&animation=fadeIn)

[![GitHub Stars](https://img.shields.io/github/stars/Antech-greyhat/ReadmeForge?style=for-the-badge&logo=github&color=7C6AF7)](https://github.com/Antech-greyhat/ReadmeGenerator)
[![License](https://img.shields.io/badge/License-MIT-7C6AF7?style=for-the-badge)](#license)
[![Vanilla JS](https://img.shields.io/badge/Vanilla-JS-7C6AF7?style=for-the-badge&logo=javascript&logoColor=white)](https://github.com/Antech-greyhat/ReadmeGenerator)
[![Python CLI](https://img.shields.io/badge/Python-CLI-7C6AF7?style=for-the-badge&logo=python&logoColor=white)](#python-cli)

</div>

<p align="center">
  <img src="https://readme-typing-svg.demolab.com?font=DM+Mono&size=24&duration=3000&pause=1000&color=7C6AF7&center=true&vCenter=true&width=600&lines=Generate+stunning+GitHub+profile+READMEs;Zero+build+step+%E2%80%94+runs+directly+from+file%3A%2F%2F;8+widget+themes+%2B+24+customizable+sections;Showcase+preset+%E2%80%94+snake%2C+3D+graph%2C+fun+zone;Web+UI+%2B+Python+CLI" alt="Typing SVG" />
</p>

---

## <img src="https://api.iconify.design/lucide/sparkles.svg?color=%237c6af7&height=24" alt="" height="24" /> Features

<div align="center">

| Feature | Description |
|---------|-------------|
| <img src="https://api.iconify.design/lucide/palette.svg?color=%237c6af7&height=16" alt="" height="16" /> **8 Widget Themes** | Tokyo Night, Dracula, Radical, One Dark, Gruvbox, Nord, GitHub Dark, Light |
| <img src="https://api.iconify.design/lucide/layout-list.svg?color=%237c6af7&height=16" alt="" height="16" /> **24 Section Types** | Banner, Header, Typing, Badges, Social Links, Tech Stack, Featured Projects, Stats, Streak, Activity, Trophies, Learning, Quote — plus the Showcase set below |
| <img src="https://api.iconify.design/lucide/wand-sparkles.svg?color=%237c6af7&height=16" alt="" height="16" /> **Showcase Preset** | One click for a rich profile: Hero GIF, About Me bullets, Profile Stats table, Stats Card Grid, 3D Contributions, Contribution Chart, Git Animals, Fun Zone (jokes + quotes), Contribution Snake, Sponsor Me, Footer Wave, animated heading accents |
| <img src="https://api.iconify.design/lucide/workflow.svg?color=%237c6af7&height=16" alt="" height="16" /> **Workflow Generator** | Sections that need a GitHub Action (snake, 3D graph) get ready-to-commit YAML in the ⚙ Workflows tab |
| <img src="https://api.iconify.design/lucide/terminal.svg?color=%237c6af7&height=16" alt="" height="16" /> **Python CLI** | `readme_forge.py` — same renderers, byte-identical output, stdlib only, reads configs exported from the web UI |
| <img src="https://api.iconify.design/lucide/zap.svg?color=%237c6af7&height=16" alt="" height="16" /> **Zero Build** | Pure vanilla JS — no npm, no bundler, runs from `file://` |
| <img src="https://api.iconify.design/lucide/key-round.svg?color=%237c6af7&height=16" alt="" height="16" /> **PAT Support** | Optional Personal Access Token for 5000/hr rate limit vs 60/hr |
| <img src="https://api.iconify.design/lucide/accessibility.svg?color=%237c6af7&height=16" alt="" height="16" /> **Accessible** | Full keyboard navigation, ARIA labels, focus management |
| <img src="https://api.iconify.design/lucide/hard-drive.svg?color=%237c6af7&height=16" alt="" height="16" /> **LocalStorage** | All preferences persisted locally, including featured repos and section order |
| <img src="https://api.iconify.design/lucide/arrow-up-down.svg?color=%237c6af7&height=16" alt="" height="16" /> **Reorderable** | ▲▼ buttons on every section row to customize output order |
| <img src="https://api.iconify.design/lucide/image.svg?color=%237c6af7&height=16" alt="" height="16" /> **Featured Projects** | Table or pin-card layout with searchable repo picker |

</div>

---

## <img src="https://api.iconify.design/lucide/rocket.svg?color=%237c6af7&height=24" alt="" height="24" /> Getting Started

### Quick Start

1. **Clone or download** this repository
2. **Open `tool.html`** directly in your browser (Chrome, Firefox, Edge, Safari)
3. **Paste a GitHub username** and hit →
4. **Customize** sections, colors, and content in the left panel
5. **Copy or export** your generated README

That's it. No installation, no dependencies, no server.

### Using a Personal Access Token

For heavy use (multiple profiles, 100+ repos), add a [GitHub Personal Access Token](https://github.com/settings/tokens):

1. Generate a **classic token** with **no scopes checked** (public data only)
2. Open the **Advanced** panel at the bottom of the left sidebar
3. Paste the token and save
4. Rate limit jumps from 60/hr → 5000/hr

The token is stored in your browser's `localStorage` — it never leaves your machine.

### Showcase Preset

Open the **Showcase** panel, pick **Showcase** and hit **Apply**. Fill in *Currently Working On*, *Ask Me About*, *Fun Fact* and friends to populate the About Me bullets; blank fields are skipped.

Two sections render images that a GitHub Action commits to your `<username>/<username>` profile repo:

| Section | Workflow | Output |
|---------|----------|--------|
| Contribution Snake | `Platane/snk` | `output` branch → `github-snake.svg` / `github-snake-dark.svg` |
| 3D Contributions | `yoshi389111/github-profile-3d-contrib` | `profile-3d-contrib/profile-night-rainbow.svg` |

Copy the YAML from the **⚙ Workflows** tab into `.github/workflows/`, then run each workflow once from the Actions tab.

### Python CLI

```bash
python readme_forge.py octocat                          # classic layout -> README.md
python readme_forge.py octocat --preset showcase        --workflows .github/workflows                    # rich layout + workflow files
python readme_forge.py --config forge.config.json       # settings exported from the web UI
python readme_forge.py octocat --sections hero,about,cards,snake -o -   # custom order, stdout
python readme_forge.py --list-sections
```

Python 3.8+, no dependencies. Set `GITHUB_TOKEN` (or `--token`) for the 5000/hr limit. In the web UI, **Advanced → Export config (.json)** saves your sections, socials, featured repos and text so the CLI can regenerate the same README — handy in a scheduled GitHub Action.

---

## <img src="https://api.iconify.design/lucide/wrench.svg?color=%237c6af7&height=24" alt="" height="24" /> Technical Stack

<div align="center">

![HTML5](https://img.shields.io/badge/HTML5-E34F26?style=for-the-badge&logo=html5&logoColor=white)
![CSS3](https://img.shields.io/badge/CSS3-1572B6?style=for-the-badge&logo=css3&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black)
![GitHub API](https://img.shields.io/badge/GitHub_API-181717?style=for-the-badge&logo=github&logoColor=white)
![marked.js](https://img.shields.io/badge/marked.js-000000?style=for-the-badge&logo=markdown&logoColor=white)

</div>

**Architecture:**
- **Zero dependencies** (except `marked.js` from CDN for preview)
- **~1550 lines** of vanilla JavaScript, mirrored by a stdlib-only Python port
- **24 pure renderer functions** — each section is independently testable
- **XSS-safe** — all user/API data escaped at ingress
- **Offline-ready** — cached API responses, works without CDN
- **Self-test suites** — `?selftest=1` runs 42 assertions in-page; `python readme_forge.py --selftest` runs 34

---

## <img src="https://api.iconify.design/lucide/workflow.svg?color=%237c6af7&height=24" alt="" height="24" /> How It Works

1. **Fetch** — hits GitHub's REST API for user profile + up to 100 repos
2. **Aggregate** — sums stars/forks, requests `/languages` for top 20–40 repos (budget-aware)
3. **Render** — 24 pure functions take context and return markdown lines
4. **Preview** — `marked.js` parses markdown to HTML, with XSS scrubbing on the preview copy
5. **Export** — one-click copy to clipboard or download `.md`

All widget URLs are pre-escaped. The output is GitHub-flavored markdown with `<h1 align="center">` and shield.io badges.

---

## <img src="https://api.iconify.design/lucide/flask-conical.svg?color=%237c6af7&height=24" alt="" height="24" /> Self-Test

Open `tool.html?selftest=1` in your browser's console. It runs 42 assertions covering:

- HTML/markdown/URL escaping
- Theme mapping (activity graph vs trophy vs stats)
- Shields.io query-form badge builder (hyphens preserved)
- Typing-SVG literal-semicolon separator
- Language normalization (C++, C#, F#, Jupyter Notebook)
- Renderer/section parity
- Preview scrubber (strips `<script>` and `onerror=`)
- Showcase URL builders, presets and workflow coverage

All assertions log to `console.table` with PASS/FAIL. The Python port has its own suite: `python readme_forge.py --selftest`.

---

## <img src="https://api.iconify.design/lucide/folder-tree.svg?color=%237c6af7&height=24" alt="" height="24" /> Project Structure

```
ReadmeGenerator/
├── tool.html       # UI markup (256 lines)
├── tool.css        # Styles (~470 lines)
├── tool.js         # Core logic (~1550 lines)
├── readme_forge.py # Python CLI port (stdlib only)
├── image/
│   ├── favicon.png
│   └── favicon.svg
└── README.md       # This file
```

Open `tool.html` to use the web UI, or run `readme_forge.py` from a terminal.

---

## <img src="https://api.iconify.design/lucide/handshake.svg?color=%237c6af7&height=24" alt="" height="24" /> Contributing

Found a bug? Want a new section type? PRs welcome.

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/amazing-section`)
3. Commit your changes (`git commit -m 'Add AmazingSection renderer'`)
4. Push (`git push origin feature/amazing-section`)
5. Open a Pull Request

**Guidelines:**
- Keep it vanilla — no npm, no bundler
- Add a self-test assertion for new escapers or URL builders
- New sections go in both `tool.js` and `readme_forge.py` so their output stays identical
- Match the existing code style (plain functions, `// section headers`)

---

## <img src="https://api.iconify.design/lucide/scroll-text.svg?color=%237c6af7&height=24" alt="" height="24" /> License

MIT License — use it, fork it, sell it. Attribution appreciated but not required.

---

## <img src="https://api.iconify.design/lucide/heart-handshake.svg?color=%237c6af7&height=24" alt="" height="24" /> Support the Developer

<div align="center">

### Built by [Antony Mwendwa](https://github.com/Antech-greyhat)

If this tool saved you time,
<img src="https://api.iconify.design/lucide/star.svg?color=%237c6af7&height=16" alt="" height="16" /> **star the repo** and **follow me** for more open-source tools.

[![GitHub followers](https://img.shields.io/github/followers/Antech-greyhat?label=Follow&style=for-the-badge&logo=github&color=7C6AF7)](https://github.com/Antech-greyhat)
[![Star this repo](https://img.shields.io/github/stars/Antech-greyhat/ReadmeGenerator?label=Star&style=for-the-badge&logo=github&color=7C6AF7)](https://github.com/Antech-greyhat/ReadmeGenerator)

</div>

<div align="center">

[![GitHub](https://img.shields.io/badge/GitHub-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/Antech-greyhat)

Every star helps more developers find the tool.

</div>

---

<div align="center">

![Footer Wave](https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=12,24&height=120&section=footer)

**Made with <img src="https://api.iconify.design/lucide/heart.svg?color=%23e11d48&height=14" alt="" height="14" /> by Antony Mwendwa**

<sub>Built in 2026 • README.forge v2.0</sub>

</div>
