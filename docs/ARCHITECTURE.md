# SVGDrawer architecture

## One Gallery, three entry points, one geometry engine

```text
                     Gallery/
       categories + symbol JSON + Python renderers
                        │
              engine/gallery.py (metadata)
                        │
          engine/service.py + primitives.py
                     Python → SVG
                  ┌─────┴──────┐
          cli/main.py       app/ + PythonEngine
          CPython           CPython server OR Pyodide
              │                      │
       SVG → CairoSVG PNG    SVG → browser PNG
                             OR local CairoSVG PNG
```

There is no composition model. A render request carries one asset's `type`, `params`, `parts` and optional imported SVG, plus export options. Asset recipes and personal Gallery backups remain versioned separately from application releases.

## Module boundaries

`Gallery/` contains data and trusted geometry plugins. The catalog is `Gallery/catalog.json`: category presentation metadata and symbol `id`, `name`, `category`, `style`. Each `Gallery/<category>/<id>/` holds `symbol.json` (controls, defaults and descriptive metadata) and `render.py` (geometry). Shared helpers live in `Gallery/common.py`. Renderer reuse references the owning symbol ID. Missing categories default to `uncategorized`; unknown explicit categories are rejected. `engine/gallery.py` validates definitions, returns metadata without importing renderer modules, and imports a renderer on its first actual use. Builders are cached for that process.

`engine/primitives.py` implements shared SVG shapes and part overrides. `engine/service.py` normalizes browser requests and renders one symbol. `engine/sanitize.py` handles static SVG imports. The CLI adds stricter input validation in `cli/customize.py` so malformed agent parameters are rejected instead of being clamped like interactive sliders.

`cli/main.py` provides the one-action command interface and machine-result envelope. `cli/manage.py` implements scaffolding, staging and source registration. `cli/validator.py` validates source additions in a timed subprocess. `cli/common.py` handles file I/O, no-clobber checks, source history and the cooperative writer lock.

`build.py` validates/loads source and produces `index.html`. It embeds the same engine, Gallery Python files and JSON consumed by CPython. `app/runtime.js` prefers the local server and otherwise loads Pyodide. Icon geometry is not reimplemented in JavaScript. A module-worker compatibility path can use the same Python runtime on the main thread.

`server.py` serves the application on loopback and exposes health, render and optional PNG endpoints. It checks local Host/Origin values and does not provide remote source registration. The CLI is the persistent source-management interface; the browser does not execute arbitrary uploaded Python.

## Updates and data ownership

Source additions go to `Gallery/`. CLI calls read fresh metadata on each invocation. Browser HTML and long-lived server state are generated/cached, so rebuild the HTML and restart the server after source changes. The generated HTML remains a distribution artifact, not a file to edit manually.

Browser-added personal variants, favorites, categories and sanitized SVG imports remain in local browser storage and backup JSON. They are not source registrations and are not enumerated by the CLI. Browser asset recipes can be exported and passed to `--recipe` when their referenced source symbol is available.

Recipes remain `svgdrawer.asset`, schema 1, with legacy `vector-foundry.asset` support. Libraries now use `svgdrawer.library`, schema 2, and a `symbols` collection. Schema-1 SVGDrawer/vector-foundry libraries convert on read. The browser prefers `svgdrawer.gallery.v2`, then reads earlier SVGDrawer/vector-foundry keys on the same origin; it writes only the new key after successful validation and never deletes the original data. `tools/migrate_v1.py` still converts the earlier drawing-editor presets to collection backups, dropping layout coordinates rather than reintroducing a canvas.

## Source mutation safeguards

A registration obtains `Gallery/.write.lock`, validates in a temporary project, retains old versions under `.history/`, and publishes complete source files with the catalog last. Write errors trigger in-process rollback. Source updates are not a database transaction and cannot promise crash consistency across files. The lock is local and cooperative; external manual edits bypass it. Never remove a lock while its writer is alive.

Export-file no-clobber checks are separate: output replacements require explicit `--force`, but do not get source-history backups. PNG failure can leave an already-produced SVG and recipe. This is intentional and is reflected in CLI errors.

Python scripts run with the current process's permissions. Temporary validation directories and timeouts are correctness aids, not isolation from the host. Only reviewed code should be registered; a separate operating-system sandbox is needed for untrusted code.

## Compatibility scope

Local development, CLI and launchers support Windows with Python 3.10+. The standalone HTML still runs the shared Python engine in Pyodide. The included verification was run with the environment versions recorded in `docs/VERIFICATION.json`, not evidence of current Windows verification. Browser geometry uses Pyodide; terminal PNG uses optional CairoSVG/Cairo. Text rendering depends on available fonts. Scripts with third-party or OS-only dependencies are not guaranteed to run in the single HTML.
