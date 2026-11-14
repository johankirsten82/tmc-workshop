#!/usr/bin/env python3
"""AUTO-UPDATE check (VER 11). When the app opens (or comes back to the front) and a new version is published,
it updates itself BEFORE anyone can save: full-screen "Updating… please wait", saves blocked, new worker, reload.
Unsynced saves survive. Offline: the app opens and works normally, no lock.
    python3 tests/test_autoupdate.py [/path/to/app]
Works on a temporary copy (mock server in memory, nothing sent to Google); never writes into the app folder.
Screenshots: <base>/tests/shots/autoupdate-*.png (base only)."""
import os,sys,re,json,shutil,socket,subprocess,tempfile,threading,time,urllib.request
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from functools import partial
from playwright.sync_api import sync_playwright
HERE=os.path.dirname(os.path.abspath(__file__));BASE=os.path.dirname(HERE)
APP=os.path.abspath(sys.argv[1]) if len(sys.argv)>1 else BASE
SHOTS=os.path.join(BASE,'tests','shots') if APP==BASE else tempfile.mkdtemp(prefix='au-shots-')
sys.path.insert(0,os.path.join(BASE,'tools'));import apply_config
P=F=0
def ok(c,m):
    global P,F
    if c:P+=1
    else:F+=1
    print(('  PASS ' if c else '  FAIL ')+m,flush=True)
def free():s=socket.socket();s.bind(('127.0.0.1',0));p=s.getsockname()[1];s.close();return p
TMP=tempfile.mkdtemp(prefix='au-');GP,WP=free(),free();d=os.path.join(TMP,'app')
shutil.copytree(APP,d,ignore=shutil.ignore_patterns('tests','shots*','.git','*.zip','patches','*.bak*'))
def publish(ver):   # "publish" a new version locally: bump VER, regenerate sw.js (new cache name)
    ip=os.path.join(d,'index.html');s=open(ip,encoding='utf-8').read();C=json.loads(re.search(r'/\*CONFIG\*/(.*?)/\*END\*/',s,re.S).group(1))
    C.update(SYNC_URL='http://127.0.0.1:%d/exec'%GP,SYNC_CODE='',VER=ver,VERSION='1.%d.0'%ver)
    s=re.sub(r'/\*CONFIG\*/.*?/\*END\*/','/*CONFIG*/'+json.dumps(C,ensure_ascii=False,indent=1)+'/*END*/',s,flags=re.S);open(ip,'w',encoding='utf-8').write(s)
    apply_config.main(d);return C
C=publish(1);CP=C.get('CACHE_PREFIX') or C['APP_ID']
GAS=os.path.join(APP,'sync','Code.gs') if os.path.exists(os.path.join(APP,'sync','Code.gs')) else os.path.join(BASE,'sync','Code.gs')
GS=os.path.join(APP,'tests','gas_server.js') if os.path.exists(os.path.join(APP,'tests','gas_server.js')) else os.path.join(BASE,'tests','gas_server.js')
gas=subprocess.Popen(['node',GS,str(GP),'-'],stdout=subprocess.PIPE,env=dict(os.environ,GAS_FILE=GAS));gas.stdout.readline()
SLOW={'sw':0,'down':0}
class Q(SimpleHTTPRequestHandler):
    def log_message(self,*a):pass
    def end_headers(self):self.send_header('Cache-Control','no-cache');super().end_headers()
    def do_GET(self):
        if SLOW['down']:self.close_connection=True;return   # no network (desert): connection drops, no answer
        if SLOW['sw'] and self.path.split('?')[0].endswith('icon-maskable-512.png'):time.sleep(SLOW['sw'])   # slow download of the new version's files: keeps the Updating screen up long enough to test it
        super().do_GET()
srv=ThreadingHTTPServer(('127.0.0.1',WP),partial(Q,directory=TMP));threading.Thread(target=srv.serve_forever,daemon=True).start()
URL='http://127.0.0.1:%d/app/'%WP
def dump():return json.load(urllib.request.urlopen('http://127.0.0.1:%d/_dump'%GP))
def has(pg,i):return pg.evaluate("TMC.all('x').some(r=>r.id===%r||(r.data&&r.data.id===%r))"%(i,i)) if pg.evaluate("typeof TMC.all")=='function' else False
def recs(pg):return json.dumps(pg.evaluate("TMC.L.j('R',{})")) if pg.evaluate("TMC.L.get('R')!=null") else json.dumps(pg.evaluate("Object.fromEntries(Object.keys(localStorage).map(k=>[k,localStorage[k]]))"))
try:
  with sync_playwright() as pw:
    b=pw.chromium.launch(executable_path='/usr/bin/google-chrome' if os.path.exists('/usr/bin/google-chrome') else None,args=['--no-sandbox'])
    x=b.new_context(viewport={'width':390,'height':844},device_scale_factor=2,is_mobile=True,has_touch=True,service_workers='allow')
    errs=[];pg=x.new_page();pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.goto(URL);pg.wait_for_selector('#fName')
    pg.fill('#fName','Johan Kirsten');pg.click('#fName2');pg.wait_for_selector('#fPin2',timeout=15000)
    pg.fill('#fPin','2468');pg.fill('#fPin2','2468');pg.click('#fSet');pg.wait_for_selector('header',timeout=8000)
    pg.wait_for_function("navigator.serviceWorker.controller",timeout=10000);pg.evaluate("TMC.syncNow()");pg.wait_for_timeout(800)
    ok(pg.evaluate("CONFIG.VER")==1 and pg.locator('#updGo').count()==0,'old version 1 open, no Updating screen when nothing is new')
    # 1. a save that cannot reach the server (stays queued on the phone)
    pg.route('**/exec',lambda r:r.abort());x.route('**/exec',lambda r:r.abort())
    pg.evaluate("TMC.put('x','q1',{id:'q1',text:'queued before update',by:'Johan'})");pg.wait_for_timeout(500)
    ok(pg.evaluate("TMC.pending()")>=1,'unsynced record queued on the phone (pending=%s)'%pg.evaluate("TMC.pending()"))
    pg.close()
    # 2. publish v2, reopen the app -> updates itself
    publish(2);SLOW['sw']=4
    pg=x.new_page();pg.on('pageerror',lambda e:errs.append(str(e)));pg.goto(URL)
    pg.wait_for_selector('#updGo',state='visible',timeout=10000)
    v=pg.evaluate("(()=>{const o=document.getElementById('updGo'),r=o.getBoundingClientRect(),b=o.querySelector('b');return {w:r.width,h:r.height,fs:parseFloat(getComputedStyle(b).fontSize),txt:b.textContent,want:TMC.t('updGo')}})()")
    ok(v['w']>=389 and v['h']>=843 and v['fs']>=28 and v['txt']==v['want'],'reopen: full-screen big "Updating… please wait" shows by itself %s'%v)
    pg.screenshot(path=os.path.join(SHOTS,'autoupdate-en.png'))
    r=pg.evaluate("TMC.put('x','q2',{id:'q2',text:'during update',by:'Johan'})")
    ok(r is False and pg.evaluate("TMC.updLock()") and not has(pg,'q2'),'save BLOCKED while the update is running (put → %s)'%r)
    pg.evaluate("window.__old=1")
    pg.wait_for_function("!window.__old&&!!document.querySelector('header')&&!document.getElementById('updGo')",timeout=20000);pg.wait_for_timeout(1500)
    k=pg.evaluate("caches.keys()");ctl=pg.evaluate("navigator.serviceWorker.controller&&navigator.serviceWorker.controller.state")
    ok(CP+'-v1.2.0' in k and CP+'-v1.1.0' not in k and pg.locator('#updGo').count()==0 and pg.evaluate("!TMC.updLock()"),'updated automatically: new worker active (%s), cache %s, old cache gone, screen gone'%(ctl,k))
    ok(pg.evaluate("CONFIG.VER")==2 and pg.evaluate("!!(TMC.me()&&TMC.me().admin)"),'after update: version 2, still signed in as Admin')
    ok(has(pg,'q1') and pg.evaluate("TMC.pending()")>=1,'queued unsynced record still on the phone after the reload')
    ok(not has(pg,'q2'),'the blocked save did not slip in')
    pg.unroute('**/exec');x.unroute('**/exec');pg.evaluate("TMC.syncNow()");pg.wait_for_function("TMC.pending()===0",timeout=15000)
    ok(any(r['id']=='q1' for r in dump()['recs']),'queued record reached the server after the update')
    ok(pg.evaluate("TMC.put('x','q3',{id:'q3',text:'after update',by:'Johan'})") is not False and has(pg,'q3'),'saving works again after the update')
    # 3. coming back to the front (app left open) -> updates itself too (French screen)
    pg.evaluate("TMC.L.set('lang','fr')");pg.reload();pg.wait_for_selector('header');pg.wait_for_timeout(800)
    publish(3);SLOW['sw']=4
    pg.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
    pg.wait_for_selector('#updGo',state='visible',timeout=10000)
    ok('Mise à jour' in pg.inner_text('#updGo'),'back to the front: Updating screen in the phone\'s language (FR)')
    pg.screenshot(path=os.path.join(SHOTS,'autoupdate-fr.png'))
    pg.wait_for_function("CONFIG.VER===3&&!document.getElementById('updGo')",timeout=20000);pg.wait_for_selector('header')
    ok(pg.evaluate("caches.keys()")==[CP+'-v1.3.0'] or CP+'-v1.3.0' in pg.evaluate("caches.keys()"),'back to the front: updated itself to version 3')
    pg.evaluate("TMC.L.set('lang','en')");SLOW['sw']=0
    # 4. offline open: no lock, app works
    publish(4);x.set_offline(True);SLOW['down']=1;pg.reload();pg.wait_for_selector('header',timeout=15000);pg.wait_for_timeout(2500)
    o=[pg.locator('#updGo').count(),pg.evaluate("TMC.updLock()"),pg.evaluate("CONFIG.VER")]
    ok(o==[0,False,3],'offline open: app opens normally (version 3), no Updating screen, no lock %s'%o)
    ok(pg.evaluate("TMC.put('x','q4',{id:'q4',text:'desert offline',by:'Johan'})") is not False and has(pg,'q4'),'offline: saving still works (kept on the phone)')
    x.set_offline(False);SLOW['down']=0;pg.reload();pg.wait_for_function("CONFIG.VER===4&&!document.getElementById('updGo')",timeout=20000);pg.wait_for_selector('header');pg.wait_for_timeout(800)
    ok(has(pg,'q4'),'next open with network: updated to version 4, offline save still there')
    pg.evaluate("TMC.syncNow()");pg.wait_for_function("TMC.pending()===0",timeout=15000)
    ok(any(r['id']=='q4' for r in dump()['recs']),'offline save reached the server')
    ok(not errs,'no page errors %s'%errs[:3])
    b.close()
finally:
  gas.kill();srv.shutdown();shutil.rmtree(TMP,ignore_errors=True)
print('AUTO-UPDATE: %d passed, %d failed'%(P,F));sys.exit(1 if F else 0)
