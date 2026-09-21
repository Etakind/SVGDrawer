# SVGDrawer — development instructions

## Product and architecture
SVGDrawer helps people and AI agents discover, customize and export reusable
**Symbols** as SVG or PNG. Support Windows, with one local Python application:
the CLI and browser UI read and modify the same disk-backed `Gallery/`.

- `Gallery/`: category catalog, symbol configuration and geometry, settings and palettes.
- `engine/`: lazy metadata loading, SVG drawing/customization, sanitization and Python PNG.
- `cli/`: command contracts and shared management, staged writes, trash and ZIP operations.
- `server.py`: loopback HTTP adapter; default port 9178, overridable with `--port`.
- `app/`: directly served HTML/CSS/JavaScript frontend, never drawing geometry.
- `tools/`: Python packaging and project-local Cairo provisioning.

Use Python for rendering, backend logic and tooling. Use Python entry points only; do not add BAT, CMD, PowerShell or shell launchers.
No standalone HTML runtime, browser-owned symbol library, CDN dependencies or build step.
Never write browser storage as part of Gallery management. Refresh from disk after changes;
running servers must see CLI edits without restarting.

## Gallery contract
`Gallery/catalog.json` is the authoritative category/symbol index, not a file
manifest. Symbol records contain only `id`, `name`, `category`, `style`; category
records retain presentation metadata. Keep IDs stable and globally unique, and
names unique after trimming and case-insensitive comparison. Missing category
means `uncategorized`; unknown categories are errors. Uncategorized is permanent.

Each symbol lives at `Gallery/<category>/<id>/symbol.json`, alongside `render.py`
for owned Python geometry or sanitized `source.svg` for static vectors. Configuration
holds descriptions, tags, controls, defaults, version and type-specific data, not
catalog identity. Optional `renderer` names the owning symbol ID. Shared helpers
live in `Gallery/common.py`. Variants retain parameters, part overrides and output
defaults. Names must distinguish subject/function, geometry, perspective, fixed features
and configurable capabilities, not just style. Agents may refine existing display names
when adding related symbols; keep stable IDs, recipes and renderer references unchanged.
Do not turn a default adjustable pin count into a fixed-count family name. Style is
appearance metadata, not an identity key. Inspect related symbols before adding another;
use meaningful names and search tags, and retain useful previous names as tags.
Discovery never imports renderers.
Renderers export `render(drawing, params)` in a 256 × 256 design space. Preserve
artwork, parameter names, deterministic output and stable part IDs.

Publish changes through existing locking, staging and rollback functions. Do not
remove another writer's lock. Trash retains semantic records and sources grouped
by original category. Validate whole batches and preserve renderer dependencies.
Permanent removal and full sync require confirmation. Gallery ZIPs contain active
Gallery sources only; exclude trash, history, caches and locks. Full sync preserves
the prior active Gallery as a trash snapshot, along with all existing trash.

## Working rules
Keep changes small and readable. Reuse existing code; avoid speculative features,
extra dependencies, abstractions or safety frameworks. No file inventories,
checksums, generated governance files, remote-server setup or memory MCP.
Preserve useful input validation, overwrite protection and local HTTP boundaries.
Python sources are trusted executable code, not sandboxed plugins. For third-party
icons, verify the upstream license and keep source attribution and license notices
with the symbol and exported artwork; see docs/THIRD_PARTY.md.

Use the repository-local Conda environment (`.conda/`) defined by `environment.yml`.
Conda supplies Python, CairoSVG and native Cairo. On Windows, discover DLLs from the
active interpreter's `Library/bin` for this process only. No manual DLL downloaders,
pip-managed runtime environment, global PATH changes, or global environment edits.
Do not install dependencies, commit or push without explicit authorization.

## Verification and guides
Use exactly one isolated `tester_worker` (`fork_turns=none`) for executable tests.
Only that tester may inspect, edit or run `tests/**` and test commands. Implementers
own product files. No other subagents unless explicitly requested. Compare SVGs and
part IDs directly, never with hashes. Activate with `conda activate ./.conda`. The tester runs:

```powershell
python -m unittest discover -s tests -v
python svgdrawer.py --validate --json
```

Verify CLI/HTTP parity, live cache refresh, offline startup, actual Python PNG,
trash dependencies, ZIP conflicts/sync and failed-write rollback. Report skipped
or blocked checks explicitly. Historical reports do not verify current changes.

Usage: [Agent guide](docs/AGENT_GUIDE.md), [CLI reference](docs/CLI_REFERENCE.md).
Design: [Architecture](docs/ARCHITECTURE.md), [Extending](docs/EXTENDING.md).
