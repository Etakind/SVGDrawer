"""Extension and v1 migration checks. Adding gallery files does not require UI changes."""
import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.migrate_v1 import migrate

class MaintenanceTests(unittest.TestCase):
    def test_add_renderer_and_definition_without_ui_changes(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            for name in ('Gallery','engine','app'):
                shutil.copytree(ROOT/name,root/name,ignore=shutil.ignore_patterns('__pycache__'))
            shutil.copy(ROOT/'build.py',root/'build.py')
            (root/'Gallery/instruments/signal_probe').mkdir(parents=True)
            shutil.copy(ROOT/'examples/extension/signal_probe.py.example',root/'Gallery/instruments/signal_probe/render.py')
            shutil.copy(ROOT/'examples/extension/signal_probe.json.example',root/'Gallery/instruments/signal_probe/symbol.json')
            catalog = json.loads((root/'Gallery/catalog.json').read_text())
            catalog['categories'].append({'id':'instruments','name':'Instruments','description':'Extension test collection.','icon':'wave','order':60})
            spec=json.loads((root/'Gallery/instruments/signal_probe/symbol.json').read_text())
            spec.pop('id', None); spec.pop('name', None); spec.pop('category', None); spec.pop('style', None)
            (root/'Gallery/instruments/signal_probe/symbol.json').write_text(json.dumps(spec))
            catalog['symbols'].append({'id':'signal_probe','name':'Signal probe','category':'instruments','style':'default'})
            (root/'Gallery/catalog.json').write_text(json.dumps(catalog))
            result=subprocess.run([sys.executable,'build.py'],cwd=root,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            html=(root/'index.html').read_text();self.assertIn('Signal probe',html);self.assertIn('Instruments',html)
            result=subprocess.run([sys.executable,'-c',"from engine import handle_request; import xml.etree.ElementTree as ET; r=handle_request({'asset':{'type':'signal_probe','params':{'ports':8}}}); ET.fromstring(r['svg']); assert r['svg'].count('data-part=\"port-')==8"],cwd=root,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)

    def test_v1_presets_migrate_without_canvas_positions(self):
        project={'version':1,'customLibrary':[{'id':'p','name':'Old chip','category':'Hardware','node':{'type':'chip','params':{'pins':10},'parts':{'pin-top-1':{'fill':'#FF0000'}},'x':200,'y':300,'rotation':45}}],'nodes':[{'id':'n','type':'folder','name':'Old folder'}]}
        original=copy.deepcopy(project)
        result=migrate(project);self.assertEqual(project,original)
        self.assertEqual(len(result['symbols']),1)
        self.assertEqual(result['symbols'][0]['asset']['params']['pins'],10)
        self.assertNotIn('x',result['symbols'][0]['asset']);self.assertNotIn('rotation',result['symbols'][0]['asset'])
        self.assertEqual(result,migrate(project))
        self.assertEqual(len(migrate(project,True)['symbols']),2)

    def test_v1_imported_svg_is_sanitized(self):
        project={'version':1,'customLibrary':[{'name':'Old vector','category':'Custom','node':{'type':'custom','source':'<svg viewBox="0 0 10 10" onload="bad()"><rect width="10" height="10"/></svg>'}}]}
        result=migrate(project);self.assertNotIn('onload',result['symbols'][0]['asset']['raw_svg'])
        self.assertEqual(len(result['categories']),1)

    def test_v1_unknown_types_fail_without_silent_drops(self):
        with self.assertRaises(ValueError):migrate({'version':1,'customLibrary':[{'node':{'type':'missing'}}]})
        with self.assertRaises(ValueError):migrate({'version':2})

if __name__=='__main__':unittest.main()
