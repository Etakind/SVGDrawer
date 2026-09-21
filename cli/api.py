"""HTTP adapter for the same noninteractive commands used by agents."""
import base64
import json
from pathlib import Path
import tempfile

from .main import parser, check_flags, dispatch
from .common import UserError


def manage(payload):
    if not isinstance(payload, dict):
        raise UserError('Expected a JSON object.')
    action = payload.get('action')
    singles = {'add-symbol', 'save-symbol', 'update-symbol', 'add-category', 'update-category', 'delete-category'}
    batches = {'move-symbol', 'delete-symbol', 'restore', 'purge'}
    allowed = singles | batches | {'import-svg', 'import-gallery', 'empty-trash', 'list-trash'}
    if action not in allowed:
        raise UserError('Unknown management action.')
    with tempfile.TemporaryDirectory(prefix='svgdrawer-upload-') as temporary:
        folder = Path(temporary)
        argv = ['--' + action]
        if action in singles:
            argv.append(str(payload.get('id', '')))
        elif action in batches:
            ids = payload.get('ids', [])
            if not isinstance(ids, list) or not ids:
                raise UserError('Select at least one ID.')
            argv.extend(str(ident) for ident in ids)
        for key, extension in (('svg', '.svg'), ('archive', '.zip'), ('script', '.py'), ('spec', '.json'), ('recipe', '.json')):
            if key not in payload:
                continue
            value = payload[key]
            path = folder / ('upload' + extension if key not in ('spec', 'recipe') else key + extension)
            data = base64.b64decode(value, validate=True) if key == 'archive' else (json.dumps(value) if isinstance(value, dict) else str(value)).encode('utf-8')
            path.write_bytes(data)
            if key in ('svg', 'archive'):
                argv.append(str(path))
            else:
                argv.extend(['--' + key, str(path)])
        if action == 'import-svg':
            argv.extend(['--id', str(payload.get('id', ''))])
        for key in ('name', 'description', 'tags', 'style', 'category', 'contents', 'order', 'icon'):
            if key in payload:
                value = payload[key]
                if key == 'tags' and isinstance(value, list):
                    value = ','.join(value)
                argv.extend(['--' + key, str(value)])
        if 'favorite' in payload:
            argv.append('--favorite' if payload['favorite'] else '--unfavorite')
        for key in ('dry_run', 'force_sync', 'yes', 'force'):
            if payload.get(key) is True:
                argv.append('--' + key.replace('_', '-'))
        p = parser()
        args = p.parse_args(argv)
        command = action.replace('-', '_')
        check_flags(p, args, argv, command)
        return {'schema_version': 2, 'ok': True, 'action': action, 'data': dispatch(args, command)}
