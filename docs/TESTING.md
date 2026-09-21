# Testing SVGDrawer

## Core and CLI regression suite

```powershell
python -m unittest discover -s tests -v
python svgdrawer.py --validate --json
```

The unittest suite includes engine geometry and import checks, CLI discovery/customization/export/error contracts, temporary-project source registrations, failed-renderer rollback, metadata-only lazy imports, force/version/history behavior, writer-lock conflicts, legacy recipes, HTTP endpoint tests and extension discovery. Temporary-project tests do not modify the shipped Gallery.

`--validate` exercises defaults, individual control extremes, combined numeric extremes and repeated default renders. It checks parseable/static SVG, editable part IDs and determinism. It is not a formal geometric-bounds proof or a complete SVG standards validator; inspect rendered examples visually too.

Unit tests use Python's standard `unittest`. PNG-specific tests skip when optional CairoSVG is not available. Install `requirements-png.txt` to exercise terminal/server PNG output. The verification report identifies the dependencies actually installed for this release.

## Browser checks

With optional development dependencies and a Chromium installation:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python -m playwright install chromium
python server.py --no-browser
# In a second terminal:
python tests/browser_integration.py --url http://127.0.0.1:8765
```

The browser tests cover Gallery browsing, categories, favorites, sorting, geometry/color/part changes, undo/redo, draft retention, SVG and browser PNG exports, recipes and exported Python scripts, personal collections, static SVG sanitization, backup merging and mobile layouts.

When browser access to loopback is blocked by the environment, run the explicit bridge:

```powershell
python tests/browser_integration.py --bridge
python tests/browser_storage.py
node tests/runtime_fallback.js
```

Bridge mode binds the browser to the real CPython renderer and substitutes in-memory storage. It exercises UI behavior and real SVG generation, but **does not verify direct HTTP browser navigation, native localStorage persistence, or successful CDN/Pyodide startup**. Storage safety tests also use the adapter. Runtime-fallback tests simulate worker failures; they do not download a Python runtime.

## Executed verification and limitations

The existing `VERIFICATION.json` and `verification-output.txt` describe an earlier release, not the reorganized source. The following limitations are historical: Browser navigation to the local server was attempted and blocked by the environment with `ERR_BLOCKED_BY_ADMINISTRATOR`. HTTP endpoints were separately tested using Python HTTP clients, and browser workflows were tested through the explicit bridge. Successful standalone CDN startup was not verified.

That historical report had no native Windows verification. Current support is Windows with Python 3.10+; rerun the checks on Windows rather than inheriting old results. CLI/server PNG additionally requires CairoSVG and the Cairo runtime. Rendered text can differ with available fonts.

## Releasing updated Gallery contents

After adding definitions and passing checks:

```powershell
python svgdrawer.py --validate
python svgdrawer.py --build
python tools/package_release.py --output-dir dist
```

The packaging helper writes `dist/SVGDrawer.html` and `dist/SVGDrawer.zip`, using a `SVGDrawer/` root directory inside the archive. It includes the nested symbol folders and catalog without generating file inventories or checksums. It excludes locks, source history, drafts, exports, virtual environments and browser test output. Keep personal Gallery/history backups separately; they are deliberately not copied into a distributable release.

## Reorganization acceptance

Compare all 33 pre-move SVG outputs and part IDs directly (no hashes). Cover catalog uniqueness, style search, uncategorized defaults, lazy imports, missing files, registration/replacement/rollback and renderer reuse. Exercise library schema-1 conversion, schema-2 round trips, preserved original storage on conversion failures, CLI schema-2 output and rejection of legacy flags. Check generated HTML, self-contained Python downloads, local HTTP and PNG/browser export when dependencies are available.

## Current Windows verification — 2026-09-21

For the Symbol reorganization, the isolated tester reported:

- `python -m unittest discover -s tests -v`: 74 tests, successful, with 2 CairoSVG-dependent PNG tests skipped.
- Direct comparison with the original source renderers: all 33 default SVG outputs and part IDs unchanged; no hashes used.
- `python svgdrawer.py --validate --json`: 33 symbols, 294 geometry cases passed.
- `python svgdrawer.py --build --json`: generated HTML with 33 symbols and 6 categories, including nested configuration/renderers and shared helpers.
- Browser storage conversion, bridge integration and local HTTP browser integration passed.
- Packaging contained the nested Gallery sources without old flat directories or a checksum manifest.

CairoSVG-dependent PNG verification remains unavailable in this environment; no dependencies were installed. Local/bridge browser success is not evidence of standalone CDN/Pyodide startup.
