"""End-to-end UI checks. By default, use a running server.

  python server.py --no-browser
  python tests/browser_integration.py --url http://127.0.0.1:8765

For restricted environments where Chromium navigation is blocked:
  python tests/browser_integration.py --bridge

Bridge mode runs the real CPython renderer through Playwright bindings and
uses an in-memory storage adapter. It is not a test of native localStorage,
HTTP navigation or the CDN. Real HTTP is covered separately by test_http.py.
"""
from pathlib import Path
import argparse
import ast
import json
import os
import shutil
import struct
import subprocess
import sys
import xml.etree.ElementTree as ET
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from engine import handle_request, gallery
from build import build

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--bridge',action='store_true')
parser.add_argument('--url',default='http://127.0.0.1:8765')
args=parser.parse_args()
build();BUILTIN_COUNT=len(gallery().symbols);HARDWARE_COUNT=sum(e['category']=='hardware' for e in gallery().symbols.values());DOCUMENT_COUNT=sum(e['category']=='documents' for e in gallery().symbols.values());OUT=ROOT/'tests/output';OUT.mkdir(exist_ok=True)

with sync_playwright() as p:
    executable=os.environ.get('CHROMIUM_PATH') or shutil.which('chromium') or shutil.which('chromium-browser')
    browser=p.chromium.launch(headless=True,**({'executable_path':executable} if executable else {}),args=['--no-sandbox'])
    context=browser.new_context(viewport={'width':1440,'height':1060},accept_downloads=True)
    page=context.new_page();errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.on('dialog',lambda dialog:dialog.accept())

    def load(target,stored=None):
        if args.bridge:
            target.expose_function('testRender',handle_request)
            text=(ROOT/'index.html').read_text()
            adapter="SD.engine.initialize=async function(){this.ready=true;this.mode='local';this.pythonPNG=false;this.onStatus('Python · local','ready');};SD.engine.request=payload=>window.testRender(payload);SD.startEngine();"
            text=text.replace('SD.startEngine();',adapter)
            storage={'svgdrawer.gallery.v1':stored} if stored else {}
            shim='<script>window.__storage='+json.dumps(storage).replace('<','\\u003c')+';Object.defineProperty(window,"localStorage",{value:{getItem:key=>window.__storage[key]??null,setItem:(key,value)=>window.__storage[key]=String(value),removeItem:key=>delete window.__storage[key]}});</script>'
            text=text.replace('<head>','<head>'+shim,1)
            target.set_content(text,wait_until='domcontentloaded')
        else:
            target.goto(args.url,wait_until='networkidle')
        target.wait_for_selector('#engineStatus.ready',state='attached',timeout=20000)
        target.wait_for_timeout(220)

    def wait_render():page.wait_for_timeout(170)
    def number(key,value,scope='param'):
        locator=page.locator(f'#settingsPanel input[type=number][data-scope="{scope}"][data-key="{key}"]')
        locator.fill(str(value));locator.press('Tab');wait_render()
    def text(selector,value):
        el=page.locator(selector);el.fill(value);el.press('Tab');wait_render()
    def download(selector,name):
        with page.expect_download() as info:page.locator(selector).click()
        path=OUT/name;info.value.save_as(str(path));return path
    def snapshot():return page.evaluate('window.SVGDrawer.getLibrarySnapshot()')

    load(page)
    assert page.locator('.symbol-card').count()==min(48,BUILTIN_COUNT)
    assert page.locator('canvas').count()==0
    page.screenshot(path=str(OUT/'gallery-desktop.png'),full_page=False)
    page.locator('[data-filter="hardware"]').click();assert page.locator('.symbol-card').count()==min(48,HARDWARE_COUNT)
    page.locator('[data-filter="documents"]').click();assert page.locator('.symbol-card').count()==min(48,DOCUMENT_COUNT)
    page.locator('[data-filter="all"]').click()
    page.locator('#search').fill('CPU');assert page.locator('[data-open="chip"]').count()==1
    page.locator('#search').fill('zzzzzz');assert page.locator('#emptyState').is_visible()
    page.locator('#clearSearch').click();assert page.locator('.symbol-card').count()==min(48,BUILTIN_COUNT)
    page.locator('[data-favorite="chip"]').click();page.locator('[data-filter="favorites"]').click();assert page.locator('.symbol-card').count()==1
    page.locator('[data-filter="all"]').click()
    page.locator('#sort').select_option('name');assert page.locator('.card-title').count()>0
    page.locator('#sort').select_option('featured')

    page.locator('[data-open="chip"]').click();wait_render()
    assert page.locator('#artPreview [data-part^="pin-"]').count()==24
    number('pins',12);number('pin_width',11);number('pin_length',28)
    assert page.locator('#artPreview [data-part^="pin-"]').count()==48
    assert page.locator('#artPreview [data-part="pin-top-1"]').get_attribute('height')=='33'
    page.locator('[data-palette-index="1"]').click();wait_render()
    assert page.locator('#artPreview [data-part="chip-face"]').get_attribute('fill')=='#C4BFFC'
    text('#param-fill-hex','17b890')
    assert page.locator('#artPreview [data-part="chip-face"]').get_attribute('fill')=='#17B890'
    page.locator('#tabParts').click();page.locator('#partSelect').select_option('pin-top-1')
    text('#part-fill-hex','#FF0033');number('sx',150,'part')
    assert page.locator('#artPreview [data-part="pin-top-1"]').get_attribute('fill')=='#FF0033'
    assert 'scale(1.5 1)' in page.locator('#artPreview [data-part="pin-top-1"]').get_attribute('transform')
    page.locator('[data-scope="part"][data-key="hidden"]').check();wait_render()
    assert page.locator('#artPreview [data-part="pin-top-1"]').get_attribute('visibility')=='hidden'
    page.locator('#undoEdit').click();wait_render()
    assert page.locator('#artPreview [data-part="pin-top-1"]').get_attribute('visibility') is None
    page.locator('#redoEdit').click();wait_render()
    assert page.locator('#artPreview [data-part="pin-top-1"]').get_attribute('visibility')=='hidden'
    page.locator('[data-reset-part]').click();wait_render()
    assert page.locator('#artPreview [data-part="pin-top-1"]').get_attribute('visibility') is None
    page.locator('#tabCustomize').click()
    page.locator('#saveVariant').click()
    page.locator('#saveName').fill('Research processor')
    page.locator('#saveDialog summary').click();page.locator('#saveNewCategory').fill('Research')
    page.locator('#saveTags').fill('research, custom, chip')
    page.locator('#confirmSave').click();page.wait_for_function("!document.querySelector('#saveDialog').open")
    assert len(snapshot()['symbols'])==1
    saved_id=snapshot()['symbols'][0]['id'];research_id=snapshot()['categories'][0]['id']
    assert snapshot()['symbols'][0]['asset']['params']['pins']==12
    page.locator('[data-close="assetDialog"]').click()
    assert page.locator('.symbol-card').count()==min(48,BUILTIN_COUNT+1)
    # Closing and reopening preserves a tab-local draft, without changing the original gallery definition.
    page.locator('[data-open="chip"]').click();wait_render()
    assert page.locator('#artPreview [data-part^="pin-"]').count()==48
    assert page.evaluate("SD.boot.gallery.symbols.find(e=>e.id==='chip').defaults.pins")==6

    page.locator('#tabExport').click();number('width',640,'output');number('height',320,'output')
    page.locator('[data-scope="ui"][data-key="pngScale"]').select_option('2')
    page.locator('[data-scope="ui"][data-key="pngEngine"]').select_option('browser')
    svg=download('#downloadSVG','browser-export.svg').read_text();ET.fromstring(svg)
    assert 'data-part' not in svg and 'data-node' not in svg
    assert 'viewBox="0 0 640 320"' in svg
    png=download('#downloadPNG','browser-export.png').read_bytes()
    assert png[:8]==b'\x89PNG\r\n\x1a\n' and struct.unpack('>II',png[16:24])==(1280,640)
    page.locator('[data-scope="output"][data-key="transparent"]').uncheck();wait_render()
    text('#output-background-hex','#F0EDE7')
    bg_png=download('#downloadPNG','browser-background.png')
    try:
        from PIL import Image
        with Image.open(bg_png) as im:assert im.convert('RGBA').getpixel((0,0))==(240,237,231,255)
    except ImportError:pass
    recipe_file=download('[data-save-recipe]','processor.asset.json')
    recipe=json.loads(recipe_file.read_text());assert recipe['asset']['params']['pins']==12
    script_file=download('[data-python-script]','processor.py');ast.parse(script_file.read_text())
    result=subprocess.run([sys.executable,str(script_file),'--output',str(OUT/'script-export.svg')],capture_output=True,text=True)
    assert result.returncode==0,result.stderr;ET.fromstring((OUT/'script-export.svg').read_text())
    page.locator('[data-view-source]').click();page.wait_for_selector('#sourceDialog[open]')
    assert '<svg' in page.locator('#sourceText').input_value()
    page.locator('[data-close="sourceDialog"]').click()
    page.locator('[data-close="assetDialog"]').click()
    backup_file=download('#backupShortcut','initial-library.json')
    before_backup=json.loads(backup_file.read_text());assert len(before_backup['symbols'])==1

    page.locator('#manageLibrary').click()
    text(f'[data-rename-category="{research_id}"]','Research & science')
    assert snapshot()['categories'][0]['id']==research_id
    page.locator('#newCategoryName').fill('Personal icons');page.locator('#addCategoryForm button').click();wait_render()
    assert len(snapshot()['categories'])==2
    page.locator('[data-manager-tab="symbols"]').click()
    text(f'[data-rename-item="{saved_id}"]','Research processor v2')
    assert snapshot()['symbols'][0]['name']=='Research processor v2'
    page.locator('[data-close="libraryDialog"]').click()

    page.locator('#addSymbol').click()
    unsafe=b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" onload="window.XSS=true"><script>window.XSS=true</script><rect x="10" y="10" width="80" height="80" fill="#ffaa00"/><circle cx="50" cy="50" r="20" fill="#FFFFFF"/><image href="https://bad.example/x.png"/></svg>'
    page.locator('#svgInput').set_input_files({'name':'Experimental sensor.svg','mimeType':'image/svg+xml','buffer':unsafe});wait_render()
    page.wait_for_selector('#assetDialog[open]')
    assert page.locator('#artPreview script').count()==0
    assert page.locator('#artPreview image').count()==0
    assert page.evaluate('window.XSS') is None
    page.locator('#partSelect').select_option('imported-part-1')
    text('#part-fill-hex','#6B51D1')
    assert page.locator('#artPreview [data-part="imported-part-1"]').get_attribute('fill')=='#6B51D1'
    page.locator('#saveVariant').click();page.locator('#saveName').fill('Experimental sensor')
    page.locator('#saveCategory').select_option(research_id);page.locator('#confirmSave').click()
    page.wait_for_function("!document.querySelector('#saveDialog').open")
    assert len(snapshot()['symbols'])==2
    page.locator('[data-close="assetDialog"]').click()

    # Merge an older backup with conflicting IDs: keep both versions, then deduplicate a repeated import.
    page.locator('#manageLibrary').click();page.locator('[data-manager-tab="backup"]').click()
    page.locator('#libraryInput').set_input_files(str(backup_file));wait_render()
    page.wait_for_function('window.SVGDrawer.getLibrarySnapshot().symbols.length===3')
    names=[e['name'] for e in snapshot()['symbols']]
    assert 'Research processor' in names and 'Research processor v2' in names and 'Experimental sensor' in names
    page.locator('#libraryInput').set_input_files(str(backup_file));wait_render()
    assert len(snapshot()['symbols'])==3
    final_backup=snapshot()
    page.locator('[data-manager-tab="guide"]').click();assert 'Gallery/catalog.json' in page.locator('#managerPanel').inner_text()
    page.locator('[data-close="libraryDialog"]').click()

    # Restore a recipe as a single preview, not as a scene.
    page.locator('#addSymbol').click();page.locator('#recipeInput').set_input_files(str(recipe_file));wait_render()
    assert page.locator('#artPreview [data-part^="pin-"]').count()==48
    page.locator('[data-close="assetDialog"]').click()

    # Different geometry family, screenshot, and mobile layout.
    page.locator('[data-open="waveform"]').click();wait_render()
    page.locator('[data-scope="param"][data-key="wave_type"]').select_option('sine');number('cycles',7)
    assert page.evaluate('window.SVGDrawer.getCurrentRecipe().asset.params.cycles')==7
    assert ' L ' in page.locator('#artPreview [data-part="signal-trace"]').get_attribute('d')
    page.screenshot(path=str(OUT/'waveform-detail.png'),full_page=False)
    page.locator('[data-close="assetDialog"]').click()
    page.locator('[data-open="chip"]').click();wait_render();page.locator('#resetSymbol').click();wait_render()
    page.screenshot(path=str(OUT/'chip-detail.png'),full_page=False)
    page.locator('[data-close="assetDialog"]').click()
    page.set_viewport_size({'width':390,'height':844});page.evaluate('window.scrollTo(0,0)');wait_render()
    assert page.evaluate('document.documentElement.scrollWidth')<=390
    page.screenshot(path=str(OUT/'gallery-mobile.png'),full_page=False)
    page.locator('#mobileCategory').select_option('hardware')
    assert page.locator('.symbol-card').count()==min(48,HARDWARE_COUNT)
    page.locator('[data-open="servers"]').click();wait_render()
    assert page.locator('#assetDialog').bounding_box()['width']<=390
    page.screenshot(path=str(OUT/'detail-mobile.png'),full_page=False)
    page.locator('[data-close="assetDialog"]').click()

    # Simulated persisted storage reload in bridge mode; real localStorage reload in server mode.
    if args.bridge:
        second=context.new_page();second.on('pageerror',lambda e:errors.append(str(e)))
        load(second,json.dumps(final_backup));assert second.evaluate('window.SVGDrawer.getLibrarySnapshot().symbols.length')==3
        assert second.locator('.symbol-card').count()==min(48,BUILTIN_COUNT+3)
        second.close()
    else:
        page.reload(wait_until='networkidle');page.wait_for_selector('#engineStatus.ready',state='attached');assert len(snapshot()['symbols'])==3
    assert not errors,errors
    print('PASS: gallery search / category filters / favorites / sorting; Python geometry and colors; part overrides; undo/redo; draft retention; save variants; SVG and browser PNG; opaque non-square PNG; recipes and self-contained Python script; category renaming; SVG sanitization; non-destructive merge and repeat deduplication; mobile layouts; storage reload adapter.' if args.bridge else 'PASS: browser integration via local HTTP.')
    print('Browser errors:',errors)
    browser.close()
