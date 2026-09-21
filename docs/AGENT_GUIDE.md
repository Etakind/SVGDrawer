# SVGDrawer: simple command-line guide

This guide works for people and AI agents. Every command runs from the extracted **SVGDrawer** project directory unless otherwise stated. Use Python 3.10 or newer on Windows.

SVGDrawer generates **one symbol per export**, not a composition. Its shared collection is named **Gallery**. Position the resulting pictures in your preferred design, slide or document software.

## 1. Find an symbol

```powershell
python svgdrawer.py --list
python svgdrawer.py --list-all-flat
python svgdrawer.py --list-category
python svgdrawer.py --list-category hardware
python svgdrawer.py --list-all-flat --search waveform
```

`--list` groups symbols by category. `--list-all-flat` returns every matching symbol without grouping. `--list-category` alone returns categories and counts; supplying a category ID lists its symbols.

For an AI agent, add `--json`:

```powershell
python svgdrawer.py --list-all-flat --json
python svgdrawer.py --describe chip --json
```

Discover the available controls before changing them. For a chip, `pins`, `pin_length`, `pin_width`, `core_size`, `label` and `font_size` are geometry controls. `fill`, `accent`, `stroke`, `highlight`, `stroke_width` and `radius` are common controls. Other symbols declare their own controls.

## 2. Create SVGs and customize them

```powershell
# Original symbol and colors. Default output: exports/chip.svg.
python svgdrawer.py --create chip --color-sets default

# A named color set and custom chip geometry.
python svgdrawer.py --create chip --color-sets mint --set pins=10 --set pin_length=24 --set pin_width=9 --set label=DSP --output exports/dsp.svg

# Hex colors: the first is fill; the second is accent.
python svgdrawer.py --create chip --color-sets '["012345","427abc"]' --output exports/custom-chip.svg

# All four roles: fill, accent, stroke, highlight.
python svgdrawer.py --create folder --color-sets '["DCEBFF","2878D4","193E5B","FFFFFF"]' --output exports/folder.svg

# Geometry-specific controls for another symbol.
python svgdrawer.py --create waveform --set wave_type=sine --set cycles=5 --set amplitude=90 --set trace_width=3.5 --output exports/wave.svg

# Discover available named color sets.
python svgdrawer.py --list-color-sets
```

A custom array accepts **one to four** strings containing 3- or 6-digit hex values, with or without `#`. Roles omitted from the array keep their existing values. It does not generate an automatic color gradient or cycle colors among individual parts. `default` means the symbol's original colors, not the Ocean preset.

Use straight ASCII quotes (`"`), not typographic quotes (`“` or `”`). PowerShell quoting varies by version; for complex input the file-based form avoids nested quoting:

Create `colors.json` containing:

```json
["012345", "427abc"]
```

Create `chip-params.json` containing:

```json
{"pins": 10, "pin_length": 24, "pin_width": 9, "label": "DSP"}
```

Then run:

```powershell
python svgdrawer.py --create chip --color-sets @colors.json --params @chip-params.json --output exports/dsp-file.svg
```

Effective parameter order is: symbol defaults → recipe values, when loading a recipe → color set → `--params` → repeated `--set` options from left to right. Unknown controls, invalid values, out-of-range numbers and incorrect steps are errors, not silent corrections.

## 3. Customize an inner part

Discover part IDs using the same geometry you plan to export:

```powershell
python svgdrawer.py --list-parts chip --set pins=10 --json
```

Create `parts.json` containing:

```json
{
  "pin-top-1": {"fill": "FF6B35", "sx": 1.5, "sy": 0.75},
  "core": {"stroke": "012345", "stroke_width": 3}
}
```

```powershell
python svgdrawer.py --create chip --set pins=10 --parts @parts.json --output exports/edited-chip.svg
```

`sx` and `sy` scale that part's width and height around its geometric center. They are **multipliers**, so `1.5` means 150%. For exact, named dimensions, prefer symbol controls such as `pin_width` and `pin_length`. Part overrides also support `dx`, `dy`, `cx`, `cy` and `hidden`. `--parts` replaces the recipe's entire part-override object; `--parts '{}'` clears it.

## 4. Download PNG or save reusable settings

Terminal PNG needs the optional CairoSVG package and its Cairo system runtime:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-png.txt
python svgdrawer.py --create chip --width 512 --height 512 --scale 2 --output exports/chip-preview.png
```

This writes **`chip-preview.svg` first**, then rasterizes it into a **1024 × 1024 PNG**. Both files remain available. SVG does not depend on CairoSVG. When PNG dependencies are missing, the command exits with code 5 and reports where it saved the SVG.

```powershell
# SVG and PNG with an opaque background. Otherwise exports are transparent.
python svgdrawer.py --create folder --format both --size 512 --background FFFFFF --output exports/folder-white.svg

# Save all resolved parameters, inner-part overrides and SVG output settings.
python svgdrawer.py --create chip --set pins=10 --color-sets lilac --save-recipe exports/dsp.asset.json --output exports/dsp-recipe.svg

# Reproduce the SVG or apply further overrides.
python svgdrawer.py --recipe exports/dsp.asset.json --output exports/dsp-copy.svg
python svgdrawer.py --recipe exports/dsp.asset.json --set label=CPU --output exports/cpu.png --scale 2
```

Output width and height are pixels; padding and renderer geometry use a 256-unit design space. Non-square exports preserve the aspect ratio unless `--stretch` is supplied. PNG scaling is an export option, not stored in an asset recipe; specify it again when reproducing a PNG.

Existing files are protected. Choose another filename, or intentionally add `--force` to replace them. `--dry-run` validates a planned export without writing it. `--output -` prints only raw SVG to stdout; do not combine that mode with `--json`.

## 5. Add a category and a Python-drawn symbol

```powershell
# Register a persistent source category.
python svgdrawer.py --add-category instruments --name "Instruments" --description "Sensors and measurement tools"

# Generate drafts/sensor.py and drafts/sensor.json.
python svgdrawer.py --init-symbol sensor --category instruments --name "Sensor"
```

Edit **`drafts/sensor.py`** to draw the symbol. The template already provides a working body, label and configurable ports. Its renderer contract is:

```python
def render(drawing, params):
    d, p = drawing, params
    width = p["body_width"]
    left = (256 - width) / 2
    d.rect("body", left, 72, width, 112, p["fill"], p["stroke"])
    for i in range(int(p["ports"])):
        x = left + width * (i + 1) / (int(p["ports"]) + 1)
        d.ellipse(f"port-{i + 1}", x, 159, 5, 5, p["accent"], "none", 0)
    d.label("label", 128, 123, p["label"], 24, p["stroke"])
```

Edit **`drafts/sensor.json`** to set its unique title, category, style, tags, defaults and adjustable controls. Registration puts identity metadata in `Gallery/catalog.json` and the remaining configuration in the symbol folder. If category is omitted, it uses `uncategorized`. The generated file declares `ports`, `body_width` and `label`; the browser automatically builds controls from that definition. Use standard-library Python and the shared Drawing helpers. The function appends shapes to `drawing` and does not need to return SVG text.

```powershell
# Review the code first; Python renderer scripts are executable, not sandboxed.
# Test the new symbol without installing it.
python svgdrawer.py --add-symbol sensor --script drafts/sensor.py --spec drafts/sensor.json --dry-run --json

# Install Gallery/instruments/sensor/{render.py,symbol.json} and update catalog.json.
python svgdrawer.py --add-symbol sensor --script drafts/sensor.py --spec drafts/sensor.json --json

# Use it immediately from the terminal.
python svgdrawer.py --create sensor --set ports=6 --set body_width=192 --set label=TEMP --color-sets mint --output exports/sensor.svg

# Check the entire Gallery, then rebuild the browser application.
python svgdrawer.py --validate
python svgdrawer.py --build
```

Registration tests defaults, declared control extremes and deterministic default output in a temporary copy before changing the source Gallery. Failed validation leaves the existing Gallery unchanged. The subprocess has a timeout but **is not a security sandbox**. A malicious script could perform arbitrary host actions; review or externally sandbox code before use.

A single script can instead contain a literal Python dictionary named `SPEC` with the same metadata. See `examples/agent/led.py`:

```powershell
python svgdrawer.py --add-symbol led --script examples/agent/led.py --category instruments
```

When `--spec` is omitted, metadata resolution is: embedded `SPEC`, then a sibling `.json` file, then a minimal definition using CLI metadata such as `--category`. A geometry renderer that expects custom parameters needs those parameters declared in a specification. A **spec-only** addition can reuse an existing renderer:

```powershell
python svgdrawer.py --add-symbol my_chip --spec drafts/my_chip.json
```

That JSON must have `"id": "my_chip"`, a distinct display `name`, and can set `"renderer": "chip"`. Set `style` to a descriptive value for a different design (the default is `default`). Keep the chip control definitions and change defaults for a reusable variant.

## 6. Agent workflow and project rules

Use stable IDs, not display names, in commands. `chip` is an ID; `AI chip` is its editable name. IDs start with a lowercase letter and contain only lowercase letters, numbers, `_` or `-`. Never rename referenced IDs just to change a label.

For automation, add `--json`. A successful command writes one JSON object to stdout:

```json
{"schema_version":2,"ok":true,"action":"list-all-flat","data":{"symbols":[],"symbol_count":0}}
```

This is a **shape example**, not the shipped Gallery contents. On failure stdout is empty, a JSON error is written to stderr, and the process exits nonzero. Parse the envelope rather than human tables. Core exit codes are **0 success, 2 invalid input, 3 conflict/lock, 4 renderer failure, 5 PNG dependency/conversion failure, 6 filesystem error**. Full details are in [CLI_REFERENCE.md](CLI_REFERENCE.md).

`--force` is required for replacing registered IDs; the previous source is retained under `Gallery/.history/`, and symbol versions increase. It does not create backups of overwritten export files. A `Gallery/.write.lock` coordinates CLI source writers; retry when another writer is active. After an interrupted process, confirm that the recorded PID is no longer running before manually removing a stale lock. These are local file safeguards, not a database or a multi-user hosted service.

**Maintain `Gallery/`, not `index.html`.** Source additions are immediately available to subsequent CLI runs. Rebuild with `--build` and restart an existing server to publish them in the browser. Browser-only personal variants and categories are separate from the shared source Gallery.

To browse locally:

```powershell
python svgdrawer.py --serve
```

Read [AGENTS.md](../AGENTS.md) for concise project instructions and [EXTENDING.md](EXTENDING.md) for the Drawing API.

### Runtime references

Official documentation for the underlying optional/runtime components: [CairoSVG installation and conversion](https://cairosvg.org/documentation/), [Pyodide browser loading](https://pyodide.org/en/stable/usage/quickstart.html), and [Python argparse](https://docs.python.org/3/library/argparse.html). The CLI behavior described above is SVGDrawer's own contract, not those libraries' command syntax.
