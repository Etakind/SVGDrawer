# Verification

Run tests locally on Windows after `conda activate ./.conda`. During agent changes,
one isolated tester owns the test tree and executable verification.

```powershell
python -m unittest discover -s tests -v
python svgdrawer.py --validate --json
```

Verify original geometry and part IDs for the 33 parametric symbols (allow intentional
display-title refinements), and rendering/notices for the 24 added static SVGs. Check
metadata uniqueness/lazy loading, registration/replacement/reuse, CLI contracts and recipes,
shared HTTP management, static SVGs/variants/favorites, batch trash dependencies,
category deletion choices, active-only ZIPs, additive conflicts, full-sync snapshots,
restore/purge confirmation, malformed archives and rollback after failed writes.

PNG verification must produce and decode real images from both CLI and HTTP using
Python/CairoSVG; no browser-canvas fallback exists. Use the activated Conda environment so native Cairo is available through the process-local loader. Verify startup without CDN access,
port 9178 and overrides, and live visibility of CLI edits in an already running UI.
Browser tests require an available browser automation runtime; report blockers or
skips honestly. Do not install dependencies globally.

Packaging should include nested source symbols and app assets, but no `.conda/` environment,
trash/history/cache, standalone HTML distribution, checksum or file manifest.

`VERIFICATION.json`, `verification-output.txt` and existing screenshots are historical
artifacts, not evidence for this implementation. New results must state actual checks
and skips. Do not generate test-tree inventories or hashes.

Also verify unique descriptive names, licensed SVG/PNG notices, active-interpreter Cairo
loading, Python-only launchers, and exclusion of `.conda/` from release archives.
