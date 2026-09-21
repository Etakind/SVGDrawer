"""Shared Gallery transactions for CLI and local HTTP operations."""
from __future__ import annotations
import copy
from datetime import datetime, timezone
from pathlib import Path
import shutil
import tempfile
import uuid

from engine.gallery import Gallery, read_json
from .common import ROOT, UserError, commit_gallery, json_bytes
from .manage import run_validation

EXCLUDED = {'.trash', '.history', '__pycache__', '.write.lock'}
IDENTITY = ('id', 'name', 'category', 'style')


def files_under(folder):
    """Read source bytes, not an inventory artifact. Never follow source links."""
    result = {}
    for path in Path(folder).rglob('*'):
        relative = path.relative_to(folder)
        if any(part in EXCLUDED for part in relative.parts) or path.suffix in ('.pyc', '.pyo'):
            continue
        if path.is_symlink():
            raise UserError(f'Symbolic links are not supported in Gallery sources: {path}')
        if path.is_file():
            result[relative.as_posix()] = path.read_bytes()
    return result


def active_files(root=ROOT):
    return files_under(root / 'Gallery')


def new_trash_id():
    return 'trash-' + uuid.uuid4().hex


def deleted_at():
    return datetime.now(timezone.utc).isoformat()


def catalog_change(catalog):
    return {'catalog.json': json_bytes(catalog)}


def stage_validate(changes, root=ROOT):
    """Validate the complete candidate in a separate process before publication."""
    with tempfile.TemporaryDirectory(prefix='svgdrawer-stage-') as directory:
        stage = Path(directory)
        for folder in ('engine', 'cli'):
            shutil.copytree(root / folder, stage / folder, ignore=shutil.ignore_patterns('__pycache__'))
        sources = active_files(root)
        for name, content in changes.items():
            if name.startswith('.trash/'):
                continue
            if content is None:
                sources.pop(name, None)
            else:
                sources[name] = content
        for name, content in sources.items():
            path = stage / 'Gallery' / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        return run_validation(stage)


def publish(changes, dry_run=False, root=ROOT, validate=True):
    if validate:
        stage_validate(changes, root)
    if dry_run:
        return
    # The active catalog is the commit marker and cache revision, always last.
    changes = dict(changes)
    catalog = changes.pop('catalog.json', None)
    if catalog is not None:
        changes['catalog.json'] = catalog
    commit_gallery({root / 'Gallery' / name: data for name, data in changes.items()},
                   root=root, keep_history=False)
    for name in changes:
        path = root / 'Gallery' / name
        if path.suffix == '.py':
            for cache in (path.parent / '__pycache__').glob(path.stem + '.*.pyc'):
                cache.unlink(missing_ok=True)
    # Remove only now-empty directories; never recursively delete a computed path.
    for name, data in changes.items():
        if data is not None:
            continue
        parent = (root / 'Gallery' / name).parent
        while parent != root / 'Gallery':
            try:
                parent.rmdir()
            except OSError:
                break
            parent = parent.parent


def read_state(root=ROOT):
    gal = Gallery(root, check_lock=False)
    return gal, copy.deepcopy(gal.catalog)


def require_symbols(gal, ids):
    ids = list(dict.fromkeys(ids))
    missing = [ident for ident in ids if ident not in gal.symbols]
    if missing:
        raise UserError(f'Unknown symbols: {", ".join(missing)}')
    return ids


def config_bytes(spec):
    config = {key: value for key, value in spec.items() if key not in (*IDENTITY, 'customizable')}
    if config.get('renderer') == spec['id']:
        config.pop('renderer')
    return json_bytes(config)


def move_changes(gal, catalog, ids, category):
    if category not in {row['id'] for row in catalog['categories']}:
        raise UserError(f'Unknown category {category!r}.')
    changes = {}
    for ident in require_symbols(gal, ids):
        spec = gal.symbols[ident]
        if spec['category'] == category:
            continue
        old = f'{spec["category"]}/{ident}'
        for name, content in files_under(gal.symbol_path(ident)).items():
            changes[f'{old}/{name}'] = None
            changes[f'{category}/{ident}/{name}'] = content
        next(row for row in catalog['symbols'] if row['id'] == ident)['category'] = category
    return changes
