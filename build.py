#!/usr/bin/env python3
"""Validate the source gallery and build a portable, single-file HTML app.

The HTML is a build artifact, not the source of truth. No npm or third-party
build dependencies are required. Restart server.py after changing source files.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from engine import gallery, render_asset

ROOT = Path(__file__).resolve().parent
JS_FILES = ['app.js', 'browser.js', 'detail.js', 'library.js', 'init.js']


def source_files():
    files = {}
    # An explicit allowlist prevents backups, drafts and CLI files entering the HTML.
    paths = list((ROOT / 'engine').glob('*.py'))
    cat = gallery()
    for ident in cat.symbols:
        paths.append(cat.symbol_path(ident) / 'symbol.json')
        renderer = cat.renderer_path(ident)
        if renderer not in paths:
            paths.append(renderer)
    paths += [ROOT / 'Gallery' / name for name in
              ('__init__.py', 'common.py', 'catalog.json', 'settings.json', 'color_sets.json')]
    for path in sorted(paths):
        files[path.relative_to(ROOT).as_posix()] = path.read_text(encoding='utf-8')
    return files


def build(output=None):
    cat = gallery()
    thumbs = {kind: render_asset({'type': kind}, dict(width=256, height=256, padding=8), clean=True)['svg']
              for kind in cat.symbols}
    boot = dict(gallery=cat.metadata(), thumbnails=thumbs, files=source_files())
    data = json.dumps(boot, ensure_ascii=True, separators=(',', ':')).replace('<', r'\u003c')
    replacements = {
        '__STYLES__': (ROOT / 'app/styles.css').read_text(encoding='utf-8'),
        '__BOOT_DATA__': data,
        '__RUNTIME__': (ROOT / 'app/runtime.js').read_text(encoding='utf-8'),
        '__APP__': '\n\n'.join((ROOT / 'app' / f).read_text(encoding='utf-8') for f in JS_FILES),
    }
    text = (ROOT / 'app/index.template.html').read_text(encoding='utf-8')
    for key, value in replacements.items():
        if text.count(key) != 1:
            raise ValueError(f'Template must contain {key} exactly once.')
        text = text.replace(key, value)
    path = Path(output) if output else ROOT / 'index.html'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')
    return path, len(cat.symbols), len(cat.categories)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, help='Output HTML path (default: index.html)')
    args = parser.parse_args()
    path, symbols, categories = build(args.output)
    print(f'Built {path}\n{symbols} symbols · {categories} categories · {path.stat().st_size:,} bytes')


if __name__ == '__main__':
    main()
