#!/usr/bin/env python3
"""Phone screenshots of the Workshop v3 Admin Add stock sample. Not published."""
import json, os, re, shutil, socket, subprocess, tempfile, threading, urllib.request
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from functools import partial
from playwright.sync_api import sync_playwright
APP = os.path.abspath(__file__).rsplit('/tests/', 1)[0]
OUT = os.path.join(APP, 'screenshots')
os.makedirs(OUT, exist_ok=True)
TMP = tempfile.mkdtemp(prefix='wshots-v3-')
shutil.copytree(APP, os.path.join(TMP, 'app'), ignore=shutil.ignore_patterns('tests', '.git', 'uploads', 'screenshots', 'archive'))
def free():
    s = socket.socket(); s.bind(('127.0.0.1', 0)); p = s.getsockname()[1]; s.close(); return p
GP, WP = free(), free()
gas = subprocess.Popen(['node', os.path.join(APP, 'tests', 'gas_server.js'), str(GP), '-'], stdout=subprocess.PIPE, env=dict(os.environ, GAS_FILE=os.path.join(APP, 'sync', 'Code.gs')))
gas.stdout.readline()
ip = os.path.join(TMP, 'app', 'index.html'); src = open(ip, encoding='utf-8').read()
C = json.loads(re.search(r'/\*CONFIG\*/(.*?)/\*END\*/', src, re.S).group(1))
C['SYNC_URL'] = 'http://127.0.0.1:%d/exec' % GP; C['SYNC_CODE'] = ''
src = re.sub(r'/\*CONFIG\*/.*?/\*END\*/', '/*CONFIG*/' + json.dumps(C, ensure_ascii=False) + '/*END*/', src, flags=re.S)
open(ip, 'w', encoding='utf-8').write(src)
class Q(SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
srv = ThreadingHTTPServer(('127.0.0.1', WP), partial(Q, directory=os.path.join(TMP, 'app')))
threading.Thread(target=srv.serve_forever, daemon=True).start()
SHOTS = [
    'v3-1-stock-admin-add-button.png',
    'v3-2-add-stock-form-square-tubing.png',
    'v3-3-stock-worker-no-button.png',
]
try:
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        c = b.new_context(viewport={'width': 473, 'height': 1024}, device_scale_factor=3, is_mobile=True, has_touch=True)
        c.on('dialog', lambda d: d.accept())
        pg = c.new_page()
        pg.goto('http://127.0.0.1:%d/' % WP)
        pg.fill('#fName', 'Johan Kirsten'); pg.click('#fName2'); pg.wait_for_selector('#fPin2')
        pg.fill('#fPin', '2468'); pg.fill('#fPin2', '2468'); pg.click('#fSet'); pg.wait_for_selector('header')
        pg.evaluate('TMC.syncNow()'); pg.wait_for_timeout(800)
        pg.click('nav [data-tab=work]'); pg.wait_for_timeout(300)
        pg.click('#wjStock'); pg.wait_for_timeout(250)
        pg.click('#wjAddStock'); pg.wait_for_timeout(250)
        pg.fill('#wjItem', 'Square tubing')
        pg.fill('#wjAddQty', '10')
        pg.evaluate('scrollTo(0,0)'); pg.wait_for_timeout(150)
        pg.screenshot(path=os.path.join(OUT, SHOTS[1]))
        pg.click('#wjSaveAdd'); pg.wait_for_timeout(500)
        # Angle iron at 0 as a single set-count record (no add-1 then set-0 clutter)
        pg.evaluate("""()=>{
          const at=new Date().toISOString();
          TMC.put('k','kset-angle-0',{id:'kset-angle-0',ref:'',dir:'set',mat:'steel',desc:'Angle iron',qty:0,len:0,unit:'piece',qThou:0,lThou:0,at:at,by:'JA Kirsten',jobId:'',sourceApp:'admin',note:''});
          TMC.syncNow();
        }""")
        pg.wait_for_timeout(700)
        pg.evaluate("TMC.render()"); pg.wait_for_timeout(250)
        pg.evaluate('scrollTo(0,0)'); pg.wait_for_timeout(150)
        pg.screenshot(path=os.path.join(OUT, SHOTS[0]))
        # staff user
        st = b.new_context(viewport={'width': 473, 'height': 1024}, device_scale_factor=3, is_mobile=True, has_touch=True)
        st.on('dialog', lambda d: d.accept())
        g = st.new_page()
        g.goto('http://127.0.0.1:%d/' % WP)
        g.fill('#fName', 'Pieter'); g.click('#fName2')
        g.wait_for_function("!!document.querySelector('#fCheck')", timeout=15000)
        pg.evaluate('TMC.syncNow()'); pg.wait_for_timeout(900)
        pg.click('nav [data-tab=users]'); pg.wait_for_timeout(500)
        row = pg.locator('.ulr', has_text='Pieter')
        row.wait_for(timeout=8000)
        if row.locator('.uopen').count() == 0:
            row.locator('.uli').click(); pg.wait_for_timeout(250)
        row.locator('[data-ua=approve]').click(); pg.wait_for_timeout(800)
        g.click('#fCheck'); g.wait_for_selector('#fPin2', timeout=8000)
        g.fill('#fPin', '1357'); g.fill('#fPin2', '1357'); g.click('#fSet'); g.wait_for_selector('header')
        g.evaluate('TMC.syncNow()'); g.wait_for_timeout(800)
        g.click('nav [data-tab=work]'); g.wait_for_timeout(300)
        g.click('#wjStock'); g.wait_for_timeout(300)
        g.evaluate('scrollTo(0,0)'); g.wait_for_timeout(150)
        g.screenshot(path=os.path.join(OUT, SHOTS[2]))
        b.close()
finally:
    gas.kill(); srv.shutdown(); shutil.rmtree(TMP, ignore_errors=True)
print('shots', OUT)
for n in SHOTS:
    p = os.path.join(OUT, n)
    print(' ', n, os.path.getsize(p) if os.path.exists(p) else 'MISSING')
