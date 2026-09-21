# SVGDrawer

A customizable SVG **Gallery** for people and AI agents. Browse a symbol,
customize its parameters or individual parts, and export SVG or PNG. Not a diagram editor.

## Windows quick start

```text
conda env create --prefix ./.conda --file environment.yml
conda activate ./.conda
python start.py
```

`environment.yml` is the runtime dependency definition. Conda installs Python 3.12,
CairoSVG and native Cairo from conda-forge into `.conda/`, without changing the base
environment or global PATH. Update with `conda env update --prefix ./.conda --file environment.yml`.
No manual MSYS2 installation or platform-specific launcher is needed.

Open **http://127.0.0.1:9178/**. Pass `--port 9180` or `--no-browser` to `python start.py`
when needed. The CLI remains `python svgdrawer.py`; use both in the activated environment.
Windows is the supported application platform; all project entry points and tooling
are Python, not BAT/CMD/shell scripts. The UI has no CDN requirement or build step.

## One shared Gallery

The browser and CLI use the same `Gallery/` on disk. Search, add Python symbols,
import static SVGs, save customized variants, edit metadata, move, favorite and
trash symbols. Manage categories, batch restore or permanently remove trash, and
export/import Gallery ZIPs. CLI edits appear in the browser automatically.

```powershell
python svgdrawer.py --list-all-flat --json
python svgdrawer.py --describe chip --json
python svgdrawer.py --create chip --set pins=8 --output exports/chip.png --json
python svgdrawer.py --backup-gallery --output Gallery.zip --json
```

The shipped catalog contains **57 symbols** in six categories, including Uncategorized:
33 original parametric designs and 24 licensed outline SVGs from the Lucide and Tabler
collections listed on [FreeIcons](https://www.freeicons.org/). See [artwork sources and
licenses](docs/THIRD_PARTY.md). Related symbols have descriptive names based on their
geometry and function; style is not their sole identity.
Python-backed symbols with configurable parameters show **customizable**; imported
static SVGs have part editing and output settings but no parameterized geometry.

Backup ZIPs are rooted at `Gallery/` and contain active content only. Additive
imports preserve local helpers, palettes and settings and report conflicts. Full
sync requires explicit confirmation and saves the displaced Gallery as a trash
snapshot. Python sources in imports execute locally: import only code you trust.

## Development

- [Development rules](AGENTS.md)
- [Usage and agent guide](docs/AGENT_GUIDE.md)
- [CLI reference](docs/CLI_REFERENCE.md) / [generated help](docs/CLI_HELP.txt)
- [Architecture and HTTP contract](docs/ARCHITECTURE.md)
- [Adding symbols](docs/EXTENDING.md)
- [Verification](docs/TESTING.md)

Package the local Python application with `python tools/package_release.py`.
The source ZIP includes nested Gallery sources and frontend assets, not `.conda/`,
trash, history, generated previews, standalone HTML or checksum manifests.
