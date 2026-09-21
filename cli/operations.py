"""Source edits shared by the command line and browser adapters."""
from __future__ import annotations
import copy

from engine.gallery import validate_spec, require_id, RESERVED_CATEGORIES
from engine.service import handle_request
from engine.sanitize import safe_import
from .common import ROOT, UserError, gallery_lock
from .storage import (read_state, publish, catalog_change, move_changes, require_symbols,
                      config_bytes, IDENTITY)


def update_symbol(ident, values, dry_run=False, root=ROOT):
    with gallery_lock(root):
        gal, catalog = read_state(root)
        require_symbols(gal, [ident])
        spec = copy.deepcopy(gal.symbols[ident])
        spec.update({key: value for key, value in values.items() if value is not None})
        spec['version'] += 1
        spec = validate_spec(spec, {c['id'] for c in catalog['categories']})
        for row in catalog['symbols']:
            if row['id'] == ident:
                row.update({key: spec[key] for key in IDENTITY})
        changes = {f'{spec["category"]}/{ident}/symbol.json': config_bytes(spec)}
        changes.update(catalog_change(catalog))
        publish(changes, dry_run, root)
        return {'symbol': spec, 'dry_run': dry_run}


def move_symbols(ids, category, dry_run=False, root=ROOT):
    with gallery_lock(root):
        gal, catalog = read_state(root)
        changes = move_changes(gal, catalog, ids, category)
        changes.update(catalog_change(catalog))
        publish(changes, dry_run, root)
        return {'moved': ids, 'category': category, 'dry_run': dry_run}


def update_category(ident, values, dry_run=False, root=ROOT):
    with gallery_lock(root):
        gal, catalog = read_state(root)
        row = next((c for c in catalog['categories'] if c['id'] == ident), None)
        if row is None:
            raise UserError(f'Unknown category {ident!r}.')
        row.update({key: value for key, value in values.items() if value is not None})
        if not isinstance(row.get('name'), str) or not row['name'].strip():
            raise UserError('Category name must be nonempty text.')
        row['name'] = row['name'].strip()
        if any(c['id'] != ident and c['name'].strip().casefold() == row['name'].casefold() for c in catalog['categories']):
            raise UserError('Category name already exists.', 'conflict', 3)
        publish(catalog_change(catalog), dry_run, root)
        return {'category': row, 'dry_run': dry_run}


def install_symbol(ident, metadata, source=None, recipe=None, dry_run=False, root=ROOT):
    require_id(ident, 'Symbol ID')
    # Recipe validation renders the currently active source before taking the writer lock.
    resolved = handle_request({'action': 'validate_recipe', 'recipe': recipe}) if recipe is not None else None
    with gallery_lock(root):
        gal, catalog = read_state(root)
        if ident in gal.symbols:
            raise UserError(f'Symbol {ident} already exists.', 'conflict', 3)
        spec = {'schema_version': 1, 'version': 1, 'id': ident, 'name': metadata.get('name', ident),
                'category': metadata.get('category', 'uncategorized'), 'style': metadata.get('style', 'default'),
                'description': metadata.get('description') or 'Imported symbol.', 'tags': metadata.get('tags') or [],
                'defaults': {}, 'controls': []}
        if resolved:
            asset = resolved['asset']
            if asset['type'] == 'custom':
                source = asset['raw_svg']
            else:
                original = gal.symbols[asset['type']]
                spec.update({key: copy.deepcopy(original[key]) for key in ('kind', 'controls', 'defaults')})
                spec['renderer'] = original['renderer']
                if 'source' in original:
                    spec['source'] = copy.deepcopy(original['source'])
                if original['kind'] == 'svg':
                    source = (gal.symbol_path(original['id']) / 'source.svg').read_text(encoding='utf-8')
            spec['defaults'] = asset['params']
            spec['parts'] = asset['parts']
            spec['output'] = resolved['output']
        if source is not None:
            spec['kind'] = 'svg'
            spec.pop('renderer', None)
            source = safe_import(source, prefix='')
        spec = validate_spec(spec, {c['id'] for c in catalog['categories']})
        catalog['symbols'].append({key: spec[key] for key in IDENTITY})
        base = f'{spec["category"]}/{ident}'
        changes = {f'{base}/symbol.json': config_bytes(spec)}
        if source is not None:
            changes[f'{base}/source.svg'] = source.encode('utf-8')
            if resolved and resolved['asset']['type'] != 'custom':
                license_path = gal.symbol_path(resolved['asset']['type']) / 'LICENSE.txt'
                if license_path.is_file():
                    changes[f'{base}/LICENSE.txt'] = license_path.read_bytes()
        changes.update(catalog_change(catalog))
        publish(changes, dry_run, root)
        return {'symbol': spec, 'dry_run': dry_run}
