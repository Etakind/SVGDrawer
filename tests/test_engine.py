"""Standard-library tests for gallery integrity, geometry, imports and portable data."""
from __future__ import annotations
import copy
from pathlib import Path
import sys
import unittest
import xml.etree.ElementTree as ET
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine import gallery, handle_request, render_asset
from engine.gallery import validate_spec
from engine.service import normalize_asset
from engine.sanitize import safe_import


class GalleryTests(unittest.TestCase):
    def test_reference_collection_is_preserved(self):
        expected = {'chip','pages','folder','code_page','report','code_stack','sync','database','gear','person','hierarchy','laptop','servers','waveform'}
        self.assertTrue(expected <= set(gallery().symbols))
        self.assertGreaterEqual(len(gallery().symbols), 19)
        self.assertGreaterEqual(len(gallery().categories), 5)

    def test_every_default_is_valid_svg(self):
        for kind in gallery().symbols:
            with self.subTest(kind=kind):
                result = render_asset({'type':kind})
                root = ET.fromstring(result['svg'])
                self.assertEqual(root.attrib['width'], '512')
                self.assertIn('data-part=',result['svg'])
                self.assertEqual(normalize_asset(result['asset']),result['asset'])

    def test_individual_control_extremes(self):
        for kind,spec in gallery().symbols.items():
            for control in spec['controls']:
                values = [control['min'],control['max']] if control['type']=='number' else control['options'] if control['type']=='select' else [False,True] if control['type']=='boolean' else ['< & " \' >']
                for value in values:
                    with self.subTest(kind=kind,key=control['key'],value=value):
                        ET.fromstring(render_asset({'type':kind,'params':{control['key']:value}})['svg'])

    def test_all_numeric_controls_at_extremes(self):
        for kind,spec in gallery().symbols.items():
            for side in ('min','max'):
                params={c['key']:c[side] for c in spec['controls'] if c['type']=='number'}
                result=render_asset({'type':kind,'params':params})
                ET.fromstring(result['svg'])
                self.assertNotIn('nan',result['svg'].lower())
                self.assertNotIn('infinity',result['svg'].lower())

    def test_registry_errors_are_actionable(self):
        cats={c['id'] for c in gallery().categories}
        sample=copy.deepcopy(gallery().symbols['chip'])
        for mutation in [lambda s:s.update(category='missing'), lambda s:s.update(id='custom'), lambda s:s.update(renderer='../secret'),lambda s:s.update(schema_version=99),lambda s:s['controls'].append(copy.deepcopy(s['controls'][0])),lambda s:s['defaults'].update(pins=999),lambda s:s['defaults'].update(fill='url(https://bad.example)')]:
            spec=copy.deepcopy(sample);mutation(spec)
            with self.assertRaises(ValueError):validate_spec(spec,cats,'test.json')

    def test_metadata_returns_an_independent_copy(self):
        meta=gallery().metadata();meta['categories'][0]['name']='CHANGED'
        self.assertNotEqual(gallery().categories[0]['name'],'CHANGED')


class RenderTests(unittest.TestCase):
    def test_pin_count_and_dimensions(self):
        svg=render_asset({'type':'chip','params':{'pins':12,'pin_width':11,'pin_length':28}})['svg']
        root=ET.fromstring(svg);parts=[el for el in root.iter() if el.attrib.get('data-part','').startswith('pin-')]
        self.assertEqual(len(parts),48)
        top=next(el for el in parts if el.attrib['data-part']=='pin-top-1')
        self.assertEqual(top.attrib['width'],'11');self.assertEqual(top.attrib['height'],'33')

    def test_bounds_numbers_and_unknown_ids(self):
        asset=normalize_asset({'type':'chip','params':{'pins':500,'pin_width':float('nan'),'label':'AI\x01'}})
        self.assertEqual(asset['params']['pins'],16);self.assertEqual(asset['params']['pin_width'],7)
        self.assertEqual(asset['params']['label'],'AI')
        with self.assertRaises(ValueError):normalize_asset({'type':'missing'})
        with self.assertRaises(ValueError):handle_request([])

    def test_export_is_clean_and_single_asset(self):
        result=handle_request({'action':'export','asset':{'type':'pages'}})
        self.assertNotIn('data-part',result['svg']);self.assertNotIn('data-label',result['svg'])
        self.assertNotIn('data-node-id',result['svg']);self.assertNotIn('scene',result)
        self.assertNotIn('nodes',result)

    def test_non_square_output_and_background(self):
        result=render_asset({'type':'chip'},dict(width=640,height=320,padding=12,transparent=False,background='#FF0000'))
        root=ET.fromstring(result['svg']);self.assertEqual(root.attrib['viewBox'],'0 0 640 320')
        bg=list(root)[1];self.assertEqual(bg.attrib['fill'],'#FF0000');self.assertEqual(bg.attrib['width'],'640')
        self.assertIn('viewBox="-12 -12 280 280"',result['svg'])
        self.assertIn('preserveAspectRatio="xMidYMid meet"',result['svg'])
        self.assertIn('preserveAspectRatio="none"',render_asset({'type':'chip'},{'preserve_aspect':False})['svg'])

    def test_individual_part_overrides(self):
        asset={'type':'chip','parts':{'pin-top-1':{'fill':'#FF0033','sx':1.5,'sy':.75,'hidden':True}}}
        root=ET.fromstring(render_asset(asset)['svg']);el=next(e for e in root.iter() if e.attrib.get('data-part')=='pin-top-1')
        self.assertEqual(el.attrib['fill'],'#FF0033');self.assertEqual(el.attrib['visibility'],'hidden')
        self.assertIn('scale(1.5 0.75)',el.attrib['transform'])
        self.assertEqual(normalize_asset({'type':'chip','parts':{'x':{'sx':float('inf')}}})['parts']['x']['sx'],1)

    def test_escaping_labels(self):
        result=render_asset({'type':'text','params':{'label':'<script>&"\'ABC'}})
        root=ET.fromstring(result['svg']);self.assertFalse(any(e.tag.endswith('script') for e in root.iter()))
        self.assertIn('&lt;script&gt;',result['svg'])


class ImportTests(unittest.TestCase):
    SAMPLE='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><defs><linearGradient id="g"><stop offset="0" stop-color="#fff"/><stop offset="1" stop-color="#123456"/></linearGradient></defs><rect x="10" y="10" width="80" height="80" fill="url(#g)"/></svg>'

    def test_import_is_canonical_and_repeatable(self):
        first=safe_import(self.SAMPLE,prefix='');second=safe_import(first,prefix='')
        self.assertEqual(first,second)
        asset=handle_request({'action':'import_svg','source':self.SAMPLE})['asset']
        self.assertEqual(asset,normalize_asset(asset,sanitize_source=True))
        self.assertIn('url(#asset-g)',render_asset(asset)['svg'])

    def test_external_resources_and_scripts_are_removed(self):
        source='<svg viewBox="0 0 20 20" onload="alert(1)"><script>alert(1)</script><foreignObject>bad</foreignObject><image href="https://bad.example/a.png"/><rect id="r" width="20" height="20" style="fill:#ff0000;stroke:url(https://bad.example/a)"/><use href="https://bad.example/a.svg#x"/><animate/></svg>'
        svg=safe_import(source,prefix='')
        for value in ['onload','script','foreignObject','https://','animate','<image']:self.assertNotIn(value,svg)
        self.assertIn('fill="#ff0000"',svg)

    def test_entities_and_bad_viewboxes_rejected(self):
        for source in ['<!DOCTYPE svg><svg/>','<!ENTITY x "a"><svg/>','<html/>','<svg viewBox="nan 0 10 10"/>','<svg viewBox="0 0 -1 10"/>','<svg viewBox="0 0 inf 10"/>','not svg']:
            with self.subTest(source=source),self.assertRaises(ValueError):safe_import(source)

    def test_use_cycles_and_expansion_rejected(self):
        source='<svg><defs><g id="a"><use href="#b"/></g><g id="b"><use href="#a"/></g></defs><use href="#a"/></svg>'
        with self.assertRaises(ValueError):safe_import(source)
        source='<svg><defs><g id="a0"><rect width="1" height="1"/></g>'
        for i in range(1,16):source+=f'<g id="a{i}"><use href="#a{i-1}"/><use href="#a{i-1}"/></g>'
        source+='</defs><use href="#a15"/></svg>'
        with self.assertRaises(ValueError):safe_import(source)

    def test_import_limits(self):
        with self.assertRaises(ValueError):safe_import('<svg>'+' '*400000+'</svg>')
        with self.assertRaises(ValueError):safe_import('<svg>'+'<rect/>'*3001+'</svg>')


class RecipeTests(unittest.TestCase):
    def test_recipe_round_trip(self):
        recipe={'format':'svgdrawer.asset','schema_version':1,'name':'My waveform','asset':{'type':'waveform','params':{'cycles':7,'wave_type':'sine'}},'output':{'width':600,'height':300}}
        result=handle_request({'action':'validate_recipe','recipe':recipe})
        self.assertEqual(result,handle_request({'action':'validate_recipe','recipe':result}))
        self.assertEqual(result['asset']['params']['cycles'],7)
        with self.assertRaises(ValueError):handle_request({'action':'validate_recipe','recipe':{'nodes':[],'version':1}})


if __name__=='__main__':unittest.main()
