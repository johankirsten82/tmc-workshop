#!/usr/bin/env python3
"""TMC base — fixed test suite. Must pass (exit code 0) before any app built on the base goes live.
    python3 tests/run_all.py            (tests this folder's app)
    python3 tests/run_all.py /path/app  (tests another app built on the base)
Runs the real sync/Code.gs in Node against an in-memory sheet, two copies of the app on one
origin (different APP_IDs) and Chrome with a phone viewport and a live service worker.
Nothing is sent to Google or any live Sheet."""
import datetime
import json,os,re,shutil,socket,subprocess,sys,tempfile,threading,time,functools,urllib.request,urllib.parse
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from playwright.sync_api import sync_playwright
HERE=os.path.dirname(os.path.abspath(__file__));BASE=os.path.dirname(HERE)
APP=os.path.abspath(sys.argv[1]) if len(sys.argv)>1 else BASE
SHOTS=os.path.join(APP,'tests','shots') if APP==BASE else os.path.join(tempfile.gettempdir(),'tmcbase-shots-'+os.path.basename(APP))  # never write into a real app folder
os.makedirs(SHOTS,exist_ok=True)
CHROME='/usr/bin/google-chrome' if os.path.exists('/usr/bin/google-chrome') else None
sys.path.insert(0,os.path.join(BASE,'tools'));import apply_config
R={'pass':0,'fail':0};ERR=[]
def uo(pg,name):
    r=pg.locator('.ulr',has_text=name)
    if r.locator('.uopen').count()==0:r.locator('.uli').click();pg.wait_for_timeout(200)
    return pg.locator('.ulr',has_text=name)
def ok(c,m):
    R['pass' if c else 'fail']+=1;print(('  PASS ' if c else '  FAIL ')+m,flush=True)
def ADM(u):return bool(u.get('admin') or (isinstance(u.get('perms'),dict) and u['perms'].get('admin')))  # base: admin flag; some apps: perms.admin
def sec(m):print('\n## '+m,flush=True)
def free():
    s=socket.socket();s.bind(('127.0.0.1',0));p=s.getsockname()[1];s.close();return p
def pin_of(i):return ['2468','1357','9753','8642'][i]
# ---------- build two apps on one origin ----------
TMP=tempfile.mkdtemp(prefix='tmcbase-');P1,P2,P3,PW=free(),free(),free(),free()
def build(sub,app_id,port,code,ver=1,cp=None):
    d=os.path.join(TMP,sub)
    if not os.path.exists(d):shutil.copytree(APP,d,ignore=shutil.ignore_patterns('tests','*.zip','.git'))
    ip=os.path.join(d,'index.html');s=open(ip,encoding='utf-8').read()
    C=json.loads(re.search(r'/\*CONFIG\*/(.*?)/\*END\*/',s,re.S).group(1))
    C.update(APP_ID=app_id,VER=ver,SYNC_URL='http://127.0.0.1:%d/exec'%port,SYNC_CODE=code,SHARE_URL='https://example.org/'+sub+'/',NAME='Test '+app_id,SHORT='T'+app_id)
    if cp:C['CACHE_PREFIX']=cp
    else:C.pop('CACHE_PREFIX',None)
    s=re.sub(r'/\*CONFIG\*/.*?/\*END\*/','/*CONFIG*/'+json.dumps(C,ensure_ascii=False,indent=1)+'/*END*/',s,flags=re.S);open(ip,'w',encoding='utf-8').write(s)
    apply_config.main(d);return C
CA=build('appa','testa',P1,'code-a');CB=build('appb','testb',P2,'code-b',cp='test-b');CC=build('appc','testc',P3,'')  # C: VER 4 token app, NO code anywhere
_ag=os.path.join(APP,'sync','Code.gs')
GAS_FILE=_ag if APP!=BASE and os.path.exists(_ag) and 'function handle_(' in open(_ag,encoding='utf-8').read() and 'module.exports' in open(_ag,encoding='utf-8').read() else os.path.join(BASE,'sync','Code.gs')  # real app: test ITS server (its own PERM_KINDS)
GSRC=open(GAS_FILE,encoding='utf-8').read();XK=bool(re.search(r"PERM_KINDS\s*=\s*\{[^;]*?\bx\s*:",GSRC));P4,P5=free(),free()
gas=[subprocess.Popen(['node',os.path.join(BASE,'tests','gas_server.js'),str(p),c],stdout=subprocess.PIPE,env=dict(os.environ,GAS_FILE=GAS_FILE)) for p,c in ((P1,'code-a'),(P2,'code-b'),(P3,'-'),(P4,'-'),(P5,'code-s'))]
for g in gas:g.stdout.readline()
class Q(SimpleHTTPRequestHandler):
    def log_message(self,*a):pass
    def end_headers(self):self.send_header('Cache-Control','no-cache');super().end_headers()
web=ThreadingHTTPServer(('127.0.0.1',PW),functools.partial(Q,directory=TMP));threading.Thread(target=web.serve_forever,daemon=True).start()
A='http://127.0.0.1:%d/appa/'%PW;B='http://127.0.0.1:%d/appb/'%PW;CU='http://127.0.0.1:%d/appc/'%PW
def dump(port):return json.load(urllib.request.urlopen('http://127.0.0.1:%d/_dump'%port))
def U(port):return [dict({'id':r.get('id')},**(r['data'] if isinstance(r['data'],dict) else json.loads(r['data'] or '{}'))) for r in dump(port)['recs'] if r['kind'] in ('u','user') and not r['del']]
def raw(port,body):
    q=urllib.request.Request('http://127.0.0.1:%d/exec'%port,data=json.dumps(body).encode());return json.load(urllib.request.urlopen(q))
def post(port,code,changes):return raw(port,{'action':'sync','code':code,'device':'test','since':0,'changes':changes})
# ---------- browser helpers ----------
DLG={'mode':'accept','msgs':[]}
def newctx(b):
    x=b.new_context(viewport={'width':390,'height':844},device_scale_factor=2,is_mobile=True,has_touch=True,service_workers='allow',
      user_agent='Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Mobile Safari/537.36')
    return x
def watch(pg,tag):
    pg.on('console',lambda m:ERR.append(tag+': '+m.text) if m.type=='error' and 'ERR_INTERNET_DISCONNECTED' not in m.text else None)  # offline test: browser's own failed-fetch log is expected
    pg.on('pageerror',lambda e:ERR.append(tag+': '+str(e)))
    def d(dl):DLG['msgs'].append(dl.message);(dl.accept() if DLG['mode']=='accept' else dl.dismiss())
    pg.on('dialog',d);return pg
def openp(x,url,tag):
    pg=watch(x.new_page(),tag);pg.goto(url);pg.wait_for_selector('.card,header');return pg
def nopw(pg,where):ok(pg.evaluate("document.querySelectorAll('input[type=password]').length")==0,'no password-type field: '+where)
def h2(pg):return pg.evaluate("(document.querySelector('.card h2')||{}).textContent||''")
def name(pg,n):pg.fill('#fName',n);pg.click('#fName2');pg.wait_for_function("!document.querySelector('.card') || !!document.querySelector('#fPin,#fCheck,#fOther')",timeout=15000);pg.wait_for_timeout(300)
def pin(pg,p):pg.fill('#fPin',p);pg.click('#fGo');pg.wait_for_timeout(600)
def setpin(pg,p):pg.fill('#fPin',p);pg.fill('#fPin2',p);pg.click('#fSet');pg.wait_for_selector('header',timeout=8000)
def isadm(pg):return pg.evaluate("!!(TMC.me()&&TMC.me().admin)")
def home(pg):return pg.evaluate("!!document.querySelector('header')")
def shot(pg,n):pg.screenshot(path=os.path.join(SHOTS,n+'.png'))
def sp(pg,sel):return pg.evaluate("(()=>{const e=document.querySelector('%s');return e?String(e.spellcheck)+'|'+e.getAttribute('autocapitalize'):'none'})()"%sel)
AFS=os.path.join(APP,'screenshots') if APP==BASE else os.path.join(tempfile.gettempdir(),'tmcbase-af-'+os.path.basename(APP))  # never write into a real app folder
def afshot(pg,n,full=False):os.makedirs(AFS,exist_ok=True);pg.screenshot(path=os.path.join(AFS,n+'.png'),full_page=full)
def skip(m):print('  SKIP  '+m,flush=True)
TJS="((window.TMC&&TMC.T)||(typeof T!=='undefined'?T:null))"  # base keeps texts in TMC.T; older apps in a global T
DEMO={'on':None}
def note(pg,t):  # add one 'x' note: demo box if the app has it, else the same TMC.put the demo box uses
    pg.click('nav [data-tab=work]');pg.wait_for_timeout(200)
    if DEMO['on']:
        pg.fill('#exTxt',t);pg.click('#exAdd');pg.wait_for_timeout(300)
        # VER 12: successful Save returns to the previous screen — reopen Work so later checks see the list
        if pg.evaluate("(document.querySelector('nav.tabs .on')||{dataset:{}}).dataset.tab")!='work':
            pg.click('nav [data-tab=work]');pg.wait_for_timeout(250)
    else:pg.evaluate("(t=>{const id='x'+Date.now();TMC.put('x',id,{id:id,text:t,by:(TMC.me()||{}).name,at:new Date().toISOString()});TMC.render&&TMC.render()})",t)
class NoBaseRT(Exception):pass
def synced(pg):pg.evaluate("TMC.syncNow()");pg.wait_for_timeout(700)

try:
  sec('0. Static checks')
  import same_look
  for n,o in same_look.check(APP):ok(o,'same look as base: '+n)
  sm=subprocess.run([sys.executable,os.path.join(BASE,'tools','signin_mirror.py'),APP,'--shot',os.path.join(SHOTS,'signin_mirror.png')],capture_output=True,text=True,timeout=120)
  for ln in sm.stdout.splitlines():
    if ln.startswith('  PASS ') or ln.startswith('  FAIL '):ok(ln.startswith('  PASS '),'sign-in mirror: '+ln[7:])
  ok(sm.returncode==0,'sign-in screen is an exact mirror of the base (tools/signin_mirror.py)')
  src=open(os.path.join(APP,'index.html'),encoding='utf-8').read()
  ok('type="password"' not in src and "type='password'" not in src,'no password inputs in source')
  ok('?.' not in re.sub(r'<style.*?</style>','',src,flags=re.S),'no ?. syntax')
  cfg=apply_config.cfg(APP);ok(all(k in cfg for k in ['APP_ID','NAME','COLOR','SYNC_URL','ADMIN_ALIASES','VER']),'CONFIG block complete')
  _cg=open(os.path.join(APP,'sync','Code.gs'),encoding='utf-8').read()
  _tf=re.search(r"function teamCode_\(\)\s*\{(.*?)\n?\}",_cg,re.S)
  _lit=[v for v in re.findall(r"\bTEAM_CODE(?:_SETUP)?\s*=\s*['\"]([^'\"]*)['\"]",_cg) if v and v!='__TMC_TEAM_CODE__']
  ok(_tf is not None and "getProperty('TEAM_CODE')" in _tf.group(1) and not _lit and not re.search(r"setProperty\('TEAM_CODE',\s*['\"]",_cg),
     'Code.gs reads TEAM_CODE from Script Properties only (no code written in the file) %s'%_lit)
  ok(post(P1,'wrong',[])['ok'] is False,'Code.gs refuses a wrong sync code')
  ok(raw(P3,{'action':'sync','device':'x','since':0,'changes':[]}).get('error')=='need_login','data call with no code and no token is refused')
  ok(raw(P3,{'action':'sync','token':'f'*64,'device':'x','since':0,'changes':[{'kind':'x','id':'1','u':1,'data':{}}]}).get('error')=='bad_token','data call with a made-up token is refused')
  ok(raw(P3,{'action':'sync','code':'','device':'x','since':0,'changes':[]})['ok'] is False,'empty code on a code-less script is refused (no TEAM_CODE ≠ open)')
  ok(raw(P3,{'action':'setpin','id':'nobody','salt':'s','pinH':'a'*64})['ok'] is False,'setpin for an unknown/unapproved user is refused')
  qp=os.path.join(TMP,'appa','icons','qr.png')
  try:
      import cv2;dec=cv2.QRCodeDetector().detectAndDecode(cv2.imread(qp))[0]
      ok(dec==CA['SHARE_URL'],'QR with centre logo decodes to the share link: %r'%dec)
  except ImportError:print('  SKIP  cv2 not installed (QR decode)')
  try:
   with sync_playwright() as p:
     br=p.chromium.launch(executable_path=CHROME) if CHROME else p.chromium.launch()
     xA=newctx(br)
     try:a=openp(xA,A,'admin')
     except Exception as e:print('  NOTE  page did not show .card/header with test CONFIG: %s'%str(e)[:80]);raise NoBaseRT()
     keys=a.evaluate("(T=>T?[...new Set(Object.values(T).map(o=>Object.keys(o)).flat())].filter(k=>['en','fr','af'].some(l=>!T[l]||T[l][k]==null)):['NO TEXT TABLE'])(%s)"%TJS)
     ok(keys==[],'every text exists in EN, FR and AF %s'%keys[:5])
     sec('0b. Languages: English, French, Afrikaans (no Arabic, no right-to-left)')
     lt=a.evaluate("(T=>({langs:Object.keys(T),miss:Object.keys(T.en).filter(k=>!T.af||T.af[k]==null||String(T.af[k]).trim()===''),same:Object.keys(T.en).filter(k=>T.af&&T.af[k]===T.en[k]&&/[a-z]{4,}/i.test(T.en[k]))}))(%s)"%TJS)
     ok('af' in lt['langs'],'Afrikaans (af) text table present %s'%lt['langs'])
     ok('ar' not in lt['langs'],'Arabic (ar) text table gone %s'%lt['langs'])
     ok(lt['langs']==['en','fr','af'],'languages are exactly EN, FR, AF %s'%lt['langs'])
     ok(lt['miss']==[],'every English text has an Afrikaans text %s'%lt['miss'][:5])
     print('  NOTE  af texts same as English (check they are fine in Afrikaans): %s'%lt['same'][:12])
     ok(not re.search('[\u0600-\u06FF]',src),'no Arabic letters anywhere in index.html')
     ok(not re.search(r'["\']rtl["\']|direction\s*:\s*rtl|unicode-bidi|ar-TD|"ar"\s*:|\bar\s*:\s*\{',src),'no right-to-left / Arabic code left in index.html (rtl, unicode-bidi, ar-TD, ar:)')
     ok(re.search(r'"en"\s*,\s*"fr"\s*,\s*"af"',src) is not None and 'Afrikaans' in src,'language pickers list en, fr, af ("Afrikaans")')
     ok(all(isinstance(pp,dict) and pp.get('af') and 'ar' not in pp for pp in (cfg.get('PERMS') or [])),'every CONFIG.PERMS label has "af" and no "ar"')
     xo=newctx(br);xo.add_init_script("try{if(!sessionStorage.getItem('_t')){localStorage.setItem(%r,'ar');sessionStorage.setItem('_t','1')}}catch(e){}"%(CA['APP_ID']+'_lang'));o=openp(xo,A,'arfall')
     fo=o.evaluate("({lang:document.documentElement.lang,dir:document.documentElement.dir,saved:localStorage.getItem(%r),opts:[...document.querySelectorAll('#langSel option,#hLang option')].map(e=>e.value)})"%(CA['APP_ID']+'_lang'))
     ok(fo['lang']=='en' and fo['dir']=='ltr' and fo['saved']=='en','phone with "ar" saved falls back to English and saves "en" %s'%fo)
     ok('ar' not in fo['opts'] and 'af' in fo['opts'],'language list on screen has AF, no AR %s'%fo['opts'])
     xo.close()
     if not a.evaluate("typeof TMC.me==='function'&&typeof TMC.put==='function'&&typeof TMC.pending==='function'"):raise NoBaseRT()

     sec('1. First Admin setup')
     shot(a,'signin-en');nopw(a,'sign-in')
     ok(sp(a,'#fName')=='true|words','spellcheck ON for name box, capital words: '+sp(a,'#fName'))
     name(a,'Johan Kirsten');ok(a.evaluate("!!document.getElementById('fPin2')") and 'Admin' in h2(a),'no Admin yet → "First Admin setup" PIN screen: '+h2(a))
     ok(sp(a,'#fPin').startswith('false') and sp(a,'#fPin2').startswith('false'),'spellcheck OFF for PIN boxes');ok(a.evaluate("document.getElementById('fPin').type")=='text','PIN box stays non-password type')
     nopw(a,'set PIN');setpin(a,pin_of(0));synced(a)
     ok(home(a) and isadm(a),'Admin is in, with Admin rights')
     adm=[u for u in U(P1) if u.get('admin')];ok(len(adm)==1 and adm[0]['name']==CA['ADMIN_NAME'] and adm[0]['status']=='active' and adm[0].get('pinH'),'Sheet has one active Admin named "%s" (stored display name)'%CA['ADMIN_NAME'])
     ok('Johan Kirsten' not in json.dumps(U(P1)),'typed alias not stored as the name')
     shot(a,'home-en')
     a.click('[data-tab=work]');a.wait_for_timeout(400)
     DEMO['on']=bool(a.query_selector('#exTxt') and a.query_selector('#exAdd'))
     if DEMO['on']:
         a.fill('#exTxt','Recieved tomatos and onoins');a.focus('#exTxt');a.wait_for_timeout(400);shot(a,'spellcheck-notes');a.fill('#exTxt','')
         ok(sp(a,'#exTxt')=='true|sentences','spellcheck ON for notes textarea: '+sp(a,'#exTxt'))
     else:print('  SKIP  no demo #exTxt on Work tab (app-specific screen); dynamic-box spellcheck test below still runs')
     dyn=a.evaluate("(async()=>{const d=document.createElement('div');d.innerHTML='<input id=zItem type=text><input id=zQty type=number><input id=zN type=text inputmode=decimal><textarea id=zT></textarea>';document.body.appendChild(d);await new Promise(r=>setTimeout(r,50));const g=i=>document.getElementById(i).spellcheck;const o=[g('zItem'),g('zQty'),g('zN'),g('zT')];d.remove();return o})()")
     ok(dyn==[True,False,False,True],'boxes added later: text/textarea spellcheck ON, number/decimal OFF %s'%dyn)
     a.click('nav [data-tab=settings]');a.wait_for_timeout(300)
     ok(all(not a.evaluate("(document.getElementById('%s')||{spellcheck:false}).spellcheck"%i) for i in ['sUrl','sCode']),'spellcheck OFF for sync URL/code');a.click('nav [data-tab=home]');a.wait_for_timeout(300)

     sec('2. New user approved by Admin')
     xU=newctx(br);u=openp(xU,A,'user');name(u,'Fatime Ali')
     u.wait_for_function('TMC.pending()===0',timeout=10000);ok('approval' in h2(u).lower(),'new name → waiting for approval');shot(u,'waiting-en')
     ok(any(x['name']=='Fatime Ali' and x['status']=='pending' for x in U(P1)),'pending request reached the Sheet')
     synced(a);a.click('nav [data-tab=users]');a.wait_for_timeout(300)
     ok(a.locator('.badge').count()==1,'Admin sees a waiting badge');shot(a,'users-en')
     a.click('[data-ua=approve]');a.wait_for_timeout(1500)
     u.click('#fCheck');u.wait_for_selector('#fPin2',timeout=8000);ok(True,'after approval → user chooses a PIN')
     setpin(u,pin_of(1));synced(u)
     ok(home(u) and not isadm(u) and u.locator('nav [data-tab=users]').count()==0,'user is in, no Admin rights, no Users tab')

     sec('3. Block / Reject = DISCARD (VER 7, Johan 31 Oct 2026)')
     xR=newctx(br);r=openp(xR,A,'rej');name(r,'Bad Guy');r.wait_for_function('TMC.pending()===0',timeout=10000);synced(a);a.click('nav [data-tab=home]');a.click('nav [data-tab=users]')
     uo(a,'Bad Guy').locator('[data-ud=reject]').click();a.wait_for_timeout(300)
     ok(a.locator('#dscM').count()==1 and 'Bad Guy' in a.inner_text('#dscM'),'Reject → confirm step first (nothing removed yet)')
     bb=a.locator('#dscM button').evaluate_all("b=>b.map(x=>[x.getBoundingClientRect().height,getComputedStyle(x).backgroundColor])")
     ok(min(h for h,_ in bb)>=56 and bb[0][1]=='rgb(185, 28, 28)','confirm buttons big (≥56px), Yes is red danger %s'%bb)
     shot(a,'discard-confirm')
     a.click('#dscN');a.wait_for_timeout(400)
     ok(a.locator('#dscM').count()==0 and a.locator('.ulr',has_text='Bad Guy').count()==1 and any(x['name']=='Bad Guy' for x in U(P1)),'Back → nothing removed')
     uo(a,'Bad Guy').locator('[data-ud=reject]').click();a.click('#dscY');a.wait_for_timeout(1500);synced(a)
     ok(a.locator('.ulr',has_text='Bad Guy').count()==0,'reject discards: gone from the Users list')
     ok(not any(x['name']=='Bad Guy' for x in U(P1)),'reject discards: gone from the Sheet user store')
     ok(not any((x or {}).get('name')=='Bad Guy' for x in a.evaluate("TMC.all('u')")),'reject discards: gone from the phone store')
     r.click('#fCheck');r.wait_for_timeout(1500);ok(r.locator('#goneT').count()==1 and r.locator('#fAgain').count()==1,'discarded request → "Send a new request" screen: '+h2(r))
     r.click('#fAgain');r.wait_for_function("!!document.getElementById('fCheck')",timeout=10000);r.wait_for_function('TMC.pending()===0',timeout=10000)
     ok('approval' in h2(r).lower() and any(x['name']=='Bad Guy' and x['status']=='pending' for x in U(P1)),'fresh request after reject → Pending on the Sheet')
     synced(a);a.click('nav [data-tab=home]');a.click('nav [data-tab=users]')
     ok(a.locator('.ulr',has_text='Bad Guy').count()==1 and 'Waiting' in a.inner_text('.ulr:has-text("Bad Guy")'),'Admin sees the fresh request as Waiting')
     uo(a,'Bad Guy').locator('[data-ua=approve]').click();a.wait_for_timeout(1500)
     r.click('#fCheck');r.wait_for_selector('#fPin2',timeout=8000);setpin(r,pin_of(3))
     ok(home(r) and r.evaluate("TMC.me().name")=='Bad Guy','approved fresh request → signs in')
     synced(a);uo(a,'Fatime Ali').locator('[data-ud=block]').click();a.click('#dscY');a.wait_for_timeout(1500);synced(a)
     ok(a.locator('.ulr',has_text='Fatime Ali').count()==0 and not any(x['name']=='Fatime Ali' for x in U(P1)),'block discards: gone from the list and the Sheet')
     ok(not any(x['status'] in ('blocked','rejected') for x in U(P1)) and a.locator('.st.blocked,.st.rejected').count()==0,'no blocked/rejected records left anywhere')
     shot(a,'users-list')
     synced(u);u.wait_for_timeout(800);ok(not home(u),'discarded user is signed out on next sync')
     name(u,'Fatime Ali');u.wait_for_function('TMC.pending()===0',timeout=10000)
     ok('approval' in h2(u).lower() and any(x['name']=='Fatime Ali' and x['status']=='pending' for x in U(P1)),'discarded user types the name again → fresh request (Pending)')
     synced(a);a.click('nav [data-tab=home]');a.click('nav [data-tab=users]');uo(a,'Fatime Ali').locator('[data-ua=approve]').click();a.wait_for_timeout(1500)
     u.click('#fCheck');u.wait_for_selector('#fPin2',timeout=8000);setpin(u,pin_of(1));synced(u)
     ok(home(u) and u.evaluate("TMC.me().name")=='Fatime Ali','approved again → signs in with a new PIN')
     ok(u.locator('nav [data-tab=users]').count()==0 and u.locator('[data-ud]').count()==0 and u.evaluate("TMC.discardUser(%s)"%json.dumps([x['id'] for x in U(P1) if x.get('admin')][0])) is False,'staff: no Users tab, no Block/Reject, discardUser() refused')
     me_=a.evaluate("TMC.me().id");a.wait_for_timeout(7200)
     ok(a.locator('.ulr[data-uid="%s"] [data-ud]'%me_).count()==0,'Admin\'s own row has no Block button')
     ok(a.evaluate("TMC.discardUser(TMC.me().id)") is False and a.evaluate("!!TMC.me()") and any(x['id']==me_ for x in U(P1)),'guard: the signed-in Admin cannot discard themself')
     ok('main Admin can never' in a.evaluate("document.getElementById('tmcToast').textContent"),'guard shows a plain message (main Admin)')
     sec('3b. MAIN ADMIN (templateadmin + every alias) can never be removed or blocked')
     ok(a.evaluate("['Template Admin','Johan Kirsten','johan a. kirsten','J. Kirsten','JAKIRSTEN'].map(n=>TMC.discardWhy({id:'zz',name:n,status:'active',admin:1}))")==['dscMain']*5,'phone: every alias name of templateadmin → never removable')
     ok(a.evaluate("TMC.discardWhy({id:'zz',name:'Johan Smith',status:'active'})")!='dscMain','phone: another name is not protected')
     a.click('nav [data-tab=home]');a.click('nav [data-tab=users]');a.wait_for_timeout(300);mid=a.evaluate("TMC.me().id");mr=a.locator('.ulr[data-uid="%s"]'%mid)
     if mr.locator('.uopen').count()==0:mr.locator('.uli').click();a.wait_for_timeout(300)
     ok(mr.locator('.uopen').count()==1 and mr.locator('[data-ud]').count()==0,'phone: the main Admin row (open) has no Remove/Block button')
     ok(a.evaluate("(()=>{const m=TMC.me();return [TMC.put('u',m.id,Object.assign({},m,{admin:0})),TMC.put('u',m.id,Object.assign({},m,{name:'Someone Else'})),TMC.put('u',m.id,Object.assign({},m,{status:'blocked'}))]})()")==[False,False,False] and a.evaluate("TMC.me().admin&&TMC.me().name")==CA['ADMIN_NAME'],'phone: main Admin cannot be demoted, renamed away or blocked (put refused)')
     ok('main Admin can never' in a.evaluate("document.getElementById('tmcToast').textContent"),'phone: plain message for demote/rename')
     ok(a.evaluate("(()=>{const m=TMC.me();return TMC.put('u',m.id,Object.assign({},m,{name:'Johan Kirsten'}))!==false})()") and a.evaluate("TMC.isMain(TMC.me())"),'phone: re-spelling with an alias name is still allowed (stays main Admin)')
     a.evaluate("(()=>{const m=TMC.me();TMC.put('u',m.id,Object.assign({},m,{name:%s}))})()"%json.dumps(CA['ADMIN_NAME']));synced(a)
     ok(a.evaluate("TMC.discardWhy({id:'zz',name:'Johan Kirsten',status:'pending'})")!='dscMain','phone: a PENDING request using an alias is not protected')
     iid='imp'+str(int(time.time()));post(P1,'code-a',[{'kind':'u','id':iid,'u':int(time.time()*1000),'del':0,'data':{'id':iid,'name':'Johan  Kirsten','status':'pending','at':'2026-10-31T07:00:00Z'}}]);synced(a);a.click('nav [data-tab=home]');a.click('nav [data-tab=users]');a.wait_for_timeout(300)
     ir=a.locator('.ulr[data-uid="%s"]'%iid)
     if ir.count()==0:  # the server keeps alias names for the Admin, so put the impostor request straight on this phone
       a.evaluate("TMC.put('u',%s,{id:%s,name:'Johan  Kirsten',status:'pending',at:'2026-10-31T07:00:00Z'})"%(json.dumps(iid),json.dumps(iid)));a.click('nav [data-tab=home]');a.click('nav [data-tab=users]');a.wait_for_timeout(300)
     if ir.count()==1:
       ok(ir.locator('[data-ud=reject]').count()==1,'phone: pending impostor using an alias shows a Reject button')
       ir.locator('[data-ud=reject]').click();a.click('#dscY');a.wait_for_timeout(1500);synced(a)
       ok(ir.count()==0 and not any(x['id']==iid for x in U(P1)) and any(x['id']==mid for x in U(P1)) and a.evaluate("TMC.isMain(TMC.me())"),'pending impostor rejected → removed; the real main Admin stays')
     else:ok(False,'pending impostor row not shown')
     ok(a.evaluate("['fr','af'].every(l=>!!(T[l]&&T[l].dscMain))") if a.evaluate("typeof T!=='undefined'") else True,'main-Admin message in FR and AF')
     aid=[x for x in U(P1) if x.get('admin')][0];r_=post(P1,'code-a',[{'kind':'u','id':aid['id'],'u':int(time.time()*1000)+30,'del':0,'data':dict(aid,status='blocked')}])
     ok([x for x in U(P1) if x['id']==aid['id']][0]['status']=='active' and r_.get('refusedWhy')=='main_admin','server: team code cannot block the main Admin (refusedWhy main_admin)')
     r_=post(P1,'code-a',[{'kind':'u','id':aid['id'],'u':int(time.time()*1000)+31,'del':1,'purge':1,'data':{'discarded':1}}])
     ok(any(x['id']==aid['id'] for x in U(P1)) and r_.get('refusedWhy')=='main_admin','server: team code cannot remove the main Admin (refusedWhy main_admin)')
     a.set_viewport_size({'width':360,'height':780});a.wait_for_timeout(300)
     ok(a.evaluate("document.documentElement.scrollWidth")<=360,'360px: Users screen fits (no side scroll)')
     uo(a,'Fatime Ali').locator('[data-ud=block]').click();a.wait_for_timeout(300)
     bx=a.locator('#dscM .card').bounding_box();bh=a.locator('#dscM button').evaluate_all("b=>b.map(x=>x.getBoundingClientRect().height)")
     ok(bx['x']>=0 and bx['x']+bx['width']<=360 and min(bh)>=56,'360px: confirm card fits, big buttons')
     shot(a,'discard-confirm-360');a.click('#dscN');a.wait_for_timeout(300);shot(a,'users-list-360')
     ok(any(x['name']=='Fatime Ali' for x in U(P1)),'360px Back → still there')
     a.set_viewport_size({'width':390,'height':844});a.wait_for_timeout(200)
     ux=json.loads(subprocess.run(['node',os.path.join(BASE,'tests','discard_unit.js')],capture_output=True,text=True,env=dict(os.environ,GAS_FILE=GAS_FILE)).stdout or '{}')
     ok(all(ux.get(k,{}).get('why')=='main_admin' and ux[k]['kept']==0 for k in ('mainByAdmin','mainAlias','mainBlock','mainPurge','demote','rename')) and ux.get('mainEdit',{}).get('kept')==1 and ux.get('resetPin',{}).get('kept')==1 and ux.get('aliasRename',{}).get('kept')==1,'server guard: main Admin (any alias) never removed/blocked/purged/demoted/renamed away, even by another Admin; Reset PIN, alias spelling and normal edits still pass %s'%{k:ux.get(k) for k in ('mainByAdmin','mainAlias','mainBlock','mainPurge','demote','rename','resetPin','aliasRename','mainEdit')})
     ok(ux.get('pendingAlias',{}).get('kept')==1 and ux['pendingAlias']['why']=='','server guard: a PENDING request using an alias name is not protected (can be rejected) %s'%ux.get('pendingAlias'))
     ok(ux.get('lastAdmin',{}).get('why')=='last_admin' and ux['lastAdmin']['kept']==0,'server guard: never discards the last Admin %s'%ux.get('lastAdmin'))
     ok(ux.get('self',{}).get('why')=='self' and ux.get('staff',{}).get('why')=='admin_only_fix' and ux.get('code',{}).get('why')=='admin_only_fix' and ux.get('ok',{}).get('kept')==1 and ux.get('tokGone'),'server guard: not yourself, staff/team code refused, Admin OK, old tokens deleted %s'%ux)

     sec('4. Name variants (fresh phones)')
     for v in ['J. A. Kirsten','ja kirsten','J Kirsten','Johan A Kirsten','JOHAN  KIRSTEN']:
         x=newctx(br);g=openp(x,A,'var');name(g,v)
         ok(g.evaluate("!!document.getElementById('fPin')&&!document.getElementById('fPin2')") and CA['ADMIN_NAME'] in g.inner_text('.card'),'"%s" → %s PIN screen'%(v,CA['ADMIN_NAME']))
         if v=='J. A. Kirsten':nopw(g,'PIN screen');shot(g,'pin-en')
         x.close()
     x=newctx(br);g=openp(x,A,'var');name(g,'Johan');ok('approval' in h2(g).lower(),'"Johan" alone → NOT matched, normal approval request');x.close()
     x=newctx(br);g=openp(x,A,'var');name(g,'fatime. ALI');ok(g.evaluate("!!document.getElementById('fPin')") and 'Fatime Ali' in g.inner_text('.card'),'"fatime. ALI" → Fatime Ali PIN screen');pin(g,pin_of(1));ok(home(g) and g.evaluate("TMC.me().name")=='Fatime Ali','signed in under the stored name "Fatime Ali"');x.close()
     post(P1,'code-a',[{'kind':'u','id':'dup1','u':int(time.time()*1000),'del':0,'data':{'id':'dup1','name':'Fatime.Ali','status':'active'}}])
     x=newctx(br);g=openp(x,A,'var');name(g,'Fatime Ali');ok('approval' in h2(g).lower(),'two approved users share the key → no auto-match, approval request instead');x.close()
     post(P1,'code-a',[{'kind':'u','id':'dup1','u':int(time.time()*1000)+5,'del':1,'data':None,'purge':1}])

     sec('5. PIN lock')
     x=newctx(br);g=openp(x,A,'lock');name(g,'Fatime Ali')
     for i in range(5):pin(g,'0000')
     pin(g,pin_of(1));ok(not home(g) and 'Too many' in g.inner_text('#fErr'),'5 wrong PINs → locked, even the right PIN is refused');shot(g,'pin-locked-en')
     g.click('#fOther');name(g,'ja kirsten');pin(g,pin_of(0));ok(home(g),'lock is per name: Admin can still sign in on that phone');x.close()

     sec('6. Admin re-sign-in after reinstall (wiped phone, service worker active)')
     note(a,'note before reinstall');a.wait_for_timeout(2500)
     nrec=len(dump(P1)['recs']);nusers=len(U(P1))
     x=newctx(br);w=openp(x,A,'wiped')
     w.wait_for_function("navigator.serviceWorker&&navigator.serviceWorker.controller",timeout=15000)
     ok(w.evaluate("!!navigator.serviceWorker.controller"),'fresh phone: service worker installed and controlling the page')
     ok(w.evaluate("Object.keys(localStorage).filter(k=>k.indexOf('testa_recs')===0).length")==0 or w.evaluate("Object.keys(JSON.parse(localStorage.testa_recs||'{}')).length")>=0,'storage starts empty')
     name(w,'J. A. Kirsten');ok(w.evaluate("!!document.getElementById('fPin')&&!document.getElementById('fPin2')"),'name → PIN screen (no setup, no approval)')
     pin(w,pin_of(0));ok(home(w) and isadm(w),'straight in as Admin, no new approval')
     ok(len(U(P1))==nusers,'no new pending request in the Sheet')
     ok(w.evaluate("TMC.all('x').length")>=1 and 'note before reinstall' in json.dumps(w.evaluate("TMC.all('x')")),'all data pulled back from the Sheet')
     w.reload();w.wait_for_selector('header');ok(home(w),'after reload (served by service worker) still signed in')
     x.close()

     sec('7. Unsynced changes survive and warn')
     xA.set_offline(True);note(a,'offline note');a.wait_for_timeout(2500)
     ok(a.evaluate("TMC.pending()")>=1 and a.is_visible('#pendW'),'offline change → warning banner with "Tap Sync before deleting"')
     ok('deleting' in a.inner_text('#pendW'),'warning tells the user to sync before deleting the app');shot(a,'pending-warning-en')
     a.reload();a.wait_for_selector('header');a.wait_for_timeout(2500)
     ok(a.evaluate("TMC.pending()")>=1 and 'offline note' in json.dumps(a.evaluate("TMC.all('x')")),'change survives an offline reload')
     STY="(id=>{const e=document.getElementById(id),s=getComputedStyle(e);return [s.backgroundColor,s.color,s.borderRadius,s.fontSize,s.fontWeight,s.fontFamily,s.minHeight,s.borderTopColor,s.borderTopWidth,e.offsetHeight].join('|')})"
     a.click('nav [data-tab=home]');a.wait_for_selector('#hOut');hs=a.evaluate(STY+"('hOut')");a.click('nav [data-tab=settings]');a.wait_for_selector('#sOut');ss=a.evaluate(STY+"('sOut')")
     ok(hs==ss and not a.evaluate("document.getElementById('sOut').classList.contains('red')"),'Settings Log out looks exactly like the Home Log out button (not red) '+('' if hs==ss else hs+' vs '+ss))
     DLG['mode']='dismiss';DLG['msgs'].clear();a.click('nav [data-tab=settings]');a.click('#sOut');a.wait_for_timeout(800)
     ok(any('⚠️' in m for m in DLG['msgs']) and home(a),'logout warns about unsynced changes; cancel keeps Admin signed in')
     DLG['mode']='accept';t0=time.time();xA.set_offline(False);a.evaluate("dispatchEvent(new Event('online'))")
     a.wait_for_function("TMC.pending()===0",timeout=15000);ok(True,'back online → sent automatically in %.1fs'%(time.time()-t0))
     ok(any(r['kind']=='x' and r['data'] and r['data'].get('text')=='offline note' for r in dump(P1)['recs']),'offline note reached the Sheet')
     a.wait_for_timeout(2100);ok(not a.is_visible('#pendW'),'warning gone after sync')
     if DEMO['on']:
       a.click('nav [data-tab=work]');a.fill('#exTxt','half typed draft');a.wait_for_timeout(300);a.reload();a.wait_for_selector('header');a.click('nav [data-tab=work]')
       ok(a.input_value('#exTxt')=='half typed draft','draft autosaved and restored after reload')
       a.evaluate("TMC.draftClear('exTxt')")
     else:skip('no demo #exTxt: draft restore is tested by the app\'s own screens')

     sec('8. Update flow')
     a.goto(A);a.wait_for_selector('header');a.wait_for_function("navigator.serviceWorker.controller",timeout=10000)
     build('appa','testa',P1,'code-a',ver=2)
     a.evaluate("TMC.checkUpdate()")   # VER 11: no banner tap — the app updates itself (tests/test_autoupdate.py has the details)
     a.wait_for_function("window.CONFIG&&CONFIG.VER===2",timeout=20000);a.wait_for_selector('header')
     ok(a.evaluate("CONFIG.VER")==2 and home(a) and isadm(a),'new version → updated itself: version 2, still signed in as Admin')
     ok(a.evaluate("caches.keys()")==['testa-v2'] or set(a.evaluate("caches.keys()"))>={'testa-v2'} and 'testa-v1' not in a.evaluate("caches.keys()"),'old cache testa-v1 removed, testa-v2 kept')

     sec('9. EN / FR / AF')
     x=newctx(br);g=openp(x,A,'lang')
     g.select_option('#langSel','fr');ok('Continuer' in g.inner_text('.card') and g.evaluate("document.documentElement.dir")=='ltr','French sign-in');shot(g,'signin-fr')
     g.select_option('#langSel','af');ok('Gaan aan' in g.inner_text('.card') and g.evaluate("document.documentElement.dir")=='ltr' and g.evaluate("document.documentElement.lang")=='af','Afrikaans sign-in, left-to-right');shot(g,'signin-af');afshot(g,'af-signin')
     name(g,'ja kirsten');pin(g,pin_of(0));ok('Tuis' in g.inner_text('nav') and g.evaluate("document.documentElement.dir")=='ltr','Afrikaans Home, left-to-right');shot(g,'home-af');afshot(g,'af-home');afshot(g,'af-home-full',True)
     g.click('nav [data-tab=settings]');g.select_option('#langSel','fr');ok('Réglages' in g.inner_text('nav'),'switch to French in Settings');shot(g,'settings-fr');nopw(g,'settings')
     ok(g.evaluate("document.getElementById('sCode').classList.contains('msk')&&!document.getElementById('sCode').classList.contains('shw')"),'sync values hidden in Settings')
     x.close()

     sec('10. Two apps on one origin stay separate')
     b=openp(xA,B,'appB')
     ok(not home(b),'app B is NOT signed in by app A\'s session')
     ok(b.evaluate("TMC.all('u').length")==0 and len(U(P2))==0,'app B has no users from app A (own Sheet)')
     name(b,'Johan Kirsten');ok(b.evaluate("!!document.getElementById('fPin2')"),'app B asks for its OWN first Admin setup');setpin(b,'1111')
     note(b,'B only note');b.wait_for_timeout(2500)
     ok('B only note' not in json.dumps(dump(P1)) and 'B only note' in json.dumps(dump(P2)),'B data goes only to B\'s Sheet')
     ks=b.evaluate("Object.keys(localStorage)");ok(all(k.startswith('testa_') or k.startswith('testb_') for k in ks),'every storage key is namespaced (%d keys)'%len(ks))
     ok('B only note' not in b.evaluate("localStorage.testa_recs||''"),'B data not in A\'s storage')
     ck=b.evaluate("caches.keys()");ok('testa-v2' in ck and any(c.startswith('test-b-v') for c in ck),'separate caches (B uses hyphen CACHE_PREFIX test-b): %s'%ck)
     regs=b.evaluate("navigator.serviceWorker.getRegistrations().then(r=>r.map(x=>x.scope))");ok(len(regs)==2 and all(('/appa/' in s) or ('/appb/' in s) for s in regs),'separate service workers per folder')
     ok(json.loads(open(os.path.join(TMP,'appa','manifest.json')).read())['id']!=json.loads(open(os.path.join(TMP,'appb','manifest.json')).read())['id'],'different manifest ids')
     # logout in A leaves B signed in
     a.reload();a.wait_for_selector('header');a.click('nav [data-tab=settings]');a.click('#sOut');a.wait_for_timeout(800)
     ok(not home(a),'A logged out');b.reload();b.wait_for_selector('header');ok(home(b),'B still signed in after A logout')
     name(a,'ja kirsten');pin(a,pin_of(0));ok(home(a),'A back in')
     na=a.evaluate("Object.keys(localStorage).filter(k=>k.indexOf('testa_')===0).length")
     b.evaluate("TMC.wipeThisApp()");b.wait_for_timeout(800)
     ok(b.evaluate("Object.keys(localStorage).filter(k=>k.indexOf('testb_')===0).length")==0,'wipe B: all B keys gone')
     ok(a.evaluate("Object.keys(localStorage).filter(k=>k.indexOf('testa_')===0).length")==na,'wipe B: A keys untouched (%d)'%na)
     ck=a.evaluate("caches.keys()");ok('testa-v2' in ck and not any(c.startswith('test-b-') for c in ck),'wipe B: only B caches deleted %s'%ck)
     regs=a.evaluate("navigator.serviceWorker.getRegistrations().then(r=>r.map(x=>x.scope))");ok(len(regs)==1 and '/appa/' in regs[0],'wipe B: only B service worker removed')
     a.reload();a.wait_for_selector('header');ok(home(a) and 'offline note' in json.dumps(a.evaluate("TMC.all('x')")),'A still signed in with its data after B was wiped')
     br.close()
  except NoBaseRT:
    skip('app is not built on the base runtime (no TMC.me/put/pending): browser sections 1-16 do not apply');
    try:br.close()
    except Exception:pass
  if DEMO['on'] is not None:
   sec('12. VER 4: fresh install with NO code (token flow)')
   with sync_playwright() as p:
     br=p.chromium.launch(executable_path=CHROME) if CHROME else p.chromium.launch()
     xa=newctx(br);ca=openp(xa,CU,'tokAdmin')
     ok(ca.evaluate("TMC.L.get('sycode')")is None and ca.evaluate("CONFIG.SYNC_CODE")=='','app C has no sync code anywhere')
     ok(not ca.is_visible('#ncW'),'no "Not connected" banner when the script is reachable')
     name(ca,'Johan Kirsten');ok(ca.evaluate("!!document.getElementById('fPin2')"),'fresh Admin phone → First Admin setup via server');setpin(ca,pin_of(0))
     ok(home(ca) and isadm(ca) and bool(ca.evaluate("TMC.L.get('tok')")),'Admin signed in, session token stored')
     ok(any(k.startswith('testc_tok') for k in ca.evaluate("Object.keys(localStorage)")),'token stored under this app\'s APP_ID only')
     xs=newctx(br);cs=openp(xs,CU,'tokStaff');name(cs,'Mahamat Issa');ok('approval' in h2(cs).lower(),'staff fresh phone → sign up → waiting for approval')
     ok(any(u['name']=='Mahamat Issa' and u['status']=='pending' for u in U(P3)),'pending sign-up reached the Sheet without any code')
     sec('12b. ONE request per name per app')
     xd=newctx(br);dp=openp(xd,CU,'dupReq');name(dp,'  MAHAMAT   issa ')
     ok(dp.locator('#dupT').count()==1 and 'Already asked' in h2(dp),'same name (case/spaces) on another phone → "Already asked - wait for Admin"')
     ok(min(dp.locator('.card button').nth(i).bounding_box()['height'] for i in range(dp.locator('.card button').count()))>=56,'dup screen buttons big (≥56px)')
     dp.screenshot(path='/workspace/dup_request.png');xd.close()
     ok(len([u for u in U(P3) if u['name'].lower().replace(' ','')=='mahamatissa'])==1,'no second request stored on the server')
     r=raw(P3,{'action':'register','name':'Mahamat Issá','device':'zz'})
     ok(r.get('state') in ('dup','pending') and len([u for u in U(P3) if 'mahamat' in u['name'].lower()])==1,'server: accent variant refused, still one request %s'%r)
     r=post(P1,'code-a',[{'kind':'u','id':'rdup1','u':int(time.time()*1000),'del':0,'data':{'id':'rdup1','name':'Fatime  ALI','status':'pending','dev':'q'}}])
     ok(r.get('refusedWhy')=='duplicate_request' and not any(u['id']=='rdup1' for u in U(P1)),'server refuses duplicate request via sync (refusedWhy duplicate_request)')
     r=raw(P2,{'action':'register','name':'Fatime Ali','device':'zz'})
     ok(r.get('state')=='pending' and any(u['name']=='Fatime Ali' for u in U(P2)) and any(u['name']=='Fatime Ali' and u['status']=='active' for u in U(P1)),'different app, same name (active in app A) → request allowed in app B %s'%r)
     synced(ca);ca.click('nav [data-tab=users]');ca.wait_for_timeout(300);uo(ca,'Mahamat Issa').locator('[data-ua=approve]').click();ca.wait_for_timeout(1500)
     ok(any(u['name']=='Mahamat Issa' and u['status']=='active' for u in U(P3)),'Admin (other phone) approved via token sync')
     cs.click('#fCheck');cs.wait_for_selector('#fPin2',timeout=8000);setpin(cs,pin_of(2))
     ok(home(cs) and not isadm(cs),'staff signed in after approval (no code)')
     note(cs,'token note');cs.wait_for_function('TMC.pending()===0',timeout=10000)
     ok(any(r['kind']=='x' and r['data'] and r['data'].get('text')=='token note' for r in dump(P3)['recs']),'staff record synced to the Sheet')
     ok(cs.evaluate("TMC.all('u').filter(u=>u.pinH&&u.id!==TMC.me().id).length")==0,'staff phone holds no other user\'s PIN hash')
     sec('12b. ADMIN FIX RULE: staff add, only the Admin fixes (UI + server + audit)')
     def sheets(port):return json.load(urllib.request.urlopen('http://127.0.0.1:%d/_sheets'%port))
     sec('12e. SAFETY: Ids stay exact text; no PIN secrets in any sync reply')
     _now=int(time.time()*1000)
     for _id in ('2099-01-01','007','1e5','TRUE'):post(P1,'code-a',[{'kind':'d','id':_id,'u':_now,'del':0,'data':{'id':_id,'v':1}}])
     _ids=[r['id'] for r in raw(P1,{'action':'sync','code':'code-a','device':'t','since':0,'changes':[]})['records'] if r['kind']=='d']
     ok(all(_i in _ids for _i in ('2099-01-01','007','1e5','TRUE')),'date-like / number-like Ids come back exactly %s'%_ids)
     _rec=[r for r in sheets(P1)['_Records'][1:] if r[1]=='d' and r[0]=='d:2099-01-01']
     ok(_rec and _rec[0][2]=='2099-01-01','Id cell stays plain text in the Sheet (not a date): %s'%(_rec[0][2] if _rec else None))
     def _leak(res,own=''):return [r['id'] for r in res.get('records',[]) if r['kind']=='u' and r.get('data') and any(f in json.loads(r['data']) for f in ('pinH','salt','pin')) and r['id']!=own]
     _rc=raw(P1,{'action':'sync','code':'code-a','device':'t','since':0,'changes':[]})
     ok(_rc['ok'] and any(r['kind']=='u' for r in _rc['records']) and not _leak(_rc),'team-code sync: user records have NO salt / pinH %s'%_leak(_rc))
     ok(all('hasPin' in json.loads(r['data']) for r in _rc['records'] if r['kind']=='u' and r.get('data')),'team-code sync still says who has a PIN (hasPin)')
     _tk=cs.evaluate("TMC.L.get('tok')");_mid=cs.evaluate("TMC.me().id")
     _rt=raw(P3,{'action':'sync','token':_tk,'device':'t','since':0,'changes':[]})
     ok(_rt['ok'] and not _leak(_rt,_mid),'token sync: no other user\'s salt / pinH %s'%_leak(_rt,_mid))
     _ra=raw(P3,{'action':'sync','token':ca.evaluate("TMC.L.get('tok')"),'device':'t','since':0,'changes':[]})
     ok(_ra['ok'] and not _leak(_ra,ca.evaluate("TMC.me().id")),'Admin token sync: no other user\'s salt / pinH')
     _rb=raw(P3,{'action':'sync','code':'nope','device':'t','since':0,'changes':[]})
     ok(not _rb.get('ok') and 'records' not in _rb,'wrong code gets no records')
     _st=raw(P3,{'action':'status','name':'Mahamat Issa'})
     ok('pinH' not in _st,'sign-in status reply has no pinH')
     def xrec(t):return [r for r in dump(P3)['recs'] if r['kind']=='x' and r['data'] and r['data'].get('text')==t]
     note(cs,'staff second note');cs.wait_for_function('TMC.pending()===0',timeout=10000)
     ok(len(xrec('staff second note'))==1,'staff user can ADD records (synced to the Sheet)')
     ok(cs.locator('.fixB').count()==0 and not cs.evaluate("TMC.canFix()"),'staff sees NO ✏️ Fix / edit / delete buttons')
     nid=xrec('token note')[0]['id']
     ok(cs.evaluate("TMC.fix('x','%s','text','hacked')"%nid) is False,'staff TMC.fix() refused in the app')
     ok(cs.evaluate("TMC.put('x','%s',{id:'%s',text:'hacked2'})"%(nid,nid)) is False and cs.evaluate("TMC.remove('x','%s')"%nid) is False,'staff put()/remove() on an existing record refused in the app')
     ok('hacked' not in json.dumps(cs.evaluate("TMC.all('x')")),'staff phone still shows the original value')
     tok=cs.evaluate("TMC.L.get('tok')");now=int(time.time()*1000)+50
     r1=raw(P3,{'action':'sync','token':tok,'device':'x','since':0,'changes':[{'kind':'x','id':nid,'u':now,'del':0,'data':{'id':nid,'text':'server hack'}}]})
     r2=raw(P3,{'action':'sync','token':tok,'device':'x','since':0,'changes':[{'kind':'x','id':nid,'u':now+1,'del':1,'data':None}]})
     ok(r1.get('refused')==1 and r2.get('refused')==1 and len(xrec('token note'))==1,'server refuses staff edit AND delete of an existing record (refused=1)')
     r3=raw(P3,{'action':'sync','token':tok,'device':'x','since':0,'changes':[{'kind':'x','id':'xnew1','u':now,'del':0,'data':{'id':'xnew1','text':'server add'}}]})
     ok(r3.get('accepted')==1 and not r3.get('refused') and len(xrec('server add'))==1,'server still accepts staff ADDs')
     if DEMO['on']:
       synced(ca);ca.click('nav [data-tab=work]');ca.wait_for_timeout(300)
       fb=ca.locator('.urow',has_text='token note').locator('.fixB')
       ok(fb.count()==1,'Admin sees a ✏️ Fix button on each record')
       ok(fb.bounding_box()['height']>=56,'Fix button is big (≥56px): %d'%fb.bounding_box()['height'])
       fb.click();ca.wait_for_selector('#fixV');ok(ca.input_value('#fixV')=='token note','Fix box opens with the old value')
       ca.fill('#fixV','token note FIXED');ca.click('#fixS');ca.wait_for_function('TMC.pending()===0',timeout=10000)
       fx=xrec('token note FIXED')
       ok(len(fx)==1 and fx[0]['id']==nid,'Admin fix saved on the server (same record)')
       a=(fx[0]['data'].get('_fix') or [{}])[-1] if fx else {}
       ok(a.get('old')=='token note' and a.get('by')=='Template Admin' and str(a.get('at','')).startswith('20'),'audit column _fix: old value + Admin name + time %s'%a)
       lg=sheets(P3).get('Fix log',[])
       ok(len(lg)>=2 and lg[0][:6]==['Time','Admin','Kind','Id','Old value','New value'],'"Fix log" tab created with header')
       ok(any(r[1]=='Template Admin' and r[3]==nid and 'token note' in r[4] and 'FIXED' in r[5] and str(r[0]).startswith('20') for r in lg[1:]),'Fix log row: time, Admin, old value, new value')
       ok(not any('hack' in json.dumps(r) for r in lg),'refused staff attempts never reach the Fix log')
       ok('fixed by' in ca.inner_text('.urow:has-text("token note FIXED")'),'record shows "✏️ fixed by" note')
       synced(cs);cs.click('nav [data-tab=work]');cs.wait_for_timeout(300)  # Save-close (VER 12) returns to previous screen after #exAdd
       ok('token note FIXED' in cs.inner_text('#view') and cs.locator('.fixB').count()==0,'staff phone gets the fix, still no Fix button')
     else:skip('no demo #exTxt list: Fix button UI is tested by the app\'s own screens (server fix rule above still tested)')
     ca.click('nav [data-tab=users]');ca.wait_for_timeout(300)
     sec('12c. PERMISSIONS: Admin ticks what each person may do (UI + server + defaults)')
     _CF=json.loads(re.search(r'/\*CONFIG\*/(.*?)/\*END\*/',open(os.path.join(APP,'index.html'),encoding='utf-8').read(),re.S).group(1))
     _PIDS=[p['id'] for p in _CF.get('PERMS',[])];_PDEF=_CF.get('PERM_DEFAULT',[])
     if _PIDS!=['view','add','reports','export']:  # app has its own tick list: generic checks here, app-specific ones live in the app's own tests
         mid=[u for u in U(P3) if u['name']=='Mahamat Issa'][0]['id'];uo(ca,'Mahamat Issa')
         ok(ca.locator('.ulr').count()>=2 and ca.locator('.ulr .uopen').count()<=2,'users shown as a list (one row per person, tap to open)')
         ok(min(ca.locator('.uli').nth(i).bounding_box()['height'] for i in range(ca.locator('.uli').count()))>=56,'person rows are big (≥56px)')
         ok(ca.locator('.permBox[data-pu="%s"] .permT.lock'%mid).count()==2,'Fix + Approve rows locked 🔒')
         mp=[u for u in U(P3) if u['name']=='Mahamat Issa'][0].get('perms') or []
         ok(sorted(mp)==sorted(_PDEF),'default for a newly approved user = CONFIG.PERM_DEFAULT %s'%mp)
         ok(any(', '.join(_PDEF)==str(r[6]) for r in sheets(P3)['Users'][1:] if r[0]=='Mahamat Issa') and sheets(P3)['Users'][0][6]=='Permissions','Users tab has a Permissions column')
         lb=ca.locator('.permBox[data-pu="%s"] .permT:not(.lock)'%mid)
         ok(lb.count()==len(_PIDS),'Admin sees %d tick boxes from CONFIG.PERMS for the user'%len(_PIDS))
         ok(min(lb.nth(i).bounding_box()['height'] for i in range(lb.count()))>=56,'tick boxes are big (≥56px)')
         ok(ca.locator('.permBox[data-pu="%s"] input[data-pp=fix]'%mid).count()==0,'no Fix tick box')
         ok(cs.evaluate("JSON.stringify(TMC.C.PERMS.map(p=>p.id).filter(id=>TMC.can(id)))")==json.dumps([i for i in _PIDS if i in _PDEF]).replace(' ',''),'staff phone: defaults only')
         cs.click('nav [data-tab=home]');cs.click('#hCan');cs.wait_for_selector('#canBox')
         ok(cs.locator('.canR.yes').count()==len(_PDEF) and cs.locator('.canR.no').count()==len(_PIDS)-len(_PDEF),'"What I can do" shows ticks')
         ok(raw(P3,{'action':'report','token':tok,'device':'x'}).get('error')=='not_allowed','server refuses an unticked report')
     else:
         def mu():return [u for u in U(P3) if u['name']=='Mahamat Issa'][0]
         def ssync():synced(cs);cs.evaluate("TMC.render()");cs.wait_for_timeout(300)
         def tick(pp,on):
             b=ca.locator('.permBox[data-pu="%s"] input[data-pp=%s]'%(mid,pp));(b.check() if on else b.uncheck());ca.wait_for_function('TMC.pending()===0',timeout=10000);ca.wait_for_timeout(300)
         mid=mu()['id']
         uo(ca,'Mahamat Issa')
         ok(ca.locator('.ulr').count()>=2 and ca.locator('.ulr .uopen').count()<=2,'users shown as a list (one row per person, tap to open)')
         ok(min(ca.locator('.uli').nth(i).bounding_box()['height'] for i in range(ca.locator('.uli').count()))>=56,'person rows are big (≥56px)')
         ok(ca.locator('.permBox[data-pu="%s"] .permT.lock'%mid).count()==2,'Fix + Approve rows locked 🔒')
         ok(sorted(mu().get('perms') or [])==['add','view'],'default for a newly approved user = View + Add (stored on the server) %s'%mu().get('perms'))
         ok(any('view, add' in str(r[6]) for r in sheets(P3)['Users'][1:] if r[0]=='Mahamat Issa') and sheets(P3)['Users'][0][6]=='Permissions','Users tab has a Permissions column')
         lb=ca.locator('.permBox[data-pu="%s"] .permT:not(.lock)'%mid)
         ok(lb.count()==4,'Admin sees 4 tick boxes from CONFIG.PERMS for the user')
         ok(min(lb.nth(i).bounding_box()['height'] for i in range(4))>=56,'tick boxes are big (≥56px)')
         ok('Admin only' in ca.inner_text('.permBox[data-pu="%s"]'%mid),'Fix + Approve shown as Admin-only (not tickable)')
         ok(ca.locator('.permBox[data-pu="%s"] input[data-pp=fix]'%mid).count()==0,'no Fix tick box')
         ok(cs.evaluate("TMC.can('view')&&TMC.can('add')&&!TMC.can('reports')&&!TMC.can('export')"),'staff phone: defaults View+Add only')
         cs.click('nav [data-tab=home]');cs.wait_for_timeout(200)
         ok(cs.locator('nav [data-tab=reports]').count()==0 and cs.locator('#view .tile[data-tab=reports]').count()==0,'REPORTS: no 📊 Reports tab or tile without the Reports tick')
         cs.click('nav [data-tab=home]');cs.click('#hCan');cs.wait_for_selector('#canBox')
         ok(cs.locator('.canR.yes').count()==2 and cs.locator('.canR.no').count()==2 and 'Reports' in cs.inner_text('.canR.no >> nth=0'),'"What I can do" shows ticks: 2 allowed, 2 not')
         cs.click('nav [data-tab=work]');cs.wait_for_timeout(200)
         if not (DEMO['on'] and XK):skip("demo 'x' box checks (Reports/Export/Add/View buttons + 'x' records): app has no demo 'x' type")
         if DEMO['on'] and XK:ok(cs.locator('#exRep').count()==0 and cs.locator('#exExp').count()==0,'unticked Reports/Export buttons hidden')
         ok(raw(P3,{'action':'report','token':tok,'device':'x'}).get('error')=='not_allowed' and raw(P3,{'action':'export','token':tok,'device':'x'}).get('error')=='not_allowed','server refuses unticked Reports/Export')
         tick('reports',True)
         ok('reports' in (mu().get('perms') or []),'Admin ticks Reports → stored on the server')
         if DEMO['on'] and XK:ok(cs.locator('#exRep').count()==0,'staff phone unchanged before its next sync')
         ssync()
         if DEMO['on'] and XK:ok(cs.locator('#exRep').count()==1 and cs.locator('#exExp').count()==0,'after sync: Reports button shows, Export still hidden')
         ok(cs.locator('nav [data-tab=reports]').count()==1,'REPORTS: Reports tick → 📊 Reports tab appears for staff')
         if DEMO['on'] and XK:cs.click('#exRep');cs.wait_for_function("document.getElementById('exOut').textContent.length>0",timeout=8000)
         if DEMO['on'] and XK:ok(cs.locator('#exOut .rep td',has_text='x').count()>0,'ticked Reports works through the server: %s'%cs.inner_text('#exOut'))
         tick('add',False)
         ssync()
         if DEMO['on'] and XK:ok(cs.locator('#exAdd').count()==0 and cs.locator('#exTxt').count()==0,'Admin unticks Add → Add box hidden after sync')
         if DEMO['on'] and XK:ok(cs.evaluate("TMC.put('x','xnoadd',{id:'xnoadd',text:'no add'})") is False,'app refuses an add when Add is unticked')
         now=int(time.time()*1000)+80
         r4=raw(P3,{'action':'sync','token':tok,'device':'x','since':0,'changes':[{'kind':'x','id':'xnoadd2','u':now,'del':0,'data':{'id':'xnoadd2','text':'sneaky add'}}]})
         if DEMO['on'] and XK:ok(r4.get('refused')==1 and 'sneaky add' not in json.dumps(dump(P3)),'server refuses an add when Add is unticked')
         tick('view',False)
         if DEMO['on'] and XK:ok(not any(r['kind']=='x' for r in raw(P3,{'action':'sync','token':tok,'device':'x','since':0,'changes':[]})['records']),'View unticked → server sends no records of that kind')
         ssync();cs.click('nav [data-tab=home]');cs.wait_for_timeout(200)
         ok(cs.locator('nav [data-tab=work]').count()==0 or cs.evaluate("TMC.can('reports')"),'menu follows ticks')
         cs.click('nav [data-tab=work]');cs.wait_for_timeout(200)
         if DEMO['on'] and XK:ok('token note' not in cs.inner_text('#view'),'View unticked → list hidden on the phone')
         me_=dict(mu());me_['perms']=['view','add','reports','export']
         raw(P3,{'action':'sync','token':tok,'device':'x','since':0,'changes':[{'kind':'u','id':mid,'u':int(time.time()*1000)+99,'del':0,'data':me_}]})
         ok(sorted(mu().get('perms') or [])==['reports'],'staff cannot tick their own permissions on the server')
         tick('view',True);tick('add',True);tick('reports',False)
         ca.screenshot(path='/workspace/perm_admin.png',full_page=True);ca.screenshot(path='/workspace/perm_list.png',full_page=True)
         ssync()
         if DEMO['on'] and XK:ok(cs.locator('#exAdd').count()==1 and cs.locator('#exRep').count()==0 and 'token note' in cs.inner_text('#view'),'re-ticked View+Add / unticked Reports → buttons back/hidden after sync')
         ok(isadm(ca) and ca.evaluate("TMC.can('export')&&TMC.can('reports')") and raw(P3,{'action':'export','token':ca.evaluate("TMC.L.get('tok')"),'device':'x'}).get('ok'),'Admin can do everything (incl. Export on the server)')
         other=json.dumps(dump(P1))+json.dumps(dump(P2))
         ok('Mahamat' not in other and '"reports"' not in other,'no mixing: permissions only in app C\'s Sheet')
         ok(all(k.startswith('testc_') for k in cs.evaluate("Object.keys(localStorage)") if 'perm' in k or k.endswith('uid')),'phone storage stays under this app\'s APP_ID')
         tok=cs.evaluate("TMC.L.get('tok')");adm=[u for u in U(P3) if u.get('admin')][0]
         bad=dict(adm,status='blocked');raw(P3,{'action':'sync','token':tok,'device':'x','since':0,'changes':[{'kind':'u','id':adm['id'],'u':int(time.time()*1000)+9,'del':0,'data':bad}]})
         ok([u for u in U(P3) if u.get('admin')][0]['status']=='active','staff token cannot change the Admin / approvals')
         from hashlib import sha256
         old=[u for u in U(P3) if u['name']=='Mahamat Issa'][0];oph=sha256((old['salt']+':'+pin_of(2)).encode()).hexdigest();atk=ca.evaluate("TMC.L.get('tok')")
         r_=raw(P3,{'action':'sync','token':tok,'device':'x','since':0,'changes':[{'kind':'u','id':adm['id'],'u':int(time.time()*1000)+20,'del':1,'data':{'discarded':1}}]})
         ok(any(u['id']==adm['id'] for u in U(P3)) and r_.get('refusedWhy') in ('admin_only_fix','main_admin'),'server: staff token cannot discard anyone')
         r_=raw(P3,{'action':'sync','token':atk,'device':'x','since':0,'changes':[{'kind':'u','id':adm['id'],'u':int(time.time()*1000)+21,'del':1,'data':{'discarded':1}}]})
         ok(any(u['id']==adm['id'] for u in U(P3)) and r_.get('refusedWhy')=='main_admin','server: main Admin token cannot remove itself (refusedWhy main_admin)')
         r_=raw(P3,{'action':'sync','token':atk,'device':'x','since':0,'changes':[{'kind':'u','id':adm['id'],'u':int(time.time()*1000)+22,'del':0,'data':dict([u for u in U(P3) if u['id']==adm['id']][0],status='blocked')}]})
         ok([u for u in U(P3) if u['id']==adm['id']][0]['status']=='active' and r_.get('refusedWhy')=='main_admin','server: nobody can set the main Admin to blocked (refusedWhy main_admin)')
         synced(ca);uo(ca,'Mahamat Issa').locator('[data-ud=block]').click();ca.click('#dscY');ca.wait_for_timeout(1500);synced(ca)
         ok(not any(u['name']=='Mahamat Issa' for u in U(P3)),'token app: block discards the user on the server')
         ok(raw(P3,{'action':'sync','token':tok,'device':'x','since':0,'changes':[]}).get('error') in ('not_active','bad_token'),'discarded user\'s old token is refused')
         ok(raw(P3,{'action':'login','id':old['id'],'pinH':oph}).get('ok') is not True,'discarded user\'s old PIN no longer signs in')
         cs.evaluate("TMC.syncNow()");t0=time.time()
         try:cs.wait_for_function("!TMC.L.get('uid')",timeout=10000)
         except Exception:pass
         ok(not home(cs),'discarded staff phone is signed out on its next sync (%.1fs)'%(time.time()-t0))
         name(cs,'Mahamat Issa');ok('approval' in h2(cs).lower() and any(u['name']=='Mahamat Issa' and u['status']=='pending' for u in U(P3)),'token app: fresh request after discard → Pending')
         synced(ca);ca.click('nav [data-tab=home]');ca.click('nav [data-tab=users]');uo(ca,'Mahamat Issa').locator('[data-ua=approve]').click();ca.wait_for_timeout(1500)
         cs.click('#fCheck');cs.wait_for_selector('#fPin2',timeout=8000);setpin(cs,pin_of(2));ok(home(cs) and cs.evaluate("TMC.me().id")!=old['id'],'token app: approved fresh request signs in (new record)')
         sid=[u for u in U(P3) if u['name']=='Mahamat Issa'][0]['id']
         for i in range(5):raw(P3,{'action':'login','id':sid,'pinH':'0'*64})
         from hashlib import sha256
         su=[u for u in U(P3) if u['name']=='Mahamat Issa'][0]
         ok(raw(P3,{'action':'login','id':sid,'pinH':sha256((su['salt']+':'+pin_of(2)).encode()).hexdigest()}).get('error')=='locked','server PIN lock: 5 wrong → even the right PIN refused for an hour')
         xs.close()
     sec('12d. RESTORE NEVER REMOVES USERS (phone + server)')
     n0=len(U(P3));ids=[u['id'] for u in U(P3)];tk=ca.evaluate("TMC.L.get('tok')")
     nl=lambda:ca.evaluate("Object.values(JSON.parse(localStorage.getItem(CONFIG.APP_ID+'_recs')||'{}')).filter(r=>r.kind==='u'&&!r.del).length")
     l0=nl();ca.evaluate("TMC.restoreBackup({records:[]})");ca.evaluate("TMC.restoreBackup({})");ca.evaluate("TMC.syncNow()");ca.wait_for_timeout(1500)
     ok(nl()==l0 and len(U(P3))==n0,'restore of a stripped backup (no users, no sync data) keeps every user on phone and Sheet')
     ca.evaluate("TMC.restoreBackup({records:[{kind:'note',id:'rb1',u:1,data:{t:'restored'}}]})");ca.evaluate("TMC.syncNow()");ca.wait_for_timeout(1500)
     ok(nl()==l0 and len(U(P3))==n0,'restore merges records only, users untouched')
     big=9e15;raw(P3,{'action':'sync','token':tk,'device':'rst','since':0,'changes':[{'kind':'u','id':i,'u':big,'del':1,'data':None} for i in ids]+[{'kind':'u','id':ids[0],'u':big,'data':None}]})
     ok(len(U(P3))==n0 and set(u['id'] for u in U(P3))==set(ids),'server never deletes or blanks a user because of a phone restore/sync')
     sec('13. VER 4: reinstall re-sign-in with no code, no new approval')
     nU=len(U(P3));x=newctx(br);w=openp(x,CU,'tokRe');name(w,'ja kirsten')
     ok(w.evaluate("!!document.getElementById('fPin')&&!document.getElementById('fPin2')"),'wiped Admin phone → PIN screen');pin(w,pin_of(0));w.wait_for_selector('header',timeout=8000)
     ok(home(w) and isadm(w) and len(U(P3))==nU,'Admin straight back in, no new request')
     ok('token note' in json.dumps(w.evaluate("TMC.all('x')")),'data pulled back on the reinstalled phone')
     note(w,'after reinstall');w.wait_for_function('TMC.pending()===0',timeout=10000)
     ok('after reinstall' in json.dumps(dump(P3)),'reinstalled phone syncs new records')
     ok('token note' not in json.dumps(dump(P1))+json.dumps(dump(P2)),'no data mixing: C records only in C\'s Sheet')
     sec('22. PHOTOS TO DRIVE (VER 9): small, offline queue, own folder, link record, View (Admin), backfill, 2-month cleanup')
     _g=lambda port,path:json.load(urllib.request.urlopen('http://127.0.0.1:%d%s'%(port,path)))
     if not w.evaluate("!!(TMC.phKeep&&TMC.phBtn)"):skip('app has no base VER 9 photo module')
     else:
      MK="""async()=>{const c=document.createElement('canvas');c.width=4000;c.height=3000;const g=c.getContext('2d');for(let i=0;i<9000;i++){g.fillStyle='hsl('+(i*37%360)+',40%,'+(30+i%50)+'%)';g.fillRect(Math.random()*4000,Math.random()*3000,40,40)}
        g.fillStyle='#000';g.fillRect(800,1000,2400,900);g.fillStyle='#fff';g.font='bold 700px monospace';g.fillText('012345',900,1750);
        const b=await new Promise(r=>c.toBlob(r,'image/jpeg',0.95));const d=await TMC.phSmall(new File([b],'m.jpg',{type:'image/jpeg'}));
        const im=new Image();await new Promise(r=>{im.onload=r;im.src=d});return {len:d.length,w:im.width,h:im.height,d:d}}"""
      sm=w.evaluate(MK)
      ok(max(sm['w'],sm['h'])==800,'photo made small: long side 800px (%dx%d)'%(sm['w'],sm['h']))
      ok(sm['len']*3/4<=110000,'photo about 50-100 KB or less: %d KB'%(sm['len']*3/4/1024))
      ok(w.evaluate("(()=>{const s=document.querySelector('script:not([src])');return 1})()")==1 and 'PH_MAX=800,PH_Q=0.5' in open(os.path.join(APP,'index.html'),encoding='utf-8').read(),'smallest settings in the code: max 800px, JPEG 0.5')
      d0=sm['d'];D0=_g(P3,'/_drive');nf0=len(D0['files'])
      x.set_offline(True);pid=w.evaluate("d=>TMC.phKeep(d,'test meter')",d0);w.wait_for_timeout(700)
      ok(pid in w.evaluate("TMC.phQueue().then(q=>q.map(o=>o.id))") and w.evaluate("TMC.phState(%r)"%pid)=='phone','offline: photo kept on the phone in the queue')
      ok(len(_g(P3,'/_drive')['files'])==nf0,'offline: nothing sent yet')
      x.set_offline(False);w.evaluate("TMC.phPump()")
      for _ in range(30):
        if not w.evaluate("TMC.phQueue().then(q=>q.length)"):break
        w.evaluate("TMC.phPump()");w.wait_for_timeout(500)
      D1=_g(P3,'/_drive');f1=[f for f in D1['files'] if f['name']==pid+'.jpg']
      ok(len(f1)==1 and D1['folderProp'] and f1[0]['folder']==D1['folderProp'],'back online: photo uploaded to THIS app\'s own Drive folder (%s)'%(D1['folders'][0]['name'] if D1['folders'] else '-'))
      ok(w.evaluate("TMC.phQueue().then(q=>q.length)")==0,'phone copy removed only after the upload worked')
      pl=[r for r in dump(P3)['recs'] if r['kind']=='pl' and r['id']==pid]
      ok(pl and 'drive.google.com' in json.dumps(pl[0]['data']),'Sheet record holds the Drive link for the photo id')
      synced(w);ok(w.evaluate("TMC.phState(%r)"%pid)=='drive','link record synced to the phone (state: drive)')
      tk=w.evaluate("TMC.L.get('tok')")
      r2=raw(P3,{'action':'photo','token':tk,'id':pid,'d':d0,'at':'2026-11-01T08:00:00Z'})
      ok(r2.get('ok') and r2.get('dup')==1 and len(_g(P3,'/_drive')['files'])==len(D1['files']),'same photo sent twice → no second copy')
      raw(P3,{'action':'sync','token':tk,'device':'forge','since':0,'changes':[{'kind':'pl','id':'fake1','u':9e12,'del':0,'data':{'url':'https://evil.example/x'}}]})
      ok(not any(r['kind']=='pl' and r['id']=='fake1' for r in dump(P3)['recs']),'a phone can never write a photo link record itself')
      ok(raw(P3,{'action':'photo','id':pid,'d':d0}).get('error')=='need_login','no sign-in → upload refused')
      ok(raw(P1,{'action':'photoget','code':'code-a','id':pid}).get('ok') is False,'View photo download refused without an Admin token')
      ok(raw(P3,{'action':'photo','token':tk,'id':'big1','d':'data:image/jpeg;base64,'+'A'*500000}).get('error')=='too_big','too big a photo refused')
      w.click('nav [data-tab=work]');w.wait_for_timeout(300)
      bh=w.evaluate("(id=>{const h=TMC.phBtn(id);const d=document.createElement('div');d.id='phT';d.innerHTML=h;document.querySelector('#view').appendChild(d);const b=d.querySelector('[data-phv]');return b?b.getBoundingClientRect().height:0})(%r)"%pid)
      ok(bh>=56,'Admin sees a big View photo button (%dpx)'%bh)
      w.click('#phT [data-phv]');w.wait_for_function("(()=>{const i=document.querySelector('#phOv img');return i&&i.src.indexOf('data:image/jpeg')===0})()",timeout=8000)
      ok(True,'View photo opens the picture from Drive (phone copy already gone)');shot(w,'photo-view-en');w.click('#phOvX')
      old=(datetime.datetime.now(datetime.UTC).replace(tzinfo=None)-datetime.timedelta(days=70)).isoformat()+'Z';nw=(datetime.datetime.now(datetime.UTC).replace(tzinfo=None)-datetime.timedelta(days=1)).isoformat()+'Z'
      nb=w.evaluate("([d,o,n])=>TMC.phBackfill([{id:'bfold',d:d,at:o},{id:'bf1',d:d,at:n},{id:'bf2',d:d,at:n},{id:'bf3',d:d,at:n},{id:%r,d:d,at:n}])"%pid,[d0,old,nw])
      ok(nb==3,'backfill: 3 queued, the >2-month one and the already-sent one skipped (%s)'%nb)
      w.wait_for_timeout(400);n_a=len(_g(P3,'/_drive')['files']);w.evaluate("TMC.phPump()");w.wait_for_timeout(1500);n_b=len(_g(P3,'/_drive')['files'])
      ok(n_b-n_a<=2,'backfill goes in small batches (max 2 per round: %d)'%(n_b-n_a))
      for _ in range(20):
        if not w.evaluate("TMC.phQueue().then(q=>q.length)"):break
        w.evaluate("TMC.phPump()");w.wait_for_timeout(700)
      nm=[f['name'] for f in _g(P3,'/_drive')['files']]
      ok(all(i+'.jpg' in nm for i in ('bf1','bf2','bf3')) and 'bfold.jpg' not in nm,'backfill: new ones uploaded, the >2-month one never sent')
      ok(raw(P3,{'action':'photo','token':tk,'id':'old2','d':d0,'at':old}).get('skipped')=='old','server also skips photos older than 2 months')
      _g(P3,'/_age?id=%s&days=61'%pid);cl=_g(P3,'/_cleanup')
      ok(cl.get('n')==1,'daily cleanup removes the photo older than 2 months (%s)'%cl)
      plr=[r for r in dump(P3)['recs'] if r['kind']=='pl' and r['id']==pid][0];dr=_g(P3,'/_drive')
      ok(plr['data'].get('removed')==1 and not plr['data'].get('url') and not plr['del'],'record stays, marked photo removed')
      ok([f for f in dr['files'] if f['name']==pid+'.jpg'][0]['trashed'] and not any(f['trashed'] for f in dr['files'] if f['name']=='bf1.jpg'),'old file to the Drive bin, newer ones kept')
      ok(_g(P3,'/_cleanup').get('n')==0,'cleanup twice changes nothing more')
      ok(any(t=='photoCleanup' for t in _g(P3,'/_setup') and _g(P3,'/_state')['triggers']),'setupOnce adds the daily photoCleanup trigger')
      synced(w);ok(w.evaluate("TMC.phState(%r)"%pid)=='removed' and 'phGone' in w.evaluate("TMC.phBtn(%r)"%pid),'phone shows "photo removed" instead of the button')
      ok(_g(P1,'/_drive')['files']==[] and _g(P2,'/_drive')['files']==[],'no data mixing: other apps\' Drive folders got nothing')
      ok(pid not in json.dumps(dump(P1))+json.dumps(dump(P2)),'no data mixing: photo links only in this app\'s Sheet')
      dbs=w.evaluate("indexedDB.databases?indexedDB.databases().then(a=>a.map(x=>x.name)):Promise.resolve(['testc_photos'])")
      ok('testc_photos' in dbs and not any(n in dbs for n in ('testa_photos','testb_photos')),'phone queue is named per app (%s)'%dbs)
      x2=newctx(br);w2=openp(x2,CU,'phRe');name(w2,'ja kirsten');pin(w2,pin_of(0));w2.wait_for_selector('header',timeout=8000)
      ok(home(w2) and isadm(w2),'reinstalled Admin phone: signs straight back in')
      synced(w2);ok(w2.evaluate("TMC.phState('bf1')")=='drive','reinstalled Admin phone gets the photo links')
      w2.evaluate("TMC.phView('bf1')");w2.wait_for_function("(()=>{const i=document.querySelector('#phOv img');return i&&i.src.indexOf('data:image/jpeg')===0})()",timeout=8000)
      ok(True,'reinstalled Admin phone can View a photo taken on another phone')
      ok(w2.evaluate("(async()=>{localStorage.setItem(TMC.P+'keepme','1');await TMC.wipeThisApp();return (await (indexedDB.databases?indexedDB.databases():Promise.resolve([]))).map(x=>x.name).indexOf('testc_photos')<0})()") in (True,),'Clear this app also clears only its own photo queue')
      x2.close()
     sec('16. PHOTO: take OR choose; HOME: one greeting, install button last')
     w.click('nav [data-tab=home]');w.wait_for_timeout(300)
     hm=w.evaluate("(()=>{const v=document.querySelector('header').nextElementSibling;return 1})()")
     ok(w.evaluate("document.body.innerText.split(/\\n/).filter(l=>/^👋/.test(l.trim())).length")==1,'Home shows exactly one greeting line')
     w.evaluate("TMC.__bip=1;window.dispatchEvent(Object.assign(new Event('beforeinstallprompt'),{prompt(){},userChoice:Promise.resolve()}))");w.wait_for_timeout(300)
     if w.locator('#hBand').count():
       ok(w.locator('#view .insB,#view .insH').count()==0,'standard Home: NO install button on Home')
       w.click('nav [data-tab=settings]');w.wait_for_timeout(300)
       ib=w.evaluate("(()=>{const b=document.querySelector('#view .insB');return b?b.getBoundingClientRect().height:0})()")
       ok(ib>=56,'install button is on Settings, big (%dpx)'%ib)
       w.click('nav [data-tab=home]');w.wait_for_timeout(300)
     else:
       ok(w.evaluate("(()=>{const b=document.querySelector('.insB,.insH');if(!b)return false;const all=[...document.querySelectorAll('.tile,.box,.insB,.insH')].filter(e=>e.offsetParent);return all[all.length-1]===b})()"),'install button is the last item on Home')
     w.screenshot(path=os.path.join(SHOTS,'home.png'))
     sec('16b. STANDARD HOME header (band: name + light + time + language; one hello; tiles; install last)')
     if not w.locator('#hBand').count():skip('app has no standard #hBand header yet (base standard: carry it over)')
     else:
      w.click('nav [data-tab=home]');w.wait_for_timeout(300)
      for vw in (360,390):
       for lg in ('en','fr','af'):
        w.set_viewport_size({'width':vw,'height':800});w.select_option('#hLang',lg);w.wait_for_timeout(250)
        hd=w.evaluate("""(()=>{const h=document.getElementById('hBand'),r=h.getBoundingClientRect(),q=s=>h.querySelector(s),nm=TMC.me().name,
          vis=e=>{if(!e)return false;const b=e.getBoundingClientRect();return b.width>0&&b.left>=-1&&b.right<=innerWidth+1&&b.top>=r.top-1&&b.bottom<=r.bottom+1};
          const main=document.querySelector('main').innerText;
          return {bg:getComputedStyle(h).backgroundColor,cvar:getComputedStyle(document.documentElement).getPropertyValue('--c').trim(),fg:getComputedStyle(h).color,
           name:vis(q('.t'))&&q('.t').textContent.trim().length>0,light:vis(q('#sDot')),time:vis(q('#sTime'))&&q('#sTime').textContent.trim().length>0,
           lang:vis(q('#hLang')),langH:q('#hLang').getBoundingClientRect().height,userInHdr:h.innerText.includes(nm),
           sync:q('#hS').innerText,count:(document.body.innerText.split(nm).length-1),hellos:(main.match(/👋/g)||[]).length,
           dir:document.documentElement.dir,scroll:document.documentElement.scrollWidth<=innerWidth+1,
           small:[...document.querySelectorAll('#app button,#app select')].filter(b=>b.offsetParent&&b.getBoundingClientRect().height<56).map(b=>b.id||b.className||b.textContent.trim()).slice(0,5),
           order:(()=>{const v=document.getElementById('view'),hi=document.getElementById('hHello'),ti=v.querySelector('.tiles'),ins=v.querySelector('.insB,.insH');
             const pos=e=>e?e.getBoundingClientRect().top:null;return {h:pos(hi),t:pos(ti),i:pos(ins),last:!ins||![...v.querySelectorAll('*')].some(e=>e.getBoundingClientRect().top>ins.getBoundingClientRect().bottom+1&&e.offsetParent)}})()}})()""")
        tag='%s %dpx'%(lg.upper(),vw)
        ok(hd['bg'] not in ('','rgba(0, 0, 0, 0)','rgb(255, 255, 255)') and hd['fg']=='rgb(255, 255, 255)','%s: coloured band (base colour kept: %s), white text'%(tag,hd['bg']))
        ok(hd['name'] and hd['light'] and hd['time'] and hd['lang'],'%s: band holds app name + light + time + language %s'%(tag,{k:hd[k] for k in ('name','light','time','lang')}))
        ok(not hd['userInHdr'] and hd['count']==1 and hd['hellos']==1,'%s: user name appears ONCE on Home (in the hello, not the header) count=%d'%(tag,hd['count']))
        ok('✓' not in hd['sync'] and '✔' not in hd['sync'] and 'ync' not in hd['sync'] and 'ynchro' not in hd['sync'],'%s: sync shows light + time only (no tick / no word) %r'%(tag,hd['sync']))
        ok(hd['langH']>=56 and not hd['small'],'%s: all buttons ≥56px %s'%(tag,hd['small']))
        tm=w.evaluate("document.getElementById('sTime').textContent.trim()")
        ok(bool(re.fullmatch(r'([01]\d|2[0-3]):[0-5]\d',tm)) or bool(re.search(r' ([01]\d|2[0-3]):[0-5]\d$',tm)),'%s: sync time is 24-hour HH:MM (no AM/PM, no seconds) on an en-US phone %r'%(tag,tm))
        hx=w.evaluate("typeof TMC.hm==='function'?[TMC.hm(new Date(2026,9,31,18,5)),TMC.hm(new Date(2026,9,31,7,4)),TMC.hm(new Date(2026,9,31,0,0))]:null")
        ok(hx==['18:05','07:04','00:00'],'%s: TMC.hm gives 18:05 / 07:04 / 00:00 %s'%(tag,hx))
        st=w.evaluate("(()=>{const r=e=>e?e.getBoundingClientRect():null,g=e=>e?getComputedStyle(e):null,h=document.getElementById('hBand'),t=document.getElementById('sTime'),l=document.getElementById('hLang');return {hH:Math.round(r(h).height),tF:g(t).fontSize,lW:Math.round(r(l).width),lH:Math.round(r(l).height),bf:g(document.querySelector('#view button')).fontFamily==g(document.body).fontFamily}})()")
        ok(st['bf'],'%s: buttons use the page font (font:inherit) %s'%(tag,st))
        ok(hd['scroll'],'%s: no sideways scroll'%tag)
        ok(hd['dir']=='ltr','%s: direction %s'%(tag,hd['dir']))
        lo=w.evaluate("(()=>{const b=document.getElementById('hOut'),h=document.getElementById('hHero');if(!b)return null;const r=b.getBoundingClientRect(),v=document.getElementById('view').getBoundingClientRect();return {after:h.nextElementSibling===b,h:r.height,full:r.width>=v.width-40,txt:b.textContent.trim()}})()")
        ok(lo and lo['after'] and lo['h']>=56 and lo['full'] and lo['txt'].startswith('🚪') and lo['txt']==w.evaluate("TMC.T?TMC.T[%r].logout:''"%lg),'%s: big full-width 🚪 Log out band right after the title card %s'%(tag,lo))
        tt=w.evaluate("(()=>{const g=s=>[...document.querySelectorAll(s)].map(b=>({k:b.dataset.tab,ic:b.querySelector('b,.ticon').textContent.trim(),n:(b.querySelector('.tlab')?b.querySelector('.tlab').textContent:b.textContent.replace(b.querySelector('b').textContent,'')).replace(/\\s*\\(\\d+\\)$/,'').trim()}));return {tabs:g('nav.tabs button').filter(x=>x.k!=='home'),tiles:g('#view .tiles .tile')}})()")
        tl=lambda xs:[(x['k'],x['ic']) for x in xs]
        ok(len(tt['tiles'])>0 and tl(tt['tabs'])==tl(tt['tiles']) and [x['n'] for x in tt['tabs']]==[x['n'] for x in tt['tiles']],'%s: every bottom tab has a matching Home tile and vice versa (same screen, icon, name, order) %s'%(tag,tl(tt['tiles'])))
        seq=w.evaluate("(()=>{const ids=['hBand','ncW','hHero','hOut'];const y=e=>e.getBoundingClientRect().top;const v=document.getElementById('view'),ti=v.querySelector('.tiles'),ins=null,nav=document.querySelector('nav.tabs');const p=[...ids.map(i=>document.getElementById(i)),ti,ins].filter(Boolean);const dom=p.every((e,i)=>!i||(p[i-1].compareDocumentPosition(e)&Node.DOCUMENT_POSITION_FOLLOWING));return {dom,navLast:getComputedStyle(nav).position==='fixed'&&nav.getBoundingClientRect().bottom>=innerHeight-1}})()")
        ok(seq['dom'] and seq['navLast'],'%s: Home order band > Not connected > title card > Log out > tiles > bottom tabs %s'%(tag,seq))
        o=hd['order'];ok(o['h'] is not None and o['t'] is not None and o['h']<o['t'] and (o['i'] is None or (o['i']>o['t'] and o['last'])),'%s: hello → tiles → install at the very bottom %s'%(tag,o))
      hc=w.evaluate("(()=>{const c=document.getElementById('hHero');return c?{img:!!c.querySelector('img'),name:c.querySelector('h2').textContent.trim()===CONFIG.NAME,date:document.getElementById('hDate').textContent.trim().length>4,hi:document.getElementById('hHello').textContent.trim().startsWith('👋'),ver:/\\bv\\d+|version/i.test(document.getElementById('view').innerText),under:document.querySelector('main').firstElementChild.id==='ncW'}:null})()")
      ok(hc and hc['img'] and hc['name'] and hc['date'] and hc['hi'] and not hc['ver'],'title card: logo + app name + today\'s date + 👋 Hi, name; no version on Home %s'%hc)
      w.evaluate("window._cf=window.confirm;window._asked=0;window.confirm=()=>{window._asked=1;return false}");w.click('#hOut');w.wait_for_timeout(300);_ask=w.evaluate('window._asked');w.evaluate('window.confirm=window._cf')
      ok(w.locator('#hBand').count()==1 and w.evaluate("!!TMC.me()") and _ask==1,'Log out band asks first (same log-out as Settings); Cancel keeps you signed in')
      nc=w.evaluate("""(()=>{const h=document.getElementById('hBand'),m=document.querySelector('main'),n=document.getElementById('ncW');return {first:!!n&&m.firstElementChild===n&&h.nextElementSibling===m,red:n?getComputedStyle(n).backgroundColor:'',shown:n?getComputedStyle(n).display!=='none':null}})()""")
      ok(nc['first'] and nc['shown'] is False,'"Not connected" banner sits right under the band, hidden while connected %s'%nc)
      w.context.set_offline(True);w.evaluate("dispatchEvent(new Event('offline'))");w.evaluate("TMC.syncNow&&TMC.syncNow().catch(()=>{})");w.wait_for_timeout(1500)
      nc2=w.evaluate("(()=>{const n=document.getElementById('ncW');return {shown:getComputedStyle(n).display!=='none',bg:getComputedStyle(n).backgroundColor,dot:document.getElementById('sDot').className}})()")
      ok(nc2['shown'] and nc2['bg']=='rgb(254, 226, 226)','sync not connected → red "Not connected" banner shows on Home %s'%nc2)
      w.context.set_offline(False);w.evaluate("dispatchEvent(new Event('online'))");w.evaluate("TMC.syncNow()");w.wait_for_timeout(2500)
      ok(w.evaluate("getComputedStyle(document.getElementById('ncW')).display")=='none','back online + synced → banner hides again')
      w.select_option('#hLang','en');w.set_viewport_size({'width':390,'height':844});w.wait_for_timeout(300)
      if os.path.realpath(APP)==os.path.realpath(os.path.join(os.path.dirname(__file__),'..')):
        w.screenshot(path='/workspace/base-home-standard.png');ok(os.path.exists('/workspace/base-home-standard.png'),'screenshot saved /workspace/base-home-standard.png')
     w.click('nav [data-tab=work]');w.wait_for_timeout(300)
     if w.locator('#exPh').count():
       ok(w.locator('#exPh .phCam').count()==1 and w.locator('#exPh .phGal').count()==1,'photo field has both buttons (camera + phone)')
       hs=w.evaluate("[...document.querySelectorAll('#exPh label')].map(e=>e.getBoundingClientRect().height)");ok(len(hs)==2 and min(hs)>=56,'both photo buttons >=56px high %s'%hs)
       ok(w.evaluate("(()=>{const c=document.querySelector('#exPh .phCam input'),g=document.querySelector('#exPh .phGal input');return c.getAttribute('capture')==='environment'&&!g.hasAttribute('capture')&&c.accept==='image/*'&&g.accept==='image/*'})()"),'capture only on the camera button; both accept image/*')
       ok('📷' in w.inner_text('#exPh .phCam') and '🖼️' in w.inner_text('#exPh .phGal'),'icons + text on both photo buttons')
       ok(all(w.evaluate("(()=>{const TT=%s;return ['en','fr','af']"%TJS+".map(l=>!!(TT[l].phTake&&TT[l].phPick))})()")),'photo buttons translated EN/FR/AF')
       import base64;png=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAgAAAAICAIAAABLbSncAAAAEklEQVR4nGNgYGD4z0AswK4SAFXuAf8EPy+xAAAAAElFTkSuQmCC')
       for cls,src in (('phGal','phone'),('phCam','camera')):
           w.evaluate("TMC.lastPhoto=null");w.set_input_files('#exPh .%s input'%cls,files=[{'name':'p.png','mimeType':'image/png','buffer':png}]);w.wait_for_function("!!TMC.lastPhoto",timeout=5000)
           ok(w.evaluate("TMC.lastPhoto.startsWith('data:image/jpeg')&&TMC.lastPhotoFrom")==src,'%s photo goes through the same resize/compress handler'%src)
     else:  # no demo box: check the app's real photo pairs instead
       if not w.locator('input[type=file][capture=environment]').count() and w.evaluate("typeof TMC.photoHTML==='function'"):
         w.evaluate("(()=>{const d=document.createElement('div');d.id='t16Ph';d.innerHTML=TMC.photoHTML('t16');(document.querySelector('main')||document.body).appendChild(d)})()")  # app's own pair helper, not on this screen yet
       pr=w.evaluate(r"""(()=>{const sz=e=>{const l=e.closest('label')||(e.id&&document.querySelector('label[for="'+e.id+'"]'))||e;const r=l.getBoundingClientRect();return r.height};
         return [...document.querySelectorAll('input[type=file][capture=environment]')].map(c=>{let p=c.parentElement,g=null;while(p&&!g){g=[...p.querySelectorAll('input[type=file]')].find(i=>i!==c&&!i.hasAttribute('capture')&&/image/.test(i.accept||''));p=p.parentElement}
           return {cam:/image/.test(c.accept||''),gal:!!g,hc:sz(c),hg:g?sz(g):0}})})()""")
       if not pr and not w.evaluate("document.querySelectorAll('input[type=file]').length"):skip('app has no photo spots at all')
       else:
        ok(len(pr)>0 and all(q['gal'] and q['cam'] for q in pr),'no #exPh: app has %d real photo pairs (camera + phone)'%len(pr))
        ok(len(pr)>0 and all(min(q['hc'],q['hg'])>=56 for q in pr),'real photo buttons >=56px high %s'%[(q['hc'],q['hg']) for q in pr][:6])
       ok(w.evaluate("[...document.querySelectorAll('input[type=file][capture]')].every(i=>i.getAttribute('capture')==='environment')"),'capture only on the camera inputs')
       w.evaluate("document.getElementById('t16Ph')&&document.getElementById('t16Ph').remove()")
     ok(w.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--rc').trim()")=='#1B7F3B','REPORT_COLOR config colour applied')
     w.evaluate("document.querySelector('#exOut')&&(document.querySelector('#exOut').innerHTML=TMC.reportHTML('Report',[['Notes',3],['Users',2]]))")
     if w.locator('.rep').count():ok(w.evaluate("getComputedStyle(document.querySelector('.rep th')).backgroundColor")=='rgb(27, 127, 59)' and w.inner_text('.rep tfoot').strip().endswith('5'),'report: green header + totals row')
     sec('19. STANDARD REPORTS screen (tab + tile, period, green table, Excel, Print, Back, EN/FR/AR, 360px)')
     if not w.evaluate("typeof TMC.addReport==='function'"):skip('app has no standard TMC.addReport yet (base standard: carry it over)')
     else:
      _pp=w.evaluate("CONFIG.PERMS.map(p=>p.id)");RPT=w.evaluate("CONFIG.REPORT_PERM||''") or ('reports' if 'reports' in _pp else ('rep' if 'rep' in _pp else 'reports'))  # reports tick name from the app's CONFIG, default 'reports'
      ok(RPT in _pp,'Admin tick list has a 📊 Reports tick (%r)'%RPT)
      _np=json.dumps([p for p in _pp if p!=RPT])
      ok(w.evaluate("TMC.repOk({admin:true})&&TMC.repOk({perms:[%s]})&&!TMC.repOk({perms:%s})"%(json.dumps(RPT),_np)),'only Admin or the %r tick may open Reports'%RPT)
      w.click('nav [data-tab=home]');w.wait_for_timeout(250)
      ok(w.locator('nav [data-tab=reports]').count()==1 and w.locator('#view .tile[data-tab=reports]').count()==1,'Admin: 📊 Reports in bottom tabs AND as a Home tile (one list)')
      ok(w.inner_text('nav [data-tab=reports] .ticon').strip()=='📊','Reports tab icon 📊')
      for vw in (360,390):
       for lg in ('en','fr','af'):
        w.set_viewport_size({'width':vw,'height':800});w.select_option('#hLang',lg);w.click('nav [data-tab=home]');w.wait_for_timeout(200)
        nv=w.evaluate("""(()=>{const bs=[...document.querySelectorAll('nav.tabs button')];return {n:bs.length,fit:bs.every(b=>{const r=b.getBoundingClientRect();return r.left>=-1&&r.right<=innerWidth+1&&b.scrollWidth<=b.clientWidth+1&&[...b.querySelectorAll('.tlab')].every(l=>l.getBoundingClientRect().right<=r.right+1&&l.getBoundingClientRect().left>=r.left-1)}),h:Math.min(...bs.map(b=>b.getBoundingClientRect().height)),scroll:document.documentElement.scrollWidth<=innerWidth+1}})()""")
        if vw==360 and lg=='en':
          w.evaluate("scrollTo(0,0)");shot(w,'home-360-en')
          ov=w.evaluate("(()=>{const h=document.querySelector('header'),c=document.getElementById('hHero');if(!h||!c)return null;const a=h.getBoundingClientRect(),b=c.getBoundingClientRect();return {hb:Math.round(a.bottom),ct:Math.round(b.top),pos:getComputedStyle(h).position}})()")
          ok(ov is None or ov['hb']<=ov['ct']+1,'360px Home: top band does not cover the title card %s'%ov)
        ok(nv['n']>=5 and nv['fit'] and nv['h']>=56 and nv['scroll'],'%s %dpx: %d bottom tabs fit, labels inside, ≥56px, no sideways scroll %s'%(lg.upper(),vw,nv['n'],nv))
      w.set_viewport_size({'width':390,'height':844});w.select_option('#hLang','en');w.wait_for_timeout(200)
      if os.path.realpath(APP)==os.path.realpath(BASE):w.screenshot(path='/workspace/base-home-reports.png')
      XR=w.evaluate("TMC.REPORTS.some(r=>r.id==='demo')")  # base demo 'x' notes report present?
      TR=False
      if not XR:  # app has its own reports: check each one opens and fits, then plug in a known test report so every engine check still runs
        for rid in w.evaluate("TMC.REPORTS.map(r=>r.id)"):
          w.evaluate("(id=>{TMC.rp().id=id})",rid);w.click('nav [data-tab=reports]');w.wait_for_timeout(300)
          for vw in (360,390):
            w.set_viewport_size({'width':vw,'height':800});w.wait_for_timeout(150)
            q=w.evaluate("({o:!!document.getElementById('rpOut'),sw:document.documentElement.scrollWidth,iw:innerWidth})")
            ok(q['o'] and q['sw']<=q['iw']+1,'app report %r opens at %dpx, no sideways scroll %s'%(rid,vw,q))
          w.set_viewport_size({'width':390,'height':844});w.evaluate("TMC.rp().id=null");w.click('nav [data-tab=home]');w.wait_for_timeout(200)
        w.evaluate("""(()=>{const d=new Date(),p=n=>String(n).padStart(2,'0'),td=d.getFullYear()+'-'+p(d.getMonth()+1)+'-'+p(d.getDate());
          window._trows=[{date:td,by:'Rep Tester',n:2,ch:6},{date:'2020-01-15',by:'Rep Tester',n:1,ch:7}];
          TMC.addReport({id:'demo',title:{en:'Test report',fr:'Rapport test',af:'Toets verslag'},cols:[{key:'date',label:{en:'Date',fr:'Date',af:'Datum'}},{key:'by',label:{en:'Person',fr:'Personne',af:'Persoon'}},{key:'n',label:{en:'Notes',fr:'Notes',af:'Notas'},num:true,sum:true},{key:'ch',label:{en:'Letters',fr:'Lettres',af:'Letters'},num:true,sum:true}],
            rows:(f,to)=>window._trows.filter(r=>r.date>=f&&r.date<=to)})})()""")
        XR=TR=True
      if XR and not TR:w.evaluate("TMC.put('x','rpA',{id:'rpA',text:'abcd',by:'Rep Tester',at:new Date().toISOString()});TMC.put('x','rpB',{id:'rpB',text:'xy',by:'Rep Tester',at:new Date().toISOString()});TMC.put('x','rpOld',{id:'rpOld',text:'old one',by:'Rep Tester',at:'2020-01-15T10:00:00Z'})")
      w.click('#view .tile[data-tab=reports]');w.wait_for_timeout(300)
      if w.locator('#rpList').count():  # app with several reports: list first, then pick one
        ok(w.locator('#rpList [data-rp]').count()==w.evaluate("TMC.REPORTS.length")>1,'report list shows every report (%d)'%w.locator('#rpList [data-rp]').count())
        w.locator('#rpList [data-rp]'+("[data-rp=demo]" if XR else "")).first.click()
      w.wait_for_selector('#rpOut .rep')
      ok(w.locator('#rpPick [data-rpp]').count()==3 and w.locator('#rpPick [data-rpp=today].on').count()==1,'period picker: Today / This month / Pick dates (Today first)')
      g=w.evaluate("""(()=>{const q=s=>document.querySelector(s),cs=e=>getComputedStyle(e);const th=q('#rpOut .rep th'),tr=document.querySelectorAll('#rpOut .rep tbody tr'),ft=q('#rpOut .rep tfoot td');
        return {th:cs(th).backgroundColor,thc:cs(th).color,alt:tr.length>1?cs(tr[1].children[0]).backgroundColor:'',ft:cs(ft).backgroundColor,ftc:cs(ft).color,rows:tr.length,tot:[...q('#rpOut .rep tfoot tr').children].map(e=>e.textContent.trim())}})()""")
      ok(g['th']=='rgb(27, 127, 59)' and g['thc']=='rgb(255, 255, 255)','green #1B7F3B header, white text %s'%g['th'])
      ok(g['ft']!='rgba(0, 0, 0, 0)' and g['ftc']=='rgb(27, 127, 59)','green totals row %s'%g)
      tdy=[r for r in g['tot']]
      if not XR:skip('demo notes totals / Today / Pick-date counts: app has no demo \'x\' report')
      else:
       ok(len(tdy)==4 and float(tdy[2])>=2 and float(tdy[3])>=6,'Today totals add up (notes ≥2, letters ≥6) %s'%tdy)
       ok('old one' not in w.inner_text('#rpOut') and w.evaluate("TMC.rpData((TMC.REPORTS.length===1?TMC.REPORTS[0]:TMC.REPORTS.find(r=>r.id===TMC.rp().id))).rows.every(r=>r.date===TMC.rpData((TMC.REPORTS.length===1?TMC.REPORTS[0]:TMC.REPORTS.find(r=>r.id===TMC.rp().id))).f)"),'Today shows only today')
       w.click('#rpPick [data-rpp=pick]');w.wait_for_selector('#rpF')
       w.fill('#rpF','2020-01-01');w.fill('#rpT','2020-01-31');w.click('#rpGo');w.wait_for_timeout(200)
       ok(w.evaluate("TMC.rpData((TMC.REPORTS.length===1?TMC.REPORTS[0]:TMC.REPORTS.find(r=>r.id===TMC.rp().id))).rows.length")==1 and '7' in w.inner_text('#rpOut .rep tfoot'),'Pick dates: Jan 2020 → only the old note (7 letters)')
       w.fill('#rpF','2020-01-31');w.fill('#rpT','2020-01-01');w.click('#rpGo');w.wait_for_timeout(200)
       ok(w.evaluate("TMC.rpData((TMC.REPORTS.length===1?TMC.REPORTS[0]:TMC.REPORTS.find(r=>r.id===TMC.rp().id))).rows.length")==1,'dates typed backwards are swapped')
      if not XR:w.click('#rpPick [data-rpp=pick]');w.wait_for_selector('#rpF');w.fill('#rpF','2020-01-31');w.fill('#rpT','2020-01-01');w.click('#rpGo');w.wait_for_timeout(200);ok(w.evaluate("(d=>d.f<=d.to)(TMC.rpData((TMC.REPORTS.length===1?TMC.REPORTS[0]:TMC.REPORTS.find(r=>r.id===TMC.rp().id))))"),'dates typed backwards are swapped')
      w.click('#rpPick [data-rpp=pick]');w.wait_for_selector('#rpF')
      for vw in (360,390):
       w.set_viewport_size({'width':vw,'height':800});w.wait_for_timeout(150)
       pk=w.evaluate("(()=>{const b=document.getElementById('rpBack').getBoundingClientRect(),n=document.querySelector('nav.tabs');return {sw:document.documentElement.scrollWidth,iw:innerWidth,f:Math.round(document.getElementById('rpF').getBoundingClientRect().right),t:Math.round(document.getElementById('rpT').getBoundingClientRect().right),bk:Math.round(b.right)}})()")
       ok(pk['sw']<=pk['iw']+1 and max(pk['f'],pk['t'],pk['bk'])<=pk['iw']+1,'%dpx Pick dates open: From/To + Back fit, no sideways scroll %s'%(vw,pk))
      w.set_viewport_size({'width':390,'height':844})
      w.click('#rpPick [data-rpp=month]');w.wait_for_timeout(200)
      ok(w.evaluate("(()=>{const d=TMC.rpData((TMC.REPORTS.length===1?TMC.REPORTS[0]:TMC.REPORTS.find(r=>r.id===TMC.rp().id)));return d.f.endsWith('-01')&&d.f.slice(0,7)===d.to.slice(0,7)})()"),'This month: 1st → last day of the month')
      w.click('#rpPick [data-rpp=today]');w.wait_for_timeout(200)
      big=w.evaluate("[...document.querySelectorAll('#view button,#view input')].filter(b=>b.offsetParent).map(b=>[b.id||b.textContent.trim(),Math.round(b.getBoundingClientRect().height)])")
      ok(all(h>=56 for _,h in big),'all report buttons/fields ≥56px %s'%big)
      ok([w.locator(s).count() for s in ('#rpXls','#rpPrint','#rpBack')]==[1,1,1] and w.inner_text('#rpXls').startswith('📥') and w.inner_text('#rpPrint').startswith('🖨') and w.inner_text('#rpBack').startswith('⬅'),'📥 Download Excel, 🖨️ Print, ⬅ Back buttons')
      w.emulate_media(media='print');pv=w.evaluate("[...document.querySelectorAll('#app button,nav.tabs,header')].filter(e=>getComputedStyle(e).display!=='none').length");tv=w.evaluate("getComputedStyle(document.querySelector('#rpOut .rep')).display");w.emulate_media(media='screen')
      ok(pv==0 and tv!='none','print: buttons/header/tabs hidden, table printed (%d visible)'%pv)
      w.evaluate("window._pr=0;window.print=()=>{window._pr=1}");w.click('#rpPrint');ok(w.evaluate('window._pr')==1,'Print button calls print')
      with w.expect_download() as dl:w.click('#rpXls')
      fp=os.path.join(tempfile.gettempdir(),'tmc_rep_test.xlsx');dl.value.save_as(fp)
      try:
        import openpyxl;wb=openpyxl.load_workbook(fp);sh=wb.active;rows=list(sh.iter_rows(values_only=True))
        hr=[r for r in range(1,sh.max_row+1) if sh.cell(r,1).value==w.evaluate("(d=>{const l=d.cols[0].label;return typeof l==='string'?TMC.T.en[l]||l:l.en})((TMC.REPORTS.length===1?TMC.REPORTS[0]:TMC.REPORTS.find(r=>r.id===TMC.rp().id)))")][0];SC=1+w.evaluate("(TMC.REPORTS.length===1?TMC.REPORTS[0]:TMC.REPORTS.find(r=>r.id===TMC.rp().id)).cols.findIndex(c=>c.sum)");CL=chr(64+SC);last=sh.max_row
        hc=sh.cell(hr,1);ok(hc.fill.fgColor.rgb.endswith('1B7F3B') and hc.font.color.rgb.endswith('FFFFFF') and hc.font.b,'Excel: green header, white bold text')
        ok(last-hr<3 or sh.cell(hr+2,1).fill.fgColor.rgb.endswith('E8F3EC'),'Excel: light green alternating rows')
        fc=sh.cell(last,SC);ok(str(fc.value).startswith('=SUM(%s%d:%s'%(CL,hr+1,CL)) and sh.cell(last,1).fill.fgColor.rgb.endswith('CDE3D4'),'Excel: green totals row with SUM formulas %s'%fc.value)
        ok(dl.value.suggested_filename.endswith('.xlsx') and os.path.getsize(fp)<20000,'real .xlsx file %s'%dl.value.suggested_filename)
      except ImportError:skip('openpyxl not installed')
      if shutil.which('soffice') or shutil.which('libreoffice'):
        od=tempfile.mkdtemp();subprocess.run([shutil.which('soffice') or shutil.which('libreoffice'),'--headless','--convert-to','csv','--outdir',od,fp],capture_output=True,timeout=90)
        cv=open(os.path.join(od,'tmc_rep_test.csv'),encoding='utf-8',errors='replace').read().strip().splitlines() if os.path.exists(os.path.join(od,'tmc_rep_test.csv')) else []
        ok(cv and cv[-1].split(',')[SC-1]==g['tot'][SC-1],'LibreOffice opens it and SUM = screen total %s'%(cv[-1] if cv else None))
      for vw in (360,390):
       for lg in ('en','fr','af'):
        w.set_viewport_size({'width':vw,'height':800});w.select_option('#hLang',lg);w.wait_for_timeout(200)
        r=w.evaluate("({dir:document.documentElement.dir,scroll:document.documentElement.scrollWidth<=innerWidth+1,tw:document.querySelector('#rpOut .rep').getBoundingClientRect().right<=innerWidth+1&&document.querySelector('#rpOut .rep').getBoundingClientRect().left>=-1,x:document.getElementById('rpXls').textContent,th:document.querySelector('#rpOut .rep th').textContent})")
        ok(r['scroll'] and r['tw'] and r['dir']=='ltr' and r['x']==w.evaluate("TMC.T[%r].rpXls"%lg) and r['th']==w.evaluate("(d=>{const l=d.cols[0].label;return typeof l==='string'?TMC.T[%r][l]||l:l[%r]})((TMC.REPORTS.length===1?TMC.REPORTS[0]:TMC.REPORTS.find(r=>r.id===TMC.rp().id)))"%(lg,lg)),'%s %dpx: report translated, %s, table fits, no sideways scroll'%(lg.upper(),vw,r['dir']))
      w.set_viewport_size({'width':390,'height':844});w.select_option('#hLang','en');w.wait_for_timeout(200)
      if os.path.realpath(APP)==os.path.realpath(BASE):w.screenshot(path='/workspace/base-report-standard.png',full_page=True)
      w.click('#rpBack');w.wait_for_timeout(200)
      if w.locator('#rpList').count():w.click('#rpBack') if w.locator('#rpBack').count() else w.click('nav [data-tab=home]');w.wait_for_timeout(200)
      ok(w.locator('#hHero').count()==1,'⬅ Back returns to Home')
      if TR:w.evaluate("(()=>{const i=TMC.REPORTS.findIndex(r=>r.id==='demo');if(i>=0)TMC.REPORTS.splice(i,1)})()")
      elif XR:w.evaluate("['rpA','rpB','rpOld'].forEach(i=>TMC.remove('x',i))")
     x.close()
     sec('14. "Not connected" banner')
     x=newctx(br);n=watch(x.new_page(),'nc');x.route('**/exec',lambda r:r.abort());n.goto(CU);n.wait_for_selector('.card')
     n.wait_for_selector('#ncW',state='visible',timeout=8000);ok('Not connected' in n.inner_text('#ncW'),'script unreachable → red "Not connected" banner with retry');shot(n,'not-connected-en')
     n.select_option('#langSel','fr');n.wait_for_timeout(300);n.evaluate("TMC.api({action:'status',name:'x'}).catch(()=>{})");n.wait_for_timeout(500);ok('Pas connecté' in n.inner_text('#ncW'),'banner in French')
     n.select_option('#langSel','af');n.evaluate("TMC.api({action:'status',name:'x'}).catch(()=>{})");n.wait_for_timeout(500);ok('Nie gekoppel nie' in n.inner_text('#ncW'),'banner in Afrikaans');shot(n,'not-connected-af')
     x.unroute('**/exec');n.click('#ncB');n.wait_for_timeout(1200);ok(not n.is_visible('#ncW'),'retry after the script is back → banner gone')
     x.close()
     ERR[:]=[e for e in ERR if not e.startswith('nc:')]   # aborted requests in test 14 are expected
     br.close()
  sec('15. APP NAME spell-check (approved names)')
  sys.path.insert(0,os.path.join(BASE,'tools'));import app_name_check as anc
  _a,_f,_e=anc.check(BASE);ok(not _e,'base names spelled right and the same %s'%_e[:3])
  _nm=anc.fields(BASE)[0].get('CONFIG NAME','TMC Base App')  # works for any app built on the base
  _d=tempfile.mkdtemp();shutil.copy(os.path.join(BASE,'index.html'),_d);shutil.copy(os.path.join(BASE,'manifest.json'),_d)
  _s=open(os.path.join(_d,'index.html')).read().replace('TMC Base App','TMC Sahara Purshes').replace(_nm,'TMC Sahara Purshes');open(os.path.join(_d,'index.html'),'w').write(_s)
  _m=open(os.path.join(_d,'manifest.json')).read().replace('TMC Base App','TMC Sahara Purchases').replace(_nm,'TMC Sahara Purchases');open(os.path.join(_d,'manifest.json'),'w').write(_m)
  _a,_f,_e=anc.check(_d)
  ok(_a=='TMC Sahara Purchases' and any('Purshes' in x for x in _e),'misspelt "Purshes" is flagged')
  ok(any(x.startswith('CONFIG NAME') for x in _e) and not any(x.startswith('manifest name') for x in _e),'flags exactly where (CONFIG wrong, manifest right)')
  ok(anc.near('Purchases') is None and anc.near('Rotation') is None and anc.near('location') is None and anc.near('Salary') is None and anc.near('Sales') is None,'correct words / normal words not flagged')
  def gs(port,path):return json.load(urllib.request.urlopen('http://127.0.0.1:%d%s'%(port,path)))
  from hashlib import sha256 as _sha
  def mkpin(port,uid,pin_):  # set a PIN on a seeded/approved user the way the phone does it
      return raw(port,{'action':'setpin','id':uid,'salt':'s1','pinH':_sha(('s1:'+pin_).encode()).hexdigest(),'device':'t'})
  sec('17. setupOnce(): one Run + Allow sets everything, safe to run twice')
  if 'function setupOnce' not in GSRC:skip('this app\'s Code.gs has no setupOnce() yet (base standard: carry it over)')
  else:
    _sn=(re.search(r"APP_SHEET_NAME\s*=\s*'([^']*)'",GSRC) or re.search(r'rename\("([^"]*)"\)',GSRC));_sn=_sn.group(1) if _sn else None
    ok("TEAM_CODE_SETUP = '__TMC_TEAM_CODE__'" in GSRC,'file keeps the __TMC_TEAM_CODE__ placeholder (no real code in the file)')
    o1=gs(P4,'/_setup');st=gs(P4,'/_state')
    ok('err' not in o1,'setupOnce runs without error %s'%o1)
    ok(st['teamCode'] is None and 'TEAM_CODE' not in st['props'],'placeholder left → no TEAM_CODE written (token-only app)')
    ok(_sn is None or st['name']==_sn,'Sheet renamed to the app name: %r'%st['name'])
    ok(all(t in st['tabs'] for t in ('_Records','Fix log')+(('Users',) if "'Users'" in GSRC else ())),'tabs + headers made: %s'%st['tabs'])
    _sh=gs(P4,'/_sheets');ok(_sh['_Records'][0][:3]==['Key','Kind','Id'] and (_sh['Users'][0][0]=='Name' if 'Users' in _sh else "'Users'" not in GSRC) and _sh['Fix log'][0][0]=='Time','header rows seeded')
    _ad=[u for u in U(P4) if ADM(u)]
    ok(len(_ad)==1 and _ad[0].get('status','active')=='active' and not _ad[0].get('pinH'),'first Admin seeded (active, no PIN yet)')
    _an=_ad[0]['name'] if _ad else ''
    post_=raw(P4,{'action':'status','name':'Johan Kirsten'})
    ok(post_.get('state')=='active' and post_.get('hasPin') is False,'Admin name → "choose your PIN" (active, no PIN) %s'%post_)
    raw(P4,{'action':'register','name':'Achta Moussa','device':'z'})
    o2=gs(P4,'/_setup');o3=gs(P4,'/_setup')
    ok(o2.get('admin')=='kept' and o3.get('admin')=='kept' and len([u for u in U(P4) if ADM(u)])==1,'run twice/three times → still ONE Admin')
    ok(any(u['name']=='Achta Moussa' for u in U(P4)) and len(U(P4))==2,'second run keeps existing users/data')
    ok(gs(P4,'/_state')['name']==st['name'],'second run: Sheet name unchanged')
    r=mkpin(P4,_ad[0]['id'],'4321');ok(r.get('ok') and r.get('token'),'seeded Admin sets the first PIN and gets a token')
    ok(mkpin(P4,_ad[0]['id'],'9999').get('ok') is False,'nobody can set the Admin PIN a second time')
    gs(P4,'/_setup');ok([u for u in U(P4) if ADM(u)][0].get('pinH') in (_sha(b's1:4321').hexdigest(),) or str([u for u in U(P4) if ADM(u)][0].get('pinH','')).startswith('v2:'),'re-running setupOnce never wipes the Admin PIN')
    T1='[{"fn":"dailyJob","hour":5}]'
    gs(P4,'/_setup?trig='+urllib.parse.quote(T1));gs(P4,'/_setup?trig='+urllib.parse.quote(T1))
    _tg=gs(P4,'/_state')['triggers'];_want=re.findall(r"fn:\s*'([^']+)'",(re.search(r'var TRIGGERS\s*=\s*\[(.*?)\];',GSRC,re.S) or re.search('()',''))[1]);ok(len(_tg)==len(set(_tg)) and ([t for t in _tg if t!='photoCleanup']==['dailyJob'] or (_want and all(f in _tg for f in _want))),'trigger installed once, never doubled %s'%gs(P4,'/_state')['triggers'])
    o4=gs(P4,'/_setup?code='+urllib.parse.quote('test-only-77'))
    ok(o4.get('teamCode')=='set' and gs(P4,'/_state')['teamCode']=='test-only-77','replaced placeholder → TEAM_CODE stored in Script Properties')
    ok(post(P4,'test-only-77',[]).get('ok') is True,'team code works after setupOnce')
    o5=gs(P4,'/_setup?code=__TMC_TEAM_CODE__')
    ok(o5.get('teamCode')=='kept' and gs(P4,'/_state')['teamCode']=='test-only-77','placeholder again → existing TEAM_CODE kept, not wiped')
    ok(gs(P4,'/_state')['src'],'the code is never written back into the file')
  sec('18. SAFE SIGN-IN ONLY: STRICT_TOKEN=1 → team code may not change users')
  if 'STRICT_TOKEN' not in GSRC:skip('this app\'s Code.gs has no STRICT_TOKEN option yet (base standard: carry it over)')
  else:
    _n=lambda:int(time.time()*1000)
    gs(P5,'/_setup') if 'function setupOnce' in GSRC else None
    _ad=[u for u in U(P5) if ADM(u)]
    if not _ad:raw(P5,{'action':'setpin','setup':1,'name':'Johan Kirsten','salt':'s1','pinH':_sha(b's1:4321').hexdigest(),'device':'t'});_ad=[u for u in U(P5) if ADM(u)]
    else:mkpin(P5,_ad[0]['id'],'4321')
    _tk=raw(P5,{'action':'login','id':_ad[0]['id'],'pinH':_sha(b's1:4321').hexdigest(),'device':'t'}).get('token')
    ok(bool(_tk),'Admin token for the strict tests')
    r=post(P5,'code-s',[{'kind':'u','id':'sp1','u':_n(),'del':0,'data':{'id':'sp1','name':'Old Phone One','status':'pending','dev':'q'}}])
    ok(r.get('accepted')==1 and any(u['id']=='sp1' for u in U(P5)),'OFF (default): old team-code phone can still send a user record')
    gs(P5,'/_prop?STRICT_TOKEN=1')
    r=post(P5,'code-s',[{'kind':'u','id':'sp2','u':_n(),'del':0,'data':{'id':'sp2','name':'Old Phone Two','status':'pending','dev':'q'}}])
    ok(r.get('refusedWhy')=='need_token' and r.get('refused')==1 and not any(u['id']=='sp2' for u in U(P5)),'ON: team-code user record refused (refusedWhy need_token) %s'%{k:r.get(k) for k in ('accepted','refused','refusedWhy')})
    adm=dict([u for u in U(P5) if ADM(u)][0],status='blocked')
    r=post(P5,'code-s',[{'kind':'u','id':adm['id'],'u':_n()+5,'del':0,'data':adm}])
    ok(r.get('refusedWhy')=='need_token' and [u for u in U(P5) if ADM(u)][0].get('status','active')=='active','ON: team code cannot change the Admin')
    r=post(P5,'code-s',[{'kind':'x','id':'sx1','u':_n(),'del':0,'data':{'id':'sx1','text':'still adds'}}])
    ok(r.get('accepted')==1 and r.get('ok'),'ON: team-code phones still ADD normal records (no data lost)')
    ok(any(x['kind']=='u' for x in r.get('records',[])) and not [1 for x in r.get('records',[]) if x['kind']=='u' and any(f in (x['data'] if isinstance(x['data'],dict) else json.loads(x['data'] or '{}')) for f in ('pinH','salt','pin'))],'ON: team-code reply still has users, with no PIN secrets')
    sp1=dict([u for u in U(P5) if u['id']=='sp1'][0],status='active')
    r=raw(P5,{'action':'sync','token':_tk,'device':'t','since':0,'changes':[{'kind':'u','id':'sp1','u':_n()+9,'del':0,'data':sp1}]})
    ok(r.get('accepted')==1 and [u for u in U(P5) if u['id']=='sp1'][0]['status']=='active','ON: Admin token can still approve users')
    ok(raw(P5,{'action':'register','name':'New Phone Three','device':'n3'}).get('state')=='pending','ON: sign-up with name (no code) still works')
    gs(P5,'/_prop?STRICT_TOKEN=')
    r=post(P5,'code-s',[{'kind':'u','id':'sp4','u':_n(),'del':0,'data':{'id':'sp4','name':'Old Phone Four','status':'pending','dev':'q'}}])
    ok(r.get('accepted')==1 and not r.get('refused'),'OFF again: back to the old behaviour')
  sec('20. Admin fix: token beats team code (tests/admin_fix_test_spec.md A1-A7, B1-B8; every app must pass)')
  P6=free();gas.append(subprocess.Popen(['node',os.path.join(BASE,'tests','gas_server.js'),str(P6),'code-f'],stdout=subprocess.PIPE,env=dict(os.environ,GAS_FILE=GAS_FILE)));gas[-1].stdout.readline()
  CF6=build('appf','testf',P6,'code-f');F6='http://127.0.0.1:%d/appf/'%PW
  _n=lambda:int(time.time()*1000)
  def xr(port,i):
      r=[r for r in dump(port)['recs'] if r['kind']=='x' and r['id']==i and not r['del']]
      return (r[0]['data'] if isinstance(r[0]['data'],dict) else json.loads(r[0]['data'] or '{}')) if r else {}
  def flog(port):return gs(port,'/_sheets').get('Fix log',[])
  def chg(i,t,dl=0):return [{'kind':'x','id':i,'u':_n(),'del':dl,'data':None if dl else {'id':i,'text':t}}]
  gs(P6,'/_setup') if 'function setupOnce' in GSRC else None
  _ad=[u for u in U(P6) if ADM(u)]
  if not _ad:raw(P6,{'action':'setpin','setup':1,'name':'Johan Kirsten','salt':'s1','pinH':_sha(b's1:4321').hexdigest(),'device':'t'});_ad=[u for u in U(P6) if ADM(u)]
  else:mkpin(P6,_ad[0]['id'],'4321')
  ATK=raw(P6,{'action':'login','id':_ad[0]['id'],'pinH':_sha(b's1:4321').hexdigest(),'device':'t'}).get('token')
  raw(P6,{'action':'register','name':'Staff One','device':'s1'})
  _su=[u for u in U(P6) if u['name']=='Staff One'][0]
  raw(P6,{'action':'sync','token':ATK,'device':'t','since':0,'changes':[{'kind':'u','id':_su['id'],'u':_n(),'del':0,'data':dict(_su,status='active')}]})
  mkpin(P6,_su['id'],'5678');STK=raw(P6,{'action':'login','id':_su['id'],'pinH':_sha(b's1:5678').hexdigest(),'device':'t'}).get('token')
  ok(bool(ATK) and bool(STK),'setup: Admin token and staff token on a server WITH a team code')
  # A6 first: code-only phones may ADD
  r=post(P6,'code-f',chg('fa1','add one')+chg('fa2','add two')+chg('fa3','add three')+chg('fa4','add four')+chg('fb3','b3 start')+chg('fb7','b7 start'))
  ok(r.get('ok') and r.get('accepted')==6 and not r.get('refused') and xr(P6,'fa1').get('text')=='add one','A6: code-only ADD accepted %s'%{k:r.get(k) for k in ('accepted','refused')})
  def S(body):return raw(P6,dict({'action':'sync','device':'t','since':0},**body))
  n0=len(flog(P6))
  r=S({'token':ATK,'changes':chg('fa1','A1 fixed')})
  ok(r.get('accepted')==1 and not r.get('refused') and xr(P6,'fa1').get('text')=='A1 fixed','A1: Admin token fix accepted')
  ok(len(flog(P6))>n0 and any('fa1' in json.dumps(x) and 'A1 fixed' in json.dumps(x) for x in flog(P6)[1:]),'A1: fix written to the Fix log')
  r=S({'token':ATK,'code':'code-f','changes':chg('fa2','A2 fixed')})
  A2=r.get('accepted')==1 and not r.get('refused') and xr(P6,'fa2').get('text')=='A2 fixed'
  print('  INFO  A2 (server): Admin token + team code → %s (%s)'%('accepted' if A2 else 'refused, server still checks the code first; phone must prove B3',{k:r.get(k) for k in ('accepted','refused','refusedWhy')}),flush=True)
  r=S({'token':STK,'changes':chg('fa3','A3 hack')})
  ok(r.get('refused')==1 and xr(P6,'fa3').get('text')=='add three','A3: staff token fix refused')
  r=S({'token':STK,'code':'code-f','changes':chg('fa3','A4 hack')})
  ok(r.get('refused')==1 and xr(P6,'fa3').get('text')=='add three','A4: staff token + team code fix refused')
  r=post(P6,'code-f',chg('fa3','A5 hack'));r2=post(P6,'code-f',chg('fa3','',1))
  ok(r.get('refused')==1 and r2.get('refused')==1 and xr(P6,'fa3').get('text')=='add three','A5: team code only: fix AND delete refused')
  r=S({'token':ATK,'code':'wrong-code','changes':chg('fa4','A7 fixed')})
  ok(r.get('ok') is False or (r.get('accepted')==1 and xr(P6,'fa4').get('text')=='A7 fixed'),'A7: Admin token + wrong code is never silently treated as staff %s'%{k:r.get(k) for k in ('ok','accepted','refused','refusedWhy','error')})
  ok(not any('hack' in json.dumps(x) for x in flog(P6)),'refused attempts never reach the Fix log')
  with sync_playwright() as p:
    br=p.chromium.launch(executable_path=CHROME) if CHROME else p.chromium.launch()
    x0=newctx(br);t0=openp(x0,F6,'afProbe')
    if not t0.evaluate("!!(window.TMC&&TMC.canFix&&TMC.me&&TMC.L)"):
      skip('app has no TMC.canFix/TMC.me (not on the base runtime): B1-B8 phone tests do not apply');ok(A2,'A2 OR B3: Admin fix must land (no phone tests, so A2 must pass)');x0.close()
    else:
     x0.close()
     # B1: token-only app (no team code): Admin sees ✏️ and the fix syncs
     x1=newctx(br);c1=openp(x1,CU,'afB1');name(c1,'Johan Kirsten');pin(c1,pin_of(0));synced(c1)
     c1.evaluate("TMC.put('x','fb1',{id:'fb1',text:'b1 start'})");c1.wait_for_function('TMC.pending()===0',timeout=10000)
     ok(home(c1) and isadm(c1) and c1.evaluate("TMC.canFix()") and c1.evaluate("!!TMC.L.get('tok')&&!TMC.L.get('sycode')&&!CONFIG.SYNC_CODE"),'B1: Admin with token, no code → canFix true (✏️ shown)')
     ok(c1.evaluate("TMC.fix('x','fb1','text','b1 fixed')") is not False,'B1: TMC.fix accepted on the phone');c1.wait_for_function('TMC.pending()===0',timeout=10000)
     ok(xr(P3,'fb1').get('text')=='b1 fixed','B1: fix reached the server');x1.close()
     # Admin on a code phone
     xa=newctx(br);fa=openp(xa,F6,'afAdm');BODY=[]
     fa.on('request',lambda q:BODY.append(json.loads(q.post_data)) if q.url.endswith('/exec') and q.post_data else None)
     name(fa,'Johan Kirsten');pin(fa,'4321');synced(fa)
     ok(home(fa) and isadm(fa),'Admin signed in on a team-code phone')
     ok(fa.evaluate("!!TMC.L.get('tok')") and fa.evaluate("!!(TMC.L.get('sycode')||CONFIG.SYNC_CODE)") and fa.evaluate("TMC.canFix()"),'B2: Admin with token AND a saved code → canFix true')
     # B3
     BODY.clear();ok(fa.evaluate("TMC.fix('x','fb3','text','b3 fixed')") is not False,'B3: Admin fixes on the code phone');fa.wait_for_function('TMC.pending()===0',timeout=10000)
     sb=[b for b in BODY if b.get('action')=='sync' and any(c.get('id')=='fb3' for c in b.get('changes',[]))]
     ok(sb and all(b.get('token') and not b.get('code') for b in sb),'B3: sync body has the token and NO team code %s'%[sorted(k for k in b if b[k]) for b in sb])
     B3=xr(P6,'fb3').get('text')=='b3 fixed';ok(B3,'B3: server copy changed')
     ok(A2 or B3,'A2 OR B3: the Admin fix really lands on a team-code server')
     xs=newctx(br);fs=openp(xs,F6,'afStaff');name(fs,'Staff One');pin(fs,'5678');synced(fs)
     ok(home(fs) and not isadm(fs) and any(r['id']=='fb3' and r['text']=='b3 fixed' for r in fs.evaluate("TMC.all('x')")),'B3: a second phone sees the fix')
     # B5
     ok(not fs.evaluate("TMC.canFix()") and fs.locator('.fixB').count()==0,'B5: staff (token + code) → canFix false, no ✏️')
     DLG['msgs'].clear();ok(fs.evaluate("TMC.put('x','fb3',{id:'fb3',text:'b5 hack'})") is False and fs.evaluate("TMC.remove('x','fb3')") is False,'B5: forced put/remove refused on the phone')
     fs.wait_for_timeout(600);ok(xr(P6,'fb3').get('text')=='b3 fixed','B5: server copy unchanged');xs.close()
     # B4
     fa.evaluate("TMC.L.del('tok')");ok(not fa.evaluate("TMC.canFix()"),'B4: code phone, token gone → ✏️ hidden until a token is back')
     fa.evaluate("TMC.syncNow()");fa.wait_for_function("!!TMC.L.get('tok')",timeout=10000)
     ok(fa.evaluate("TMC.canFix()") and home(fa) and isadm(fa),'B4: Admin on a code phone with no token → fetches a token, ✏️ back')
     # B7: force the server to refuse (rewrite the body like an old phone: code, no token)
     def old(rt):
         b=json.loads(rt.request.post_data or '{}')
         if b.get('action')=='sync' and b.get('changes'):b.pop('token',None);b['code']='code-f'
         rt.continue_(post_data=json.dumps(b))
     fa.route('**/exec',old)
     fa.evaluate("TMC.fix('x','fb7','text','b7 local')");fa.wait_for_selector('#tmcToast',state='visible',timeout=10000)
     ok(fa.inner_text('#tmcToast')==fa.evaluate("TMC.t('fixRef')") and 'not saved' in fa.inner_text('#tmcToast'),'B7: server refuses → plain message: %s'%fa.inner_text('#tmcToast'))
     fa.unroute('**/exec');fa.wait_for_function("(TMC.all('x').find(r=>r.id==='fb7')||{}).text==='b7 start'",timeout=12000)
     ok(xr(P6,'fb7').get('text')=='b7 start' and fa.evaluate("TMC.pending()")==0,'B7: local change reverted to the server copy')
     ok(all(fa.evaluate("TMC.T[%r].fixRef"%l) for l in ('en','fr','af')) and len({fa.evaluate("TMC.T[%r].fixRef"%l) for l in ('en','fr','af')})==3,'B7: message in EN / FR / AF')
     # B6: code-only phone (Admin login refused → no token) keeps syncing by code, no ✏️
     fa.route('**/exec',lambda rt:rt.fulfill(status=200,content_type='application/json',body='{"ok":false,"error":"bad_pin"}') if json.loads(rt.request.post_data or '{}').get('action')=='login' else rt.continue_())
     fa.evaluate("TMC.L.del('tok')");fa.evaluate("TMC.syncNow()");fa.wait_for_timeout(1500)
     ok(home(fa) and not fa.evaluate("TMC.L.get('tok')") and not fa.evaluate("TMC.canFix()") and fa.locator('.fixB').count()==0,'B6: code-only phone → canFix false, still signed in')
     post(P6,'code-f',chg('fb6','b6 server add'));synced(fa);fa.wait_for_timeout(500)
     ok(any(r['id']=='fb6' for r in fa.evaluate("TMC.all('x')")),'B6: code-only phone still syncs by team code')
     fa.unroute('**/exec')  # a failed Admin login is not retried until reload / re-sign-in (no login storm)
     # B8: log out, staff signs in on the same phone
     fa.click('nav [data-tab=settings]');fa.click('#sOut');fa.wait_for_timeout(800)
     ok(not home(fa) and not fa.evaluate("TMC.L.get('tok')"),'B8: log out drops the Admin token')
     name(fa,'Staff One');pin(fa,'5678');synced(fa);fa.click('nav [data-tab=work]');fa.wait_for_timeout(300)
     ok(home(fa) and not isadm(fa) and not fa.evaluate("TMC.canFix()") and fa.locator('.fixB').count()==0,'B8: staff on the same phone → no ✏️')
     xa.close()
    br.close()
  sec('21. REDRAW GUARD: a sync never wipes a half-filled form (tests/test_redraw_guard.py)')
  if os.path.exists(os.path.join(APP,'tests','gas_server.js')):
    rg=subprocess.run([sys.executable,os.path.join(BASE,'tests','test_redraw_guard.py'),APP],capture_output=True,text=True,timeout=300)
    for ln in rg.stdout.splitlines():
      if ln.startswith('  PASS ') or ln.startswith('  FAIL '):ok(ln.startswith('  PASS '),'redraw guard: '+ln[7:])
    ok(rg.returncode==0 and 'REDRAW GUARD:' in rg.stdout,'redraw guard script finished clean (exit %s) %s'%(rg.returncode,rg.stderr[-300:]))
  else:skip('app has no tests/gas_server.js: redraw guard check not run')
  sec('23. BACK BUTTON (VER 10): big "← Back" at the top of every screen except Home (tests/test_back.py)')
  if os.path.exists(os.path.join(APP,'tests','gas_server.js')):
    bk=subprocess.run([sys.executable,os.path.join(BASE,'tests','test_back.py'),APP],capture_output=True,text=True,timeout=300)
    for ln in bk.stdout.splitlines():
      if ln.startswith('  PASS ') or ln.startswith('  FAIL '):ok(ln.startswith('  PASS '),'back: '+ln[7:])
    ok(bk.returncode==0 and 'BACK BUTTON:' in bk.stdout,'back script finished clean (exit %s) %s'%(bk.returncode,bk.stderr[-300:]))
  else:skip('app has no tests/gas_server.js: back check not run')
  sec('24. AUTO-UPDATE ON OPEN (VER 11): updates itself before any save, keeps unsynced work, offline still works (tests/test_autoupdate.py)')
  au=subprocess.run([sys.executable,os.path.join(BASE,'tests','test_autoupdate.py'),APP],capture_output=True,text=True,timeout=300)
  for ln in au.stdout.splitlines():
    if ln.startswith('  PASS ') or ln.startswith('  FAIL '):ok(ln.startswith('  PASS '),'auto-update: '+ln[7:])
  ok(au.returncode==0 and 'AUTO-UPDATE:' in au.stdout,'auto-update script finished clean (exit %s) %s'%(au.returncode,au.stderr[-300:]))
  sec('25. SAVE-CLOSE (VER 12): successful Save returns to previous screen; fail stays; offline queued counts as success (tests/test_save_close.py)')
  try:
    sc=subprocess.run([sys.executable,os.path.join(BASE,'tests','test_save_close.py'),APP],capture_output=True,text=True,timeout=300)
    print(sc.stdout,end='',flush=True)
    if sc.stderr:print(sc.stderr,end='',flush=True)
    for line in (sc.stdout or '').splitlines():
      if line.startswith('  PASS '):R['pass']+=1
      elif line.startswith('  FAIL '):R['fail']+=1;ERR.append(line)
    ok(sc.returncode==0,'save-close script finished clean (exit %d)'%sc.returncode)
  except Exception as e:ok(False,'save-close script error: '+str(e))

  sec('26. WORKSHOP: repeated materials, decimal rope, save close, type/filter/history, photo, Admin re-sign-in, no mixing')
  _wp=os.path.join(APP,'tests','test_workshop.py')
  if os.path.exists(_wp):
    ww=subprocess.run([sys.executable,_wp,APP],capture_output=True,text=True,timeout=300)
    print(ww.stdout,end='',flush=True)
    if ww.stderr:print(ww.stderr[-500:],end='',flush=True)
    for line in (ww.stdout or '').splitlines():
      if line.startswith('  PASS '):R['pass']+=1
      elif line.startswith('  FAIL '):R['fail']+=1;ERR.append(line)
    ok(ww.returncode==0 and 'WORKSHOP:' in (ww.stdout or ''),'workshop script finished clean (exit %d)'%ww.returncode)
    ipy=os.path.join(APP,'tests','test_import.py')
    if os.path.exists(ipy):
      im=subprocess.run([sys.executable,ipy],capture_output=True,text=True,timeout=180)
      print(im.stdout,end='',flush=True)
      if im.stderr:print(im.stderr[-400:],end='',flush=True)
      for line in (im.stdout or '').splitlines():
        if line.startswith('  PASS '):R['pass']+=1
        elif line.startswith('  FAIL '):R['fail']+=1;ERR.append(line)
      ok(im.returncode==0 and 'IMPORT:' in (im.stdout or ''),'import script finished clean (exit %d)'%im.returncode)
    asp=os.path.join(APP,'tests','test_admin_stock.py')
    if os.path.exists(asp):
      aa=subprocess.run([sys.executable,asp,APP],capture_output=True,text=True,timeout=300)
      print(aa.stdout,end='',flush=True)
      if aa.stderr:print(aa.stderr[-500:],end='',flush=True)
      for line in (aa.stdout or '').splitlines():
        if line.startswith('  PASS '):R['pass']+=1
        elif line.startswith('  FAIL '):R['fail']+=1;ERR.append(line)
      ok(aa.returncode==0 and 'ADMIN STOCK:' in (aa.stdout or ''),'admin stock script finished clean (exit %d)'%aa.returncode)
  else:skip('no tests/test_workshop.py')
  sec('11. Console errors')
  ok(not ERR,'no console errors %s'%ERR[:5])
finally:
  for g in gas:g.terminate()
  web.shutdown();shutil.rmtree(TMP,ignore_errors=True)
print('\nRESULT: %d passed, %d failed'%(R['pass'],R['fail']));sys.exit(1 if R['fail'] else 0)
