"""Active Gallery ZIPs: additive import and explicitly confirmed snapshot sync."""
from __future__ import annotations
import copy
import io
import json
from pathlib import PurePosixPath
import stat
import zipfile

from .common import ROOT, UserError, gallery_lock, json_bytes, atomic_write, preflight
from .storage import (active_files, read_state, stage_validate, publish, catalog_change,
                      new_trash_id, deleted_at, EXCLUDED)


def zip_bytes(sources):
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, content in sorted(sources.items()):
            archive.writestr('Gallery/' + name, content)
    return output.getvalue()


def backup_bytes(root=ROOT):
    with gallery_lock(root):
        read_state(root)
        return zip_bytes(active_files(root))


def backup(output, force=False, dry_run=False, root=ROOT):
    if output.suffix.lower() != '.zip':
        raise UserError('Gallery backup output must end in .zip.')
    if output.resolve().is_relative_to((root / 'Gallery').resolve()):
        raise UserError('Save backups outside Gallery/.')
    target = preflight([output], force)[0]
    data = backup_bytes(root)
    if not dry_run:
        atomic_write(target, data, overwrite=force)
    return {'file': str(target), 'bytes': len(data), 'dry_run': dry_run}


def read_archive(data):
    sources = {}
    seen = set()
    total = 0
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            for info in archive.infolist():
                name = info.filename
                path = PurePosixPath(name)
                if ('\\' in name or ':' in name or path.is_absolute() or '..' in path.parts
                        or not path.parts or path.parts[0] != 'Gallery'
                        or any(part.endswith((' ', '.')) for part in path.parts)
                        or stat.S_ISLNK(info.external_attr >> 16)):
                    raise UserError(f'Unsafe Gallery archive path: {name}')
                if info.is_dir():
                    continue
                relative = PurePosixPath(*path.parts[1:]).as_posix()
                if relative == '.' or any(part in EXCLUDED for part in path.parts[1:]):
                    raise UserError(f'Archive must contain active Gallery sources only: {name}')
                key = relative.casefold()
                if key in seen:
                    raise UserError(f'Duplicate archive path: {name}')
                seen.add(key)
                total += info.file_size
                if total > 128_000_000:
                    raise UserError('Unpacked Gallery exceeds 128 MB.')
                sources[relative] = archive.read(info)
    except (zipfile.BadZipFile, RuntimeError) as exc:
        raise UserError(f'Invalid Gallery ZIP: {exc}') from exc
    for name in ('catalog.json', 'settings.json', 'color_sets.json', '__init__.py', 'common.py'):
        if name not in sources:
            raise UserError(f'Gallery ZIP is missing {name}.')
    return sources


def replacement_changes(sources, root):
    return {**{name: None for name in active_files(root) if name not in sources}, **sources}


def sync_sources(sources, dry_run=False, root=ROOT):
    """Caller holds the writer lock. Existing trash is never part of replacement."""
    sources = dict(sources)
    sources.setdefault('uncategorized/.gitkeep', b'')
    current = read_state(root)[1]
    incoming = json.loads(sources['catalog.json'])
    before = {s['id'] for s in current['symbols']}
    after = {s['id'] for s in incoming['symbols']}
    changes = replacement_changes(sources, root)
    token = new_trash_id()
    base = f'.trash/snapshots/{token}'
    for name, data in active_files(root).items():
        changes[f'{base}/Gallery/{name}'] = data
    changes[f'{base}/entry.json'] = json_bytes(
        {'trash_id': token, 'kind': 'snapshot', 'name': 'Gallery before sync', 'deleted_at': deleted_at()})
    publish(changes, dry_run, root)
    return {'mode': 'force-sync', 'snapshot_id': token, 'dry_run': dry_run,
            'symbol_count': len(after), 'added': sorted(after - before),
            'removed': sorted(before - after), 'replaced': sorted(before & after)}


def import_archive(data, force_sync=False, yes=False, dry_run=False, root=ROOT):
    if force_sync and not yes and not dry_run:
        raise UserError('Force sync requires --yes after reviewing --dry-run.', 'confirmation_required', 3)
    sources = read_archive(data)
    with gallery_lock(root):
        if force_sync:
            return sync_sources(sources, dry_run, root)
        # Additive imports must also be complete without accidentally available local files.
        stage_validate(replacement_changes(sources, root), root)
        gal, catalog = read_state(root)
        incoming = json.loads(sources['catalog.json'])
        local_files = active_files(root)
        specs = {}
        rows = {row['id']: row for row in incoming['symbols']}
        for row in incoming['symbols']:
            base = f'{row.get("category", "uncategorized")}/{row["id"]}'
            specs[row['id']] = json.loads(sources[f'{base}/symbol.json'])
        names = {spec['name'].casefold() for spec in gal.symbols.values()}
        candidates, skipped, conflicts = {}, [], []
        for ident, row in rows.items():
            if ident in gal.symbols or row['name'].strip().casefold() in names:
                skipped.append(ident)
                continue
            spec = specs[ident]
            if spec.get('kind', 'python') == 'python' and any(sources[n] != local_files[n] for n in ('common.py', '__init__.py')):
                conflicts.append({'id': ident, 'reason': 'Shared Python helpers differ; use confirmed force sync.'})
                continue
            candidates[ident] = row
        # Prune dependent candidates until every owner is present and equivalent.
        changed = True
        while changed:
            changed = False
            for ident in list(candidates):
                spec = specs[ident]
                if spec.get('kind', 'python') != 'python':
                    continue
                owner = spec.get('renderer', ident)
                if owner == ident or owner in candidates:
                    continue
                compatible = (owner in gal.symbols and gal.symbols[owner]['kind'] == 'python'
                              and gal.symbols[owner]['renderer'] == owner)
                if compatible:
                    row = rows[owner]
                    source = sources[f'{row.get("category", "uncategorized")}/{owner}/render.py']
                    compatible = source == gal.renderer_path(owner).read_bytes()
                if not compatible:
                    conflicts.append({'id': ident, 'reason': f'Renderer owner {owner} is missing or different.'})
                    del candidates[ident]
                    changed = True
        changes = {}
        added_categories = []
        blocked_categories = set()
        for category in incoming['categories']:
            if any(c['id'] == category['id'] for c in catalog['categories']):
                continue
            if any(c['name'].strip().casefold() == category['name'].strip().casefold() for c in catalog['categories']):
                conflicts.append({'category': category['id'], 'reason': 'Category name already exists.'})
                blocked_categories.add(category['id'])
                continue
            catalog['categories'].append(copy.deepcopy(category))
            added_categories.append(category['id'])
            changes[f'{category["id"]}/.gitkeep'] = b''
        if blocked_categories:
            # A dependent cannot be installed without its rejected renderer owner.
            changed = True
            while changed:
                changed = False
                for ident, row in list(candidates.items()):
                    owner = specs[ident].get('renderer', ident)
                    if row.get('category', 'uncategorized') in blocked_categories or (owner != ident and owner not in candidates and owner not in gal.symbols):
                        conflicts.append({'id': ident, 'reason': 'Category or renderer owner conflicts.'})
                        del candidates[ident]
                        changed = True
        for ident, row in candidates.items():
            row = {**row, 'category': row.get('category', 'uncategorized'), 'style': row.get('style', 'default')}
            catalog['symbols'].append(row)
            category = row['category']
            if not any(c['id'] == category for c in catalog['categories']):
                catalog['categories'].append(copy.deepcopy(next(c for c in incoming['categories'] if c['id'] == category)))
            prefix = f'{category}/{ident}/'
            changes.update({name: value for name, value in sources.items() if name.startswith(prefix)})
        if candidates or added_categories:
            changes.update(catalog_change(catalog))
            publish(changes, dry_run, root)
        return {'mode': 'additive', 'added': list(candidates), 'skipped': skipped,
                'conflicts': conflicts, 'added_categories': added_categories, 'dry_run': dry_run}
