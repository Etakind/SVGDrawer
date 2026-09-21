# Extending the SVGDrawer Gallery

## Normal extension path

Use the CLI so validation, source history and naming remain consistent:

```powershell
python svgdrawer.py --add-category instruments --name "Instruments"
python svgdrawer.py --init-symbol sensor --category instruments
# Edit drafts/sensor.py and drafts/sensor.json.
python svgdrawer.py --add-symbol sensor --script drafts/sensor.py --spec drafts/sensor.json --dry-run
python svgdrawer.py --add-symbol sensor --script drafts/sensor.py --spec drafts/sensor.json
python svgdrawer.py --validate
python svgdrawer.py --build
```

No engine, browser or export switch statement needs to be updated. The `Gallery/` directory is the common source for CPython and browser Pyodide. Restart a running server after source updates.

## Files and IDs

`Gallery/catalog.json` is the authoritative index. It contains category presentation metadata and only four identity fields per source symbol:

```json
{
  "categories": [
    {"id": "instruments", "name": "Instruments", "description": "Measurement tools", "icon": "folder", "order": 100},
    {"id": "uncategorized", "name": "Uncategorized", "icon": "folder", "order": 100}
  ],
  "symbols": [
    {"id": "sensor", "name": "Sensor", "category": "instruments", "style": "default"}
  ]
}
```

This is a shape example, not a replacement for the shipped catalog. Keep all existing rows when adding entries. Each symbol lives at `Gallery/<category>/<id>/`, with `symbol.json` and `render.py` together. Shared sheet/code helpers live in `Gallery/common.py`; renderers import them with `from Gallery.common import sheet, code_symbol`.

The **draft/import specification** combines identity and configuration so the existing registration command can split them into the catalog and symbol folder:

```json
{
  "schema_version": 1,
  "id": "sensor",
  "version": 1,
  "name": "Sensor",
  "category": "instruments",
  "style": "default",
  "description": "An instrument with configurable ports.",
  "tags": ["measurement", "sensor"],
  "order": 100,
  "defaults": {"fill": "#DCEBFF", "accent": "#2878D4"},
  "controls": [
    {"key":"ports","label":"Ports","type":"number","default":3,"min":1,"max":8,"step":1},
    {"key":"body_width","label":"Body width","type":"number","default":168,"min":100,"max":208,"step":1,"unit":"u"},
    {"key":"label","label":"Label","type":"text","default":"SENSOR","max_length":12}
  ]
}
```

The installed `symbol.json` contains this configuration **without** `id`, `name`, `category` or `style`: those belong only in the catalog. The optional `renderer` field names another symbol that owns its `render.py`; omit it for the symbol's own drawing. Renderer-reference chains are not supported.

Source IDs and trimmed, case-insensitive display names are globally unique. Related designs use distinct IDs and names, with descriptive `style` metadata (for example `outline` or `filled`). Existing symbols use `default`. No separate style folders or style-management commands are needed. Omitting category selects `uncategorized`; an explicitly unknown category is an error.

Default values omitted from `defaults` come from the controls or the common color/style defaults. Unknown default keys are rejected. Numeric controls require finite `min`, `max`, positive `step` and an in-range default. `select` controls have an `options` array and a member default. `boolean` controls use true/false. `text` controls declare a default and maximum length (up to 500).

Common reserved control keys are `fill`, `accent`, `stroke`, `highlight`, `stroke_width` and `radius`. These are already provided by the interface and CLI. Do not duplicate them in `controls`; set their values in `defaults` instead.

IDs have 1–80 lowercase letters/digits/underscores/hyphens, begin with a letter, and cannot be Windows-reserved filenames. Symbol ID `custom` is reserved for static SVG imports. Category IDs `all`, `favorites` and `mine` are navigation-reserved; source category `common` is reserved for the shared geometry module. The symbol folder name must match the ID; its configuration filename is always `symbol.json`. Names can change; IDs should not, because recipes, personal variants and links refer to them.

## Python drawing contract

```python
def render(drawing, params):
    # Append vector shapes to drawing. No return value is needed.
    drawing.rect("body", 40, 64, 176, 128, params["fill"], params["stroke"])
```

Use a **256 × 256 local design space**. The engine adds output scaling, aspect preservation, padding and optional background. Every shape has a stable, unique part ID. Use parameter values rather than hard-coded colors/dimensions when the value is intended to be adjustable. The same source is embedded in HTML and executed in Pyodide; standard-library math and these helpers are the portable default. Do not use a desktop graphics application or raster image to draw the SVG.

### Drawing helpers

```python
d.rect(part, x, y, w, h, fill=None, stroke=None, sw=None, rx=None, **extra)
d.path(part, path_data, fill=None, stroke=None, sw=None, center=(128,128), **extra)
d.line(part, x1, y1, x2, y2, stroke=None, sw=None, **extra)
d.ellipse(part, cx, cy, rx, ry, fill=None, stroke=None, sw=None)
d.label(part, x, y, content, size=32, fill=None, weight=600)
d.add(part, svg_tag, attributes, body=None, center=(128,128))
```

Shapes use `fill` and `stroke` from common parameters when not overridden. Lines use the accent color by default. Text is horizontally centered, defaults to the highlight color, and escapes label contents. Numeric `sw` means stroke width. `rx` controls rectangle rounding. Ellipse can represent a circle by using equal radii.

`d.add` is the lower-level primitive for supported static SVG tags. Use `d.label` for text, because `d.add`'s body is raw SVG markup and must be correctly escaped. The CLI validator rejects scripts, external references, images, duplicate part IDs, invalid XML and some other non-static structures. This validation is not a full implementation of all SVG standards or a Python security sandbox.

For path geometry, set a meaningful `center` so inner-part scaling behaves naturally. Other helpers compute their own centers. Parts can be individually colored, hidden, translated and scaled by both the CLI and browser.

### Color and geometry conventions

Common parameters are normalized `#RGB`/`#RRGGBB` or `none` values inside the engine; the CLI additionally accepts bare hex and expands it to `#RRGGBB`. `fill` is the main surface, `accent` the emphasis color, `stroke` the outline, and `highlight` the light/text detail. `--color-sets` maps these roles, not every individual part.

The renderer controls determine what actually changes; a declared parameter that is never used cannot alter the picture. Keep counts integer-valued, arrange repeated parts predictably, and use stable part names such as `port-1` through `port-N`. Removing a part by reducing a count can make an old override invalid; CLI discovery and validation expose that rather than silently dropping it.

SVG text remains text, not font outlines. Native/browser font rendering may differ, especially for fonts absent from a machine. No font files are bundled. Keep labels compact and use the default common font stack for portability.

## One-file extensions and reusable variants

A script may define a **literal top-level dictionary** called `SPEC` followed by `render`. The CLI reads the metadata with `ast.literal_eval` and then validates the executable renderer in a temporary project. See `examples/agent/led.py`.

```powershell
python svgdrawer.py --add-symbol led --script examples/agent/led.py
```

Metadata resolution is explicit `--spec`, embedded `SPEC`, sibling JSON, or a minimal definition. For custom geometry controls, a spec is required somewhere. `--category` and other metadata flags can override the selected definition. A supplied script is installed as `Gallery/<category>/<symbol-id>/render.py`; the catalog is updated by the same registration.

A spec-only variant may reuse `"renderer":"chip"` while choosing a different symbol ID, name and defaults. Keep the full compatible control schema. Reusing a renderer avoids duplicated Python geometry and produces another Gallery card automatically.

## Color sets and categories

Add a color set to `Gallery/color_sets.json` with a stable lowercase `id`, `name`, and all four `#RRGGBB` color roles. Color-set IDs must be unique; `default` is reserved for each symbol's original colors. Validate and rebuild after manual color-set changes.

The CLI category path modifies shared source. The browser's category manager modifies only a personal collection, not the filesystem. Import/export that personal collection separately; no implicit browser-to-source synchronization is performed.

## Updates and checks

Use `--force` only for deliberate replacement. Source history is retained under `Gallery/.history/`; output files are not backed up. The engine loads renderers lazily, so listing metadata does not execute code. Registration uses a separate validation subprocess, but `--create`, `--build`, server requests and browser customization execute trusted renderer code directly. Do not install code that performs I/O, starts processes or modifies the environment.

Run `python svgdrawer.py --validate` for geometry checks and `python -m unittest discover -s tests -v` for regression tests. Inspect representative SVG/PNG previews visually; valid XML alone does not prove the design is attractive, readable or within your intended bounds.

The HTML build embeds only engine source, active catalog entries and their nested configuration/renderers, shared geometry helpers, color/runtime settings and the Gallery package initializer. It excludes `.history/`, CLI source, drafts and example outputs. The original catalog edition's extension examples remain available under `examples/extension/` for compatibility, but use the current CLI for new maintenance.
