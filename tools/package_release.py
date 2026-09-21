#!/usr/bin/env python3
"""Package the local Python application without file manifests.

    python tools/package_release.py --output-dir dist

Drafts, exports, browser test outputs, virtual environments, locks and source
history are excluded. Keep personal backups separately from public releases.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def distributable(path, out):
    rel = path.relative_to(ROOT)
    if not path.is_file() or path.is_symlink():
        return False
    if any(part in {'.git', '.venv', '.conda', '__pycache__', '.pytest_cache', '.history', '.trash', 'drafts', 'exports', 'dist'} for part in rel.parts):
        return False
    if rel.parts[:2] == ('tests', 'output'):
        return False
    if path.name == '.write.lock' or path.suffix in {'.pyc', '.pyo', '.log', '.pid'}:
        return False
    if out == path or out in path.parents:
        return False
    return True


def package(out):
    out = out.expanduser().resolve()
    if out == ROOT or out in ROOT.parents:
        raise ValueError('Use a dedicated output directory, not the project root or an ancestor.')
    if (ROOT / 'Gallery/.write.lock').exists():
        raise ValueError('A Gallery writer is active; retry after it finishes.')
    paths = sorted(p for p in ROOT.rglob('*') if distributable(p, out))
    out.mkdir(parents=True, exist_ok=True)
    zip_path = out / 'SVGDrawer.zip'
    tmp = out / '.SVGDrawer.zip.tmp'
    try:
        with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for path in paths:
                archive.write(path, 'SVGDrawer/' + path.relative_to(ROOT).as_posix())
        tmp.replace(zip_path)
    finally:
        tmp.unlink(missing_ok=True)
    return zip_path


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output-dir', type=Path, default=ROOT / 'dist')
    args = p.parse_args()
    try:
        zip_path = package(args.output_dir)
        print(f'Python application: {zip_path}')
    except (ValueError, OSError) as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == '__main__':
    main()
