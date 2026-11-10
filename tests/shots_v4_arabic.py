#!/usr/bin/env python3
"""Phone screenshots of the Workshop v4 Arabic sample. Not published."""
import json, os, re, shutil, socket, subprocess, tempfile, threading, urllib.request
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from functools import partial
from playwright.sync_api import sync_playwright
APP = os.path.abspath(__file__).rsplit('/tests/', 1)[0]
OUT = os.path.join(APP, 'screenshots')
os.makedirs(OUT, exist_ok=True)
TMP = tempfile.mkdtemp(prefix='wshots-v4-')
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
URL = 'http://127.0.0.1:%d/' % WP
SHOTS = {
    'signin': 'ar-signin.png',
    'home': 'ar-home.png',
    'home360': 'ar-home-360.png',
    'stock': 'ar-stock.png',
    'picker': 'ar-lang-picker.png',
    'enhome': 'en-home.png',
}
CHROME = '/usr/bin/google-chrome' if os.path.exists('/usr/bin/google-chrome') else None
try:
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path=CHROME, args=['--no-sandbox'])
        c = b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=3, is_mobile=True, has_touch=True, locale='en-US')
        c.on('dialog', lambda d: d.accept())
        pg = c.new_page()
        pg.goto(URL)
        pg.wait_for_selector('#langSel')
        pg.select_option('#langSel', 'ar')
        pg.wait_for_timeout(300)
        pg.evaluate('scrollTo(0,0)')
        pg.screenshot(path=os.path.join(OUT, SHOTS['signin']))
        # language picker with all 4 options visible (native dropdown is not captured in headless)
        pg.evaluate("""()=>{
          const s=document.getElementById('langSel');
          const st=document.createElement('style');st.id='shotLang';
          st.textContent='.tmcS .tmcS-lang{height:auto!important;min-height:0!important;max-height:none!important;padding:8px 10px!important;text-align:start!important;text-align-last:start!important;}';
          document.head.appendChild(st);s.size=4;
        }""")
        pg.wait_for_timeout(200)
        pg.evaluate('scrollTo(0,0)')
        pg.screenshot(path=os.path.join(OUT, SHOTS['picker']))
        pg.evaluate("""()=>{const s=document.getElementById('langSel');if(s)s.size=1;const st=document.getElementById('shotLang');if(st)st.remove()}""")
        # sign in as Admin
        pg.fill('#fName', 'Johan Kirsten'); pg.click('#fName2'); pg.wait_for_selector('#fPin2')
        pg.fill('#fPin', '2468'); pg.fill('#fPin2', '2468'); pg.click('#fSet'); pg.wait_for_selector('header')
        pg.evaluate('TMC.syncNow()'); pg.wait_for_timeout(800)
        # seed v3 sample stock
        pg.evaluate("""()=>{
          const at=new Date().toISOString();
          TMC.put('k','kin-sq-10',{id:'kin-sq-10',ref:'',dir:'in',mat:'steel',desc:'Square tubing',qty:10,len:0,unit:'piece',qThou:10000,lThou:0,at:at,by:'JA Kirsten',jobId:'',sourceApp:'admin',note:''});
          TMC.put('k','kset-angle-0',{id:'kset-angle-0',ref:'',dir:'set',mat:'steel',desc:'Angle iron',qty:0,len:0,unit:'piece',qThou:0,lThou:0,at:at,by:'JA Kirsten',jobId:'',sourceApp:'admin',note:''});
          TMC.syncNow();
        }""")
        pg.wait_for_timeout(700)
        # Home in Arabic
        pg.select_option('#hLang', 'ar'); pg.wait_for_timeout(300)
        pg.click('nav [data-tab=home]'); pg.wait_for_timeout(250)
        pg.evaluate('TMC.fitTabs&&TMC.fitTabs()')
        pg.evaluate('scrollTo(0,0)'); pg.wait_for_timeout(150)
        pg.screenshot(path=os.path.join(OUT, SHOTS['home']))
        # Arabic Home at 360px
        pg.set_viewport_size({'width': 360, 'height': 844})
        pg.wait_for_timeout(200)
        pg.evaluate('TMC.fitTabs&&TMC.fitTabs()')
        pg.evaluate('scrollTo(0,0)'); pg.wait_for_timeout(150)
        pg.screenshot(path=os.path.join(OUT, SHOTS['home360']))
        pg.set_viewport_size({'width': 390, 'height': 844})
        pg.wait_for_timeout(200)
        pg.evaluate('TMC.fitTabs&&TMC.fitTabs()')
        # Stock in Arabic
        pg.click('nav [data-tab=work]'); pg.wait_for_timeout(300)
        pg.click('#wjStock'); pg.wait_for_timeout(300)
        pg.evaluate('scrollTo(0,0)'); pg.wait_for_timeout(150)
        pg.screenshot(path=os.path.join(OUT, SHOTS['stock']))
        # Home in English (nothing else changed)
        pg.select_option('#hLang', 'en'); pg.wait_for_timeout(300)
        pg.click('nav [data-tab=home]'); pg.wait_for_timeout(250)
        pg.evaluate('scrollTo(0,0)'); pg.wait_for_timeout(150)
        pg.screenshot(path=os.path.join(OUT, SHOTS['enhome']))
        info = pg.evaluate("""()=>({lang:document.documentElement.lang,dir:document.documentElement.dir})""")
        print('last (en home)', info)
        b.close()
    print('SHOTS', [os.path.join(OUT, n) for n in SHOTS.values()])
finally:
    try: gas.kill()
    except Exception: pass
    try: srv.shutdown()
    except Exception: pass
