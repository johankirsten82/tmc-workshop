#!/usr/bin/env python3
"""Redraw-guard check for an app built on tmc-base (base patch: redraw-guard.patch).
    python3 test_redraw_guard.py /path/to/patched/app
Runs the app's REAL sync/Code.gs in the app's own tests/gas_server.js mock (in memory, test PIN only,
nothing sent to Google). Works on a temporary copy; never writes into the app folder.
Steps: sign in as first Admin on the mock, open Reports, half-fill the From/To date fields (no focus,
like a user who looked away), let another phone sync a new record, run a sync on this phone, and check
the half-filled fields survived; then check a screen nobody typed on still refreshes after a sync."""
import os,sys,re,json,shutil,socket,subprocess,tempfile,threading,time,urllib.request
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from functools import partial
from playwright.sync_api import sync_playwright
APP=os.path.abspath(sys.argv[1]);P=F=0
def ok(c,m):
    global P,F
    if c:P+=1
    else:F+=1
    print(('  PASS ' if c else '  FAIL ')+m,flush=True)
def free():s=socket.socket();s.bind(('127.0.0.1',0));p=s.getsockname()[1];s.close();return p
TMP=tempfile.mkdtemp(prefix='redraw-');GP,WP=free(),free();d=os.path.join(TMP,'app')
shutil.copytree(APP,d,ignore=shutil.ignore_patterns('tests','shots*','.git','*.zip','patches'))
ip=os.path.join(d,'index.html');s=open(ip,encoding='utf-8').read();C=json.loads(re.search(r'/\*CONFIG\*/(.*?)/\*END\*/',s,re.S).group(1))
C.update(SYNC_URL='http://127.0.0.1:%d/exec'%GP,SYNC_CODE='')
s=re.sub(r'/\*CONFIG\*/.*?/\*END\*/','/*CONFIG*/'+json.dumps(C,ensure_ascii=False,indent=1)+'/*END*/',s,flags=re.S);open(ip,'w',encoding='utf-8').write(s)
gas=subprocess.Popen(['node',os.path.join(APP,'tests','gas_server.js'),str(GP),'-'],stdout=subprocess.PIPE,env=dict(os.environ,GAS_FILE=os.path.join(APP,'sync','Code.gs')));gas.stdout.readline()
class Q(SimpleHTTPRequestHandler):
    def log_message(self,*a):pass
srv=ThreadingHTTPServer(('127.0.0.1',WP),partial(Q,directory=TMP));threading.Thread(target=srv.serve_forever,daemon=True).start()
def raw(b):return json.load(urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:%d/exec'%GP,data=json.dumps(b).encode())))
def synced(pg):pg.evaluate("TMC.syncNow()");pg.wait_for_timeout(900)
def other(pg,i):
    raw({'action':'sync','token':pg.evaluate("TMC.L.get('tok')"),'device':'other','since':0,'changes':[{'kind':'ex','id':'o%d'%i,'u':int(time.time()*1000),'del':0,'data':{'id':'o%d'%i,'txt':'from the other phone %d'%i,'by':'Other','at':'2026-10-31T09:00:00Z'}}]})
try:
  with sync_playwright() as pw:
    b=pw.chromium.launch(executable_path='/usr/bin/google-chrome' if os.path.exists('/usr/bin/google-chrome') else None,args=['--no-sandbox'])
    pg=b.new_page(viewport={'width':390,'height':844});errs=[];pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.goto('http://127.0.0.1:%d/app/'%WP);pg.wait_for_selector('#fName')
    pg.fill('#fName','Johan Kirsten');pg.click('#fName2');pg.wait_for_selector('#fPin2',timeout=15000)
    pg.fill('#fPin','2468');pg.fill('#fPin2','2468');pg.click('#fSet');pg.wait_for_selector('header',timeout=8000);synced(pg)
    has=pg.evaluate("typeof TMC.formDirty==='function'");ok(has,'patch present (TMC.formDirty)')
    pg.click('nav [data-tab=reports]');pg.wait_for_timeout(300)
    if not pg.locator('#rpF').count():  # Fuel-style 'Choose a report' list: open the first report
        pg.locator('#app button:has-text("\U0001F4CA")').first.click();pg.wait_for_timeout(300)
    if pg.locator('#rpPick [data-rpp=pick]').count():pg.click('#rpPick [data-rpp=pick]');pg.wait_for_selector('#rpF')
    ok(not has or pg.evaluate("TMC.formDirty()")==0,'fresh screen is not dirty')
    pg.fill('#rpF','2026-10-01');pg.fill('#rpT','2026-10-15');pg.evaluate("document.activeElement&&document.activeElement.blur()")
    ok(not has or pg.evaluate("TMC.formDirty()")==1,'typing marks the form as dirty')
    other(pg,1);synced(pg);synced(pg)
    ok(pg.locator('#rpF').count()==1 and pg.input_value('#rpF')=='2026-10-01' and pg.input_value('#rpT')=='2026-10-15','half-filled form survives a sync that brought new data')
    ok(pg.evaluate("TMC.all('ex').some(r=>r.id==='o1')"),'the new data did arrive (shows on the next screen change)')
    pg.click('nav [data-tab=home]');pg.wait_for_timeout(300)
    ok(not has or pg.evaluate("TMC.formDirty()")==0,'changing screen clears the dirty flag')
    pg.evaluate("document.querySelector('#app').firstElementChild.dataset.old='1'")  # marker: gone after a redraw
    other(pg,2);synced(pg);synced(pg)
    ok(pg.evaluate("TMC.all('ex').some(r=>r.id==='o2')") and pg.locator('#app [data-old]').count()==0,'untouched screen still redraws after a sync')
    ok(not errs,'no page errors %s'%errs[:2]);b.close()
finally:
    gas.kill();srv.shutdown();shutil.rmtree(TMP,ignore_errors=True)
print('\nREDRAW GUARD: %d passed, %d failed'%(P,F));sys.exit(1 if F else 0)
