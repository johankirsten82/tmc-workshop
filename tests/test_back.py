#!/usr/bin/env python3
"""BACK button check (VER 10). Big "← Back" at the top of every screen except Home.
(was: Redraw-guard check for an app built on tmc-base (base patch: redraw-guard.patch).
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
TMP=tempfile.mkdtemp(prefix='back-');GP,WP=free(),free();d=os.path.join(TMP,'app')
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

def vb(pg):return pg.evaluate("""(()=>{const v=document.getElementById('view'),b=v&&v.firstElementChild;if(!b||!b.classList.contains('navBack'))return null;const r=b.getBoundingClientRect(),q=v.getBoundingClientRect(),cs=getComputedStyle(b),x=document.createElement('button');v.appendChild(x);const rs=getComputedStyle(x),st={bg:cs.backgroundColor==='rgb(229, 231, 235)',fg:cs.color==='rgb(31, 41, 55)',al:cs.textAlign==='center',fw:+cs.fontWeight>=700,rad:cs.borderRadius===rs.borderRadius,fs:cs.fontSize===rs.fontSize,mh:cs.minHeight===rs.minHeight};x.remove();return {sty:Object.values(st).every(Boolean),stw:Object.keys(st).filter(k=>!st[k]).join(','),txt:b.textContent,h:r.height,w:r.width,vw:q.width,top:r.top-q.top,vis:r.height>0&&getComputedStyle(b).display!=='none'}})()""")
def tabs(pg):return pg.evaluate("[...document.querySelectorAll('nav.tabs [data-tab]')].map(b=>b.dataset.tab)")
def cur(pg):return pg.evaluate("(document.querySelector('nav.tabs .on')||{dataset:{}}).dataset.tab")
try:
  with sync_playwright() as pw:
    b=pw.chromium.launch(executable_path='/usr/bin/google-chrome' if os.path.exists('/usr/bin/google-chrome') else None,args=['--no-sandbox'])
    pg=b.new_page(viewport={'width':390,'height':844});errs=[];pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.goto('http://127.0.0.1:%d/app/'%WP);pg.wait_for_selector('#fName')
    pg.fill('#fName','Johan Kirsten');pg.click('#fName2');pg.wait_for_selector('#fPin2',timeout=15000)
    pg.fill('#fPin','2468');pg.fill('#fPin2','2468');pg.click('#fSet');pg.wait_for_selector('header',timeout=8000);synced(pg)
    ok(pg.locator('#view .navBack').count()==0,'Home has NO Back button')
    T=[x for x in tabs(pg) if x!='home'];ok(len(T)>=3,'non-Home tabs found: %s'%T)
    for x in T:
        pg.click('nav [data-tab=home]');pg.wait_for_timeout(150);pg.click('nav [data-tab=%s]'%x);pg.wait_for_timeout(250)
        v=vb(pg);ok(v and v['sty'] and v['vis'] and v['top']<=1 and v['h']>=56 and v['w']>=v['vw']-2 and v['txt']==pg.evaluate("TMC.t('navBack')"),'%s: big full-width Back at the TOP (grey #E5E7EB, dark bold centred text, app button size) %s'%(x,v))
        pg.click('#view .navBack');pg.wait_for_timeout(250);ok(cur(pg)=='home' and pg.locator('#view .navBack').count()==0,'%s: Back → Home'%x)
    # previous screen, then Home
    a,c=T[0],T[-1];pg.click('nav [data-tab=%s]'%a);pg.wait_for_timeout(150);pg.click('nav [data-tab=%s]'%c);pg.wait_for_timeout(200)
    pg.click('#view .navBack');pg.wait_for_timeout(200);ok(cur(pg)==a,'Back goes to the PREVIOUS screen (%s → %s)'%(c,a))
    pg.click('#view .navBack');pg.wait_for_timeout(200);ok(cur(pg)=='home','second Back → Home')
    # no history → Home
    pg.click('nav [data-tab=settings]');pg.wait_for_timeout(150);pg.evaluate("TMC.nav.st.length=0");pg.click('#view .navBack');pg.wait_for_timeout(200)
    ok(cur(pg)=='home','no history → Back goes Home')
    # Home tiles open screens that also have Back
    n=pg.evaluate("document.querySelectorAll('#view .tile[data-tab]').length");okt=True
    for i in range(n):
        pg.locator('#view .tile[data-tab]').nth(i).click();pg.wait_for_timeout(200);v=vb(pg);okt=okt and bool(v) and cur(pg)!='home'
        pg.click('#view .navBack');pg.wait_for_timeout(200);okt=okt and cur(pg)=='home'
    ok(n==0 or okt,'every Home tile (%d) → screen with Back → Back to Home'%n)
    # report detail → report list (one level up)
    if 'reports' in T:
        pg.evaluate("TMC.addReport({id:'bk2',title:'rpDemo',cols:[{key:'date',label:'rpDate'}],rows:()=>[]})")
        pg.click('nav [data-tab=reports]');pg.wait_for_timeout(250)
        if pg.locator('#view [data-rp]').count()>1:
            pg.locator('#view [data-rp]').first.click();pg.wait_for_timeout(250);ok(vb(pg) is not None and pg.locator('#view [data-rp]').count()==0,'report detail has Back at the top')
            pg.click('#view .navBack');pg.wait_for_timeout(250);ok(cur(pg)=='reports' and pg.locator('#view [data-rp]').count()>1,'report detail → Back → report LIST (one level)')
            pg.click('#view .navBack');pg.wait_for_timeout(250);ok(cur(pg)=='home','report list → Back → Home')
        else:ok(False,'second report did not show in the list')
    # unsaved form: ask first
    if 'work' in T:
        pg.click('nav [data-tab=work]');pg.wait_for_timeout(250)
        if pg.locator('#exTxt').count():
            pg.fill('#exTxt','half typed note');pg.click('#view .navBack');pg.wait_for_timeout(200)
            ok(pg.locator('#navAsk').count()==1 and pg.inner_text('#navAsk h2')==pg.evaluate("TMC.t('navLeave')") and pg.locator('#navYes').count()==1 and pg.locator('#navNo').count()==1,'unsaved form → "Leave without saving?" Yes / No')
            pg.click('#navNo');pg.wait_for_timeout(200);ok(cur(pg)=='work' and pg.input_value('#exTxt')=='half typed note' and pg.locator('#navAsk').count()==0,'No → stays, typing kept')
            pg.click('#view .navBack');pg.wait_for_timeout(200);pg.click('#navYes');pg.wait_for_timeout(250);ok(cur(pg)=='home','Yes → leaves')
            pg.click('nav [data-tab=work]');pg.wait_for_timeout(250);ok(pg.input_value('#exTxt')=='','Yes → the draft is discarded')
            pg.click('#view .navBack');pg.wait_for_timeout(200);ok(pg.locator('#navAsk').count()==0 and cur(pg)=='home','clean form → no question')
            pg.click('nav [data-tab=work]');pg.wait_for_timeout(250);pg.fill('#exTxt','typed then redraw');pg.evaluate("TMC.render()");pg.wait_for_timeout(200)
            pg.click('#view .navBack');pg.wait_for_timeout(200);ok(pg.locator('#navAsk').count()==1,'typed, then the same screen redraws → Back still asks');pg.click('#navNo');pg.wait_for_timeout(150)
            pg.fill('#exTxt','x');pg.fill('#exTxt','');pg.click('#view .navBack');pg.wait_for_timeout(200);ok(pg.locator('#navAsk').count()==0 and cur(pg)=='home','typed then cleared (nothing left) → no question')
            pg.click('nav [data-tab=work]');pg.wait_for_timeout(250)
            if pg.locator('#exAdd').count():
                pg.fill('#exTxt','saved note');pg.click('#exAdd');pg.wait_for_timeout(400)
                ok(pg.locator('#navAsk').count()==0 and cur(pg)=='home','after Save → previous screen (no Leave ask)')
        elif pg.locator('#wjNew').count():
            pg.click('#wjNew');pg.wait_for_timeout(250)
            pg.fill('#wjName','half typed note');pg.click('#view .navBack');pg.wait_for_timeout(200)
            ok(pg.locator('#navAsk').count()==1 and pg.inner_text('#navAsk h2')==pg.evaluate("TMC.t('navLeave')") and pg.locator('#navYes').count()==1 and pg.locator('#navNo').count()==1,'unsaved job form → "Leave without saving?" Yes / No')
            pg.click('#navNo');pg.wait_for_timeout(200);ok(pg.locator('#wjForm').count()==1 and pg.input_value('#wjName')=='half typed note' and pg.locator('#navAsk').count()==0,'No → stays, typing kept')
            pg.click('#view .navBack');pg.wait_for_timeout(200);pg.click('#navYes');pg.wait_for_timeout(250)
            ok(pg.locator('#wjList').count()==1 and pg.locator('#wjName').count()==0,'Yes → leaves the form for the job list')
            pg.click('#view .navBack');pg.wait_for_timeout(200);ok(cur(pg)=='home','job list Back → Home')
            pg.click('nav [data-tab=work]');pg.wait_for_timeout(250);pg.click('#wjNew');pg.wait_for_timeout(200)
            ok(pg.input_value('#wjName')=='','Yes → the draft is discarded')
            pg.click('#view .navBack');pg.wait_for_timeout(200);ok(pg.locator('#navAsk').count()==0 and pg.locator('#wjList').count()==1,'clean form → no question')
            pg.click('#wjNew');pg.wait_for_timeout(200);pg.fill('#wjName','typed then redraw');pg.evaluate("TMC.render()");pg.wait_for_timeout(200)
            pg.click('#view .navBack');pg.wait_for_timeout(200);ok(pg.locator('#navAsk').count()==1,'typed, then the same screen redraws → Back still asks');pg.click('#navNo');pg.wait_for_timeout(150)
            pg.fill('#wjName','x');pg.fill('#wjName','');pg.click('#view .navBack');pg.wait_for_timeout(200);ok(pg.locator('#navAsk').count()==0 and pg.locator('#wjList').count()==1,'typed then cleared (nothing left) → no question')
            pg.click('#wjNew');pg.wait_for_timeout(200)
            if pg.locator('#wjSave').count():
                pg.fill('#wjName','saved note');pg.click('#wjSave');pg.wait_for_timeout(400)
                ok(pg.locator('#navAsk').count()==0 and pg.locator('#wjList').count()==1 and 'saved note' in pg.inner_text('#wjList'),'after Save → previous screen (no Leave ask)')
        else:print('  SKIP no #exTxt on work')
    # labels
    L=pg.evaluate("Object.keys(TMC.T)");lab={l:pg.evaluate("TMC.T[%r].navBack"%l) for l in L}
    ok(all(lab.values()) and len(set(lab.values()))==len(L) and all(pg.evaluate("!!(TMC.T[%r].navLeave&&TMC.T[%r].navYes&&TMC.T[%r].navNo)"%(l,l,l)) for l in L),'Back / Leave / Yes / No in every language %s'%lab)
    ok(pg.locator('nav.tabs [data-tab]').count()==len(T)+1,'bottom menu unchanged')
    ok(not errs,'no page errors %s'%errs[:2]);b.close()
finally:
    gas.kill();srv.shutdown();shutil.rmtree(TMP,ignore_errors=True)
print('\nBACK BUTTON: %d passed, %d failed'%(P,F));sys.exit(1 if F else 0)
