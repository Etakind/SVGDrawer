# Changelog

## Unreleased — Symbol organization

- Use Symbol terminology and co-locate each symbol's configuration and Python renderer under its Gallery category.
- Add a compact authoritative category/symbol catalog with unique names, style metadata and an Uncategorized default.
- Rename source commands to `--add-symbol` and `--init-symbol`; CLI schema 2 uses `symbol`, `symbols` and `symbol_count` without old flag aliases.
- Write library schema 2 and convert supported schema-1 collections on load/import, preserving old browser storage. Asset recipes remain unchanged.
- Focus development instructions and launchers on Windows; retain Python rendering across CLI, local browser UI and standalone HTML.
- Remove file/checksum manifests and packaging checksum generation. Earlier verification reports remain historical.

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
