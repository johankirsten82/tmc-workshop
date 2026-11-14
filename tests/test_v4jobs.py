#!/usr/bin/env python3
"""v4 jobs -> Already built (in use) -> Send to Assets tests (Johan 14 Nov 02:27-02:29). Mock Sheet only. Sample, not published.
  python3 tests/test_cutlist.py /path/to/workshop
"""
import os,sys,re,json,shutil,socket,subprocess,tempfile,threading,urllib.request
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
TMP=tempfile.mkdtemp(prefix='wj-cutlist-');GP,OP,WP=free(),free(),free()
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
def name(pg,n):
    pg.fill('#fName',n);pg.click('#fName2')
def setpin(pg,p):
    pg.fill('#fPin',p);pg.fill('#fPin2',p);pg.click('#fSet');pg.wait_for_selector('header',timeout=8000)
def pin(pg,p):
    pg.fill('#fPin',p);pg.click('#fGo');pg.wait_for_timeout(600)
def synced(pg):
    pg.evaluate("TMC.syncNow()");pg.wait_for_timeout(800)
def work(pg):
    pg.click('nav [data-tab=work]');pg.wait_for_timeout(250)
def back(pg):
    if pg.locator('#navAsk').count():
        pg.click('#navYes');pg.wait_for_timeout(250);return
    if pg.locator('#view .navBack').count():
        pg.click('#view .navBack');pg.wait_for_timeout(250)
    if pg.locator('#navAsk').count():
        pg.click('#navYes');pg.wait_for_timeout(250)

V4JOBS=[{'id':'j1794300000001','name':'Shaun Bed'},{'id':'j1794300000002','name':'Ben Bed'},{'id':'j1794300000003','name':'Alex Bed'},
        {'id':'j1794300000004','name':'Elton Bed'},{'id':'j1794300000005','name':'Johan Side Table'},{'id':'j1794300000006','name':'Cliff Bed'}]
for i,j in enumerate(V4JOBS):j.update(type='build',by='JA Kirsten',at='2026-11-11T%02d:00:00.000Z'%(8+i),example=0)
SPLIT={'Shaun Bed':('Shaun','Bed'),'Ben Bed':('Ben','Bed'),'Alex Bed':('Alex','Bed'),'Elton Bed':('Elton','Bed'),'Johan Side Table':('Johan','Side Table'),'Cliff Bed':('Cliff','Bed')}
KEYS=["wjInUse","wjInUseH","wjIuMats","wjIuType","wjIuTypeH","wjIuAmt","wjIuAdd","wjDoneH","wjLoc","wjLocChoose","wjLocNone","wjNeedLoc","wjPlace","wjPlaceH","wjIuPhoto","wjJobPhoto","wjSizeEx","wjNeedIu","wjNotStock","wjIuMatsL","wjIuTook","wjPerson","wjPersonH","wjRdItem","wjSaveReady","wjEditFa","wjNoPerson","wjReadyH"]
CHROME='/usr/bin/google-chrome' if os.path.exists('/usr/bin/google-chrome') else None
def jobs(pg):return pg.evaluate("()=>JSON.stringify(TMC.all('j').slice().sort((a,b)=>a.id<b.id?-1:1))")
def ks(pg):return pg.evaluate("()=>JSON.stringify(TMC.all('k').slice().sort((a,b)=>a.id<b.id?-1:1))")
def bal(pg,mat,d):return pg.evaluate("([m,d])=>TMC.wBal(m,d).len",[mat,d])
def open_job(pg,jid):
    pg.evaluate("id=>{const w=TMC.ws();w.screen='job';w.jobId=id;TMC.render()}",jid);pg.wait_for_timeout(200)
LOCS=[{'id':'c-alfa','name':'10 Alfa','camp':'10 Alfa','places':[{'id':'p-store','name':'Store A'}]},{'id':'c-bravo','name':'Bravo','camp':'Bravo','places':[]}]
def pickloc(pg,camp='10 Alfa'):
    pg.click('#wjLocBtn');pg.wait_for_timeout(120);pg.locator('.wjLocPick',has_text=camp).click();pg.wait_for_timeout(120)
def amt(pg,row,digits):
    pg.click('.wjIuCell[data-r="%d"]'%row)
    for d in digits:pg.click('[data-iupad="%s"]'%d)
try:
  with sync_playwright() as pw:
    b=pw.chromium.launch(executable_path=CHROME,args=['--no-sandbox'])
    c=b.new_context(viewport={'width':360,'height':780},is_mobile=True,has_touch=True);c.on('dialog',lambda d:d.accept())
    pg=c.new_page();pg.goto(SHOP);pg.wait_for_selector('#langSel')
    have=pg.evaluate("ks=>ks.filter(k=>!['en','fr','ar','af'].every(l=>TMC.T[l]&&TMC.T[l][k]))",KEYS)
    ok(not have,'new in-use keys exist in en/fr/ar/af %s'%have)
    name(pg,'Johan Kirsten');pg.wait_for_selector('#fPin2');setpin(pg,'2468')
    pg.evaluate("""jobs=>{const at=new Date().toISOString();
      TMC.put('k','kin-sq',{id:'kin-sq',ref:'',dir:'in',mat:'steel',desc:'Square tubing 40×40',qty:0,len:18,unit:'m',qThou:0,lThou:18000,at:at,by:'JA Kirsten',jobId:'',sourceApp:'admin',note:''});
      TMC.put('k','kin-rope',{id:'kin-rope',ref:'',dir:'in',mat:'rope',desc:'Rope 10 mm',qty:0,len:20,unit:'m',qThou:0,lThou:20000,at:at,by:'JA Kirsten',jobId:'',sourceApp:'admin',note:''});
      jobs.forEach(j=>TMC.put('j',j.id,j))}""",V4JOBS)
    pg.evaluate("l=>TMC.L.set('assetsLoc',JSON.stringify({at:Date.now(),locations:l}))",LOCS)
    pg.wait_for_timeout(200)
    J0=jobs(pg);K0=ks(pg)
    ok(len(json.loads(J0))==6 and all(set(j.keys())>={'id','name','type','by','at'} and 'item' not in j for j in json.loads(J0)),'6 v4-shaped Build jobs loaded (no item/units fields)')
    work(pg);pg.evaluate("()=>{const w=TMC.ws();w.screen='list';w.jobId=null;TMC.render()}");pg.wait_for_timeout(200)
    lt=pg.inner_text('#wjList')
    ok(all(j['name'] in lt for j in V4JOBS),'v5 jobs list shows all 6 v4 jobs unchanged')
    sp=pg.evaluate("jobs=>jobs.map(j=>TMC.wSplitJob(j))",V4JOBS)
    ok(all((s['person'],s['item'])==SPLIT[j['name']] for s,j in zip(sp,V4JOBS)),'suggested person / item from the job name %s'%sp)
    # Shaun Bed: Already built, square tubing 12 m + rope 8 m, size 2 m x 1 m, Admin old job (v1.6.0: no stock switch, nothing comes off stock)
    open_job(pg,'j1794300000001')
    ok(pg.locator('#wjInUse').count()==1 and pg.locator('#wjMarkReady').count()==0,'v4 job (no cut list) shows the Already built button')
    pg.click('#wjInUse');pg.wait_for_timeout(200)
    ok(pg.locator('#wjInUseBox').count()==1 and pg.input_value('#wjIu_person')=='Shaun' and pg.input_value('#wjIu_item')=='Bed','in-use form prefilled: Bed / Shaun')
    ok(pg.locator('#wjIuTake').count()==0 and pg.locator('#wjInUseBox [role=switch]').count()==0,'Admin old-job form has no Take off stock switch')
    pg.fill('.wjIuType[data-r="0"]','Square tubing 40×40');amt(pg,0,'12')
    pg.click('#wjIuAdd');pg.wait_for_timeout(150)
    pg.fill('.wjIuType[data-r="1"]','Rope 10 mm');amt(pg,1,'8')
    pg.fill('#wjIu_size','2 m x 1 m');pickloc(pg)
    pg.click('#wjSendIu');pg.wait_for_timeout(400)
    ok(pg.locator('#wjJob').count()==1,'Send to Assets saves and returns to the job')
    ok(ks(pg)==K0 and bal(pg,'steel','Square tubing 40×40')==18 and bal(pg,'rope','Rope 10 mm')==20,'Admin old job: no stock record added or changed (18 m / 20 m)')
    fa=pg.evaluate("()=>TMC.all('fa').find(f=>f.jobId==='j1794300000001')")
    ok(fa and fa['builtBefore']==1 and fa['jobName']=='Shaun Bed' and fa['name']=='Bed' and fa['suggestedPerson']=='Shaun' and fa['size']=='2 m x 1 m' and fa['tookStock']==0 and fa['status']=='waiting' and fa['campId']=='c-alfa' and fa['campName']=='10 Alfa' and fa['placeId']=='' and fa['by']=='JA Kirsten','queued item: built before, location, job id/name, Bed, Shaun, size %s'%fa)
    ok(fa and [(m['type'],m['qty'],m['unit']) for m in fa['materials']]==[('Square tubing 40×40',12,'m'),('Rope 10 mm',8,'m')],'queued item carries materials %s'%(fa or {}).get('materials'))
    # Johan Side Table: Admin old job with materials and an edited person -> still nothing off stock
    open_job(pg,'j1794300000005');pg.click('#wjInUse');pg.wait_for_timeout(200)
    ok(pg.input_value('#wjIu_person')=='Johan' and pg.input_value('#wjIu_item')=='Side Table','Johan Side Table -> Johan / Side Table')
    pg.fill('.wjIuType[data-r="0"]','Square tubing 40×40');amt(pg,0,'3')
    pg.click('#wjIuAdd');pg.wait_for_timeout(150);pg.fill('.wjIuType[data-r="1"]','Rope 10 mm');amt(pg,1,'500');pg.click('[data-iuu="1"][data-u="mm"]');pg.wait_for_timeout(150)
    pg.fill('#wjIu_person','Johan K')
    pg.click('#wjSendIu');pg.wait_for_timeout(300)
    ok(pg.locator('#wjInUseBox').count()==1 and pg.inner_text('#wjErr').strip()!='' and not pg.evaluate("()=>TMC.all('fa').some(f=>f.jobId==='j1794300000005')"),'no location chosen: save refused, form kept %s'%pg.inner_text('#wjErr'))
    ok(pg.input_value('#wjIu_person')=='Johan K','typed values kept after the refusal')
    pickloc(pg,'Bravo');pg.click('#wjSendIu');pg.wait_for_timeout(400)
    ok(ks(pg)==K0 and bal(pg,'steel','Square tubing 40×40')==18 and bal(pg,'rope','Rope 10 mm')==20,'Admin old job with materials: nothing comes off stock')
    fa2=pg.evaluate("()=>TMC.all('fa').find(f=>f.jobId==='j1794300000005')")
    ok(fa2 and fa2['tookStock']==0 and fa2['suggestedPerson']=='Johan K' and fa2['builtBefore']==1 and fa2['campName']=='Bravo','old-job item: no stock taken, edited person, camp Bravo %s'%fa2)
    ok(not pg.evaluate("()=>TMC.all('k').some(k=>k.faId==='fa-j1794300000005')"),'no stock out records for an old job')
    pg.click('#view .navBack');pg.wait_for_timeout(200)
    if pg.locator('#navAsk').count():pg.click('#navYes');pg.wait_for_timeout(200)
    # job records never changed
    ok(jobs(pg)==J0,'all 6 v4 job records unchanged after finishing (nothing rewritten or lost)')
    # Assets list
    pg.evaluate("()=>{const w=TMC.ws();w.screen='assets';TMC.render()}");pg.wait_for_timeout(200)
    at=pg.inner_text('#wjAssetsBox')
    ok('Shaun' in at and 'Square tubing 40×40 12 m' in at and 'Rope 10 mm 8 m' in at and '2 m x 1 m' in at and 'Built before' in at and 'Shaun Bed' in at,'Send to Assets list shows person, materials, size, Built before: %s'%at.replace('\n',' / ')[:300])
    open_job(pg,'j1794300000001')
    ok(pg.locator('#wjInUse').count()==0 and 'Already on the Assets list' in pg.inner_text('#wjReadyJob'),'finished job cannot be queued twice')
    # v4 Add steel / Add rope records on a job pre-fill the rows (Johan 02:45); never deducted twice
    pg.evaluate("""()=>{const mk=(id,jid,mat,desc,q,l,at)=>{TMC.put('m',id,{id:id,jobId:jid,mat:mat,desc:desc,qty:q,len:l,unit:'m',by:'JA Kirsten',at:at,example:0});
        TMC.put('k','kout'+id,{id:'kout'+id,ref:'',dir:'out',mat:mat,desc:desc,qty:q,len:l,unit:'m',qThou:Math.round(q*1000),lThou:Math.round(l*1000),at:at,by:'JA Kirsten',jobId:jid,example:0})};
      mk('m1794300000101','j1794300000006','steel','Square tubing 40×40',2,6,'2026-11-11T14:10:00.000Z');
      mk('m1794300000102','j1794300000006','rope','Rope 10 mm',0,4,'2026-11-11T14:20:00.000Z');
      mk('m1794300000103','j1794300000004','rope','Rope 10 mm',0,2,'2026-11-11T12:10:00.000Z')}""")
    pg.wait_for_timeout(150)
    def ms(pg):return pg.evaluate("()=>JSON.stringify(TMC.all('m').slice().sort((a,b)=>a.id<b.id?-1:1))")
    J2,K2,M2=jobs(pg),ks(pg),ms(pg);s0=bal(pg,'steel','Square tubing 40×40');r0=bal(pg,'rope','Rope 10 mm')
    # Elton Bed: pre-filled rope 2 m, switch OFF -> no stock change
    open_job(pg,'j1794300000004');pg.click('#wjInUse');pg.wait_for_timeout(200)
    rows=pg.evaluate("()=>TMC.ws().iu.rows.map(r=>[r.type,r.amt,r.unit,!!r.pre])")
    ok(rows==[['Rope 10 mm','2','m',True]] and pg.locator('.wjIuPre').count()==1,'Elton Bed: row pre-filled from its v4 Add rope record %s'%rows)
    pickloc(pg);pg.click('#wjSendIu');pg.wait_for_timeout(400)
    ok(ks(pg)==K2,'Admin old job with pre-filled rows: no stock change')
    # Cliff Bed: pre-filled steel 6 m + rope 4 m, Admin adds 1 m on an old job -> nothing comes off (workers: tests/test_v16.py)
    open_job(pg,'j1794300000006');pg.click('#wjInUse');pg.wait_for_timeout(200)
    rows=pg.evaluate("()=>TMC.ws().iu.rows.map(r=>[r.type,r.amt,r.unit,!!r.pre])")
    ok(rows==[['Square tubing 40×40','6','m',True],['Rope 10 mm','4','m',True]],'Cliff Bed: steel and rope rows pre-filled from v4 records (type, amount, unit) %s'%rows)
    pg.click('#wjIuAdd');pg.wait_for_timeout(150);pg.fill('.wjIuType[data-r="2"]','Square tubing 40×40');amt(pg,2,'1')
    pickloc(pg);pg.click('#wjSendIu');pg.wait_for_timeout(400)
    ok(abs(bal(pg,'steel','Square tubing 40×40')-s0)<1e-9 and abs(bal(pg,'rope','Rope 10 mm')-r0)<1e-9 and ks(pg)==K2,'Admin old job: pre-filled and added rows never come off stock')
    fa3=pg.evaluate("()=>TMC.all('fa').find(f=>f.jobId==='j1794300000006')")
    ok(fa3 and [(m['type'],m['qty'],m['unit'],m.get('jobRecord','')) for m in fa3['materials']]==[('Square tubing 40×40',6,'m','m1794300000101'),('Rope 10 mm',4,'m','m1794300000102'),('Square tubing 40×40',1,'m','')] and fa3['suggestedPerson']=='Cliff','queued item carries pre-filled + added materials %s'%(fa3 or {}).get('materials'))
    oldk=[k for k in json.loads(ks(pg)) if k['id'] in {x['id'] for x in json.loads(K2)}]
    ok(jobs(pg)==J2 and ms(pg)==M2 and json.dumps(sorted(oldk,key=lambda k:k['id']))==json.dumps(sorted(json.loads(K2),key=lambda k:k['id'])),'job records, v4 steel/rope records and old stock records unchanged')
    # repair jobs never get the button
    pg.evaluate("()=>TMC.put('j','jrep',{id:'jrep',name:'Fix gate',type:'repair',by:'JA Kirsten',at:new Date().toISOString()})")
    open_job(pg,'jrep')
    ok(pg.locator('#wjInUse').count()==0,'Repair job has no Already built button')
    b.close()
finally:
    for gproc in gas:gproc.terminate()
    srv.shutdown();shutil.rmtree(TMP,ignore_errors=True)
print('V4 JOBS: %d passed, %d failed'%(P,F))
sys.exit(1 if F else 0)
