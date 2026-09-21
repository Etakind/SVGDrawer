# Changelog

## Unreleased — Conda, Python entry points and curated symbols

- Define the runtime in environment.yml; Conda supplies Python, CairoSVG and native Cairo.
- Replace BAT/CMD launchers with start.py and remove the manual MSYS2 installer.
- Add 24 licensed Lucide/Tabler outline symbols, with upstream notices retained in SVG and PNG exports.
- Clarify five existing display names without changing IDs or geometry; document multi-factor naming and permission for agents to refine names.

## Earlier foundation — One Python application, one shared Gallery

- Use one local Python runtime, port 9178 by default, with directly served frontend assets and a shared disk Gallery for browser and CLI.
- Remove standalone HTML/Pyodide/CDN, personal browser libraries/converters and the obsolete build workflow.
- Add shared SVG import, saved variants, metadata/favorite edits, batch move/trash/restore, category management and confirmed permanent removal.
- Back up active Gallery sources directly as a ZIP; support additive conflict reporting, confirmed full sync and restorable trash snapshots.
- Keep the category-organized Symbol catalog, unique IDs/names, styles, renderer reuse, recipes and schema-2 CLI responses.
- Generate PNG only with Python/CairoSVG and project-local Windows Cairo DLL discovery. Preserve all 33 shipped symbols' geometry and part IDs.
- Refresh instructions, Windows launchers and packaging. No file inventories or checksum manifests. Older reports and release notes below are historical.

## 3.0.0 — SVGDrawer / Gallery / terminal support

Renamed the product to **SVGDrawer** and the browsable source collection to **Gallery**. The old catalog source directory is now `Gallery/`, and Python renderer modules live in `Gallery/renderers/`. The shop-style interface remains canvas-free and retains the existing 19 elements.

Added `svgdrawer.py` and optional platform launchers, with grouped/flat/category discovery, parameter and part introspection, named/custom color sets, SVG/PNG exports, recipes, scaffolding, source category/element registration, validation and browser build/serve commands. Added versioned JSON results and explicit exit codes for agents.

Renderer additions accept a Python script plus JSON or embedded literal `SPEC`. They are staged and validated before installation. Source replacement requires explicit intent, retains prior versions, increments element versions and refuses accidental replacement of shared renderer code. Gallery writer locks prevent cooperative source mutations from overlapping.

Moved metadata discovery to lazy renderer imports. Added strict terminal parameter validation, no-clobber exports, reproducible SVG-to-PNG conversion, `@file.json` inputs, optional CairoSVG dependency pin and documentation for shell quoting and trusted Python execution.

Added `AGENTS.md`, a command-line user/agent guide, full CLI contract, new examples and regression tests. Preserved reads of older asset/library formats and retained the earlier preset migration utility. Browser-only personal collections remain separate from shared source files.

## 2.0.0 — shop-style browsing

Replaced the original composition workspace with an individually customizable element collection. Added categories, search, favorites, presets, static SVG import, per-part controls, SVG/PNG export, portable personal backups and a data-driven source/build layout.

## 1.0.0 — initial geometry library

Initial parametric recreations of the reference icons and basic vector shapes. This release history is descriptive; the v3 application does not restore the original drawing plane.
