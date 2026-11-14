#!/usr/bin/env python3
"""SHOTS v1.6.0 (360px, en/fr/ar/af) into screenshots/v1.6.0/. Demo data only, nothing published. Based on: v1.6.0 worker "Job finished: send to Assets", location from Assets (A-Z), photo, version label, server send (fake Assets). Mock Sheet only.
  python3 tests/test_v16.py /path/to/workshop
"""
import os,sys,re,json,shutil,socket,subprocess,tempfile,threading,urllib.request,urllib.parse
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from functools import partial
from playwright.sync_api import sync_playwright
APP=os.path.abspath(sys.argv[1] if len(sys.argv)>1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
P=F=0
def ok(c,m):
    global P,F
    if c:P+=1
    else:F+=1
    print(('  PASS ' if c else '  FAIL ')+m,flush=True)
def free():
    s=socket.socket();s.bind(('127.0.0.1',0));p=s.getsockname()[1];s.close();return p
HERE=os.path.dirname(os.path.abspath(__file__));BASE=os.path.dirname(HERE)
sys.path.insert(0,os.path.join(BASE,'tools'));import apply_config
TMP=tempfile.mkdtemp(prefix='wj-v16shots-');GP,OP,WP=free(),free(),free()
def prep(sub,app_id,port,cp=None):
    d=os.path.join(TMP,sub)
    shutil.copytree(APP,d,ignore=shutil.ignore_patterns('tests','shots*','.git','*.zip','archive','screenshots'))
    ip=os.path.join(d,'index.html');s=open(ip,encoding='utf-8').read()
    C=json.loads(re.search(r'/\*CONFIG\*/(.*?)/\*END\*/',s,re.S).group(1))
    C.update(APP_ID=app_id,SYNC_URL='http://127.0.0.1:%d/exec'%port,SYNC_CODE='',SHARE_URL='')
    if cp:C['CACHE_PREFIX']=cp
    s=re.sub(r'/\*CONFIG\*/.*?/\*END\*/','/*CONFIG*/'+json.dumps(C,ensure_ascii=False,indent=1)+'/*END*/',s,flags=re.S)
    open(ip,'w',encoding='utf-8').write(s);apply_config.main(d);return C
CA=prep('shop','tmcworkshop',GP,'tmcworkshop')
CB=prep('other','tmcother',OP,'tmcother')
gas=[]
for port in (GP,OP):
    gas.append(subprocess.Popen(['node',os.path.join(APP,'tests','gas_server.js'),str(port),'-'],stdout=subprocess.PIPE,env=dict(os.environ,GAS_FILE=os.path.join(APP,'sync','Code.gs'))))
    gas[-1].stdout.readline()
class Q(SimpleHTTPRequestHandler):
    def log_message(self,*a):pass
srv=ThreadingHTTPServer(('127.0.0.1',WP),partial(Q,directory=TMP));threading.Thread(target=srv.serve_forever,daemon=True).start()
SHOP='http://127.0.0.1:%d/shop/'%WP
def gasget(path):
    return json.loads(urllib.request.urlopen('http://127.0.0.1:%d%s'%(GP,path),timeout=10).read() or b'{}')
def name(pg,n):
    pg.fill('#fName',n);pg.click('#fName2')
def setpin(pg,p):
    pg.fill('#fPin',p);pg.fill('#fPin2',p);pg.click('#fSet');pg.wait_for_selector('header',timeout=8000)
def pin(pg,p):
    pg.fill('#fPin',p);pg.click('#fGo');pg.wait_for_timeout(600)
def synced(pg,ms=900):
    pg.evaluate("TMC.syncNow()");pg.wait_for_timeout(ms)
def open_job(pg,jid):
    if pg.locator('nav [data-tab=work].on, nav [data-tab=work][aria-current]').count()==0:pg.click('nav [data-tab=work]');pg.wait_for_timeout(150)
    pg.evaluate("id=>{const w=TMC.ws();w.screen='job';w.jobId=id;TMC.render()}",jid);pg.wait_for_timeout(250)
def screen(pg,sc):
    pg.click('nav [data-tab=work]');pg.wait_for_timeout(150)
    pg.evaluate("s=>{const w=TMC.ws();w.screen=s;w.jobId=null;TMC.render()}",sc);pg.wait_for_timeout(250)
def amt(pg,row,digits):
    pg.click('.wjIuCell[data-r="%d"]'%row)
    for d in digits:pg.click('[data-iupad="%s"]'%d)
def pickloc(pg,camp):
    pg.click('#wjLocBtn');pg.wait_for_timeout(150);pg.locator('.wjLocPick',has_text=camp).first.click();pg.wait_for_timeout(150)
def bal(pg,mat,d):return pg.evaluate("([m,d])=>TMC.wBal(m,d).len",[mat,d])
def ks(pg):return pg.evaluate("()=>JSON.stringify(TMC.all('k').slice().sort((a,b)=>a.id<b.id?-1:1))")
def fa(pg,jid):return pg.evaluate("j=>TMC.all('fa').find(f=>f.jobId===j)||null",jid)

from PIL import Image,ImageDraw
im=Image.new('RGB',(480,360),(226,232,240));d=ImageDraw.Draw(im)
d.rectangle([60,150,420,230],fill=(120,72,40));d.rectangle([60,110,90,290],fill=(70,70,70));d.rectangle([390,110,420,290],fill=(70,70,70));d.rectangle([60,240,420,255],fill=(70,70,70))
im.save('/tmp/v16bed.jpg')
OUT=os.path.join(APP,'screenshots','v1.6.0');os.makedirs(OUT,exist_ok=True)
JOBS=[{'id':'j179430000001%d'%i,'name':n} for i,n in enumerate(['Ben Bed','Sam Bed','Tom Bed','Alex Bed'])]+[{'id':'j1794300000005','name':'Johan Side Table'}]
WJ={'en':'j1794300000010','fr':'j1794300000011','ar':'j1794300000012','af':'j1794300000013'}
for i,j in enumerate(JOBS):j.update(type='build',by='JA Kirsten',at='2026-11-11T%02d:00:00.000Z'%(8+i),example=0)
LOCS=[{'id':'c-hq','name':'HQ - Headquarters','camp':'HQ - Headquarters','places':[{'id':'p-hq-off','name':'Office'}]},{'id':'c-gz','name':'GZ - Ground Zero','camp':'GZ - Ground Zero','places':[]},
      {'id':'c-alfa','name':'10 Alfa','camp':'10 Alfa','places':[{'id':'p-store','name':'Store A'},{'id':'p-tent12','name':'Tent 12'}]},{'id':'c-prod','name':'Production','camp':'Production','places':[]}]
CHROME='/usr/bin/google-chrome' if os.path.exists('/usr/bin/google-chrome') else None
gasget('/_prop?ASSETS_LOCATIONS_READ=rdc');gasget('/_assets?'+urllib.parse.urlencode({'locs':json.dumps(LOCS)}))
SH=[];ONLY=[x for x in os.environ.get('ONLY','').split(',') if x]
def shot(pg,n,l,el=None,full=False):
    if ONLY and n.split('_')[0] not in ONLY:return  # ONLY=4,5 re-shoots just those screens
    if el and pg.locator(el).count():pg.locator(el).first.scroll_into_view_if_needed();pg.wait_for_timeout(150)
    p=os.path.join(OUT,'%s_%s.png'%(n,l))
    if full:
        h=pg.evaluate('document.documentElement.scrollHeight');pg.set_viewport_size({'width':360,'height':min(h,2400)});pg.wait_for_timeout(250)
    pg.screenshot(path=p)
    if full:pg.set_viewport_size({'width':360,'height':780});pg.wait_for_timeout(150)
    SH.append(p)
def lang(pg,l):pg.select_option('#hLang',l);pg.wait_for_timeout(250)
try:
  with sync_playwright() as pw:
    b=pw.chromium.launch(executable_path=CHROME,args=['--no-sandbox'])
    def ctx():
        c=b.new_context(viewport={'width':360,'height':780},device_scale_factor=2,is_mobile=True,has_touch=True);c.on('dialog',lambda d:d.accept());return c
    pg=ctx().new_page();pg.goto(SHOP);pg.wait_for_selector('#langSel')
    name(pg,'Johan Kirsten');pg.wait_for_selector('#fPin2');setpin(pg,'2468')
    pg.evaluate("""jobs=>{const at=new Date().toISOString();
      TMC.put('k','kin-sq',{id:'kin-sq',ref:'',dir:'in',mat:'steel',desc:'Square tubing 40×40',qty:0,len:18,unit:'m',qThou:0,lThou:18000,at:at,by:'JA Kirsten',jobId:'',sourceApp:'admin',note:''});
      TMC.put('k','kin-rope',{id:'kin-rope',ref:'',dir:'in',mat:'rope',desc:'Rope 10 mm',qty:0,len:20,unit:'m',qThou:0,lThou:20000,at:at,by:'JA Kirsten',jobId:'',sourceApp:'admin',note:''});
      jobs.forEach(j=>TMC.put('j',j.id,j))}""",JOBS)
    synced(pg)
    g=ctx().new_page();g.goto(SHOP);g.wait_for_selector('#fName');name(g,'Pieter');g.wait_for_timeout(500)
    synced(pg);pg.click('nav [data-tab=users]');pg.wait_for_timeout(400)
    row=pg.locator('.ulr',has_text='Pieter')
    if row.locator('.uopen').count()==0:row.locator('.uli').click();pg.wait_for_timeout(200)
    pg.locator('.ulr',has_text='Pieter').locator('[data-ua=approve]').click();pg.wait_for_timeout(900)
    if g.locator('#fCheck').count():g.click('#fCheck');g.wait_for_selector('#fPin2',timeout=8000)
    if g.locator('#fPin2').count():setpin(g,'1357')
    elif g.locator('#fPin').count():pin(g,'1357')
    g.wait_for_selector('header',timeout=8000);synced(g,1200)
    for l in ('en','fr','ar','af'):
        lang(g,l);lang(pg,l)
        g.click('nav [data-tab=home]');g.wait_for_timeout(250);shot(g,'5_home_version',l)
        open_job(g,WJ[l]);shot(g,'1_worker_job_button',l,'#wjFinishW')
        g.click('#wjFinishW');g.wait_for_timeout(700)
        g.click('#wjLocBtn');g.wait_for_timeout(200);shot(g,'2_worker_form_location_open',l,'#wjLocBox')
        g.locator('.wjLocPick',has_text='10 Alfa').click();g.wait_for_timeout(150)
        g.locator('.wjPlPick',has_text='Store A').click();g.wait_for_timeout(150)
        g.fill('.wjIuType[data-r="0"]','Square tubing 40×40');amt(g,0,'3');g.click('[data-iupad="ok"]');g.wait_for_timeout(150)
        if g.locator('input[data-ph="wjIuPh"]').count():g.set_input_files('input[data-ph="wjIuPh"]:not([capture])','/tmp/v16bed.jpg');g.wait_for_timeout(800)
        g.evaluate("window.scrollTo(0,document.getElementById('wjLocBox').getBoundingClientRect().top+scrollY-70)");g.wait_for_timeout(150)
        g.evaluate('scrollTo(0,0)');shot(g,'3_worker_form_filled',l,full=True)
        g.click('#wjSendIu');g.wait_for_timeout(600);synced(g,900)
        if g.locator('#wjErr').count():print('ERR',l,g.inner_text('#wjErr'))
        screen(g,'assets');shot(g,'4_send_to_assets_list',l,'.wjWhere')
        open_job(pg,'j1794300000005');pg.click('#wjInUse');pg.wait_for_timeout(700)
        pg.click('#wjLocBtn');pg.wait_for_timeout(150);pg.locator('.wjLocPick',has_text='HQ - Headquarters').click();pg.wait_for_timeout(150)
        pg.locator('.wjPlPick',has_text='Office').click();pg.wait_for_timeout(150);pg.fill('.wjIuType[data-r="0"]','Rope 10 mm');amt(pg,0,'4');pg.click('[data-iupad="ok"]');pg.wait_for_timeout(150)
        pg.evaluate("window.scrollTo(0,document.getElementById('wjLocBox').getBoundingClientRect().top+scrollY-200)");pg.wait_for_timeout(150)
        pg.evaluate('scrollTo(0,0)');shot(pg,'6_admin_already_built_location',l,full=True)
        pg.click('#view .navBack');pg.wait_for_timeout(200)
        if pg.locator('#navAsk').count():pg.click('#navYes');pg.wait_for_timeout(200)
    b.close()
finally:
    for gproc in gas:gproc.terminate()
    srv.shutdown();shutil.rmtree(TMP,ignore_errors=True)
print('SHOTS',len(SH));[print(p) for p in SH]
