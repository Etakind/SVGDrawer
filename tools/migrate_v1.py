#!/usr/bin/env python3
"""Extract reusable symbols from a v1 canvas project into a v2 gallery library.

By default, only the old customLibrary is migrated. --include-canvas also
extracts each canvas node as a separate symbol. Position, outer transforms,
canvas background and layer order are deliberately discarded. The old file
is never modified.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import sys
import uuid
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from engine import gallery
from engine.service import validate_library


def migrate(project, include_canvas=False):
    if not isinstance(project, dict) or project.get('version') != 1:
        raise ValueError('Expected a version 1 SVGDrawer canvas project.')
    source = project.get('customLibrary', [])
    if not isinstance(source, list):
        raise ValueError('customLibrary must be an array.')
    entries = [(entry.get('node', {}), entry.get('name'), entry.get('category', 'My Gallery'), 'preset:'+str(entry.get('id', i))) for i,entry in enumerate(source) if isinstance(entry,dict)]
    if include_canvas:
        nodes = project.get('nodes', [])
        if not isinstance(nodes,list):
            raise ValueError('nodes must be an array.')
        entries += [(node,node.get('name'), 'From previous canvas','node:'+str(node.get('id',i))) for i,node in enumerate(nodes) if isinstance(node,dict)]
    result = dict(format='svgdrawer.library',schema_version=2,categories=[],symbols=[],favorites=[])
    cat_names = {c['name'].lower():c['id'] for c in gallery().categories}
    used_cats = set(cat_names.values())
    for node,name,category,origin in entries:
        category = str(category)[:60].strip() or 'My Gallery'
        key = category.lower()
        if key not in cat_names:
            base = 'legacy-'+(re.sub('[^a-z0-9]+','-',key).strip('-')[:42] or 'category')
            ident = base
            if ident in used_cats:
                ident += '-'+uuid.uuid5(uuid.NAMESPACE_URL,category).hex[:8]
            cat_names[key] = ident;used_cats.add(ident)
            result['categories'].append(dict(id=ident,name=category,description='Migrated from the original canvas editor.'))
        kind=node.get('type')
        if kind not in gallery().symbols and kind!='custom':
            raise ValueError(f'Cannot migrate unknown symbol type: {kind!r}. Restore its renderer before migrating.')
        asset=dict(type=kind,params=node.get('params',{}),parts=node.get('parts',{}))
        if kind=='custom':asset['raw_svg']=node.get('source','')
        ident='legacy-'+uuid.uuid5(uuid.NAMESPACE_URL,origin+':'+str(name)).hex
        result['symbols'].append(dict(id=ident,name=str(name or gallery().symbols.get(kind,{}).get('name','Imported SVG'))[:100],category=cat_names[key],description='Migrated symbol. Outer canvas transforms were discarded.',tags=['migrated'],asset=asset,output=dict(width=512,height=512,padding=8,transparent=True),created_at=''))
    return validate_library(result)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project',type=Path)
    parser.add_argument('--output',type=Path,default=Path('migrated-library.json'))
    parser.add_argument('--include-canvas',action='store_true')
    args=parser.parse_args()
    if args.project.resolve()==args.output.resolve():
        raise SystemExit('The output must not overwrite the original project.')
    try:
        result=migrate(json.loads(args.project.read_text(encoding='utf-8')),args.include_canvas)
        args.output.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
        print(f'Saved {len(result["symbols"])} independent symbols and {len(result["categories"])} categories to {args.output}.')
        print('Open Manage my Gallery > Backup & restore > Import & merge backup.')
        print('The original project was not changed. Canvas positions, sizes, rotation, opacity and layer order were discarded.')
        if not result['symbols']:
            print('No saved presets found. Add --include-canvas to extract individual canvas nodes.')
    except (ValueError,OSError) as exc:
        raise SystemExit(str(exc)) from exc


if __name__=='__main__':main()
