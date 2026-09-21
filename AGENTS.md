# SVGDrawer — development instructions

## Product and platform

SVGDrawer helps people and AI agents discover, customize and export one reusable
**Symbol** as SVG or PNG. It is a Gallery, not a diagram editor or composition tool.
Support Windows with Python 3.10+: standalone HTML and a locally served browser UI
are for people; the noninteractive CLI with JSON output is primarily for agents.
The same Python drawing engine runs in CPython and browser Pyodide.

## Architecture

- `Gallery/`: source categories, symbol metadata, controls and Python geometry.
- `engine/`: shared SVG primitives, loading, customization and serialization.
- `cli/`: discovery, exports and existing source-management operations.
- `app/`: HTML/CSS/JavaScript browser interface; never duplicate symbol geometry here.
- `build.py` generates `index.html`; do not hand-edit the generated HTML.
- `server.py` serves the local browser UI. Rebuild and restart after source changes.

Use Python for rendering, backend logic and tooling. Keep Windows launchers thin.
Do not add OS checks that prevent the shared engine from running in Pyodide.

## Gallery contract

`Gallery/catalog.json` is the authoritative category and symbol catalog, not a
file inventory. Each symbol record has `id`, `name`, `category` and `style`.
Category records carry their existing presentation metadata.

Store a symbol's configuration and drawing together:
`Gallery/<category>/<symbol-id>/symbol.json` and `render.py`.
Configuration contains controls, defaults and descriptive metadata, not duplicate
catalog identity fields. An optional `renderer` refers to the owning symbol ID;
otherwise the symbol owns its renderer. Shared helpers live in `Gallery/common.py`.

- Keep source-symbol IDs globally unique and stable. Display names must also be
  unique after trimming and case-insensitive comparison.
- Use `uncategorized` when no category is given; reject explicitly unknown categories.
- Use descriptive style metadata to distinguish related designs. Existing symbols
  use `default`; new variants need distinct IDs and display names.
- Update the catalog with source changes. Do not maintain file manifests or hashes.
- Renderers export `render(drawing, params)`, use a 256 × 256 design space, and keep
  output deterministic and part IDs stable. Use declared parameters for adjustable
  geometry. Keep renderers compatible with CPython and Pyodide.
- Discovery must not execute renderer code. Do not add per-symbol engine/UI switches.
- Browser personal collections are separate from the shared source Gallery.

## Working rules

Keep changes small, readable and directly related to the request. Reuse existing
patterns before introducing abstractions or dependencies. Preserve artwork,
parameters and existing operations unless the task explicitly changes them.
Ask only about consequential ambiguity. Do not add speculative features or new
management operations. No file inventories, checksum verification, redundant
safety layers or generated governance/configuration systems.

Work locally in this repository; necessary read-only inspection elsewhere is fine.
Do not set up remote servers or memory MCP. Do not install dependencies, modify
installed skills/global settings, commit or push without explicit authorization.
Use an isolated project environment when dependencies or a server are needed.
Retain existing input validation, overwrite protection and local-server boundaries.
Renderers are trusted Python, not sandboxed code. Respect an active Gallery writer
lock; never delete another process's lock or edit source while it is active.

## Verification

For executable changes, use exactly one isolated `tester_worker` with
`fork_turns=none`; only that tester inspects, edits or runs `tests/**` and test
commands. The implementing agent owns product files. No other subagents unless
explicitly requested. Compare rendered outputs directly when moving drawing code;
do not add hash verification.

Relevant checks for the tester:

```powershell
python -m unittest discover -s tests -v
python svgdrawer.py --validate --json
python svgdrawer.py --build --json
```

Report actual results and distinguish skipped/blocked PNG, browser or CDN checks
from verified behavior. Historical reports are not evidence for a new change.

## References

Read only the documentation relevant to the change:
- [Usage guide](docs/AGENT_GUIDE.md): discovery, customization and export workflows.
- [CLI reference](docs/CLI_REFERENCE.md): flags, JSON contracts and exit codes.
- [Renderer API](docs/EXTENDING.md): drawing primitives and source extensions.
- [Architecture](docs/ARCHITECTURE.md) and [testing](docs/TESTING.md).

AGENTS.md contains development rules; keep usage tutorials in those guides.
