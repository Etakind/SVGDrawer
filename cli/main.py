"""SVGDrawer: browse a Gallery, customize one SVG, or register trusted Python geometry."""
from __future__ import annotations
import argparse
from contextlib import redirect_stdout, redirect_stderr
import io
import json
import math
from pathlib import Path
import sys
import traceback
from engine import gallery, handle_request, render_asset
from engine.gallery import COMMON, GalleryBusy
from engine.service import RECIPE_FORMAT, normalize_options
from .common import (ROOT, VERSION, UserError, json_input, json_bytes, preflight, atomic_write)
from .customize import (COMMON_CONTROLS, COLOR_ROLES, overrides, svg_parts, validate_parts,
                        check_svg, hex_color)
from .manage import add_category, add_symbol, scaffold, run_validation

ACTIONS = ('list', 'list_all_flat', 'list_category', 'list_color_sets', 'describe', 'list_parts',
           'create', 'add_category', 'add_symbol', 'init_symbol', 'validate', 'serve', 'version',
           'import_svg', 'save_symbol', 'update_symbol', 'move_symbol', 'update_category', 'delete_category',
           'delete_symbol', 'list_trash', 'restore', 'purge', 'empty_trash', 'backup_gallery', 'import_gallery')


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise UserError(message, 'argument_error')


def parser():
    p = Parser(prog='svgdrawer', description=__doc__, allow_abbrev=False,
               formatter_class=argparse.RawDescriptionHelpFormatter,
               epilog='Examples:\n'
               '  python svgdrawer.py --list-all-flat --json\n'
               '  python svgdrawer.py --create chip --color-sets default --set pins=10\n'
               '  python svgdrawer.py --create chip --color-sets \'["012345","427abc"]\'\n'
               '  python svgdrawer.py --add-symbol sensor --script drafts/sensor.py --spec drafts/sensor.json\n'
               'Guide: docs/AGENT_GUIDE.md. Project instructions for agents: AGENTS.md.\n'
               'SVG needs only Python 3.10+. Terminal PNG additionally needs CairoSVG + Cairo.\n'
               'Python scripts are trusted code; registration and rendering are not sandboxed.')
    actions = p.add_mutually_exclusive_group()
    actions.add_argument('--list', action='store_true', help='List the Gallery grouped by category.')
    actions.add_argument('--list-all-flat', action='store_true', help='List all symbols in one flat table or JSON array field.')
    actions.add_argument('--list-category', nargs='?', const='*', metavar='CATEGORY',
                         help='No ID: list categories. With an ID: list that category’s symbols.')
    actions.add_argument('--list-color-sets', action='store_true', help='List default and named color sets.')
    actions.add_argument('--describe', metavar='ID', help='Read defaults and control schema without executing renderers.')
    actions.add_argument('--list-parts', metavar='ID', help='Render and list stable inner-part IDs; accepts --set/--params.')
    actions.add_argument('--create', metavar='ID', help='Customize and export a registered Gallery symbol.')
    p.add_argument('--recipe', type=Path, metavar='FILE', help='Export from a saved .asset.json recipe.')
    actions.add_argument('--add-category', metavar='ID', help='Add a persistent source category to Gallery/catalog.json.')
    actions.add_argument('--add-symbol', metavar='ID', help='Validate and register a Python script/specification in Gallery/.')
    actions.add_argument('--init-symbol', metavar='ID', help='Generate editable Python + JSON templates under drafts/.')
    actions.add_argument('--validate', nargs='?', const='*', metavar='ID', help='Validate all symbols, or one ID; no persistent source changes.')
    actions.add_argument('--serve', action='store_true', help='Open the local Python Gallery server.')
    actions.add_argument('--version', action='store_true', help='Print SVGDrawer version.')
    for flag in ('import-svg', 'save-symbol', 'update-symbol', 'update-category', 'delete-category', 'import-gallery'):
        actions.add_argument('--' + flag, metavar='ID_OR_FILE')
    for flag in ('move-symbol', 'delete-symbol', 'restore', 'purge'):
        actions.add_argument('--' + flag, nargs='+', metavar='ID')
    for flag in ('list-trash', 'empty-trash', 'backup-gallery'):
        actions.add_argument('--' + flag, action='store_true')
    browsing = p.add_argument_group('Discovery')
    browsing.add_argument('--search', help='Filter list results by ID, name, style, description or tags.')
    custom = p.add_argument_group('Customization and export')
    custom.add_argument('--color-sets', metavar='NAME_OR_JSON', help='default, a named set, or 1–4 hex colors in fill/accent/stroke/highlight order.')
    custom.add_argument('--params', metavar='JSON_OR_@FILE', help='JSON parameter overrides, inline or @filename.')
    custom.add_argument('--set', dest='set_values', action='append', default=[], metavar='KEY=VALUE', help='Repeatable parameter override; takes precedence over --params.')
    custom.add_argument('--parts', metavar='JSON_OR_@FILE', help='Replace part overrides with a JSON object keyed by part ID.')
    custom.add_argument('--output', '-o', help='Output path. Default: exports/ID.svg. Use - for SVG on stdout.')
    custom.add_argument('--format', choices=('svg', 'png', 'both'), help='Infer from suffix by default. PNG always saves an SVG sidecar first.')
    custom.add_argument('--width', type=int, help='SVG width in pixels, 16–4096 (default 512).')
    custom.add_argument('--height', type=int, help='SVG height in pixels, 16–4096 (default 512).')
    custom.add_argument('--size', type=int, help='Set both width and height; --width/--height take precedence.')
    custom.add_argument('--padding', type=float, help='Padding around the 256-unit design, 0–96 (default 8).')
    custom.add_argument('--scale', type=int, choices=(1, 2, 4), default=1, help='PNG pixel scale only (default 1).')
    bg = custom.add_mutually_exclusive_group()
    bg.add_argument('--background', metavar='HEX', help='Opaque export background; hex with or without #.')
    bg.add_argument('--transparent', action='store_true', help='Export without background (default for --create).')
    custom.add_argument('--stretch', action='store_true', help='Stretch SVG to a non-square size; otherwise preserve aspect ratio.')
    custom.add_argument('--save-recipe', type=Path, metavar='FILE', help='Save the resolved, repeatable .asset.json customization.')
    manage = p.add_argument_group('Gallery source management')
    manage.add_argument('--script', type=Path, metavar='FILE.py', help='Trusted Python file defining render(drawing, params).')
    manage.add_argument('--spec', type=Path, metavar='FILE.json', help='Symbol definition with defaults and UI controls.')
    manage.add_argument('--category', metavar='ID', help='Category ID for a symbol/template.')
    manage.add_argument('--name', help='Human-readable symbol/category name; IDs remain stable.')
    manage.add_argument('--description', help='Symbol/category description.')
    manage.add_argument('--tags', help='Comma-separated symbol search tags.')
    manage.add_argument('--order', type=int, help='Display order in the Gallery.')
    manage.add_argument('--icon', help='Category icon key (folder, chip, file, network, wave, shapes).')
    manage.add_argument('--output-dir', default='drafts', help='Folder for --init-symbol templates (default drafts).')
    favorites = manage.add_mutually_exclusive_group()
    favorites.add_argument('--favorite', action='store_true')
    favorites.add_argument('--unfavorite', action='store_true')
    manage.add_argument('--id', help='Stable ID for an imported SVG.')
    manage.add_argument('--style', help='Descriptive style, default for new symbols.')
    manage.add_argument('--contents', choices=('uncategorized', 'trash'))
    manage.add_argument('--yes', action='store_true', help='Confirm permanent removal or full Gallery replacement.')
    manage.add_argument('--force-sync', action='store_true', help='Replace the active Gallery from a ZIP, retaining a trash snapshot.')
    common = p.add_argument_group('Automation and safety')
    common.add_argument('--json', action='store_true', help='One versioned JSON success on stdout; errors on stderr; no prompts.')
    common.add_argument('--dry-run', action='store_true', help='Validate and report a write without publishing files.')
    common.add_argument('--force', action='store_true', help='Explicitly allow replacement. Source updates retain history backups.')
    common.add_argument('--timeout', type=int, default=30, help='Validation subprocess timeout, 1–300 seconds (default 30).')
    common.add_argument('--debug', action='store_true', help='Include diagnostic traceback on stderr for unexpected failures.')
    common.add_argument('--port', type=int, default=9178, help='Local --serve port (default 9178).')
    common.add_argument('--no-browser', action='store_true', help='Do not launch a browser with --serve.')
    return p


def _action(args):
    return next((k for k in ACTIONS if getattr(args, k) not in (None, False)), 'recipe' if args.recipe else None)


def check_flags(p, args, argv, action):
    export_flags = {'color_sets', 'params', 'set_values', 'parts', 'output', 'format', 'width', 'height', 'size',
                    'padding', 'scale', 'background', 'transparent', 'stretch', 'save_recipe', 'dry_run', 'force'}
    allowed = {
        'list': {'search'}, 'list_all_flat': {'search'}, 'list_category': {'search'}, 'list_color_sets': set(),
        'describe': set(), 'list_parts': {'color_sets', 'params', 'set_values'}, 'create': export_flags, 'recipe': export_flags,
        'add_category': {'name', 'description', 'order', 'icon', 'force', 'dry_run'},
        'add_symbol': {'script', 'spec', 'category', 'name', 'description', 'tags', 'order', 'force', 'dry_run'},
        'init_symbol': {'output_dir', 'category', 'name', 'description', 'force', 'dry_run'},
        'import_svg': {'id', 'name', 'description', 'tags', 'style', 'category', 'dry_run'},
        'save_symbol': {'recipe', 'name', 'description', 'tags', 'style', 'category', 'dry_run'},
        'update_symbol': {'name', 'description', 'tags', 'style', 'favorite', 'unfavorite', 'dry_run'},
        'move_symbol': {'category', 'dry_run'},
        'update_category': {'name', 'description', 'icon', 'order', 'dry_run'},
        'delete_category': {'contents', 'dry_run'}, 'delete_symbol': {'dry_run'},
        'list_trash': set(), 'restore': {'yes', 'dry_run'}, 'purge': {'yes', 'dry_run'},
        'empty_trash': {'yes', 'dry_run'}, 'backup_gallery': {'output', 'force', 'dry_run'},
        'import_gallery': {'force_sync', 'yes', 'dry_run'},
        'validate': set(), 'serve': {'port', 'no_browser'}, 'version': set(),
    }[action] | {'json', 'debug', 'timeout', action}
    for token in argv:
        flag = token.split('=', 1)[0]
        entry = p._option_string_actions.get(flag)
        if entry and entry.dest not in allowed and entry.dest != 'help':
            raise UserError(f'{flag} is not used with --{action.replace("_", "-")}.')
    if not 1 <= args.timeout <= 300:
        raise UserError('--timeout must be 1–300 seconds.')
    if args.output == '-' and (args.json or args.dry_run or args.format not in (None, 'svg') or args.save_recipe):
        raise UserError('--output - is for raw SVG stdout only; do not combine with --json, --dry-run, PNG, or --save-recipe.')
    if action == 'serve' and args.json:
        raise UserError('--serve is a long-running service and does not support --json.')


def _spec(gal, ident):
    if not isinstance(ident, str) or ident not in gal.symbols:
        raise UserError(f'Unknown symbol ID {ident!r}. Run --list-all-flat. IDs are case-sensitive.')
    return gal.symbols[ident]


def _items(gal, search=None, category=None):
    items = sorted(gal.symbols.values(), key=lambda e: (e.get('order', 100), e['id']))
    if category is not None:
        if category not in {c['id'] for c in gal.categories}:
            raise UserError(f'Unknown category ID {category!r}. Run --list-category.')
        items = [e for e in items if e['category'] == category]
    if search:
        q = search.casefold()
        items = [e for e in items if q in ' '.join([e['id'], e['name'], e['style'], e['description'], *e['tags']]).casefold()]
    return [{'id': e['id'], 'name': e['name'], 'category': e['category'], 'description': e['description'],
             'style': e['style'], 'kind': e['kind'], 'customizable': e['customizable'], 'favorite': e.get('favorite', False), 'tags': e['tags'], 'version': e['version']} for e in items]


def _options(args, base=None):
    if base is not None and not isinstance(base, dict):
        raise UserError('Recipe output must be a JSON object.')
    result = dict(base or {})
    allowed = {'width', 'height', 'padding', 'transparent', 'background', 'preserve_aspect'}
    if set(result) - allowed:
        raise UserError('Unknown recipe output settings: ' + ', '.join(sorted(set(result) - allowed)))
    if args.size is not None:
        result.update(width=args.size, height=args.size)
    for key in ('width', 'height', 'padding'):
        if getattr(args, key) is not None:
            result[key] = getattr(args, key)
    if args.background:
        result.update(transparent=False, background=hex_color(args.background, none=False))
    if args.transparent:
        result['transparent'] = True
    if args.stretch:
        result['preserve_aspect'] = False
    for key in ('width', 'height'):
        if key in result and (isinstance(result[key], bool) or not isinstance(result[key], int) or not 16 <= result[key] <= 4096):
            raise UserError(f'{key} must be an integer from 16 to 4096 pixels.')
    padding = result.get('padding', 8)
    if isinstance(padding, bool) or not isinstance(padding, (int, float)) or not math.isfinite(padding) or not 0 <= padding <= 96:
        raise UserError('padding must be a finite number from 0 to 96 design units.')
    for key in ('transparent', 'preserve_aspect'):
        if key in result and not isinstance(result[key], bool):
            raise UserError(f'{key} must be true or false.')
    if 'background' in result:
        result['background'] = hex_color(result['background'])
    return normalize_options(result)


def prepare(args, gal, ident=None):
    recipe = None
    if args.recipe:
        recipe = json_input('@' + str(args.recipe), 'recipe', dict)
        if recipe.get('format') not in (RECIPE_FORMAT, 'vector-foundry.asset') or recipe.get('schema_version') != 1:
            raise UserError('Recipe must use format svgdrawer.asset (or vector-foundry.asset), schema_version 1.')
        asset = recipe.get('asset', {})
        if not isinstance(asset, dict):
            raise UserError('Recipe asset must be a JSON object.')
        ident = asset.get('type')
    else:
        ident = ident or args.create
        asset = {'type': ident}
    spec = _spec(gal, ident) if ident != 'custom' else {'id': 'custom', 'name': 'Custom SVG', 'defaults': COMMON, 'controls': []}
    base_params = asset.get('params', {})
    if not isinstance(base_params, dict):
        raise UserError('Recipe params must be a JSON object.')
    asset['params'] = overrides(args, spec, gal, base_params)
    part_values = json_input(args.parts, '--parts', dict) if args.parts is not None else asset.get('parts', spec.get('parts', {}))
    asset['parts'] = {}
    options = _options(args, recipe.get('output', {}) if recipe else spec.get('output', {}))
    result = render_asset(asset, options)
    available = svg_parts(result['svg'])
    asset = result['asset']
    asset['parts'] = validate_parts(part_values, available)
    return asset, options, spec, available


def create(args, gal):
    asset, options, spec, available = prepare(args, gal)
    result = render_asset(asset, options, clean=True)
    check_svg(result['svg'])
    if args.output == '-':
        return {'_raw_svg': result['svg']}
    ident = spec['id']
    out = Path(args.output).expanduser() if args.output else Path('exports') / (ident + ('.png' if args.format == 'png' else '.svg'))
    suffix = out.suffix.lower()
    fmt = args.format or ('png' if suffix == '.png' else 'svg')
    if suffix and suffix not in ('.svg', '.png'):
        raise UserError('Output must have .svg or .png extension, or no extension.')
    if suffix and fmt != 'both' and suffix != '.' + fmt:
        raise UserError('--format and --output extension disagree.')
    if fmt == 'svg' and args.scale != 1:
        raise UserError('--scale applies to PNG only; use --width/--height for SVG dimensions.')
    svg_path = out.with_suffix('.svg')
    png_path = out.with_suffix('.png') if fmt in ('png', 'both') else None
    targets = [svg_path] + ([png_path] if png_path else []) + ([args.save_recipe] if args.save_recipe else [])
    targets = preflight(targets, args.force)
    svg_path = targets[0]
    if png_path:
        png_path = targets[1]
    width, height = result['width'] * args.scale, result['height'] * args.scale
    if png_path and (max(width, height) > 8192 or width * height > 50_000_000):
        raise UserError('PNG limit: 8192 pixels per side and 50 megapixels. Reduce size or scale.')
    data = {'id': ident, 'params': asset['params'], 'parts': asset['parts'], 'output': options,
            'format': fmt, 'files': [str(p) for p in targets], 'dry_run': args.dry_run}
    if png_path:
        data['png'] = {'width': width, 'height': height, 'scale': args.scale, 'renderer': 'CairoSVG'}
    recipe = {'format': RECIPE_FORMAT, 'schema_version': 1, 'name': spec['name'], 'asset': asset, 'output': options}
    if not args.dry_run:
        # The Python-produced SVG is published FIRST. PNG is derived from these exact bytes.
        svg_bytes = result['svg'].encode('utf-8')
        atomic_write(svg_path, svg_bytes, overwrite=args.force)
        if args.save_recipe:
            atomic_write(targets[-1], json_bytes(recipe), overwrite=args.force)
        if png_path:
            try:
                from engine.png import svg_to_png
                png = svg_to_png(svg_bytes, width, height)
            except (ImportError, OSError) as exc:
                raise UserError(f'SVG saved. Terminal PNG needs CairoSVG and the Cairo runtime: {exc}. '
                                'Use conda env update --prefix ./.conda --file environment.yml; see docs/AGENT_GUIDE.md.',
                                'png_dependency', 5, svg_saved=str(svg_path)) from exc
            except Exception as exc:
                raise UserError(f'SVG saved, but PNG conversion failed: {exc}', 'png_failed', 5,
                                svg_saved=str(svg_path)) from exc
            atomic_write(png_path, png, overwrite=args.force)
    return data


def dispatch(args, action):
    if action == 'version':
        return {'name': 'SVGDrawer', 'version': VERSION}
    if action == 'add_category':
        return add_category(args)
    if action == 'add_symbol':
        return add_symbol(args)
    if action == 'init_symbol':
        return scaffold(args)
    from . import operations, trash, archives
    metadata = {key: getattr(args, key) for key in ('name', 'description', 'tags', 'style', 'category') if getattr(args, key) is not None}
    if 'tags' in metadata:
        metadata['tags'] = [t.strip() for t in metadata['tags'].split(',') if t.strip()]
    if action == 'import_svg':
        if not args.id:
            raise UserError('--import-svg requires --id.')
        return operations.install_symbol(args.id, metadata, source=Path(args.import_svg).read_text(encoding='utf-8'), dry_run=args.dry_run)
    if action == 'save_symbol':
        if not args.recipe:
            raise UserError('--save-symbol requires --recipe.')
        return operations.install_symbol(args.save_symbol, metadata, recipe=json_input('@' + str(args.recipe), 'recipe', dict), dry_run=args.dry_run)
    if action == 'update_symbol':
        if args.favorite or args.unfavorite:
            metadata['favorite'] = args.favorite
        return operations.update_symbol(args.update_symbol, metadata, args.dry_run)
    if action == 'move_symbol':
        return operations.move_symbols(args.move_symbol, args.category, args.dry_run)
    if action == 'update_category':
        values = {k: getattr(args, k) for k in ('name', 'description', 'order', 'icon') if getattr(args, k) is not None}
        return operations.update_category(args.update_category, values, args.dry_run)
    if action == 'delete_category':
        return trash.delete_category(args.delete_category, args.contents, args.dry_run)
    if action == 'delete_symbol':
        return trash.delete_symbols(args.delete_symbol, args.dry_run)
    if action == 'list_trash':
        return trash.list_trash()
    if action == 'restore':
        return trash.restore(args.restore, args.yes, args.dry_run)
    if action in ('purge', 'empty_trash'):
        return trash.purge(args.purge if action == 'purge' else None, args.yes, args.dry_run)
    if action == 'backup_gallery':
        if not args.output:
            raise UserError('--backup-gallery requires --output FILE.zip.')
        return archives.backup(Path(args.output), args.force, args.dry_run)
    if action == 'import_gallery':
        return archives.import_archive(Path(args.import_gallery).read_bytes(), args.force_sync, args.yes, args.dry_run)
    gal = gallery()
    if action == 'list':
        items = _items(gal, args.search)
        categories = [{**c, 'symbols': [e for e in items if e['category'] == c['id']]} for c in gal.categories]
        return {'gallery': 'Gallery', 'categories': categories, 'symbol_count': len(items)}
    if action == 'list_all_flat':
        items = sorted(_items(gal, args.search), key=lambda e: e['id'])
        return {'symbols': items, 'symbol_count': len(items)}
    if action == 'list_category':
        if args.list_category == '*':
            rows = [{**c, 'symbol_count': sum(e['category'] == c['id'] for e in gal.symbols.values())} for c in gal.categories]
            if args.search:
                rows = [c for c in rows if args.search.casefold() in (c['id'] + ' ' + c['name']).casefold()]
            return {'categories': rows, 'category_count': len(rows)}
        items = _items(gal, args.search, args.list_category)
        return {'category': args.list_category, 'symbols': items, 'symbol_count': len(items)}
    if action == 'list_color_sets':
        return {'roles': list(COLOR_ROLES), 'color_sets': [{'id': 'default', 'name': 'Default',
                'description': 'Use the selected symbol’s original colors.'},
                *[dict(p, id=p.get('id', p['name'].lower())) for p in gal.palettes]],
                'array_rule': '1–4 hex strings map to fill, accent, stroke, highlight; omitted roles retain current defaults/recipe values.'}
    if action == 'describe':
        spec = _spec(gal, args.describe)
        return {'symbol': spec, 'common_controls': [{**c, 'default': spec['defaults'][c['key']]} for c in COMMON_CONTROLS],
                'source': {'definition': (gal.symbol_path(spec['id']) / 'symbol.json').relative_to(gal.root).as_posix(),
                           'renderer': ((gal.symbol_path(spec['id']) / 'source.svg') if spec['kind'] == 'svg' else gal.renderer_path(spec['id'])).relative_to(gal.root).as_posix()},
                'design_size': 256, 'parts_command': f'python svgdrawer.py --list-parts {spec["id"]} --json'}
    if action == 'list_parts':
        _, _, _, parts = prepare(args, gal, args.list_parts)
        return {'id': args.list_parts, 'parts': parts, 'part_count': len(parts)}
    if action in ('create', 'recipe'):
        return create(args, gal)
    if action == 'validate':
        if args.validate != '*':
            _spec(gal, args.validate)
        return run_validation(ids=None if args.validate == '*' else [args.validate], timeout=args.timeout)
    raise UserError(f'Unknown action: {action}')


def human(action, data):
    if action == 'version':
        return 'SVGDrawer ' + VERSION
    if action == 'list':
        lines = ['SVGDrawer / Gallery']
        for c in data['categories']:
            lines.append(f'\n{c["name"]} [{c["id"]}] — {len(c["symbols"])} symbols')
            lines.extend(f'  {e["id"]:<20} {e["name"]}' for e in c['symbols'])
        return '\n'.join(lines)
    if action == 'list_category' and 'categories' in data:
        return '\n'.join(f'{c["id"]:<20} {c["symbol_count"]:>3}  {c["name"]}' for c in data['categories'])
    if action in ('list_all_flat', 'list_category'):
        return '\n'.join(['ID                   CATEGORY             NAME',
                          *[f'{e["id"]:<20} {e["category"]:<20} {e["name"]}' for e in data['symbols']]])
    if action == 'list_color_sets':
        return '\n'.join(f'{p["id"]:<12} ' + ('Original symbol colors' if p['id'] == 'default' else '  '.join(p[k] for k in COLOR_ROLES)) for p in data['color_sets']) + '\nArray order: fill, accent, stroke, highlight.'
    if action == 'describe':
        spec = data['symbol']
        lines = [f'{spec["name"]} [{spec["id"]}] / {spec["category"]} / {spec["style"]}', spec['description'], '', 'Parameters:']
        for c in data['common_controls'] + spec['controls']:
            rule = f'{c["min"]}..{c["max"]}' if c['type'] == 'number' else str(c.get('options', c['type']))
            lines.append(f'  {c["key"]:<22} default={str(spec["defaults"][c["key"]]):<14} {rule}')
        lines.extend(['', 'Use --json for the complete control schema.', data['parts_command']])
        return '\n'.join(lines)
    if action == 'list_parts':
        return '\n'.join(f'{p["id"]:<30} {p["shape"]:<10} {p["label"]}' for p in data['parts'])
    if action == 'validate':
        return f'Validated {data["symbol_count"]} symbols, {data["case_count"]} geometry cases; deterministic default output checked.'
    lines = []
    if data.get('dry_run'):
        lines.append('Dry run: no output or Gallery source files published.')
    for file in data.get('files', [data['file']] if 'file' in data else []):
        lines.append(('Would write ' if data.get('dry_run') else 'Saved ') + file)
    if data.get('backup'):
        lines.append('Previous source retained in ' + data['backup'])
    if data.get('next'):
        lines.append('Next: ' + data['next'])
    return '\n'.join(lines) or json.dumps(data, indent=2)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    json_mode = '--json' in argv
    debug = '--debug' in argv
    log = io.StringIO()
    try:
        p = parser()
        args = p.parse_args(argv)
        action = _action(args)
        if action is None:
            if argv:
                raise UserError('Choose an action such as --list, --create ID, or --add-symbol ID.')
            p.print_help()
            return 0
        check_flags(p, args, argv, action)
        if action == 'serve':
            from server import main as serve
            sys.argv = ['server.py', '--port', str(args.port)] + (['--no-browser'] if args.no_browser else [])
            serve()
            return 0
        # Plugin prints must never corrupt structured machine results or raw SVG output.
        with redirect_stdout(log), redirect_stderr(log):
            data = dispatch(args, action)
        if '_raw_svg' in data:
            print(data['_raw_svg'])
        elif json_mode:
            print(json.dumps({'schema_version': 2, 'ok': True, 'action': action.replace('_', '-'), 'data': data},
                             ensure_ascii=False, allow_nan=False))
        else:
            print(human(action, data))
        return 0
    except GalleryBusy as exc:
        error = UserError(str(exc), 'gallery_locked', 3)
    except (UserError, ValueError, OSError) as exc:
        error = exc if isinstance(exc, UserError) else UserError(str(exc), 'io_error' if isinstance(exc, OSError) else 'invalid_input', 6 if isinstance(exc, OSError) else 2)
    except KeyboardInterrupt:
        error = UserError('Interrupted.', 'interrupted', 130)
    except Exception as exc:
        if debug:
            traceback.print_exc(file=sys.stderr)
        error = UserError(f'{type(exc).__name__}: {exc}', 'render_failed', 4)
    details = dict(error.details)
    if log.getvalue():
        details['diagnostics'] = log.getvalue()[-4000:]
    if json_mode:
        print(json.dumps({'schema_version': 2, 'ok': False,
                          'error': {'code': error.code, 'message': str(error), 'details': details}}, ensure_ascii=False), file=sys.stderr)
    else:
        print(f'SVGDrawer: {error}', file=sys.stderr)
    return error.exit_code


if __name__ == '__main__':
    raise SystemExit(main())
