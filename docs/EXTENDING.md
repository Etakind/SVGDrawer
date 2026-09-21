# Extending the Gallery

Add ordinary symbols without engine or UI switches. Draw geometry only in Python;
HTML/CSS/JavaScript provide controls, not a second implementation of the artwork.

```powershell
python svgdrawer.py --add-category instruments --name Instruments
python svgdrawer.py --init-symbol sensor --category instruments
# Edit drafts/sensor.py and drafts/sensor.json.
python svgdrawer.py --add-symbol sensor --script drafts/sensor.py --spec drafts/sensor.json --dry-run --json
python svgdrawer.py --add-symbol sensor --script drafts/sensor.py --spec drafts/sensor.json --json
```

The registration specification includes identity (`id`, `name`, optional category
and style), schema_version 1, version, description, tags, defaults and controls.
Registration separates identity into the catalog and writes configuration alongside
the renderer at `Gallery/<category>/<id>/`. Missing categories use `uncategorized`.
Unknown categories and duplicate IDs/names are rejected. Use lowercase identifiers;
display names must be globally unique after trimming/case folding.

## Drawing contract

```python
def render(drawing, params):
    drawing.rect('body', 48, 72, 160, 112, params['fill'], params['stroke'])
```

Design space is 256 × 256. Use shared Drawing primitives and declared parameters;
keep part IDs and output deterministic. Shared helpers live in `Gallery/common.py`.
Preserve existing parameter names, recipes and artwork. Renderers are trusted Python:
validation invokes their code, not a security sandbox. Avoid I/O and new dependencies.

Controls support number, text, boolean and select values with validated defaults.
Common colors, stroke width and radius come from the engine. Style describes appearance only. Distinguish related symbols by function, geometry,
perspective and fixed/configurable features in their names, descriptions and tags.
Agents may clarify existing display names while adding new symbols; preserve stable IDs
and recipes. Follow the naming rules in [the agent guide](AGENT_GUIDE.md#naming-related-symbols-for-ai-agents).
A spec-only registration can reference an existing owning symbol with `renderer`.
A saved recipe variant uses that same owner, retaining params, parts and output defaults.
Shared renderer code cannot be replaced by ordinary `--add-symbol --force` while
other symbols depend on it; use a new owner ID.

Static imports use `--import-svg FILE --id ID`; they store sanitized `source.svg`
and kind `svg`. They receive no customizable badge. Python sources use kind `python`.
Metadata discovery never executes renderers; rendering/import validation does.

No HTML generation or server restart is necessary. CLI and UI immediately share
catalog changes. Deleting owners requires including their dependents. Use active-only
Gallery ZIP backup before broader edits and preview imports/full sync with `--dry-run`.
See [Architecture](ARCHITECTURE.md) and [CLI reference](CLI_REFERENCE.md).
