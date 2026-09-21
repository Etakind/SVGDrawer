"""Small, explicit I/O contracts for humans and automation."""
from __future__ import annotations
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile
import uuid

ROOT = Path(__file__).resolve().parents[1]
VERSION = '3.0.0'


class UserError(Exception):
    def __init__(self, message, code='invalid_input', exit_code=2, **details):
        super().__init__(message)
        self.code, self.exit_code, self.details = code, exit_code, details


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'Duplicate JSON key: {key}')
        result[key] = value
    return result


def json_value(text, label='JSON'):
    try:
        return json.loads(text, object_pairs_hook=_object,
                          parse_constant=lambda x: (_ for _ in ()).throw(ValueError(f'Non-finite JSON value: {x}')))
    except (ValueError, TypeError) as exc:
        raise UserError(f'{label}: {exc}. Use straight JSON quotes, not smart quotes.') from exc


def json_input(value, label='JSON', expected=None):
    """Accept inline JSON or @filename. File mode avoids shell quoting differences."""
    if value is None:
        return None
    if value.startswith('@'):
        path = Path(value[1:]).expanduser()
        if path.stat().st_size > 10_000_000:
            raise UserError(f'{label}: JSON files may not exceed 10 MB.')
        value = path.read_text(encoding='utf-8-sig')
    data = json_value(value, label)
    if expected and not isinstance(data, expected):
        raise UserError(f'{label} must be a JSON {"object" if expected is dict else "array"}.')
    return data


def json_bytes(value):
    return (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode('utf-8')


def preflight(paths, force=False):
    resolved = [p.expanduser().absolute() for p in paths]
    if len({str(p.resolve()) for p in resolved}) != len(resolved):
        raise UserError('Output paths must be distinct; a recipe cannot replace its SVG or PNG.')
    for path in resolved:
        if path.is_symlink():
            raise UserError(f'Refusing to write through a symbolic link: {path}', 'conflict', 3)
        if path.exists() and (not force or not path.is_file()):
            raise UserError(f'Already exists: {path}. Choose another output or explicitly use --force.', 'conflict', 3)
    return resolved


def atomic_write(path, content, overwrite=True):
    """Replace complete files; exclusive creation prevents clobbering other exporters."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not overwrite:
        try:
            with path.open('xb') as out:
                out.write(content)
        except FileExistsError as exc:
            raise UserError(f'Output appeared while writing: {path}', 'conflict', 3) from exc
        except BaseException:
            path.unlink(missing_ok=True)
            raise
        return
    fd, name = tempfile.mkstemp(prefix='.' + path.name + '.', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as out:
            out.write(content)
            out.flush()
            os.fsync(out.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


@contextmanager
def gallery_lock(root=ROOT):
    """Cooperative local writer lock; never removes another writer's lock."""
    path = root / 'Gallery/.write.lock'
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise UserError('Gallery has an active writer lock. Retry later. Do not remove a live process lock.',
                        'gallery_locked', 3, lock=str(path)) from exc
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as out:
            json.dump({'pid': os.getpid(), 'created_at': datetime.now(timezone.utc).isoformat()}, out)
        yield
    finally:
        path.unlink(missing_ok=True)


def commit_gallery(changes, force=False, root=ROOT):
    """Publish a validated change with rollback on Python errors and retained old copies.

    Caller holds the Gallery lock. This is not a crash-proof database transaction.
    Publish the catalog last; None deletes a relocated source file.
    Readers refuse an active writer lock.
    """
    originals = {p: p.read_bytes() if p.exists() else None for p in changes}
    history = None
    existing = {p: b for p, b in originals.items() if b is not None}
    if existing:
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8]
        history = root / 'Gallery/.history' / stamp
        for path, content in existing.items():
            atomic_write(history / path.relative_to(root / 'Gallery'), content)
    written = []
    try:
        for path, content in changes.items():
            if path.is_symlink():
                raise UserError(f'Refusing to replace a symbolic link: {path}', 'conflict', 3)
            if content is None:
                path.unlink(missing_ok=True)
            else:
                atomic_write(path, content)
            written.append(path)
    except BaseException:
        for path in reversed(written):
            old = originals[path]
            if old is None:
                path.unlink(missing_ok=True)
            else:
                atomic_write(path, old)
        raise
    return str(history) if history else None
