#!/usr/bin/env python3
"""v1.6.1: worker "Job finished: send to Assets", location from Assets (A-Z), photo, version label, server send (fake Assets). Mock Sheet only.
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
TMP=tempfile.mkdtemp(prefix='wj-v16-');GP,OP,WP=free(),free(),free()
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
def pick(pg,name):
    pg.locator('.wjIuPick',has_text=name).first.click();pg.wait_for_timeout(150)
def pickloc(pg,camp):
    pg.click('#wjLocBtn');pg.wait_for_timeout(150);pg.locator('.wjLocPick',has_text=camp).first.click();pg.wait_for_timeout(150)
def bal(pg,mat,d):return pg.evaluate("([m,d])=>TMC.wBal(m,d).len",[mat,d])
def ks(pg):return pg.evaluate("()=>JSON.stringify(TMC.all('k').slice().sort((a,b)=>a.id<b.id?-1:1))")
def fa(pg,jid):return pg.evaluate("j=>TMC.all('fa').find(f=>f.jobId===j)||null",jid)
JOBS=[{'id':'j1794300000002','name':'Ben Bed'},{'id':'j1794300000003','name':'Alex Bed'},{'id':'j1794300000004','name':'Elton Bed'},{'id':'j1794300000006','name':'Cliff Bed'},{'id':'j1794300000007','name':'Sam Table'}]
for i,j in enumerate(JOBS):j.update(type='build',by='JA Kirsten',at='2026-11-11T%02d:00:00.000Z'%(8+i),example=0)
# Assets sends sorted lists; these are deliberately NOT sorted to prove the phone sorts A-Z, case-insensitive (Johan 06:24)
LOCS=[{'id':'c-prod','name':'Production','camp':'Production','places':[]},{'id':'c-hq','name':'HQ - Headquarters','camp':'HQ - Headquarters','places':[]},{'id':'c-alfa','name':'10 Alfa','camp':'10 Alfa','places':[{'id':'p-zeta','name':'zeta'},{'id':'p-store','name':'Store A'},{'id':'p-alpha','name':'Alpha'},{'id':'p-beta','name':'beta'}]},{'id':'c-gz','name':'gz - Ground Zero','camp':'gz - Ground Zero','places':[]}]  # Johan 06:31 demo camps (one lower-case to prove case-insensitive A-Z)
NOLOC={'en':'Location list not loaded yet, try again with network','fr':'','af':'','ar':''}
from PIL import Image
PHOTO=os.path.join(TMP,'v16photo.jpg');Image.new('RGB',(64,48),(200,120,40)).save(PHOTO)
CHROME='/usr/bin/google-chrome' if os.path.exists('/usr/bin/google-chrome') else None
gasget('/_prop?ASSETS_LOCATIONS_READ=rdc')
gasget('/_assets?'+urllib.parse.urlencode({'locs':json.dumps(LOCS)}))
try:
  with sync_playwright() as pw:
    b=pw.chromium.launch(executable_path=CHROME,args=['--no-sandbox'])
    def ctx():
        c=b.new_context(viewport={'width':360,'height':780},is_mobile=True,has_touch=True);c.on('dialog',lambda d:d.accept());return c
    ca=ctx();pg=ca.new_page();errs=[];pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.goto(SHOP);pg.wait_for_selector('#langSel')
    name(pg,'Johan Kirsten');pg.wait_for_selector('#fPin2');setpin(pg,'2468')
    # --- version label + cache ---
    sw=open(os.path.join(TMP,'shop','sw.js'),encoding='utf-8').read()
    ok('V=APP+"-v1.6.1"' in sw and pg.evaluate("TMC.verLabel()")=='v1.6.1','sw.js cache is tmcworkshop-v1.6.1 and the label is "v1.6.1"')
    def vchk(pg):
        return pg.evaluate("""()=>{const v=document.getElementById('hVer'),n=document.querySelector('header .tN');if(!v)return null;const cs=getComputedStyle(v),r=v.getBoundingClientRect(),rn=n.getBoundingClientRect();
          return {txt:v.textContent,fs:cs.fontSize,col:cs.color,ws:cs.whiteSpace,lines:v.getClientRects().length,h:r.height,below:r.top>=rn.bottom-1,right:Math.abs(r.right-rn.right)<2,left:Math.abs(r.left-rn.left)<2,vis:r.width>0&&r.right<=innerWidth&&r.left>=0&&(()=>{const t=document.querySelector('header .t').getBoundingClientRect();return r.left>=t.left-1&&r.right<=t.right+1})()}}""")
    bad=[]
    for tab in pg.evaluate("[...document.querySelectorAll('nav [data-tab]')].map(e=>e.dataset.tab)"):
        pg.click('nav [data-tab=%s]'%tab);pg.wait_for_timeout(200);v=vchk(pg)
        if not(v and v['txt']=='v1.6.1' and v['fs']=='10px' and v['col']=='rgb(51, 51, 51)' and v['ws']=='nowrap' and v['lines']==1 and v['h']<16 and v['below'] and v['vis']):bad.append((tab,v))
    for sc in ('list','assets'):
        pg.click('nav [data-tab=work]');screen(pg,sc);v=vchk(pg)
        if not(v and v['txt']=='v1.6.1' and v['fs']=='10px' and v['lines']==1):bad.append((sc,v))
    ok(not bad,'version label "v1.6.1" under the app name on every screen: 10px, #333333, one line at 360px %s'%bad)
    pg.click('nav [data-tab=home]');pg.wait_for_timeout(150);ok(vchk(pg)['left'],'English: label starts on the left under the name')
    pg.select_option('#hLang','ar');pg.wait_for_timeout(300);v=vchk(pg)
    ok(v and v['right'] and v['lines']==1 and v['txt']=='v1.6.1' and pg.evaluate("document.documentElement.dir")=='rtl','Arabic: label mirrored to the right, Latin digits, one line %s'%v)
    pg.select_option('#hLang','en');pg.wait_for_timeout(300)
    # --- data: stock + jobs ---
    pg.evaluate("""jobs=>{const at=new Date().toISOString();
      TMC.put('k','kin-sq',{id:'kin-sq',ref:'',dir:'in',mat:'steel',desc:'Square tubing 40×40',qty:0,len:18,unit:'m',qThou:0,lThou:18000,at:at,by:'JA Kirsten',jobId:'',sourceApp:'admin',note:''});
      TMC.put('k','kin-rope',{id:'kin-rope',ref:'',dir:'in',mat:'rope',desc:'Rope 10 mm',qty:0,len:20,unit:'m',qThou:0,lThou:20000,at:at,by:'JA Kirsten',jobId:'',sourceApp:'admin',note:''});
      jobs.forEach(j=>TMC.put('j',j.id,j));
      const mk=(id,jid,mat,desc,q,l,at)=>{TMC.put('m',id,{id:id,jobId:jid,mat:mat,desc:desc,qty:q,len:l,unit:'m',by:'JA Kirsten',at:at,example:0});
        TMC.put('k','kout'+id,{id:'kout'+id,ref:'',dir:'out',mat:mat,desc:desc,qty:q,len:l,unit:'m',qThou:Math.round(q*1000),lThou:Math.round(l*1000),at:at,by:'JA Kirsten',jobId:jid,example:0})};
      mk('m1794300000101','j1794300000006','steel','Square tubing 40×40',2,6,'2026-11-11T14:10:00.000Z');
      mk('m1794300000102','j1794300000006','rope','Rope 10 mm',0,4,'2026-11-11T14:20:00.000Z');
      TMC.put('p','pjob4',{id:'pjob4',jobId:'j1794300000004',ph:'phjob4',at:at,by:'JA Kirsten'})}""",JOBS)
    synced(pg)
    # --- worker signs in ---
    cb=ctx();g=cb.new_page();g.on('pageerror',lambda e:errs.append(str(e)));g.goto(SHOP);g.wait_for_selector('#fName')
    name(g,'Pieter');g.wait_for_timeout(500)
    synced(pg);pg.click('nav [data-tab=users]');pg.wait_for_timeout(400)
    row=pg.locator('.ulr',has_text='Pieter')
    if row.locator('.uopen').count()==0:row.locator('.uli').click();pg.wait_for_timeout(200)
    pg.locator('.ulr',has_text='Pieter').locator('[data-ua=approve]').click();pg.wait_for_timeout(900)
    if g.locator('#fCheck').count():g.click('#fCheck');g.wait_for_selector('#fPin2',timeout=8000)
    if g.locator('#fPin2').count():setpin(g,'1357')
    elif g.locator('#fPin').count():pin(g,'1357')
    g.wait_for_selector('header',timeout=8000);synced(g,1200)
    ok(g.evaluate("TMC.me()&&!TMC.me().admin") and g.evaluate("TMC.all('j').length")>=5,'worker Pieter signed in and synced the jobs')
    # --- a. worker sees ONE button ---
    g.click('nav [data-tab=work]');g.wait_for_timeout(200);open_job(g,'j1794300000002')
    ok(g.locator('#wjFinishW').count()==1 and g.locator('#wjInUse').count()==0 and g.locator('#wjMarkReady').count()==0 and 'Job finished: send to Assets' in g.inner_text('#wjFinishW'),'worker on a Build job sees ONE button "Job finished: send to Assets" %s'%(g.inner_text('#wjReadyJob') if g.locator('#wjReadyJob').count() else ''))
    open_job(pg,'j1794300000002')
    ok(pg.locator('#wjInUse').count()==1 and pg.locator('#wjFinishW').count()==0,'Admin keeps its own buttons (Already built), no worker button')
    open_job(g,'j1794300000002');g.click('#wjFinishW');g.wait_for_timeout(300)
    ok(g.locator('#wjInUseBox').count()==1 and g.locator('#wjIuTake').count()==0 and g.locator('#wjInUseBox [role=switch]').count()==0,'worker finish form opens, no stock switch')
    # --- b. location list from Assets through OUR server action, sorted A-Z ---
    g.wait_for_timeout(600)
    locs=g.evaluate("TMC.wLocs()")
    ok([l['name'] for l in locs]==['10 Alfa','gz - Ground Zero','HQ - Headquarters','Production'],'camps A-Z, case-insensitive %s'%[l['name'] for l in locs])
    ok([p['name'] for p in locs[0]['places']]==['Alpha','beta','Store A','zeta'],'places A-Z, case-insensitive %s'%[p['name'] for p in locs[0]['places']])
    raw=g.evaluate("localStorage.getItem('tmcworkshop_assetsLoc')") or ''
    ok('c-alfa' in raw and 'rdc' not in raw and 'wsc' not in raw and 'script.google' not in raw,'list stored on the phone in tmcworkshop_assetsLoc, no Assets URL or code')
    src=open(os.path.join(APP,'index.html'),encoding='utf-8').read()
    ok('AKfycbx4YSw' not in src and 'ASSETS_WORKSHOP_CODE' not in src and 'importFinishedItem' not in src,'the phone app never holds the Assets URL, codes or actions')
    ok(g.locator('#wjLocList').count()==0,'camp list closed until tapped')
    g.click('#wjLocBtn');g.wait_for_timeout(150)
    ok(g.locator('#wjLocList .wjLocPick').count()==4 and g.locator('.wjLocPick').first.inner_text()=='10 Alfa','tapping opens the big camp list (4 camps, A-Z)')
    g.locator('.wjLocPick',has_text='10 Alfa').click();g.wait_for_timeout(150)
    ok([e.inner_text() for e in g.locator('#wjPlList .wjPlPick').all()]==['Alpha','beta','Store A','zeta'] and g.get_attribute('#wjLocPlace','maxlength')=='60','chosen camp shows its places A-Z and a typed Place (max 60)')
    # c. not in stock / too much refused
    K0=ks(g)
    g.evaluate("()=>{const w=TMC.ws();w.iu.rows=[{type:'Flat bar 30 mm',amt:'2',unit:'m'}];TMC.render()}");g.wait_for_timeout(150)
    g.click('#wjSendIu');g.wait_for_timeout(300)
    ok(g.locator('#wjInUseBox').count()==1 and 'Flat bar 30 mm' in g.inner_text('#wjErr') and ks(g)==K0 and not fa(g,'j1794300000002'),'worker: material not in stock is refused, nothing saved')
    ok(g.locator('.wjIuPick',has_text='Flat bar 30 mm').count()==0,'an item not in Workshop stock is not on the pick list')
    g.evaluate("()=>{const w=TMC.ws();w.iu.rows=[];TMC.render()}");g.wait_for_timeout(150)
    pick(g,'Square tubing 40×40');amt(g,0,'99');g.click('#wjSendIu');g.wait_for_timeout(300)
    ok(g.locator('#wjInUseBox').count()==1 and ks(g)==K0 and not fa(g,'j1794300000002'),'worker: more than on hand is refused')
    g.click('.wjIuCell[data-r="0"]');g.click('[data-iupad="bk"]');g.click('[data-iupad="bk"]');amt(g,0,'3')
    pick(g,'Rope 10 mm');amt(g,1,'500');g.click('[data-iuu="1"][data-u="mm"]');g.wait_for_timeout(150)
    g.fill('#wjLocPlace','store a')
    g.click('#wjSendIu');g.wait_for_timeout(500)
    f1=fa(g,'j1794300000002')
    ok(f1 and f1['by']=='Pieter' and f1['status']=='waiting' and f1['builtBefore']==0 and f1['tookStock']==1,'worker save: by = Pieter, Waiting for Assets, not built before %s'%f1)
    ok(abs(bal(g,'steel','Square tubing 40×40')-9)<1e-9 and abs(bal(g,'rope','Rope 10 mm')-15.5)<1e-9,'worker materials ALWAYS come off stock (18-6 v4-3 = 9 m / 20-4 v4-0.5 = 15.5 m) %s / %s'%(bal(g,'steel','Square tubing 40×40'),bal(g,'rope','Rope 10 mm')))
    ok(f1 and f1['campId']=='c-alfa' and f1['campName']=='10 Alfa' and f1['placeId']=='p-store' and f1['placeName']=='Store A','typed "store a" reuses the existing place Store A (same id) %s'%f1)
    ok(f1 and not f1.get('photo'),'no photo: item saved without one')
    # pre-filled rows never deducted twice (Cliff Bed)
    open_job(g,'j1794300000006');g.click('#wjFinishW');g.wait_for_timeout(300)
    rows=g.evaluate("()=>TMC.ws().iu.rows.map(r=>[r.type,r.amt,!!r.pre])")
    ok(rows==[['Square tubing 40×40','6',True],['Rope 10 mm','4',True]],'worker form pre-filled from the v4 records %s'%rows)
    s0=bal(g,'steel','Square tubing 40×40');r0=bal(g,'rope','Rope 10 mm')
    pick(g,'Square tubing 40×40');amt(g,2,'1')
    pickloc(g,'gz - Ground Zero');g.fill('#wjLocPlace','Mid shed');g.set_input_files('input[data-ph="wjIuPh"]:not([capture])',PHOTO);g.wait_for_timeout(700)
    ok(g.locator('#wjIuPic').count()==1,'Add photo shows the new photo on the form')
    g.click('#wjSendIu');g.wait_for_timeout(600)
    f2=fa(g,'j1794300000006')
    ok(abs(bal(g,'steel','Square tubing 40×40')-(s0-1))<1e-9 and abs(bal(g,'rope','Rope 10 mm')-r0)<1e-9,'only the added 1 m comes off; pre-filled 6 m / 4 m not taken again')
    ok(f2 and f2['placeId']=='' and f2['placeName']=='Mid shed' and f2['campName']=='gz - Ground Zero','new place: empty placeId, typed placeName %s'%f2)
    ph=g.evaluate("id=>TMC.all('p').find(p=>p.ph===id)||null",f2.get('photo') if f2 else '')
    ok(f2 and f2.get('photo') and ph and ph['jobId']=='j1794300000006','new photo stored like job photos (p record on the job) and referenced on the item')
    cl=[l for l in g.evaluate("TMC.wLocs()") if l['id']=='c-gz'][0]
    ok([p['name'] for p in cl['places']]==['Mid shed'],'the new place joins the local list %s'%cl['places'])
    # re-sorted after adding (10 Alfa: Alpha, beta, Mid, Store A, zeta)
    open_job(g,'j1794300000003');g.click('#wjFinishW');g.wait_for_timeout(300)
    pick(g,'Rope 10 mm');amt(g,0,'1');pickloc(g,'10 Alfa');g.fill('#wjLocPlace','Mid');g.click('#wjSendIu');g.wait_for_timeout(500)
    al=[l for l in g.evaluate("TMC.wLocs()") if l['id']=='c-alfa'][0]
    ok([p['name'] for p in al['places']]==['Alpha','beta','Mid','Store A','zeta'],'place list re-sorted A-Z after a new place %s'%[p['name'] for p in al['places']])
    open_job(g,'j1794300000007');g.click('#wjFinishW');g.wait_for_timeout(300);pickloc(g,'10 Alfa')
    ok([e.inner_text() for e in g.locator('#wjPlList .wjPlPick').all()]==['Alpha','beta','Mid','Store A','zeta'],'drop-down shows the new place in A-Z order')
    g.click('#view .navBack');g.wait_for_timeout(200)
    if g.locator('#navAsk').count():g.click('#navYes');g.wait_for_timeout(200)
    # job photo reused (Elton Bed has a job photo)
    open_job(g,'j1794300000004');g.click('#wjFinishW');g.wait_for_timeout(300)
    ok(g.locator('input[data-ph="wjIuPh"]').count()==0 and "photo is used" in g.inner_text('#wjInUseBox'),'job with a photo: the job photo is reused, no Add photo button')
    pick(g,'Rope 10 mm');amt(g,0,'1');pickloc(g,'Production');g.click('#wjSendIu');g.wait_for_timeout(500)
    f4=fa(g,'j1794300000004')
    ok(f4 and f4.get('photo')=='phjob4','item references the job photo %s'%(f4 or {}).get('photo'))
    open_job(g,'j1794300000002')
    ok(g.locator('#wjFinishW').count()==0 and g.locator('#wjReadyJob').count()==1,'finished job: worker cannot send it twice')
    # Send to Assets list shows the location
    screen(g,'assets');at=g.inner_text('#wjAssetsBox')
    ok(g.inner_text('#wjAssetsBox .hint').strip()=='Finished items go to Assets automatically.' and 'not connected' not in at.lower(),'Send to Assets hint is neutral (no "Not connected yet")')
    hw=g.evaluate("['en','fr','af','ar'].map(l=>TMC.T[l].wjAssetsH)")
    ok(hw==['Finished items go to Assets automatically.','Les articles finis vont automatiquement à Assets.','Klaar items gaan outomaties na Assets.','القطع المنتهية تذهب إلى Assets تلقائياً.'],'neutral hint in en/fr/af/ar %s'%hw)
    ok('📍' in at and '10 Alfa · Store A' in at and 'gz - Ground Zero · Mid shed' in at and 'Waiting for Assets' in at,'Send to Assets list shows the location: %s'%at.replace('\n',' / ')[:300])
    ok(g.locator('#wjAddBefore').count()==0,'worker still cannot add items built before')
    # d. no Admin check: Admin sees the items, can still Edit
    synced(g,1200);synced(pg,1200);screen(pg,'assets')
    ok(pg.locator('.wjFaRow').count()>=4 and all(f['status']=='waiting' for f in pg.evaluate("TMC.all('fa')")),'Admin sees the worker items as Waiting for Assets (no Admin check)')
    # b. location required + empty-list block, all 4 languages
    g.evaluate("TMC.L.del('assetsLoc')");cb.set_offline(True)
    msgs={}
    for l in ('en','fr','af','ar'):
        g.select_option('#hLang',l);g.wait_for_timeout(200)
        open_job(g,'j1794300000007');g.click('#wjFinishW');g.wait_for_timeout(300)
        shown=g.inner_text('#wjLocBox') if g.locator('#wjLocBox').count() else ''
        pick(g,'Rope 10 mm');amt(g,0,'1');g.click('#wjSendIu');g.wait_for_timeout(300)
        msgs[l]=(g.evaluate("l=>TMC.T[l].wjLocNone",l),shown,g.inner_text('#wjErr'))
        g.click('#view .navBack');g.wait_for_timeout(200)
        if g.locator('#navAsk').count():g.click('#navYes');g.wait_for_timeout(200)
    ok(all(m[0] and m[0] in m[1] and m[0] in m[2] for m in msgs.values()) and msgs['en'][0]=='Location list not loaded yet, try again with network' and len({m[0] for m in msgs.values()})==4,'empty list / offline: saving blocked with the message in en/fr/af/ar %s'%{k:v[0] for k,v in msgs.items()})
    ok(not fa(g,'j1794300000007'),'nothing saved while the list is missing')
    g.select_option('#hLang','en');g.wait_for_timeout(200);cb.set_offline(False)
    # Admin: Already built form + Add item built before need a location
    pg.evaluate("TMC.L.del('assetsLoc')");open_job(pg,'j1794300000007');pg.click('#wjInUse');pg.wait_for_timeout(900)
    ok(pg.locator('#wjLocBtn').count()==1 and pg.locator('#wjIuTake').count()==0,'Admin Already built form: location list loaded from our server, no stock switch')
    K1=ks(pg);pick(pg,'Rope 10 mm');amt(pg,0,'1');pg.click('#wjSendIu');pg.wait_for_timeout(300)
    ok(pg.locator('#wjInUseBox').count()==1 and pg.inner_text('#wjErr').strip()!='' and not fa(pg,'j1794300000007'),'Admin old job without a location: refused')
    pickloc(pg,'gz - Ground Zero');pg.click('#wjSendIu');pg.wait_for_timeout(500);f7=fa(pg,'j1794300000007')
    ok(f7 and f7['builtBefore']==1 and f7['tookStock']==0 and f7['campName']=='gz - Ground Zero' and ks(pg)==K1,'Admin old job: location saved, nothing off stock')
    screen(pg,'assets');pg.click('#wjAddBefore');pg.wait_for_timeout(250);pg.fill('#wjFaName','Kitchen table');pg.fill('#wjFaQty','2');pg.click('#wjSaveFa');pg.wait_for_timeout(300)
    ok(pg.locator('#wjBeforeBox').count()==1 and not pg.evaluate("TMC.all('fa').some(f=>f.name==='Kitchen table')"),'Add item built before without a location: refused')
    pickloc(pg,'Production');pg.click('#wjSaveFa');pg.wait_for_timeout(400)
    kt=pg.evaluate("TMC.all('fa').find(f=>f.name==='Kitchen table')||null")
    ok(kt and kt['campId']=='c-prod' and kt['status']=='waiting','Add item built before saves the location %s'%kt)
    # Admin Edit keeps working
    fid=f1['id'];screen(pg,'assets');pg.locator('.wjEditFa[data-fa="%s"]'%fid).click();pg.wait_for_timeout(300)
    ok(pg.locator('#wjLocBtn').count()==1 and '10 Alfa' in pg.inner_text('#wjLocBtn'),'Admin Edit opens with the saved location')
    if pg.locator('#wjSaveReady').count():pg.click('#wjSaveReady');pg.wait_for_timeout(400)
    fe=pg.evaluate("id=>TMC.all('fa').find(f=>f.id===id)",fid)
    ok(fe and fe['by']=='Pieter' and fe['status']=='waiting','Admin Edit saved: by stays the worker (Pieter) %s'%(fe or {}).get('by'))
    # --- server: send to Assets (fake Assets behind a mocked UrlFetchApp) ---
    synced(pg,1000)
    st=gasget('/_assets')
    ok(not st['items'],'codes empty: nothing sent, all items stay waiting')
    gasget('/_prop?ASSETS_WORKSHOP_CODE=wsc');gasget('/_assets?mode=down');gasget('/_assets?retry=1')
    ok(not gasget('/_assets')['items'],'Assets offline: items stay waiting')
    gasget('/_assets?mode=ok');gasget('/_assets?retry=1');st=gasget('/_assets')
    it=(st['items'].get(f1['id']) or {}).get('item') or {}
    ok(len(st['items'])>=6,'retry sends every waiting item once (%d)'%len(st['items']))
    ok(it.get('by')=='Pieter' and (st['items'].get(f2['id']) or {}).get('item',{}).get('by')=='Pieter' and it.get('campId')=='c-alfa' and it.get('placeId')=='p-store' and it.get('type')=='bed' and it.get('qty')=='1' and it.get('photo')=='','sent importFinishedItem payload: by = Pieter (also after the Admin Edit), location, type, qty %s'%it)
    i2=(st['items'].get(f2['id']) or {}).get('item') or {}
    ok(i2.get('placeId')=='' and i2.get('placeName')=='Mid shed' and not str(i2.get('photo','')).startswith('data:'),'new place sent with an empty placeId; never a data URL photo')
    synced(g,1200);screen(g,'assets')
    sts=g.evaluate("TMC.all('fa').map(f=>f.status)")
    ok(sts and all(s=='sent' for s in sts) and 'In Assets' in g.inner_text('#wjAssetsBox'),'the phone sees "In Assets" through normal sync %s'%sts)
    n0=len(st['calls']);gasget('/_assets?retry=1')
    ok(len(gasget('/_assets')['calls'])==n0,'sent items are never sent again')
    # sync-time send: a new worker item goes out on the next sync
    screen(pg,'assets');pg.click('#wjAddBefore');pg.wait_for_timeout(250);pg.fill('#wjFaName','Tent frame');pg.fill('#wjFaQty','1');pickloc(pg,'10 Alfa');pg.click('#wjSaveFa');pg.wait_for_timeout(300);synced(pg,1200)
    tf=pg.evaluate("TMC.all('fa').find(f=>f.name==='Tent frame')||null")
    ok(tf and tf['status']=='sent' and tf['id'] in gasget('/_assets')['items'] and gasget('/_assets')['items'][tf['id']]['item']['type']=='tent','a new item is sent on the next sync (no wait for the retry) %s'%(tf or {}).get('status'))
    ok(not errs,'no page errors %s'%errs[:3])
    b.close()
finally:
    for gproc in gas:gproc.terminate()
    srv.shutdown();shutil.rmtree(TMP,ignore_errors=True)
print('V1.6.1: %d passed, %d failed'%(P,F))
sys.exit(1 if F else 0)
