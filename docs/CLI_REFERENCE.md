# CLI reference

Run `python svgdrawer.py --help` for the generated option contract ([CLI_HELP.txt](CLI_HELP.txt)).
The CLI and local HTTP adapter call the same Python management functions. Commands
are noninteractive; all new write commands support `--dry-run`.

| Action | Inputs / behavior |
|---|---|
| `--list`, `--list-all-flat` | Optional `--search TEXT`; includes style, kind, customizable |
| `--list-category [ID]` | Categories or symbols in one category; optional search |
| `--describe ID`, `--list-parts ID` | Metadata without imports; parts render current geometry |
| `--list-color-sets` | Named palettes and custom color-array order |
| `--create ID`, `--recipe FILE` | SVG/PNG customization and export |
| `--init-symbol ID` | Python/spec drafts; optional category, name, output-dir |
| `--add-symbol ID` | `--script FILE.py --spec FILE.json`; trusted code; spec-only renderer reuse supported |
| `--import-svg FILE` | Required `--id ID`; optional name/category/style/description/tags |
| `--save-symbol ID --recipe FILE` | Optional identity metadata; preserve params/parts/output |
| `--update-symbol ID` | name/description/tags/style; `--favorite` or `--unfavorite` |
| `--move-symbol IDS... --category ID` | Batch move, IDs unchanged |
| `--add-category ID`, `--update-category ID` | name/description/icon/order |
| `--delete-category ID` | Nonempty requires `--contents uncategorized` or `trash` |
| `--delete-symbol IDS...` | Batch move to category-organized trash |
| `--list-trash` | Symbol/category entries and separate snapshot kind |
| `--restore TRASH_IDS...` | Batch restore; a snapshot restores alone and requires `--yes` |
| `--purge TRASH_IDS...`, `--empty-trash` | Permanent removal requires `--yes` |
| `--backup-gallery --output FILE.zip` | Active Gallery only; `--force` permits overwriting output |
| `--import-gallery FILE.zip` | Additive by default; `--force-sync --yes` replaces active content with snapshot |
| `--validate [ID]` | Render/geometry validation |
| `--serve` | Port 9178; optional `--port N --no-browser` |

IDs are case-sensitive lowercase identifiers. Names are globally unique after
trimming and case-insensitive comparison. Missing categories default to
`uncategorized`; unknown categories are errors. `--add-element`, `--init-element`
and `--build` are not supported. Style is searchable metadata, not a new filter.

## Export flags

`--params JSON_OR_@FILE`, repeatable `--set KEY=VALUE`, `--parts JSON_OR_@FILE`,
`--color-sets NAME_OR_JSON`, `--output FILE`, `--format svg|png|both`,
`--width`, `--height`, `--size`, `--padding`, `--scale 1|2|4`,
`--background HEX` / `--transparent`, `--stretch`, `--save-recipe FILE`.

PNG is Python/CairoSVG only and saves an SVG sidecar first. Size limits are 8192
pixels per side and 50 megapixels. Use `--output -` only for raw SVG stdout,
without JSON, dry-run, PNG or recipe saving. Existing outputs require `--force`.

## JSON envelope

```json
{"schema_version":2,"ok":true,"action":"list-all-flat","data":{"symbols":[],"symbol_count":0}}
```

Failures return a nonzero exit code and one stderr envelope with `ok:false` and
`error:{code,message,details}`. Parse stdout only on success. `--debug` adds tracebacks.
Recipes retain format `svgdrawer.asset`, schema 1; this is not the CLI envelope schema.

## Import semantics

Additive previews report `added`, `added_categories`, `skipped`, `conflicts` and
`dry_run`. Existing IDs/names are skipped; mismatched helper or owner code is a
conflict. Full sync previews report added/removed/replaced symbol IDs and count;
no changes occur until confirmed. Snapshot restore preserves existing trash and
retains the displaced active Gallery. Failed validation publishes nothing.
