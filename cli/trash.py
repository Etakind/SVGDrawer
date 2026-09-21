"""Category-organized trash and batch restoration. No file manifests."""
from __future__ import annotations
import copy

from engine.gallery import read_json
from .common import ROOT, UserError, gallery_lock, json_bytes
from .storage import (read_state, files_under, new_trash_id, deleted_at,
                      require_symbols, catalog_change, publish, move_changes)


def entries(root=ROOT):
    result = {}
    for path in (root / 'Gallery/.trash').glob('*/*/entry.json'):
        entry = read_json(path)
        entry['_folder'] = path.parent
        result[entry['trash_id']] = entry
    return result


def list_trash(root=ROOT):
    rows = [{key: value for key, value in row.items() if key != '_folder'} for row in entries(root).values()]
    return {'entries': sorted(rows, key=lambda row: (row.get('category', {}).get('name', ''), row['deleted_at'])),
            'entry_count': len(rows)}


def trash_symbols(gal, catalog, ids, changes):
    ids = require_symbols(gal, ids)
    dependents = [s['id'] for s in gal.symbols.values()
                  if s['kind'] == 'python' and s['renderer'] in ids and s['id'] not in ids]
    if dependents:
        raise UserError('Include dependent symbols in the batch: ' + ', '.join(dependents), 'conflict', 3)
    created = []
    for ident in ids:
        spec = gal.symbols[ident]
        category = next(c for c in catalog['categories'] if c['id'] == spec['category'])
        row = next(s for s in catalog['symbols'] if s['id'] == ident)
        token = new_trash_id()
        base = f'.trash/{category["id"]}/{token}'
        entry = {'trash_id': token, 'kind': 'symbol', 'symbol': row, 'category': category,
                 'renderer': spec.get('renderer'), 'deleted_at': deleted_at()}
        changes[f'{base}/entry.json'] = json_bytes(entry)
        for name, content in files_under(gal.symbol_path(ident)).items():
            changes[f'{base}/source/{name}'] = content
            changes[f'{category["id"]}/{ident}/{name}'] = None
        created.append(token)
    catalog['symbols'] = [row for row in catalog['symbols'] if row['id'] not in ids]
    return created


def delete_symbols(ids, dry_run=False, root=ROOT):
    with gallery_lock(root):
        gal, catalog = read_state(root)
        changes = {}
        tokens = trash_symbols(gal, catalog, ids, changes)
        changes.update(catalog_change(catalog))
        publish(changes, dry_run, root)
        return {'trash_ids': tokens, 'symbol_ids': ids, 'dry_run': dry_run}


def delete_category(ident, contents=None, dry_run=False, root=ROOT):
    if ident == 'uncategorized':
        raise UserError('Uncategorized is permanent.')
    with gallery_lock(root):
        gal, catalog = read_state(root)
        category = next((row for row in catalog['categories'] if row['id'] == ident), None)
        if category is None:
            raise UserError(f'Unknown category {ident!r}.')
        ids = [s['id'] for s in catalog['symbols'] if s['category'] == ident]
        if ids and contents not in ('uncategorized', 'trash'):
            raise UserError('Choose --contents uncategorized or trash for a nonempty category.')
        changes = {}
        tokens = []
        if contents == 'trash':
            tokens = trash_symbols(gal, catalog, ids, changes)
        elif ids:
            changes.update(move_changes(gal, catalog, ids, 'uncategorized'))
        token = new_trash_id()
        changes[f'.trash/{ident}/{token}/entry.json'] = json_bytes(
            {'trash_id': token, 'kind': 'category', 'category': category, 'deleted_at': deleted_at()})
        for name in files_under(root / 'Gallery' / ident):
            changes[f'{ident}/{name}'] = None
        catalog['categories'] = [row for row in catalog['categories'] if row['id'] != ident]
        changes.update(catalog_change(catalog))
        publish(changes, dry_run, root)
        return {'category': ident, 'symbol_ids': ids, 'trash_ids': [*tokens, token], 'dry_run': dry_run}


def selected_entries(ids, root):
    existing = entries(root)
    ids = list(dict.fromkeys(ids))
    if not ids or any(token not in existing for token in ids):
        raise UserError('Select existing trash IDs.')
    return [existing[token] for token in ids]


def restore(ids, yes=False, dry_run=False, root=ROOT):
    with gallery_lock(root):
        selected = selected_entries(ids, root)
        snapshots = [entry for entry in selected if entry['kind'] == 'snapshot']
        if snapshots:
            if len(selected) != 1:
                raise UserError('Restore a Gallery snapshot separately from symbol/category entries.')
            if not yes and not dry_run:
                raise UserError('Restoring a Gallery snapshot requires --yes.', 'confirmation_required', 3)
            from .archives import sync_sources
            return sync_sources(files_under(snapshots[0]['_folder'] / 'Gallery'), dry_run, root)
        gal, catalog = read_state(root)
        changes = {}
        ids_now = set(gal.symbols)
        names = {s['name'].casefold() for s in gal.symbols.values()}
        for entry in selected:
            category = entry['category']
            if not any(c['id'] == category['id'] for c in catalog['categories']):
                catalog['categories'].append(copy.deepcopy(category))
                changes[f'{category["id"]}/.gitkeep'] = b''
            if entry['kind'] == 'symbol':
                row = entry['symbol']
                if row['id'] in ids_now or row['name'].strip().casefold() in names:
                    raise UserError(f'Cannot restore {row["id"]}: ID or name is already active.', 'conflict', 3)
                ids_now.add(row['id'])
                names.add(row['name'].strip().casefold())
                catalog['symbols'].append(copy.deepcopy(row))
                for name, content in files_under(entry['_folder'] / 'source').items():
                    changes[f'{category["id"]}/{row["id"]}/{name}'] = content
            for path in entry['_folder'].rglob('*'):
                if path.is_file():
                    changes[path.relative_to(root / 'Gallery').as_posix()] = None
        changes.update(catalog_change(catalog))
        publish(changes, dry_run, root)
        return {'restored': ids, 'dry_run': dry_run}


def purge(ids=None, yes=False, dry_run=False, root=ROOT):
    if not yes and not dry_run:
        raise UserError('Permanent deletion requires --yes.', 'confirmation_required', 3)
    with gallery_lock(root):
        all_entries = entries(root)
        selected = selected_entries(ids, root) if ids is not None else list(all_entries.values())
        removed = {e['trash_id'] for e in selected}
        owners = {e['symbol']['id'] for e in selected if e['kind'] == 'symbol'}
        active = active_renderer_owners(root)
        for entry in all_entries.values():
            if entry['trash_id'] not in removed and entry.get('renderer') in owners and entry['renderer'] not in active:
                raise UserError(f'Include dependent trashed symbol {entry["symbol"]["id"]} ({entry["trash_id"]}) before purging renderer {entry["renderer"]}.', 'conflict', 3)
        changes = {}
        for entry in selected:
            for path in entry['_folder'].rglob('*'):
                if path.is_file():
                    changes[path.relative_to(root / 'Gallery').as_posix()] = None
        publish(changes, dry_run, root, validate=False)
        return {'purged': sorted(removed), 'dry_run': dry_run}


def active_renderer_owners(root):
    gal, _ = read_state(root)
    return {s['id'] for s in gal.symbols.values() if s['kind'] == 'python' and s['renderer'] == s['id']}
