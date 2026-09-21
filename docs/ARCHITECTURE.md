# Architecture and local HTTP API

SVGDrawer has one Python runtime and one disk-backed `Gallery/`. Human users use
HTML/CSS/JavaScript served by `server.py`; agents use `svgdrawer.py`. Both adapters
call Python management and rendering modules. There is no standalone HTML,
Pyodide, CDN loader, browser-owned symbol library or generated root HTML.

## Data and module boundaries

- `Gallery/catalog.json`: category presentation metadata and symbol identity
  records (`id`, `name`, `category`, `style`), no paths or file inventory.
- `Gallery/<category>/<id>/symbol.json`: version, kind, description, tags,
  ordering, controls/defaults and optional parts/output defaults. `renderer`
  optionally points to a Python owner symbol; locations derive from the catalog.
- `render.py`: trusted Python geometry; `source.svg`: sanitized static vector.
- `Gallery/common.py`, `settings.json`, `color_sets.json`: shared source data.
- `engine/gallery.py`: metadata validation and lazy renderer loading.
- `engine/service.py`: normalize recipes, customize and render SVG; catalog changes
  invalidate metadata and renderer imports without a server restart.
- `engine/png.py`: CairoSVG using the active Conda interpreter’s `Library/bin` on Windows;
  PNG exports retain embedded SVG license notices as Description metadata.
- `cli/manage.py`: Python registration and scaffolding.
- `cli/operations.py`, `trash.py`, `archives.py`, `storage.py`: shared management,
  active ZIPs, category-organized trash and staged publication.
- `cli/api.py`: HTTP payload adapter to the same parsed CLI commands.
- `app/`: presentation, transient customization drafts and API calls, no persistent
  browser collection. Saved favorites are symbol configuration on disk.

Writes take the existing cooperative lock, validate candidates in temporary
Galleries and publish through rollback-capable atomic file replacement. The catalog
is published last as the cache revision. This is not a crash-proof database or a
Python sandbox. Inputs and local-origin boundaries remain validated.

## HTTP contract

Server binds loopback only, default `127.0.0.1:9178`. Host and Origin must match its
actual local port. Assets are served directly from an explicit app-file allowlist.
Responses are not cached. JSON POST requests require `Content-Type: application/json`.

| Endpoint | Response |
|---|---|
| `GET /api/health` | app, version, Python PNG availability |
| `GET /api/gallery` | settings, categories, palettes, full symbols metadata, catalog revision |
| `GET /api/trash` | entries and entry_count; entries have kind symbol/category/snapshot |
| `GET /api/backup` | ZIP bytes rooted at Gallery/ |
| `POST /api/render` | Existing render/export/validate_recipe protocol |
| `POST /api/png` | `{asset, options, scale}` to Python PNG bytes |
| `POST /api/manage` | Schema-2 command envelope |

Management bodies contain `action` using CLI hyphenated names, singular `id` or
batch `ids`, plus relevant metadata (`name`, `category`, `description`, `tags`,
`style`, `icon`, `order`). Optional booleans: `dry_run`, `yes`, `force`, `force_sync`.
`update-symbol` accepts boolean `favorite`. File inputs are contents, never host
filesystem paths: `svg` text, `script` text, `spec` object, `recipe` object,
`archive` base64 ZIP. Backup is the GET endpoint, not an arbitrary server output path.

Examples:

```json
{"action":"move-symbol","ids":["chip"],"category":"uncategorized","dry_run":true}
```

```json
{"action":"import-svg","id":"square","name":"Square","svg":"<svg xmlns=\"http://www.w3.org/2000/svg\"><rect width=\"20\" height=\"20\"/></svg>"}
```

The browser refreshes metadata every two seconds and on focus. Thumbnails/drafts
are invalidated when metadata changes. Management mutations refresh immediately.
Python renderers imported through either interface execute with local permissions;
the UI requires trust confirmation before Python or ZIP import.

## Trash and ZIPs

Trash entry records contain original catalog/category metadata and deletion time,
plus the retained symbol sources under `Gallery/.trash/<category>/<trash-id>/`.
Snapshots are separate entries under `.trash/snapshots/` with an active Gallery copy.
No file inventories or checksums are generated. Trash is ignored by Git.

Backups exclude trash/history/caches/locks. Additive import preserves local global
files and checks owner/helper byte equality before reusing them. Full sync and
snapshot restoration preserve existing trash and snapshot the displaced active
Gallery. Batch dependency or identity errors leave active content unchanged.
