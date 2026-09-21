"""Browser storage safety checks with an explicit CPython/storage test adapter.

Run: python tests/browser_storage.py
This verifies application logic, not native browser localStorage persistence.
"""
from pathlib import Path
import json
import os
import shutil
import sys
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine import handle_request
from build import build

KEY = 'svgdrawer.gallery.v1'
CURRENT_KEY = 'svgdrawer.gallery.v2'
build()
HTML = (ROOT / 'index.html').read_text(encoding='utf-8')
OUT = ROOT / 'tests/output'
OUT.mkdir(exist_ok=True)
seed_data = json.loads((ROOT / 'examples/sample-library.json').read_text(encoding='utf-8'))
seed_data['schema_version'] = 1
seed_data['elements'] = seed_data.pop('symbols')
seed = json.dumps(seed_data, ensure_ascii=False)

with sync_playwright() as p:
    executable = os.environ.get('CHROMIUM_PATH') or shutil.which('chromium') or shutil.which('chromium-browser')
    browser = p.chromium.launch(headless=True, **({'executable_path': executable} if executable else {}), args=['--no-sandbox'])
    context = browser.new_context(accept_downloads=True)
    errors = []

    def load(raw=None, delayed=False):
        page = context.new_page()
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.on('dialog', lambda d: d.accept())
        page.expose_function('testRender', handle_request)
        storage = {KEY: raw} if raw is not None else {}
        shim = '''<script>
        window.__writes=0;window.__quota=false;window.__storage=__INITIAL__;
        Object.defineProperty(window,'localStorage',{value:{
          getItem:key=>window.__storage[key]??null,
          setItem:(key,value)=>{if(window.__quota)throw new DOMException('Test storage full','QuotaExceededError');window.__writes++;window.__storage[key]=String(value);},
          removeItem:key=>{delete window.__storage[key];}
        }});
        </script>'''.replace('__INITIAL__', json.dumps(storage).replace('<', '\\u003c'))
        wait = 'await new Promise(resolve=>window.__releaseEngine=resolve);' if delayed else ''
        provider = "SD.engine.initialize=async function(){" + wait + "this.ready=true;this.mode='local';this.pythonPNG=false;this.onStatus('Python · local','ready');};SD.engine.request=payload=>window.testRender(payload);SD.startEngine();"
        source = HTML.replace('<head>', '<head>' + shim, 1).replace('SD.startEngine();', provider)
        page.set_content(source, wait_until='domcontentloaded')
        if not delayed:
            page.wait_for_function('SD.libraryReady')
        return page

    # A click during a delayed runtime start must not replace stored data with an empty collection.
    page = load(seed, delayed=True)
    assert page.evaluate('SD.libraryReady') is False
    assert page.locator('[data-favorite="chip"]').is_disabled()
    page.evaluate("SD.toggleFavorite('chip')")
    failure = page.evaluate("async()=>{try{await SD.addCategory('Too early');return null;}catch(e){return e.message;}}")
    assert 'finish loading' in failure
    assert page.evaluate('window.__writes') == 0
    assert page.evaluate('(key)=>localStorage.getItem(key)', KEY) == seed
    with page.expect_download() as info:
        page.locator('#backupShortcut').click()
    before = OUT / 'startup-recovery.json'
    info.value.save_as(str(before))
    assert before.read_text() == seed
    page.evaluate('window.__releaseEngine()')
    page.wait_for_function('SD.libraryReady')
    assert page.evaluate('SD.library.symbols.length') == 1
    assert page.evaluate('window.__writes') == 1
    assert page.evaluate('(key)=>localStorage.getItem(key)', KEY) == seed
    assert page.evaluate('(key)=>JSON.parse(localStorage.getItem(key)).schema_version', CURRENT_KEY) == 2
    page.close()

    # Invalid storage is protected even after Python is ready, and its original bytes are downloadable.
    broken = '{"format":"future-format","unrecoverable-example":'
    page = load(broken)
    assert page.evaluate('SD.storageBlocked') is True
    assert page.locator('#storageNotice').is_visible()
    page.evaluate("SD.toggleFavorite('chip')")
    assert page.evaluate('SD.library.favorites.length') == 0
    failure = page.evaluate("async()=>{try{await SD.addCategory('Do not overwrite');return null;}catch(e){return e.message;}}")
    assert 'protected' in failure
    assert page.evaluate('window.__writes') == 0
    with page.expect_download() as info:
        page.locator('#recoverStorage').click()
    recovery = OUT / 'unreadable-recovery.json'
    info.value.save_as(str(recovery))
    assert recovery.read_text() == broken
    assert page.evaluate('(key)=>localStorage.getItem(key)', KEY) == broken
    assert page.evaluate('(key)=>localStorage.getItem(key)', CURRENT_KEY) is None
    page.close()

    # Quota failure keeps the new in-memory item, warns, and backs up the new state, not old bytes.
    page = load(seed)
    page.evaluate('window.__quota=true')
    page.evaluate("SD.addCategory('Still in memory')")
    assert page.locator('#storageNotice').is_visible()
    assert 'only in memory' in page.locator('#storageNoticeText').inner_text()
    assert page.evaluate('SD.library.categories.some(c=>c.name==="Still in memory")')
    assert page.evaluate('(key)=>localStorage.getItem(key)', KEY) == seed
    with page.expect_download() as info:
        page.locator('#recoverStorage').click()
    quota = OUT / 'quota-recovery.json'
    info.value.save_as(str(quota))
    recovered = json.loads(quota.read_text())
    assert any(c['name'] == 'Still in memory' for c in recovered['categories'])
    assert len(recovered['symbols']) == 1
    page.close()

    # An overlapping mutation is rejected instead of committing a stale snapshot.
    page = load(seed)
    page.evaluate("""()=>{
        const original=SD.engine.request;
        SD.engine.request=async payload=>{
          if(payload.action==='validate_library')await new Promise(resolve=>window.__releaseCommit=resolve);
          return original(payload);
        };
        window.__firstCommit=SD.addCategory('First update');
    }""")
    page.wait_for_function('SD.libraryBusy')
    initial_favorites = page.evaluate('JSON.stringify(SD.library.favorites)')
    page.evaluate("SD.toggleFavorite('chip')")
    assert page.evaluate('JSON.stringify(SD.library.favorites)') == initial_favorites
    failure = page.evaluate("async()=>{try{await SD.addCategory('Concurrent update');return null;}catch(e){return e.message;}}")
    assert 'still in progress' in failure
    page.evaluate('window.__releaseCommit()')
    page.wait_for_function('!SD.libraryBusy')
    assert page.evaluate('SD.library.categories.some(c=>c.name==="First update")')
    assert not page.evaluate('SD.library.categories.some(c=>c.name==="Concurrent update")')
    page.close()

    assert not errors, errors
    print('PASS: startup write protection; unreadable-data preservation and exact recovery; quota warning and in-memory backup; overlapping update guards.')
    print('Storage was simulated; native persistence was not tested. Browser errors:', errors)
    browser.close()
