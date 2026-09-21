"""Gallery maintenance: scaffold, stage, validate, then commit source definitions."""
from __future__ import annotations
import ast
from contextlib import nullcontext
import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from engine.gallery import Gallery, COMMON, validate_spec, require_id, RESERVED_CATEGORIES
from .common import ROOT, UserError, json_input, json_value, json_bytes, gallery_lock, commit_gallery, preflight, atomic_write


def run_validation(root=ROOT, ids=None, timeout=30):
    try:
        result = subprocess.run([sys.executable, '-B', '-m', 'cli.validator', *(ids or [])],
                                cwd=root, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise UserError(f'Renderer validation exceeded {timeout} seconds. No Gallery changes were installed.',
                        'renderer_timeout', 4) from exc
    try:
        report = json.loads(result.stdout)
    except ValueError as exc:
        raise UserError('Validation worker failed: ' + (result.stderr or result.stdout)[-1500:],
                        'renderer_invalid', 4) from exc
    if result.returncode or not report.get('ok'):
        raise UserError('Renderer validation failed: ' + report.get('error', result.stderr)[-1500:],
                        'renderer_invalid', 4, diagnostics=report.get('diagnostics', ''))
    return report['data']


def _stage(target):
    for folder in ('Gallery', 'engine', 'cli'):
        shutil.copytree(ROOT / folder, target / folder,
                        ignore=shutil.ignore_patterns('__pycache__', '.history', '.trash', '.write.lock', '*.pyc'))


def _gallery_locked():
    return Gallery(ROOT, check_lock=False)


def add_category(args):
    ident = require_id(args.add_category, 'Category ID')
    if ident in RESERVED_CATEGORIES or ident == 'common':
        raise UserError(f'Category ID {ident!r} is reserved.')
    with gallery_lock():
        gal = _gallery_locked()
        catalog = copy.deepcopy(gal.catalog)
        rows = catalog['categories']
        old = next((r for r in rows if r['id'] == ident), None)
        if old and not args.force:
            raise UserError(f'Category {ident!r} already exists. Use --force to update its metadata.', 'conflict', 3)
        row = dict(old or {'id': ident, 'name': ident.replace('_', ' ').replace('-', ' ').title(),
                          'description': '', 'icon': 'folder', 'order': 100})
        for key in ('name', 'description', 'icon', 'order'):
            value = getattr(args, key)
            if value is not None:
                row[key] = value
        if not isinstance(row['name'], str) or not row['name'].strip() or len(row['name']) > 100:
            raise UserError('Category name must contain 1–100 characters.')
        row['name'] = row['name'].strip()
        if any(r['id'] != ident and r['name'].casefold() == row['name'].casefold() for r in rows):
            raise UserError('A different category already has that display name.', 'conflict', 3)
        rows = [row if r['id'] == ident else r for r in rows] if old else rows + [row]
        catalog['categories'] = rows
        changes = {}
        if not (ROOT / 'Gallery' / ident).exists():
            changes[ROOT / 'Gallery' / ident / '.gitkeep'] = b''
        changes[ROOT / 'Gallery/catalog.json'] = json_bytes(catalog)
        backup = None if args.dry_run else commit_gallery(changes, args.force)
        return {'category': row, 'dry_run': args.dry_run, 'backup': backup,
                'files': [str(p) for p in changes]}


def _script_metadata(source):
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise UserError(f'Python script has a syntax error on line {exc.lineno}: {exc.msg}', 'renderer_invalid', 4) from exc
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'SPEC' for t in node.targets):
            try:
                value = ast.literal_eval(node.value)
            except (ValueError, TypeError) as exc:
                raise UserError('An embedded SPEC must be a literal Python dictionary, or use --spec FILE.') from exc
            if not isinstance(value, dict):
                raise UserError('Embedded SPEC must be a dictionary.')
            return value
    return None


def add_symbol(args):
    ident = require_id(args.add_symbol, 'Symbol ID')
    if ident == 'custom':
        raise UserError('Symbol ID custom is reserved.')
    source = None
    if args.script:
        source_path = Path(args.script).expanduser()
        if source_path.suffix.lower() != '.py' or source_path.stat().st_size > 1_000_000:
            raise UserError('--script requires a Python .py file of at most 1 MB.')
        source = source_path.read_text(encoding='utf-8-sig')
        embedded = _script_metadata(source)
    else:
        embedded = None
    if args.spec:
        spec = json_input('@' + str(args.spec), 'symbol specification', dict)
    elif embedded:
        spec = embedded
    elif args.script and Path(args.script).with_suffix('.json').is_file():
        spec = json_input('@' + str(Path(args.script).with_suffix('.json')), 'sibling specification', dict)
    else:
        spec = {'schema_version': 1, 'version': 1, 'id': ident, 'renderer': ident,
                'name': ident.replace('_', ' ').replace('-', ' ').title(), 'category': args.category or 'uncategorized',
                'description': 'A custom Python-drawn SVG symbol.', 'tags': [], 'defaults': {}, 'controls': []}
    if spec.get('id') != ident:
        raise UserError(f'Specification id must match --add-symbol {ident}.')
    spec = copy.deepcopy(spec)
    for key in ('category', 'name', 'description', 'order'):
        value = getattr(args, key)
        if value is not None:
            spec[key] = value
    if args.tags is not None:
        spec['tags'] = [t.strip() for t in args.tags.split(',') if t.strip()]
    if source is not None:
        # One own script per symbol. A spec-only variant may reuse another renderer.
        spec['renderer'] = ident
        spec['kind'] = 'python'
    if not args.script and not args.spec:
        raise UserError('--add-symbol requires --script FILE.py and/or --spec FILE.json.')
    with gallery_lock():
        gal = _gallery_locked()
        spec = validate_spec(spec, {r['id'] for r in gal.categories}, f'{ident}.json')
        old = gal.symbols.get(ident)
        if old and not args.force:
            raise UserError(f'Symbol {ident!r} already exists. Use a new ID or explicitly use --force.', 'conflict', 3)
        if old:
            spec['version'] = max(old['version'] + 1, spec['version'])
        if any(s['id'] != ident and s['name'].casefold() == spec['name'].casefold() for s in gal.symbols.values()):
            raise UserError('A different symbol already has that display name.', 'conflict', 3)
        target = ROOT / 'Gallery' / spec['category'] / ident
        changes = {}
        if source is not None:
            shared = [s['id'] for s in gal.symbols.values() if s['id'] != ident and s['renderer'] == ident]
            if shared:
                raise UserError(f'Renderer {ident!r} is also used by {shared}. Add a new renderer ID instead of replacing shared code.', 'conflict', 3)
            script_target = target / 'render.py'
            if script_target.exists() and not args.force:
                raise UserError(f'Renderer {ident!r} already exists. Explicit --force is required.', 'conflict', 3)
            changes[script_target] = source.encode('utf-8')
        else:
            owner = spec['renderer']
            if owner not in gal.symbols or gal.symbols[owner]['renderer'] != owner:
                raise UserError('The specification references a missing renderer owner. Supply --script FILE.py.')
            if owner == ident and gal.symbol_path(ident) != target:
                changes[target / 'render.py'] = gal.renderer_path(ident).read_bytes()
        if old and old['renderer'] == ident and spec['renderer'] != ident:
            shared = [s['id'] for s in gal.symbols.values() if s['id'] != ident and s['renderer'] == ident]
            if shared:
                raise UserError(f'Renderer {ident!r} is also used by {shared}.', 'conflict', 3)
        if old and old['kind'] == 'svg':
            changes[gal.symbol_path(ident) / 'source.svg'] = None
        if old and gal.symbol_path(ident) != target:
            changes[gal.symbol_path(ident) / 'symbol.json'] = None
            if old['renderer'] == ident:
                changes[gal.symbol_path(ident) / 'render.py'] = None
        elif old and old['renderer'] == ident and spec['renderer'] != ident:
            changes[target / 'render.py'] = None
        config = {k: v for k, v in spec.items() if k not in ('id', 'name', 'category', 'style', 'customizable')}
        if config['renderer'] == ident:
            del config['renderer']
        changes[target / 'symbol.json'] = json_bytes(config)
        catalog = copy.deepcopy(gal.catalog)
        row = {key: spec[key] for key in ('id', 'name', 'category', 'style')}
        catalog['symbols'] = [row if s['id'] == ident else s for s in catalog['symbols']]
        if not old:
            catalog['symbols'].append(row)
        changes[ROOT / 'Gallery/catalog.json'] = json_bytes(catalog)
        with tempfile.TemporaryDirectory(prefix='svgdrawer-check-') as temp:
            stage = Path(temp)
            _stage(stage)
            for path, content in changes.items():
                dest = stage / path.relative_to(ROOT)
                if content is None:
                    dest.unlink(missing_ok=True)
                else:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_bytes(content)
            report = run_validation(stage, [ident], args.timeout)
        backup = None if args.dry_run else commit_gallery(changes, args.force)
        if not args.dry_run and source is not None:
            for cache in (target / '__pycache__').glob('render.*.pyc'):
                cache.unlink(missing_ok=True)
        return {'id': ident, 'name': spec['name'], 'category': spec['category'], 'style': spec['style'], 'version': spec['version'],
                'files': [str(p) for p in changes], 'dry_run': args.dry_run, 'backup': backup,
                'validation': report}


TEMPLATE = '''"""{name}: pure Python SVG geometry for SVGDrawer.

Design space: 256 x 256. Keep part IDs stable and output deterministic.
Use params instead of hard-coded dimensions/colors. No I/O or third-party imports.
"""

def render(drawing, params):
    d, p = drawing, params
    width = p['body_width']
    left = (256 - width) / 2
    d.rect('body', left, 72, width, 112, p['fill'], p['stroke'])
    count = int(p['ports'])
    for i in range(count):
        x = left + width * (i + 1) / (count + 1)
        d.ellipse(f'port-{{i + 1}}', x, 159, 5, 5, p['accent'], 'none', 0)
    d.label('label', 128, 123, p['label'], 24, p['stroke'])
'''


def scaffold(args):
    ident = require_id(args.init_symbol, 'Symbol ID')
    if ident == 'custom':
        raise UserError('Symbol ID custom is reserved.')
    category = args.category or 'uncategorized'
    require_id(category, 'Category ID')
    if category not in {c['id'] for c in Gallery(ROOT).categories}:
        raise UserError(f'Unknown category {category!r}.')
    name = args.name or ident.replace('_', ' ').replace('-', ' ').title()
    spec = {'schema_version': 1, 'id': ident, 'version': 1, 'name': name,
            'category': category, 'style': 'default',
            'description': args.description or 'A configurable instrument with labeled ports.',
            'tags': ['instrument', 'sensor'], 'defaults': dict(COMMON), 'controls': [
                {'key': 'ports', 'label': 'Ports', 'type': 'number', 'default': 3, 'min': 1, 'max': 8, 'step': 1},
                {'key': 'body_width', 'label': 'Body width', 'type': 'number', 'default': 168, 'min': 100, 'max': 208, 'step': 1, 'unit': 'u'},
                {'key': 'label', 'label': 'Label', 'type': 'text', 'default': 'SENSOR', 'max_length': 12}]}
    paths = preflight([Path(args.output_dir) / f'{ident}.py', Path(args.output_dir) / f'{ident}.json'], args.force)
    # A name is metadata, never interpolated into executable Python source.
    source = TEMPLATE.replace('{name}', ident).replace('{{i + 1}}', '{i + 1}')
    if not args.dry_run:
        for path, content in zip(paths, [source.encode('utf-8'), json_bytes(spec)]):
            atomic_write(path, content, overwrite=args.force)
    return {'id': ident, 'files': [str(p) for p in paths], 'dry_run': args.dry_run,
            'next': f'python svgdrawer.py --add-symbol {ident} --script "{paths[0]}" --spec "{paths[1]}"'}
