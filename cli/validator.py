"""Subprocess validation worker. Timeout isolation is NOT a security sandbox."""
from __future__ import annotations
from contextlib import redirect_stdout, redirect_stderr
import io
import json
import sys
from engine import gallery, render_asset
from .customize import svg_parts


def validate(ids=None):
    gal = gallery()
    ids = ids or list(gal.symbols)
    report = []
    for ident in ids:
        spec = gal.symbols[ident]
        cases = [{}]
        for c in spec.get('controls', []):
            values = [c['min'], c['max']] if c['type'] == 'number' else c['options'] if c['type'] == 'select' else [True, False] if c['type'] == 'boolean' else [c['default'], '<&>']
            cases.extend({c['key']: value} for value in values)
        for bound in ('min', 'max'):
            cases.append({c['key']: c[bound] for c in spec.get('controls', []) if c['type'] == 'number'})
        for params in cases:
            result = render_asset({'type': ident, 'params': params})
            parts = svg_parts(result['svg'])
            if not parts:
                raise ValueError(f'{ident}: use Drawing primitives with stable part IDs; no editable parts found.')
        # Deterministic defaults are required for repeatable CLI and thumbnail output.
        first = render_asset({'type': ident})['svg']
        second = render_asset({'type': ident})['svg']
        if first != second:
            raise ValueError(f'{ident}: default SVG is not deterministic.')
        report.append({'id': ident, 'cases': len(cases), 'parts': len(svg_parts(first))})
    return {'symbols': report, 'symbol_count': len(report), 'case_count': sum(r['cases'] for r in report)}


def main():
    log = io.StringIO()
    try:
        with redirect_stdout(log), redirect_stderr(log):
            data = validate(sys.argv[1:] or None)
        print(json.dumps({'ok': True, 'data': data}))
    except Exception as exc:
        print(json.dumps({'ok': False, 'error': str(exc), 'diagnostics': log.getvalue()[-4000:]}))
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
