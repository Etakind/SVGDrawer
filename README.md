# SVGDrawer

**Browse the Gallery → customize one symbol → export SVG or PNG.**
No drawing plane, scenes, or page-layout tools. Position your downloaded images in your own software.

The **Gallery** starts with 33 parametric symbols in five populated categories, plus an Uncategorized category. The browser, terminal and AI agents share the same JSON definitions and Python SVG renderers.

## Start here

Supports **Windows**, with Python **3.10 or newer**. SVG generation and source management use only the standard library; no package installation is required.

```powershell
python svgdrawer.py --list
python svgdrawer.py --describe chip
python svgdrawer.py --create chip --color-sets default --set pins=10 --output exports/chip.svg
python svgdrawer.py --serve
```

For terminal PNG exports, install the optional dependency and ensure its Cairo system runtime is available:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-png.txt
python svgdrawer.py --create chip --output exports/chip-preview.png --scale 2
```

**Python generates `chip-preview.svg` first. CairoSVG rasterizes those exact SVG bytes to `chip-preview.png`.** The SVG sidecar is retained. The browser can also rasterize the Python-generated SVG without CairoSVG.

Run `python svgdrawer.py --help` for all flags. The `svgdrawer.cmd` Windows launcher invokes the same CLI; `start_windows.bat` opens the local browser UI. Add the project directory to your own PATH only when desired; the project does not modify your environment.

## Guides

- [Simple guide for users and AI agents](docs/AGENT_GUIDE.md)
- [Full CLI contract and error codes](docs/CLI_REFERENCE.md)
- [Adding Python symbols and understanding the renderer API](docs/EXTENDING.md)
- [Agent project instructions](AGENTS.md)
- [Architecture](docs/ARCHITECTURE.md) and [test instructions](docs/TESTING.md)

## Source layout

```text
SVGDrawer/
  svgdrawer.py                 Terminal entry point
  AGENTS.md                    Instructions for AI coding agents
  Gallery/                     SHARED SOURCE OF TRUTH
    catalog.json               Categories and symbol IDs, names, categories, styles
    color_sets.json            Named color sets
    settings.json              Product version and browser Python runtime URL
    common.py                  Shared geometry helpers
    <category>/<symbol-id>/
      symbol.json              Controls, defaults and descriptive metadata
      render.py                Trusted Python drawing function
    uncategorized/             Default for symbols without a category
    .history/                  Created when source files are updated
  cli/                         Discovery, customization, validation and maintenance
  engine/                      Shared dependency-free SVG engine
  app/                         Shop-style browsing and customization interface
  examples/                    Working renderer and export examples
  docs/                        Human and agent documentation
  tests/                       Engine, CLI, maintenance, HTTP and browser tests
  build.py                     Generates index.html
  server.py                    Local browser application server
  index.html                   Generated single-file application
```

`drafts/` and `exports/` are created in the **terminal's current working directory** when used. Source changes always go to the `Gallery/` next to `svgdrawer.py`, even when invoked from another directory.

## Maintaining the Gallery

```powershell
python svgdrawer.py --add-category instruments --name "Instruments"
python svgdrawer.py --init-symbol sensor --category instruments
# Edit drafts/sensor.py and drafts/sensor.json.
python svgdrawer.py --add-symbol sensor --script drafts/sensor.py --spec drafts/sensor.json
python svgdrawer.py --validate
python svgdrawer.py --build
```

The CLI sees registered source additions on its next invocation. Rebuild `index.html` for the browser, and restart an already-running local server. Keep this source project as your master copy; **do not maintain the generated HTML by hand**.

Python renderer scripts are **trusted executable code, not sandboxed**. Review agent-generated code before registration. Validation checks geometry and rejects broken additions; it does not make arbitrary Python safe to execute.

## Standalone browser and personal collections

Open `index.html` directly to browse. Customization in the standalone file loads Pyodide from a CDN and needs internet access. For local/offline SVG generation, use `python svgdrawer.py --serve` instead. Browsing never adds a drawing plane.

Categories, variants and static SVGs saved **inside the browser UI** remain in that browser's personal Gallery. They do not edit source files and are not automatically visible to the CLI. Back up personal collections from the interface. CLI `--add-category` and `--add-symbol` are the source-management path for shared, persistent additions.

Asset recipes remain schema 1 (`svgdrawer.asset`, with legacy `vector-foundry.asset` support). Library backups now use `svgdrawer.library`, schema 2, with `symbols` instead of `elements`. Schema-1 SVGDrawer and vector-foundry libraries are converted when loaded or imported. On the same origin, the browser writes `svgdrawer.gallery.v2` and leaves earlier storage untouched; failed conversion does not overwrite saved data. Browsers may treat a renamed local HTML file as a different storage origin; use a backup for migration rather than relying on automatic discovery.

## Verification

See [docs/TESTING.md](docs/TESTING.md) for verification commands. Packaged release reports are historical and do not establish verification of current changes. The CLI needs no browser or network connection for discovery, registration, customization or SVG exports. PNG requires its optional runtime dependencies to have been installed.

To package a later release after adding Gallery content, run `python tools/package_release.py --output-dir dist`. The helper rebuilds HTML, excludes personal/development files and packages the active source without file inventories or checksums.

Source symbol IDs and trimmed, case-insensitive display names are globally unique. The catalog keeps style metadata (currently `default`) to distinguish future designs. Use `--describe ID --json` to inspect style, controls and source locations. CLI JSON envelopes now use schema 2; the old `--add-element` and `--init-element` flags are not aliases.
