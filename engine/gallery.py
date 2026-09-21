"""Validated, file-based gallery. JSON defines the UI; Python modules define geometry.

The catalog locates each symbol's configuration and renderer without a UI switch.
Renderer code is trusted developer code, never code uploaded through the browser.
"""
from __future__ import annotations
import copy
import importlib
import json
import math
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
ID = re.compile(r'^[a-z][a-z0-9_-]{0,79}$')
RESERVED_CATEGORIES = frozenset({'all', 'favorites', 'mine'})
COMMON = {'fill': '#DCEBFF', 'accent': '#2878D4', 'stroke': '#193E5B',
          'highlight': '#FFFFFF', 'stroke_width': 5, 'radius': 7}


def require_id(value, label='ID'):
    if not isinstance(value, str) or not ID.fullmatch(value):
        raise ValueError(f'{label} must start with a lowercase letter and contain only a-z, 0-9, _ or - (max 80).')
    if value.lower() in {'con', 'prn', 'aux', 'nul', *(f'com{i}' for i in range(1,10)), *(f'lpt{i}' for i in range(1,10))}:
        raise ValueError(f'{label}: {value!r} is a reserved filename on Windows.')
    return value


def read_json(path):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f'Cannot load {path.name}: {exc}') from exc


def validate_spec(spec, categories, source='<symbol>'):
    """Fail early, with a file-specific error, instead of producing a broken control."""
    def fail(message):
        raise ValueError(f'{source}: {message}')
    if not isinstance(spec, dict) or spec.get('schema_version') != 1:
        fail('Expected symbol schema_version 1.')
    require_id(spec.get('id'), f'{source}: symbol ID')
    if spec['id'] == 'custom':
        fail('Symbol ID custom is reserved for imported SVG assets.')
    spec = dict(spec)
    spec.setdefault('category', 'uncategorized')
    spec.setdefault('style', 'default')
    spec.setdefault('renderer', spec['id'])
    require_id(spec['renderer'], f'{source}: renderer owner ID')
    if spec.get('category') not in categories:
        fail(f'Unknown category: {spec.get("category")!r}. Add it to Gallery/catalog.json.')
    for key in ('name', 'description', 'style'):
        if not isinstance(spec.get(key), str) or not spec[key].strip():
            fail(f'{key} must be nonempty text.')
    if isinstance(spec.get('version'), bool) or not isinstance(spec.get('version'), int) or spec['version'] < 1:
        fail('version must be a positive integer.')
    if isinstance(spec.get('order', 100), bool) or not isinstance(spec.get('order', 100), int):
        fail('order must be an integer.')
    if not isinstance(spec.get('tags', []), list) or not all(isinstance(x, str) for x in spec.get('tags', [])):
        fail('tags must be a list of strings.')
    if not isinstance(spec.get('defaults', {}), dict) or not isinstance(spec.get('controls', []), list):
        fail('defaults must be an object; controls must be an array.')
    keys = set(COMMON)
    for control in spec.get('controls', []):
        if not isinstance(control, dict):
            fail('Every control must be an object.')
        key = require_id(control.get('key'), f'{source}: control key')
        if key in keys:
            fail(f'Duplicate/reserved control key: {key}.')
        keys.add(key)
        if not isinstance(control.get('label'), str) or 'default' not in control:
            fail(f'{key}: label and default are required.')
        typ = control.get('type')
        if typ == 'number':
            for field in ('min', 'max', 'step', 'default'):
                value = control.get(field, 1 if field == 'step' else None)
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                    fail(f'{key}.{field}: a finite number is required.')
            if not control['min'] <= control['default'] <= control['max'] or control.get('step', 1) <= 0:
                fail(f'{key}: invalid range or step.')
            for value in (control['default'], control['max']):
                ticks = (value - control['min']) / control.get('step', 1)
                if abs(ticks - round(ticks)) > 1e-7:
                    fail(f'{key}: default and maximum must align to the declared step from min.')
        elif typ == 'select':
            options = control.get('options')
            if not isinstance(options, list) or not options or not all(isinstance(v, str) for v in options) or control['default'] not in options:
                fail(f'{key}: options must contain the default value.')
        elif typ == 'boolean':
            if not isinstance(control['default'], bool):
                fail(f'{key}: default must be true or false.')
        elif typ == 'text':
            if not isinstance(control['default'], str) or not 1 <= control.get('max_length', 80) <= 500:
                fail(f'{key}: invalid text default or max_length.')
        else:
            fail(f'{key}: unsupported control type {typ!r}.')
    out = copy.deepcopy(spec)
    out['name'] = out['name'].strip()
    out['style'] = out['style'].strip()
    defaults = dict(COMMON)
    defaults.update({c['key']: c['default'] for c in out.get('controls', [])})
    defaults.update(out.get('defaults', {}))
    unknown = set(defaults) - keys
    if unknown:
        fail(f'Defaults have no corresponding control: {", ".join(sorted(unknown))}.')
    for key in ('fill', 'accent', 'stroke', 'highlight'):
        if not isinstance(defaults[key], str) or not re.fullmatch(r'#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3})?|none', defaults[key]):
            fail(f'{key}: default must be a #RGB/#RRGGBB color or none.')
    for key, hi in [('stroke_width', 20), ('radius', 48)]:
        if isinstance(defaults[key], bool) or not isinstance(defaults[key], (int, float)) or not 0 <= defaults[key] <= hi:
            fail(f'{key}: default must be between 0 and {hi}.')
    for control in out.get('controls', []):
        key = control['key']; value = defaults[key]; typ = control['type']
        if typ == 'number' and (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not control['min'] <= value <= control['max']):
            fail(f'{key}: overridden default is outside the control range.')
        if typ == 'number':
            ticks = (value - control['min']) / control.get('step', 1)
            if abs(ticks - round(ticks)) > 1e-7:
                fail(f'{key}: overridden default must align to the declared step.')
        if typ == 'select' and value not in control['options']:
            fail(f'{key}: overridden default is not a listed option.')
        if typ == 'boolean' and not isinstance(value, bool):
            fail(f'{key}: overridden default must be true or false.')
        if typ == 'text' and (not isinstance(value, str) or len(value) > control.get('max_length', 80)):
            fail(f'{key}: overridden text default is invalid.')
    out['defaults'] = defaults
    out.setdefault('order', 100)
    return out


class GalleryBusy(ValueError):
    """A cooperative source writer is currently active."""


class Gallery:
    def __init__(self, root=ROOT, check_lock=True):
        self.root = Path(root)
        if check_lock and (self.root / 'Gallery/.write.lock').exists():
            raise GalleryBusy('Gallery is being updated. Retry after the writer finishes. See docs/AGENT_GUIDE.md for stale locks.')
        self.settings = read_json(self.root / 'Gallery/settings.json')
        if self.settings.get('schema_version') != 1:
            raise ValueError('Unsupported gallery settings schema_version.')
        self.catalog = read_json(self.root / 'Gallery/catalog.json')
        if not isinstance(self.catalog, dict) or not isinstance(self.catalog.get('categories'), list) or not isinstance(self.catalog.get('symbols'), list):
            raise ValueError('Gallery/catalog.json must contain categories and symbols arrays.')
        rows = self.catalog['categories']
        self.categories = []
        ids = set()
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError('Every category in Gallery/catalog.json must be an object.')
            ident = require_id(row.get('id'), 'Category ID')
            if ident in RESERVED_CATEGORIES or ident == 'common':
                raise ValueError(f'Category ID {ident!r} is reserved for navigation or shared geometry.')
            if ident in ids or not isinstance(row.get('name'), str) or not row['name'].strip():
                raise ValueError(f'Duplicate category ID or invalid category name: {ident}.')
            if isinstance(row.get('order', 100), bool) or not isinstance(row.get('order', 100), int):
                raise ValueError(f'Category {ident}: order must be an integer.')
            for key in ('description', 'icon'):
                if not isinstance(row.get(key, ''), str):
                    raise ValueError(f'Category {ident}: {key} must be text.')
            ids.add(ident)
            self.categories.append(dict(row))
        self.categories.sort(key=lambda c: (c.get('order', 100), c['name']))
        self.palettes = read_json(self.root / 'Gallery/color_sets.json')
        if not isinstance(self.palettes, list):
            raise ValueError('Gallery/color_sets.json must contain an array.')
        palette_ids = set()
        for palette in self.palettes:
            if not isinstance(palette, dict) or not isinstance(palette.get('name'), str) or not palette['name'].strip():
                raise ValueError('Every color set needs a nonempty name.')
            pid = require_id(palette.get('id', palette['name'].lower()), 'Color set ID')
            if pid in palette_ids or pid == 'default':
                raise ValueError(f'Duplicate/reserved color set ID: {pid}.')
            palette_ids.add(pid)
            for key in ('fill', 'accent', 'stroke', 'highlight'):
                if not isinstance(palette.get(key), str) or not re.fullmatch(r'#[0-9a-fA-F]{6}', palette[key]):
                    raise ValueError(f'Color set {pid}: {key} must be #RRGGBB.')
        self.symbols = {}
        self.builders = {}
        names = set()
        for row in self.catalog['symbols']:
            if not isinstance(row, dict) or set(row) - {'id', 'name', 'category', 'style'}:
                raise ValueError('Catalog symbol records contain only id, name, category and style.')
            ident = require_id(row.get('id'), 'Symbol ID')
            category = row.get('category', 'uncategorized')
            if category not in ids:
                raise ValueError(f'{ident}: unknown category {category!r}.')
            path = self.root / 'Gallery' / category / ident / 'symbol.json'
            config = read_json(path)
            if not isinstance(config, dict) or set(config) & {'id', 'name', 'category', 'style'}:
                raise ValueError(f'{path}: identity fields belong only in catalog.json.')
            spec = validate_spec({**config, **row}, ids, str(path))
            if ident in self.symbols or spec['name'].casefold() in names:
                raise ValueError(f'{ident}: duplicate symbol ID or name {spec["name"]!r}.')
            names.add(spec['name'].casefold())
            self.symbols[ident] = spec
        if not self.symbols:
            raise ValueError('The gallery contains no symbols.')
        for ident in self.symbols:
            renderer_path = self.renderer_path(ident)
            if not renderer_path.is_file():
                raise ValueError(f'{ident}: missing renderer {renderer_path}.')

    def symbol_path(self, ident):
        spec = self.symbols[ident]
        return self.root / 'Gallery' / spec['category'] / ident

    def renderer_path(self, ident):
        """Renderer references name an owner, not an arbitrary filesystem path."""
        owner = self.symbols[ident]['renderer']
        if owner not in self.symbols:
            raise ValueError(f'{ident}: unknown renderer owner {owner!r}.')
        if self.symbols[owner]['renderer'] != owner:
            raise ValueError(f'{ident}: renderer {owner!r} must own its render.py.')
        return self.symbol_path(owner) / 'render.py'

    def builder(self, ident):
        """Load trusted geometry only when rendering; listing never executes plugins."""
        if ident not in self.builders:
            renderer = self.symbols[ident]['renderer']
            category = self.symbols[renderer]['category']
            try:
                module = importlib.import_module(f'Gallery.{category}.{renderer}.render')
                fn = getattr(module, 'render')
                if not callable(fn):
                    raise AttributeError('render is not callable')
            except (ImportError, AttributeError) as exc:
                raise ValueError(f'{self.renderer_path(ident)} must export render(drawing, params). {exc}') from exc
            self.builders[ident] = fn
        return self.builders[ident]

    def metadata(self):
        return copy.deepcopy(dict(settings=self.settings, categories=self.categories, palettes=self.palettes,
            symbols=sorted(self.symbols.values(), key=lambda x: (x.get('order', 100), x['id']))))
