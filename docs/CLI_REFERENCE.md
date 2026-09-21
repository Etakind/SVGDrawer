# SVGDrawer CLI contract — v3.0.0

Entry point: `python svgdrawer.py`. The equivalent Windows launcher is `svgdrawer.cmd`. Windows and Python 3.10+ are supported. Commands are noninteractive and operate on the source `Gallery/` next to the entry point. Paths supplied by the caller, `drafts/` and `exports/` are relative to the current working directory unless absolute.

Use exactly **one action** per invocation. Option names are not abbreviated. Unrelated options are errors, not silently ignored. `--help` prints help; no arguments also print help and exit successfully.

## Actions

| Action | Result |
|---|---|
| `--list` | Gallery grouped by category; JSON `data.categories[].symbols`. |
| `--list-all-flat` | Flat symbols; JSON `data.symbols`, sorted by ID. |
| `--list-category` | Categories and counts; JSON `data.categories`. |
| `--list-category ID` | Symbols in one category; JSON `data.symbols`. |
| `--list-color-sets` | Named sets and color-role order. `default` is per-symbol. |
| `--describe ID` | Full symbol spec, common controls and source paths; no renderer import. |
| `--list-parts ID` | Rendered inner-part IDs, labels, types and SVG attributes. |
| `--create ID` | Customize and export a Gallery symbol. |
| `--recipe FILE` | Load an asset recipe, apply overrides, and export. |
| `--add-category ID` | Add/update source category metadata. |
| `--init-symbol ID` | Write Python and JSON templates to a drafts directory. |
| `--add-symbol ID` | Stage, validate and install trusted Python/spec source. |
| `--validate [ID]` | Check all symbols or one; geometry cases and deterministic default output. |
| `--build` | Regenerate `index.html` or `--output FILE.html`. |
| `--serve` | Build and start local browser UI; `--port`, `--no-browser`. |
| `--version` | Product name and version. |

Discovery uses exact, case-sensitive IDs. `--search TEXT` is supported on list operations; it searches IDs, names, styles, descriptions and tags, except category-summary search, which searches IDs and names. Human labels may be renamed without changing IDs.

## Customization

For `--create` and `--recipe`:

| Option | Meaning |
|---|---|
| `--color-sets default` | Restore original symbol colors, including when loading a recipe. |
| `--color-sets NAME` | Apply a named set, case-insensitive; discover with `--list-color-sets`. |
| `--color-sets '["012345","427abc"]'` | One to four hex strings mapped to fill/accent/stroke/highlight. |
| `--params JSON_OR_@FILE` | Parameter overrides as a JSON object. |
| `--set KEY=VALUE` | Repeatable overrides; last value wins. Text/select controls stay strings. |
| `--parts JSON_OR_@FILE` | Replace the complete part-override object. |
| `--size N` | Set both output dimensions; explicit width/height override size. |
| `--width N`, `--height N` | Integer pixels, each 16–4096. Default 512. |
| `--padding N` | Design-space units, 0–96. Default 8. |
| `--background HEX` | Opaque background; mutually exclusive with `--transparent`. |
| `--transparent` | No background. Default for new symbols. |
| `--stretch` | Disable aspect-ratio preservation for non-square exports. |
| `--output FILE` | Default `exports/ID.svg`, or `.png` when `--format png`. |
| `--format svg\|png\|both` | Otherwise inferred from extension. PNG always retains SVG. |
| `--scale 1\|2\|4` | PNG scale only. SVG-only output rejects a nondefault scale. |
| `--save-recipe FILE` | Save resolved parameters, parts, source type and output settings. |
| `--force` | Allow overwriting output files, without output backups. |
| `--dry-run` | Validate and report paths/settings without writing exports. |

`--list-parts` also accepts `--color-sets`, `--params` and repeated `--set`. Use the same geometry settings as your export so part IDs match the actual count and shape.

Colors may have 3 or 6 hexadecimal digits, optionally preceded by one `#`. They are normalized to uppercase `#RRGGBB`. Individual color parameters and part fill/stroke accept `none`. Custom color-set arrays require actual hex strings, not `none`. Missing array roles keep current values. Default color sets are not dynamically generated gradients.

`--params` and `--parts` require objects; a color array is an array. Use `@file.json` to bypass shell quoting. Duplicate JSON keys and non-finite JSON numbers are rejected. Common and symbol parameters are validated strictly against their schemas, including numeric step alignment. Invalid data does not silently clamp to a nearby value.

Part overrides accept `fill`, `stroke`, `stroke_width` (0–30), `sx`/`sy` (0.05–4), `dx`/`dy` (−256–256), `cx`/`cy` (−4096–4096), and `hidden` (boolean). Scale multipliers are not percentages. Named geometry controls should be used for exact dimensions whenever available. An unknown part ID is an error.

## Exports and recipes

`--output FILE` accepts `.svg`, `.png` or an extensionless base. An explicit format must match the extension except `both`, which accepts either. Output directories are created as needed. All intended output paths are checked before writing. Existing files and symbolic-link targets are refused unless an ordinary existing file is explicitly replaced with `--force`; symbolic-link files are always refused.

The order is **Python geometry → saved SVG → PNG rasterization from the same SVG bytes**. A PNG export writes `FILE.svg` and `FILE.png`; `both` produces the same pair. A requested recipe is also saved. When PNG conversion fails, the SVG remains; the error includes `details.svg_saved` for dependency/conversion errors. A multi-file export is not one all-or-nothing transaction.

PNG is limited to 8192 pixels per side and 50 million pixels total after scaling. CairoSVG and Cairo are optional for SVG but required for terminal PNG. Dry-run checks renderability, inputs, dimensions and path conflicts; it does not prove optional PNG dependencies are installed, write permissions exist, or a later filesystem write will succeed.

`--output -` prints **raw SVG only** to stdout. It cannot be combined with `--json`, `--dry-run`, PNG or `--save-recipe`. No status text contaminates raw SVG. Registered renderer prints are captured rather than mixed into command output.

Recipes use `format: "svgdrawer.asset"`, `schema_version: 1`, a `name`, an `asset` (`type`, `params`, `parts`) and `output` settings. Imported static-SVG recipes additionally include sanitized `raw_svg`. Legacy `vector-foundry.asset` recipes are accepted. Recipes reference symbol IDs; they do not embed Python plugins. Keep the relevant Gallery source. PNG scale is not stored in the recipe.

## Source management

`--add-category ID` accepts `--name`, `--description`, `--icon` and `--order`. An omitted name is derived from the ID. `--force` updates an existing category's metadata without changing its ID. Reusing another category's display name is refused.

`--init-symbol ID --category CATEGORY` writes `drafts/ID.py` and `drafts/ID.json`; customize their location with `--output-dir`. Optional `--name` and `--description` set metadata. This scaffolds files only; it does not register them. An explicit category must already exist; omitting category selects `uncategorized`. The generated spec includes `style: "default"`, which can be edited before registration.

`--add-symbol ID` accepts `--script FILE.py`, `--spec FILE.json`, or both. At least one is required. When `--spec` is absent, metadata is resolved from a literal top-level `SPEC` Python dictionary, a sibling `.json` file, or a minimal definition using CLI metadata. `--category`, `--name`, `--description`, `--tags` (comma-separated) and `--order` override the definition. The definition's ID must match the command ID.

When a script is supplied, it is installed as **`Gallery/<category>/<id>/render.py`**. The remaining configuration is stored in **`symbol.json`** beside it. Identity fields (`id`, `name`, `category`, `style`) live only in **`Gallery/catalog.json`**. IDs and trimmed, case-insensitive names must be globally unique. `style` defaults to `default` and is read from the specification, included in discovery results and matched by existing text search. A spec-only variant can name another symbol that owns a renderer with `"renderer": "chip"`; renderer-reference chains are not supported.

Existing IDs or script targets require `--force`. Symbol replacement increments the version to at least the prior version plus one, preserving old source under `Gallery/.history/`. Replacement of a renderer used by other definitions is refused; add a distinct renderer ID or deliberately maintain shared source and run full regression checks outside this single-symbol operation.

Registration copies source to a temporary project, tests the new symbol's default and control extremes, checks duplicate part IDs/static XML, and checks that default SVG is deterministic. It publishes only after validation succeeds. `--dry-run` performs staging and validation without publishing. The normal commit uses a cooperative lock, per-file replacement, retained previous source and rollback on Python write errors. This is not a crash-proof database transaction.

`--timeout SECONDS` controls validation workers, from 1 to 300; default 30. Python executes with the current environment's authority. Timeouts and temporary directories are **not a security boundary**. Renderer scripts should use deterministic standard-library math and Drawing primitives, with no filesystem/network activity or subprocesses. Review externally supplied code before registration or rendering.

`Gallery/.write.lock` coordinates writers and causes new Gallery readers to fail while publication is in progress. Retry rather than bypassing a live lock. The lock records PID and time; confirm that no writer is alive before removing one left by a terminated process. Already-running browser servers must still be restarted after source changes.

`--build` always replaces generated HTML, without `--force`, and never registers source. CLI modules, drafts, outputs and history backups are excluded from embedded browser files. Do not edit the generated HTML to add symbols.

## JSON envelope and process exit codes

With `--json`, success is one JSON object on **stdout**, with **empty stderr**:

```json
{"schema_version":2,"ok":true,"action":"create","data":{"id":"chip","files":["/absolute/path/chip.svg"]}}
```

This illustrates selected fields; actual creation data also includes resolved parameters, parts, output settings and dry-run state. Discovery results are under `data.symbols`, `data.categories`, or `data.symbol`, according to the action. Source registration results include source paths, version, validation and any backup directory.

On failure **stdout is empty** and **stderr contains one JSON object**:

```json
{"schema_version":2,"ok":false,"error":{"code":"conflict","message":"Already exists...","details":{}}}
```

Do not combine `--debug` with a machine consumer expecting exactly one error object; debug mode can additionally print a traceback for unexpected exceptions. `--help` is human text. `--serve` is a long-running foreground service and rejects `--json`.

| Exit | Meaning |
|---|---|
| 0 | Success, including successful dry-run. |
| 2 | Invalid syntax, unknown ID, invalid metadata/parameter or conflicting option. |
| 3 | Existing file/ID, shared-renderer replacement refusal, or active Gallery lock. |
| 4 | Renderer execution/validation failure or validation timeout. |
| 5 | Optional PNG dependency missing or conversion failed; SVG is retained. |
| 6 | Filesystem read/write error. |
| 130 | Interrupted CLI operation. |

For sequential batches, loop over invocations with an argv list, check the return code, and parse the appropriate stream. See `examples/agent/batch_export.py`; a server or browser is not required.

## Symbol terminology and saved data

CLI result envelopes use schema 2, including errors. Discovery uses `symbol`, `symbols` and `symbol_count`; legacy `--add-element` and `--init-element` flags are rejected. The existing export and customization flags are unchanged.

Asset recipes remain schema 1. Personal library backups use schema 2 with `symbols`; supported schema-1 backups with `elements` are converted on import. Browser conversion writes the new `svgdrawer.gallery.v2` storage key only after validation and leaves old storage untouched.
