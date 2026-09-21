"""CLI and source-maintenance integration tests. Temporary projects only; never alter shipped Gallery."""
from __future__ import annotations
import copy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


class CLITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='svgdrawer-test-')
        self.work = Path(self.temp.name)
        self.project = self.work / 'SVGDrawer'
        shutil.copytree(ROOT, self.project, ignore=shutil.ignore_patterns('__pycache__', '.history', 'tests', 'docs', 'index.html', 'exports'))

    def tearDown(self):
        self.temp.cleanup()

    def run_cli(self, *args, code=0, json_mode=True, env=None):
        command = [sys.executable, '-B', str(self.project / 'svgdrawer.py'), *map(str, args)]
        if json_mode:
            command.append('--json')
        result = subprocess.run(command, cwd=self.work, capture_output=True, text=True, timeout=45, env=env)
        self.assertEqual(result.returncode, code, (command, result.stdout, result.stderr))
        if not json_mode:
            return result
        if code:
            self.assertEqual(result.stdout, '')
            data = json.loads(result.stderr)
            self.assertFalse(data['ok'])
            return data['error']
        self.assertEqual(result.stderr, '')
        data = json.loads(result.stdout)
        self.assertTrue(data['ok'])
        self.assertEqual(data['schema_version'], 2)
        return data['data']

    def gallery_files(self):
        return {p.relative_to(self.project).as_posix(): p.read_bytes() for p in (self.project/'Gallery').rglob('*') if p.is_file()}

    def scaffold(self, ident='sensor'):
        self.run_cli('--init-symbol', ident, '--category', 'instruments')
        return self.work/'drafts'/f'{ident}.py', self.work/'drafts'/f'{ident}.json'

    def install_sensor(self):
        self.run_cli('--add-category', 'instruments', '--name', 'Instruments')
        script, spec = self.scaffold()
        return self.run_cli('--add-symbol', 'sensor', '--script', script, '--spec', spec)

    def test_lists_and_category_filters(self):
        flat = self.run_cli('--list-all-flat')
        self.assertEqual(flat['symbol_count'], 33)
        self.assertEqual([x['id'] for x in flat['symbols']], sorted(x['id'] for x in flat['symbols']))
        self.assertEqual(self.run_cli('--list')['symbol_count'], 33)
        self.assertEqual(self.run_cli('--list-category')['category_count'], 6)
        self.assertEqual(self.run_cli('--list-category', 'hardware')['symbol_count'], 3)
        self.assertEqual(self.run_cli('--list-all-flat', '--search', 'CPU')['symbols'][0]['id'], 'chip')
        self.run_cli('--list-category', 'missing', code=2)

    def test_no_canvas_and_renamed_source_layout(self):
        self.assertTrue((self.project/'Gallery/hardware/chip/render.py').exists())
        self.assertFalse((self.project/'Gallery/elements').exists())
        self.assertFalse((self.project/'Gallery/renderers').exists())
        self.assertFalse((self.project/'Gallery/categories.json').exists())
        data = self.run_cli('--build')
        html = Path(data['file']).read_text()
        self.assertIn('<title>SVGDrawer — Gallery</title>', html)
        self.assertIn('>Gallery <span', html)
        self.assertNotIn('Vector Foundry', html)
        self.assertNotIn('<canvas', html)

    def test_describe_machine_schema(self):
        spec = self.run_cli('--describe', 'chip')
        self.assertEqual(spec['symbol']['defaults']['pins'], 6)
        self.assertEqual(spec['source']['renderer'], 'Gallery/hardware/chip/render.py')
        self.assertIn('fill', [c['key'] for c in spec['common_controls']])
        self.run_cli('--describe', 'unknown', code=2)

    def test_metadata_does_not_execute_renderers(self):
        p = self.project/'Gallery/hardware/chip/render.py'
        p.write_text('raise RuntimeError("must not run on discovery")\n')
        self.run_cli('--list-all-flat')
        self.run_cli('--describe', 'chip')
        err = self.run_cli('--create', 'chip', code=4)
        self.assertIn('must not run', err['message'])
        self.run_cli('--create', 'folder')  # Unrelated broken renderer is not imported.

    def test_missing_or_irrelevant_options_are_errors(self):
        for args in [('--list', '--set', 'pins=3'), ('--create',), ('--list-all-flat','--create','chip'), ('--liss',), ('--json',), ('--create','chip','--color-set','ocean')]:
            with self.subTest(args=args):
                self.run_cli(*args, code=2)

    def test_colors_default_named_and_arrays(self):
        defaults = self.run_cli('--create','chip','--color-sets','default','--dry-run')['params']
        self.assertEqual(defaults['fill'], '#2878D4')
        ocean = self.run_cli('--create','chip','--color-sets','ocean','--dry-run')['params']
        self.assertEqual(ocean['fill'], '#DCEBFF')
        colors = self.run_cli('--create','chip','--color-sets','["012345","427abc"]','--dry-run')['params']
        self.assertEqual(colors['fill'], '#012345');self.assertEqual(colors['accent'], '#427ABC')
        self.assertEqual(colors['stroke'], defaults['stroke'])
        self.assertEqual(self.run_cli('--create','chip','--color-sets','["fff"]','--dry-run')['params']['fill'], '#FFFFFF')
        self.assertEqual(len(self.run_cli('--list-color-sets')['color_sets']),8)
        for value in ('["abcde"]','[]','["111","222","333","444","555"]','["012345","427abc“]','unknown','[123456]'):
            self.run_cli('--create','chip','--color-sets',value,'--dry-run',code=2)

    def test_params_precedence_and_files(self):
        file=self.work/'params.json';file.write_text('{"pins":8,"label":"CPU"}')
        data=self.run_cli('--create','chip','--color-sets','ocean','--params','@'+str(file),'--set','pins=9','--set','pins=10','--set','label=0123','--set','fill=123abc','--dry-run')
        self.assertEqual(data['params']['pins'],10);self.assertEqual(data['params']['label'],'0123')
        self.assertEqual(data['params']['fill'],'#123ABC')
        self.run_cli('--create','chip','--params','{"pins":6,"pins":7}','--dry-run',code=2)

    def test_invalid_geometry_fails_without_writes(self):
        for pair in ('pinz=8','pins=42','pins=true','pins=2.5','pins=NaN','pins=Infinity','pins="3"','fill=xyz'):
            with self.subTest(pair=pair):
                self.run_cli('--create','chip','--set',pair,code=2)
        self.run_cli('--create','waveform','--set','wave_type=unknown',code=2)
        self.assertFalse((self.work/'exports').exists())

    def test_parts_discovery_and_edits(self):
        parts=self.run_cli('--list-parts','chip','--set','pins=4')['parts']
        self.assertEqual(sum(p['id'].startswith('pin-') for p in parts),16)
        output=self.work/'edited.svg'
        data=self.run_cli('--create','chip','--set','pins=4','--parts','{"pin-top-1":{"fill":"ff0000","sx":2,"sy":0.5}}','--output',output)
        svg=output.read_text();self.assertIn('#FF0000',svg);self.assertIn('scale(2 0.5)',svg)
        self.assertNotIn('data-part',svg)
        self.run_cli('--create','chip','--set','pins=4','--parts','{"pin-top-9":{"fill":"f00"}}',code=2)
        self.run_cli('--create','chip','--parts','{"core":{"sx":99}}',code=2)
        self.run_cli('--create','chip','--parts','{"core":{"bad":1}}',code=2)

    def test_raw_svg_stdout_and_defaults_directory(self):
        result=self.run_cli('--create','chip','--output','-',json_mode=False)
        ET.fromstring(result.stdout);self.assertEqual(result.stderr,'')
        self.assertFalse((self.work/'exports').exists())
        data=self.run_cli('--create','chip')
        self.assertTrue((self.work/'exports/chip.svg').exists())
        self.run_cli('--create','chip','--output','-',code=2)

    def test_no_clobber_then_explicit_force(self):
        out=self.work/'saved.svg';out.write_text('keep me')
        self.run_cli('--create','chip','--output',out,code=3)
        self.assertEqual(out.read_text(),'keep me')
        self.run_cli('--create','chip','--output',out,'--force')
        ET.fromstring(out.read_text())
        self.run_cli('--create','chip','--output',out,'--save-recipe',out,'--force',code=2)

    def test_recipe_roundtrip_and_customization(self):
        a=self.work/'a.svg';b=self.work/'b.svg';r=self.work/'item.asset.json'
        self.run_cli('--create','chip','--set','pins=10','--color-sets','mint','--output',a,'--save-recipe',r)
        self.run_cli('--recipe',r,'--output',b)
        self.assertEqual(a.read_text(),b.read_text())
        data=self.run_cli('--recipe',r,'--color-sets','default','--set','pins=7','--dry-run')
        self.assertEqual(data['params']['fill'],'#2878D4');self.assertEqual(data['params']['pins'],7)
        old=json.loads(r.read_text());old['format']='vector-foundry.asset';r.write_text(json.dumps(old))
        self.run_cli('--recipe',r,'--dry-run')

    def test_export_options_and_dimension_rejection(self):
        out=self.work/'wide.svg'
        data=self.run_cli('--create','folder','--size','600','--height','300','--background','ffeecc','--padding','12','--output',out)
        self.assertEqual(data['output']['width'],600);self.assertEqual(data['output']['height'],300)
        self.assertIn('#FFEECC',out.read_text())
        for opts in [('--width','0'),('--height','5000'),('--padding','nan'),('--format','png','--output','x.svg'),('--scale','2')]:
            self.run_cli('--create','chip',*opts,code=2)
        self.run_cli('--create','chip','--format','png','--size','4096','--scale','4',code=2)

    @unittest.skipUnless(importlib.util.find_spec('cairosvg'),'Optional CairoSVG not installed')
    def test_png_is_generated_from_svg_with_correct_dimensions(self):
        out=self.work/'chip.png'
        self.run_cli('--create','chip','--width','320','--height','160','--scale','2','--output',out)
        self.assertEqual(struct.unpack('>II',out.read_bytes()[16:24]),(640,320))
        self.assertTrue(out.with_suffix('.svg').exists());ET.fromstring(out.with_suffix('.svg').read_text())
        self.run_cli('--create','chip','--output',out,code=3)

    def test_png_missing_dependency_keeps_svg(self):
        block=self.work/'blocked';block.mkdir();(block/'cairosvg.py').write_text('raise ImportError("dependency test")\n')
        env=dict(os.environ,PYTHONPATH=str(block))
        out=self.work/'nod.png'
        error=self.run_cli('--create','chip','--output',out,code=5,env=env)
        self.assertEqual(error['code'],'png_dependency')
        self.assertTrue(Path(error['details']['svg_saved']).exists());self.assertFalse(out.exists())

    def test_dry_runs_do_not_publish_files(self):
        old=self.gallery_files()
        self.run_cli('--add-category','instruments','--dry-run')
        self.run_cli('--init-symbol','sensor','--category','hardware','--dry-run')
        self.run_cli('--create','chip','--format','both','--dry-run')
        self.assertEqual(old,self.gallery_files())
        self.assertFalse((self.work/'drafts').exists());self.assertFalse((self.work/'exports').exists())

    def test_category_add_force_and_history(self):
        self.run_cli('--add-category','instruments','--name','Instruments')
        self.assertEqual(self.run_cli('--list-category')['category_count'],7)
        self.run_cli('--add-category','instruments',code=3)
        data=self.run_cli('--add-category','instruments','--name','Measurements','--force')
        self.assertTrue((Path(data['backup'])/'catalog.json').exists())
        for ident in ('../escape','All','all','custom/path','con'):
            self.run_cli('--add-category',ident,code=2)

    def test_full_scaffold_register_customize_build_workflow(self):
        data=self.install_sensor()
        self.assertEqual(data['validation']['symbol_count'],1)
        self.assertTrue((self.project/'Gallery/instruments/sensor/render.py').exists())
        spec=self.run_cli('--describe','sensor')['symbol'];self.assertEqual(spec['category'],'instruments')
        result=self.run_cli('--create','sensor','--set','ports=6','--set','body_width=192','--set','label=TEMP','--color-sets','mint')
        self.assertEqual(result['params']['ports'],6)
        built=self.run_cli('--build')
        html=Path(built['file']).read_text()
        self.assertIn('Gallery/instruments/sensor/render.py',html);self.assertIn('Gallery/__init__.py',html)
        self.assertNotIn('Gallery/.history/',html)
        self.assertEqual(built['symbol_count'],34)

    def test_embedded_spec_and_minimal_script_registration(self):
        script=self.work/'led.py'
        spec=json.loads((self.project/'Gallery/basics/rectangle/symbol.json').read_text())
        spec.update(id='led',renderer='led',name='LED')
        script.write_text('SPEC = '+repr(spec)+'\n\ndef render(d,p):\n    print("renderer diagnostic")\n    d.rect("body",32,32,192,192)\n')
        self.run_cli('--add-symbol','led','--script',script)
        self.run_cli('--create','led')  # Plugin print cannot contaminate JSON.
        basic=self.work/'basic.py';basic.write_text('def render(d,p):\n    d.rect("body",32,32,192,192)\n')
        self.run_cli('--add-symbol','simple','--script',basic,'--category','hardware')
        self.run_cli('--create','simple')

    def test_failed_addition_is_not_published(self):
        self.run_cli('--add-category','instruments')
        script,spec=self.scaffold()
        before=self.gallery_files()
        script.write_text('def render(d,p):\n    raise RuntimeError("broken shape")\n')
        err=self.run_cli('--add-symbol','sensor','--script',script,'--spec',spec,code=4)
        self.assertIn('broken shape',err['message']);self.assertEqual(before,self.gallery_files())
        script.write_text('def render(:\n')
        self.run_cli('--add-symbol','sensor','--script',script,'--spec',spec,code=4)
        self.assertEqual(before,self.gallery_files())

    def test_addition_timeout_releases_writer_lock(self):
        self.run_cli('--add-category','instruments')
        script,spec=self.scaffold();before=self.gallery_files()
        script.write_text('import time\ndef render(d,p):\n    time.sleep(3)\n    d.rect("body",20,20,100,100)\n')
        err=self.run_cli('--add-symbol','sensor','--script',script,'--spec',spec,'--timeout','1',code=4)
        self.assertEqual(err['code'],'renderer_timeout');self.assertEqual(before,self.gallery_files())

    def test_duplicate_parts_are_rejected_on_registration(self):
        self.run_cli('--add-category','instruments');script,spec=self.scaffold()
        script.write_text('def render(d,p):\n    d.rect("same",20,20,100,100)\n    d.rect("same",30,30,80,80)\n')
        self.run_cli('--add-symbol','sensor','--script',script,'--spec',spec,code=4)
        self.assertFalse((self.project/'Gallery/instruments/sensor/symbol.json').exists())

    def test_force_update_bumps_version_and_retains_old_code(self):
        self.install_sensor();script=self.work/'drafts/sensor.py';spec=self.work/'drafts/sensor.json'
        original=(self.project/'Gallery/instruments/sensor/render.py').read_bytes()
        script.write_text(script.read_text().replace("128, 123", "128, 124"))
        self.run_cli('--add-symbol','sensor','--script',script,'--spec',spec,code=3)
        data=self.run_cli('--add-symbol','sensor','--script',script,'--spec',spec,'--force')
        self.assertEqual(data['version'],2)
        self.assertEqual((Path(data['backup'])/'instruments/sensor/render.py').read_bytes(),original)

    def test_spec_only_variant_reuses_renderer_without_ui_changes(self):
        spec=json.loads((self.project/'Gallery/hardware/chip/symbol.json').read_text())
        spec.update(id='dsp',name='DSP',renderer='chip');spec['defaults'].update(label='DSP',pins=8)
        file=self.work/'dsp.json';file.write_text(json.dumps(spec))
        self.run_cli('--add-symbol','dsp','--spec',file)
        self.assertEqual(self.run_cli('--create','dsp','--dry-run')['params']['pins'],8)
        replacement=json.loads((self.project/'Gallery/hardware/chip/symbol.json').read_text())
        replacement.update(id='chip', name='AI chip replacement', category='hardware', style='default')
        replacement_file=self.work/'chip-replacement.json';replacement_file.write_text(json.dumps(replacement))
        self.run_cli('--add-symbol','chip','--spec',replacement_file,'--script',self.project/'Gallery/hardware/chip/render.py','--force',code=3)

    def test_lock_protects_readers_and_writers(self):
        lock=self.project/'Gallery/.write.lock';lock.write_text('{"pid":123}')
        self.run_cli('--list',code=3);self.run_cli('--add-category','test',code=3)
        self.assertTrue(lock.exists())

    def test_new_element_dry_run_keeps_gallery_unchanged(self):
        self.run_cli('--add-category','instruments');script,spec=self.scaffold();before=self.gallery_files()
        self.run_cli('--add-symbol','sensor','--script',script,'--spec',spec,'--dry-run')
        self.assertEqual(before,self.gallery_files())

    def test_validate_all(self):
        report=self.run_cli('--validate')
        self.assertEqual(report['symbol_count'],33)
        self.assertGreater(report['case_count'],200)
        self.run_cli('--validate','missing',code=2)

    def test_strict_color_and_empty_category_inputs(self):
        self.run_cli('--create','chip','--color-sets','["##123456"]','--dry-run',code=2)
        self.run_cli('--list-category','',code=2)
        data=self.run_cli('--create','chip','--color-sets',' ["012345", "427abc"] ','--dry-run')
        self.assertEqual(data['params']['accent'],'#427ABC')

    def test_bad_recipe_types_have_invalid_input_errors(self):
        r=self.work/'bad.asset.json'
        for value in [{'asset': {'type': {}}, 'output': {}}, {'asset': {'type':'chip'},'output':[1,2]}]:
            r.write_text(json.dumps(dict(value,format='svgdrawer.asset',schema_version=1)))
            self.run_cli('--recipe',r,'--dry-run',code=2)

    def test_shipped_single_script_example(self):
        self.run_cli('--add-symbol','led','--script',self.project/'examples/agent/led.py')
        self.run_cli('--create','led','--set','diameter=200','--set','show_label=false')
        data=self.run_cli('--list-parts','led','--set','show_label=false')
        self.assertEqual(data['part_count'],2)


if __name__ == '__main__':
    unittest.main()
