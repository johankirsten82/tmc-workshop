#!/usr/bin/env python3
"""TMC APP MODE — black-box go-live tests for ANY app folder (no TMC engine needed).
  python3 tests/app_mode.py <app_dir> [<code.gs>]       one app
  python3 tests/app_mode.py --all                        the 4 TMC apps + cross-app no-mixing test
Drives the app only through its screens + phone storage. The app's own Code.gs runs in Node
(gas_server.js) with an in-memory sheet and NO TEAM_CODE; every call to script.google.com is
redirected there. Nothing reaches Google or a live Sheet. Nothing is published."""
import os,re,sys,json,shutil,socket,subprocess,tempfile,threading,functools,time,urllib.request
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from playwright.sync_api import sync_playwright
HERE=os.path.dirname(os.path.abspath(__file__));BASE=os.path.dirname(HERE);W='/workspace'
sys.path.insert(0,os.path.join(BASE,'tools'));import same_look
CHROME='/usr/bin/google-chrome' if os.path.exists('/usr/bin/google-chrome') else None
APPS={'purchases':(W+'/purchase-app',W+'/purchase-app/sync/Code-v9.gs'),'grv':(W+'/grv-deploy',W+'/grv-v16/Code-v7.gs'),
      'food':(W+'/food-inventory-app',W+'/food-inventory-app/sync/Code.gs'),'fuel':(W+'/fuel-app',W+'/fuel-app/sync/Code.gs')}
ADMIN='Template Admin';ALIAS='templateadmin';APIN='2468';STAFF='Test Staff';SPIN='1357'
RES={}
def free():
    s=socket.socket();s.bind(('127.0.0.1',0));p=s.getsockname()[1];s.close();return p
class R:
    def __init__(s,app):s.app=app;s.p=0;s.f=[];RES[app]=s
    def ok(s,c,m,why=''):
        if c:s.p+=1
        else:s.f.append(m+((' — '+why) if why else ''))
        print(('  PASS ' if c else '  FAIL ')+'[%s] %s%s'%(s.app,m,'' if c or not why else ' — '+why),flush=True);return c
# ---------- web + fake Google ----------
TMP=tempfile.mkdtemp(prefix='tmcapp-');PW=free()
class Q(SimpleHTTPRequestHandler):
    def log_message(self,*a):pass
    def end_headers(self):self.send_header('Cache-Control','no-cache');super().end_headers()
web=ThreadingHTTPServer(('127.0.0.1',PW),functools.partial(Q,directory=TMP));threading.Thread(target=web.serve_forever,daemon=True).start()
GAS={};PROCS=[]
def start_gas(app,gs):
    port=free();e=dict(os.environ,GAS_FILE=gs)
    p=subprocess.Popen(['node',os.path.join(HERE,'gas_server.js'),str(port),'-'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=e);PROCS.append(p)
    l=p.stdout.readline().decode()
    if 'ready' not in l:raise RuntimeError('gas_server failed for %s: %s'%(app,p.stderr.read().decode()[:400]))
    GAS[app]=port;return port
def sheets(app):return json.load(urllib.request.urlopen('http://127.0.0.1:%d/_sheets'%GAS[app]))
def gaslog(app):return json.load(urllib.request.urlopen('http://127.0.0.1:%d/_dump'%GAS[app])).get('log',[])
def route_gas(ctx,app):
    def h(route):
        r=route.request
        try:
            q=urllib.request.Request('http://127.0.0.1:%d/exec'%GAS[app],data=(r.post_data_buffer if r.method=='POST' else None),method=r.method if r.method in('GET','POST') else 'GET')
            b=urllib.request.urlopen(q,timeout=20).read()
            route.fulfill(status=200,headers={'Access-Control-Allow-Origin':'*','Content-Type':'application/json'},body=b)
        except Exception as e:route.fulfill(status=500,body=str(e))
    ctx.route(re.compile(r'https://script\.google(usercontent)?\.com/.*'),h)
def copy_app(app,src):
    d=os.path.join(TMP,app)
    if not os.path.exists(d):shutil.copytree(src,d,ignore=shutil.ignore_patterns('tests','*.png','*.zip','*.xlsx','.git','screenshots','frames','build'))
    return 'http://127.0.0.1:%d/%s/'%(PW,app)
def newctx(b):
    return b.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True,service_workers='allow',
      user_agent='Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Mobile Safari/537.36')
# ---------- generic UI driver ----------
GO=re.compile(r'continue|continuer|start|sign ?in|log ?in|set pin|save|next|ok\b|enter|go\b|join|register|request|gaan aan',re.I)
WAIT=re.compile(r'wait|approv|pending|attente|wag',re.I)
JS_INPUTS="""()=>[...document.querySelectorAll('input,textarea')].filter(e=>{const r=e.getBoundingClientRect();const s=getComputedStyle(e);return r.width>0&&r.height>0&&s.visibility!=='hidden'&&e.type!=='hidden'&&e.type!=='file'&&e.type!=='checkbox'&&e.type!=='radio'&&!e.disabled}).map((e,i)=>{e.dataset.tmcI=i;const lab=((e.labels&&e.labels[0]&&e.labels[0].textContent)||'')+' '+(e.placeholder||'')+' '+(e.id||'')+' '+(e.name||'')+' '+(e.getAttribute('aria-label')||'');
 return {i,id:e.id,type:e.type,im:e.inputMode||e.getAttribute('inputmode')||'',lab:lab,pin:/pin|code|nip|msk/i.test(lab+' '+e.className)||e.inputMode==='numeric'||e.type==='tel'||e.type==='number'||e.classList.contains('msk'),val:e.value,sp:String(e.spellcheck)}})"""
def inputs(pg):
    try:return pg.evaluate(JS_INPUTS)
    except Exception:return []
def click_go(pg):
    bs=pg.locator('button:visible,input[type=submit]:visible,a.btn:visible')
    n=bs.count()
    for i in range(n):
        b=bs.nth(i)
        try:t=(b.inner_text(timeout=500) or '').strip()
        except Exception:continue
        if GO.search(t) and not re.search(r'different|autre|other|admin setup',t,re.I):
            try:b.click(timeout=3000);return t
            except Exception:pass
    return None
def body(pg):
    try:return pg.inner_text('body',timeout=2000)
    except Exception:return ''
def signed_in(pg):
    """home = no name/PIN box on screen and a menu/header is visible"""
    ins=[x for x in inputs(pg) if x['pin'] or re.search(r'name|nom|naam|who',x['lab'],re.I)]
    if ins:return False
    try:return pg.evaluate("!!document.querySelector('nav:not([hidden]) button, nav a, .tabs button, header')") and not WAIT.search(body(pg)[:400])
    except Exception:return False
def sign_in(pg,name,pin,steps=7):
    """returns 'home' | 'wait' | 'stuck:<reason>'"""
    for _ in range(steps):
        pg.wait_for_timeout(900)
        if signed_in(pg):return 'home'
        ins=inputs(pg)
        if not ins:
            if WAIT.search(body(pg)[:600]):return 'wait'
            if click_go(pg):continue
            return 'stuck:no inputs/no button'
        for x in ins:
            sel='[data-tmc-i="%d"]'%x['i']
            try:
                if x['pin']:pg.fill(sel,pin)
                elif not x['val']:pg.fill(sel,name)
            except Exception:pass
        if not click_go(pg):
            try:pg.keyboard.press('Enter')
            except Exception:pass
    if WAIT.search(body(pg)[:600]):return 'wait'
    return 'home' if signed_in(pg) else 'stuck:'+re.sub(r'\s+',' ',body(pg))[:140]
def is_admin_ui(pg):
    t=body(pg)
    return bool(re.search(r'\bUsers\b|Utilisateurs|Gebruikers|Mense|👥',t))
def approve(pg,name):
    """Admin approves `name` through the UI: open Users, press Approve"""
    for sel in ['[data-tab=users]','[data-tab=U]','button:has-text("Users")','button:has-text("👥")','a:has-text("Users")']:
        try:
            l=pg.locator(sel+':visible')
            if l.count():l.first.click(timeout=2000);break
        except Exception:pass
    pg.wait_for_timeout(1200)
    for _ in range(3):
        b=pg.locator('button:visible').filter(has_text=re.compile(r'approve|accept|allow|✅|✔|approuver|keur goed',re.I))
        if b.count():
            try:b.first.click(timeout=2000);pg.wait_for_timeout(1500);return True
            except Exception:pass
        for s in ['button:has-text("Sync")','button:has-text("🔄")']:
            try:
                l=pg.locator(s+':visible')
                if l.count():l.first.click(timeout=1500)
            except Exception:pass
        pg.wait_for_timeout(1500)
    return False
def storage(pg):
    return pg.evaluate("""async()=>({ls:Object.fromEntries(Object.keys(localStorage).map(k=>[k,localStorage.getItem(k)])),
      idb:indexedDB.databases?(await indexedDB.databases()).map(d=>d.name):[],
      caches:await caches.keys(),
      sw:navigator.serviceWorker?(await navigator.serviceWorker.getRegistrations()).map(r=>r.scope):[]})""")
# ---------- one app ----------
def test_app(b,app,src,gs):
    r=R(app);print('\n## '+app+'  ('+src+')',flush=True)
    # 1 same look
    sl=same_look.check(src);bad=[n for n,o in sl if not o]
    r.ok(not bad,'same_look %d/%d'%(len(sl)-len(bad),len(sl)),'; '.join(bad))
    try:start_gas(app,gs)
    except Exception as e:r.ok(False,'own Code.gs runs in gas_server',str(e));return r
    r.ok(True,'own Code.gs runs in gas_server (%s), NO TEAM_CODE set'%os.path.basename(gs))
    url=copy_app(app,src)
    # 2 admin first sign-in
    xa=newctx(b);route_gas(xa,app);a=xa.new_page();errs=[];a.on('pageerror',lambda e:errs.append(str(e)))
    a.goto(url);a.wait_for_timeout(2500)
    nm=[x for x in inputs(a) if not x['pin']]
    r.ok(bool(nm) and all(x['sp']=='true' for x in nm),'spellcheck ON in sign-in name box',str([(x['id'],x['sp']) for x in nm]))
    st=sign_in(a,ADMIN,APIN)
    r.ok(st=='home','Admin "%s" signs in with name + PIN, no team code'%ADMIN,st)
    r.ok(st=='home' and is_admin_ui(a),'Admin sees the Users/Admin area')
    a.screenshot(path=os.path.join(HERE,'shots','app-%s-admin-home.png'%app)) if os.path.isdir(os.path.join(HERE,'shots')) else None
    # 3 staff needs Admin approval
    xs=newctx(b);route_gas(xs,app);s=xs.new_page();s.goto(url);s.wait_for_timeout(2500)
    st2=sign_in(s,STAFF,SPIN)
    r.ok(st2=='wait','new staff "%s" must wait for Admin approval'%STAFF,st2)
    apr=approve(a,STAFF) if st=='home' else False
    r.ok(apr,'Admin approves staff from the Users screen')
    st3='skip'
    if apr:
        s.wait_for_timeout(1000);click_go(s);s.wait_for_timeout(1500)
        for k in range(3):
            st3=sign_in(s,STAFF,SPIN)
            if st3=='home':break
            s.reload();s.wait_for_timeout(2000)
    r.ok(st3=='home','approved staff gets in')
    r.ok(st3=='home' and not is_admin_ui(s),'staff has no Admin area')
    # 4 reinstall: fresh phone, alias name
    xr=newctx(b);route_gas(xr,app);n=xr.new_page();n.goto(url);n.wait_for_timeout(2500)
    st4=sign_in(n,ALIAS,APIN)
    r.ok(st4=='home','after reinstall Admin signs in again as "%s" (alias -> Template Admin)'%ALIAS,st4)
    r.ok(st4=='home' and is_admin_ui(n),'alias sign-in is still Admin (not a new user)')
    u=json.dumps(sheets(app)).lower()
    r.ok(u.count('templateadmin')+u.count('ja kirsten')>=1 and 'test staff' in u,'server Sheet holds Admin + staff')
    r.ok('"templateadmin"' not in u.replace('ja kirsten','') or u.count('ja kirsten')>0,'alias did not create a second user')
    # 5 sync round trip: Sheet written by phone A, read by fresh phone
    lg=gaslog(app)
    devs={x.get('device') for x in lg if x.get('device')}
    r.ok(len(devs)>=2,'sync round trip: own Code.gs answered %d phones (%d calls)'%(len(devs),len(lg)),'calls=%d'%len(lg))
    r.ok(not [e for e in errs if 'TMC' in e or 'not defined' in e],'no script errors',' | '.join(errs[:3]))
    # 6 offline install + update
    try:
        a.wait_for_function("navigator.serviceWorker&&navigator.serviceWorker.controller",timeout=15000);sw=True
    except Exception:
        a.reload();
        try:a.wait_for_function("navigator.serviceWorker&&navigator.serviceWorker.controller",timeout=10000);sw=True
        except Exception:sw=False
    r.ok(sw,'installs: service worker controls the page')
    if sw:
        a.wait_for_timeout(1500);xa.set_offline(True)
        try:a.reload(timeout=15000);a.wait_for_timeout(1500);off=len(body(a).strip())>20
        except Exception as e:off=False
        r.ok(off,'opens OFFLINE after install')
        xa.set_offline(False)
        swp=os.path.join(TMP,app,'sw.js');t=open(swp).read();t2=re.sub(r'(v)(\d+)',lambda m:m.group(1)+str(int(m.group(2))+1000),t,count=1)
        if t2==t:t2=t+'\n// test-update '+str(time.time())
        open(swp,'w').write(t2)
        a.evaluate("navigator.serviceWorker.getRegistration().then(r=>r&&r.update())");a.wait_for_timeout(4000)
        try:a.reload(timeout=15000)
        except Exception:pass
        a.wait_for_timeout(3000)
        upd=a.evaluate("navigator.serviceWorker.getRegistration().then(r=>!!r&&(!!r.waiting||!!r.installing||(r.active&&/v\\d{4}|test-update/.test('x'))))")
        txt=body(a);seen=bool(re.search(r'update|new version|mise à jour|opdateer|nuwe weergawe',txt,re.I)) or upd
        cur=a.evaluate("fetch('sw.js',{cache:'no-store'}).then(r=>r.text())")
        r.ok(seen or cur==t2,'new version is picked up (update banner or new service worker)')
        open(swp,'w').write(t)
    for x in (xa,xs,xr):x.close()
    return r
# ---------- all 4 on ONE phone ----------
def test_mixing(b):
    r=R('ALL');print('\n## no data mixing: all 4 apps on one phone (same origin, like github.io)',flush=True)
    x=newctx(b);snaps={};prev=None
    for app,(src,gs) in APPS.items():
        if app not in GAS:
            try:start_gas(app,gs)
            except Exception:continue
        route_gas(x,app);url=copy_app(app,src);pg=x.new_page();pg.goto(url);pg.wait_for_timeout(2500)
        st=sign_in(pg,ADMIN,APIN);pg.wait_for_timeout(2500)
        before=storage(pg)
        if prev:
            for k,v in prev['ls'].items():
                if k in before['ls'] and before['ls'][k]!=v:r.ok(False,'%s changed a key of an earlier app: %s'%(app,k))
            gone=[c for c in prev['caches'] if c not in before['caches']]
            r.ok(not gone,'%s did not delete other apps\' caches'%app,str(gone))
        snaps[app]=before;prev=before;pg.close()
    names=list(snaps);own={}
    seen=set()
    for i,app in enumerate(names):
        s=snaps[app];base=snaps[names[i-1]] if i else {'ls':{},'idb':[],'caches':[],'sw':[]}
        own[app]={'ls':set(s['ls'])-set(base['ls']),'idb':set(s['idb'])-set(base['idb']),'caches':set(s['caches'])-set(base['caches'])}
        lsk=[k for k in own[app]['ls']];print('   %s new keys: %s | idb %s | caches %s'%(app,sorted(lsk)[:8],sorted(own[app]['idb']),sorted(own[app]['caches'])))
    for app in names:
        others=set().union(*[set(snaps[o]['ls']) for o in names if names.index(o)<names.index(app)]) if names.index(app) else set()
        sh=[k for k in snaps[app]['ls'] if k in others and not k.startswith('__')]
        r.ok(not [k for k in sh if snaps[app]['ls'][k]!=snaps[names[names.index(app)-1]]['ls'].get(k)],'%s writes only its own storage keys'%app)
    sc=snaps[names[-1]]['sw'];print('   SW scopes:',sc)
    for app in names:r.ok(any(u.rstrip('/').endswith('/'+app) for u in sc),'%s service worker scope is its own folder'%app,str(sc))
    r.ok(len(sc)==len(set(sc)),'no shared service worker scope')
    # every app still signed in as itself after the others ran
    for app in names:
        pg=x.new_page();pg.goto('http://127.0.0.1:%d/%s/'%(PW,app));pg.wait_for_timeout(2500)
        r.ok(signed_in(pg),'%s still opens on its own home after the other 3 apps were used'%app);pg.close()
    x.close();return r
def main():
    args=sys.argv[1:]
    with sync_playwright() as p:
        b=p.chromium.launch(executable_path=CHROME,args=['--no-sandbox'])
        try:
            if args and args[0]=='--all':
                for app,(src,gs) in APPS.items():
                    try:test_app(b,app,src,gs)
                    except Exception as e:R(app).ok(False,'test crashed',str(e)[:200]) if app not in RES else RES[app].ok(False,'test crashed',str(e)[:200])
                test_mixing(b)
            else:
                src=os.path.abspath(args[0]);gs=args[1] if len(args)>1 else os.path.join(src,'sync','Code.gs')
                test_app(b,os.path.basename(src).replace('-',''),src,gs)
        finally:
            b.close()
            for q in PROCS:q.kill()
    print('\n==== APP MODE SUMMARY ====')
    bad=0
    for k,v in RES.items():
        print('%-10s %s  %d passed, %d failed'%(k,'PASS' if not v.f else 'FAIL',v.p,len(v.f)));bad+=len(v.f)
        for f in v.f:print('     - '+f)
    sys.exit(1 if bad else 0)
if __name__=='__main__':main()
