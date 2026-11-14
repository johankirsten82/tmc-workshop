#!/usr/bin/env python3
"""Workshop domain tests. Mock Sheet only. Nothing is published or sent to Google.
  python3 tests/test_workshop.py /path/to/workshop
Covers repeated materials, decimal rope lengths, save-close, job type/filter/history,
completed-photo attach, Admin re-sign-in after a wiped phone, and no mixing with another app.
"""
import os,sys,re,json,shutil,socket,subprocess,tempfile,threading,time,base64,urllib.request,urllib.parse
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
TMP=tempfile.mkdtemp(prefix='workshop-');GP,OP,WP=free(),free(),free()
def prep(sub,app_id,port,cp=None):
    d=os.path.join(TMP,sub)
    shutil.copytree(APP,d,ignore=shutil.ignore_patterns('tests','shots*','.git','*.zip','archive'))
    ip=os.path.join(d,'index.html');s=open(ip,encoding='utf-8').read()
    C=json.loads(re.search(r'/\*CONFIG\*/(.*?)/\*END\*/',s,re.S).group(1))
    C.update(APP_ID=app_id,SYNC_URL='http://127.0.0.1:%d/exec'%port,SYNC_CODE='',SHARE_URL='')
    if cp:C['CACHE_PREFIX']=cp
    s=re.sub(r'/\*CONFIG\*/.*?/\*END\*/','/*CONFIG*/'+json.dumps(C,ensure_ascii=False,indent=1)+'/*END*/',s,flags=re.S)
    open(ip,'w',encoding='utf-8').write(s);apply_config.main(d);return C
CA=prep('shop','tmcworkshop',GP,'tmc-workshop')
CB=prep('other','tmcother',OP,'tmc-other')
gas=[]
for port in (GP,OP):
    gas.append(subprocess.Popen(['node',os.path.join(APP,'tests','gas_server.js'),str(port),'-'],stdout=subprocess.PIPE,env=dict(os.environ,GAS_FILE=os.path.join(APP,'sync','Code.gs'))))
    gas[-1].stdout.readline()
class Q(SimpleHTTPRequestHandler):
    def log_message(self,*a):pass
srv=ThreadingHTTPServer(('127.0.0.1',WP),partial(Q,directory=TMP));threading.Thread(target=srv.serve_forever,daemon=True).start()
SHOP='http://127.0.0.1:%d/shop/'%WP
OTHER='http://127.0.0.1:%d/other/'%WP
PNG=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAgAAAAICAIAAABLbSncAAAAEklEQVR4nGNgYGD4z0AswK4SAFXuAf8EPy+xAAAAAElFTkSuQmCC')
def dump(port):return json.load(urllib.request.urlopen('http://127.0.0.1:%d/_dump'%port))
def users(port):
    out=[]
    for r in dump(port)['recs']:
        if r['kind']=='u' and not r['del']:
            d=r['data'] if isinstance(r['data'],dict) else json.loads(r['data'] or '{}')
            out.append(d)
    return out
def name(pg,n):
    pg.fill('#fName',n);pg.click('#fName2')
    pg.wait_for_function("!document.querySelector('.card') || !!document.querySelector('#fPin,#fCheck,#fOther')",timeout=15000)
    pg.wait_for_timeout(300)
def setpin(pg,pin):
    pg.fill('#fPin',pin);pg.fill('#fPin2',pin);pg.click('#fSet');pg.wait_for_selector('header',timeout=8000)
def pin(pg,p):
    pg.fill('#fPin',p);pg.click('#fGo');pg.wait_for_selector('header',timeout=8000)
def synced(pg):
    pg.evaluate("TMC.syncNow()");pg.wait_for_timeout(800)
def work(pg):
    pg.evaluate("(()=>{const w=TMC.ws();w.screen='list';w.jobId=null;w.mat=null;w.pendingPhoto=null})()")
    pg.click('nav [data-tab=work]');pg.wait_for_timeout(250)
def new_job(pg,title,kind):
    work(pg);pg.click('#wjNew');pg.wait_for_timeout(200)
    pg.fill('#wjName',title);pg.click('#wjTyR' if kind=='repair' else '#wjTyB');pg.wait_for_timeout(150)
    pg.click('#wjSave');pg.wait_for_timeout(400)
def open_job(pg,title):
    work(pg);pg.locator('.wjOpen',has_text=title).first.click();pg.wait_for_timeout(250)

def buy_row(pg,row=0):
    return pg.locator('.wjBuy[data-r="%d"]'%row)
def pick_buy(pg,name,row=0,new=False):
    root=buy_row(pg,row)
    inp=root.locator('.wjBuyName')
    inp.click();inp.fill(name);pg.wait_for_timeout(200)
    sug=root.locator('.sug')
    if new:sug.locator('.wjSugNew').click()
    else:sug.locator('div[data-n]:not(.wjSugNew)',has_text=name).first.click()
    pg.wait_for_timeout(200)
def fill_buy(pg,row,qty=None,used=None,h=None,w=None,l=None):
    root=buy_row(pg,row)
    if qty is not None:root.locator('.wjBuyQty').fill(str(qty))
    if used is not None:root.locator('.wjBuyUsed').fill(str(used))
    if h is not None:root.locator('.wjBuyH').fill(str(h))
    if w is not None:root.locator('.wjBuyW').fill(str(w))
    if l is not None:root.locator('.wjBuyL').fill(str(l))
    pg.wait_for_timeout(80)
def mm(length):
    return str(int(round(float(str(length).replace(",","."))*1000)))

def add_mat(pg,kind,desc,pcs,length):
    pg.click({'steel':'#wjAddSteel','rope':'#wjAddRope','other':'#wjAddOther'}[kind]);pg.wait_for_timeout(200)
    row=pg.locator('.wjBuy').count()-1
    pick_buy(pg,desc,row)
    if length is not None:fill_buy(pg,row,qty=1,used=mm(length))
    elif pcs is not None:fill_buy(pg,row,qty=pcs)
    pg.click('#wjSaveM');pg.wait_for_timeout(400)
try:
  with sync_playwright() as pw:
    b=pw.chromium.launch(executable_path='/usr/bin/google-chrome' if os.path.exists('/usr/bin/google-chrome') else None,args=['--no-sandbox'])
    def ctx():
        c=b.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True,service_workers='allow')
        c.on('dialog',lambda d:d.accept())
        return c
    x=ctx();pg=x.new_page();errs=[];pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.goto(SHOP);pg.wait_for_selector('#fName')
    name(pg,'Johan Kirsten');ok(pg.locator('#fPin2').count()==1,'Johan Kirsten → first Admin setup (alias of jakirsten)')
    setpin(pg,'2468');synced(pg)
    me=pg.evaluate("TMC.me()")
    ok(me and me.get('admin') and me.get('name')=='JA Kirsten','stored Admin name is JA Kirsten, not the typed alias')
    ok(pg.evaluate("TMC.NK('Johan Kirsten')==='jakirsten'&&TMC.NK('J. A. Kirsten')==='jakirsten'&&TMC.NK('JA Kirsten')==='jakirsten'&&TMC.NK('Johan')!=='jakirsten'"),'Johan spellings map to jakirsten; Johan alone does not')
    ok(len(users(GP))==1,'one Admin on this app Sheet')
    work(pg);ok(pg.locator('#wjEmpty').count()==1,'empty job list')
    new_job(pg,'EXAMPLE Gate frame','build')
    ok(pg.locator('#wjList').count()==1 and pg.locator('#wjName').count()==0 and pg.locator('#navAsk').count()==0,'save job closes the form onto the list')
    ok('EXAMPLE Gate frame' in pg.inner_text('#wjList'),'job is on the list')
    pg.click('#wjStock');pg.wait_for_timeout(250)
    ok(pg.locator('#wjStockBox').count()==1 and 'http' not in pg.inner_text('#wjStockBox').lower() and 'No stock yet' in pg.inner_text('#wjOnHand'),'stock screen has no live Food link and no credit yet')
    urllib.request.urlopen('http://127.0.0.1:%d/_prop?STOCK_IMPORT_CODE=%s'%(GP,urllib.parse.quote('test-import-workshop')))
    xfer={"action":"importStockTransfer","code":"test-import-workshop","transfer":{"id":"EX-FOOD-0001","v":1,"sourceApp":"fi","sourceIssueId":"EX-FOOD-0001","destinationApp":"tmcworkshop","at":"2026-11-08T09:00:00.000Z","by":"EXAMPLE Food","qtyScale":3,"lines":[{"id":"EX-LN-STEEL-PC","sourceItemId":"FI-ANGLE-PC","name":"EXAMPLE angle iron","unit":"piece","qty":"20"},{"id":"EX-LN-STEEL-M","sourceItemId":"FI-ANGLE-M","name":"EXAMPLE angle iron","unit":"m","qty":"30"},{"id":"EX-LN-ROPE","sourceItemId":"FI-ROPE-M","name":"EXAMPLE rope","unit":"m","qty":"40"}]}}
    got=json.load(urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:%d/exec'%GP,data=json.dumps(xfer).encode(),method='POST')))
    ok(got.get('ok') and got.get('result')=='accepted' and got.get('transferId')=='EX-FOOD-0001','sample Food transfer accepted once')
    pg.evaluate("TMC.syncNow()");pg.wait_for_timeout(800);pg.evaluate("TMC.render()");pg.wait_for_timeout(300)
    ok('Received' in pg.inner_text('#wjStockBox') and 'EX-FOOD-0001' in pg.inner_text('#wjStockBox'),'accepted transfer shows as received')
    bal=pg.evaluate("TMC.wBal('steel','EXAMPLE angle iron')")
    ok(bal['qty']==20 and bal['len']==30,'steel pieces and metres credited once: %s'%bal)
    again=json.load(urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:%d/exec'%GP,data=json.dumps(xfer).encode(),method='POST')))
    ok(again.get('result')=='duplicate','identical retry is a duplicate')
    pg.evaluate("TMC.syncNow()");pg.wait_for_timeout(600)
    ok(pg.evaluate("TMC.wBal('steel','EXAMPLE angle iron').qty")==20 and pg.evaluate("TMC.all('k').filter(k=>k.dir==='in').length")==3,'duplicate did not add a second credit')
    pg.click('#view .navBack');pg.wait_for_timeout(250)
    open_job(pg,'EXAMPLE Gate frame')
    pg.click('#wjAddSteel');pg.wait_for_timeout(200);pick_buy(pg,'EXAMPLE angle iron',0);fill_buy(pg,0,qty=1,used='999000');pg.click('#wjSaveM');pg.wait_for_timeout(300)
    ok(pg.locator('#wjMat').count()==1 and 'Not enough' in pg.inner_text('#wjErr'),'over-allocation stays on the form')
    ok(pg.evaluate("TMC.wBal('steel','EXAMPLE angle iron').qty")==20,'failed save does not deduct stock')
    pg.click('#view .navBack');pg.wait_for_timeout(200)
    if pg.locator('#navAsk').count():pg.click('#navYes');pg.wait_for_timeout(200)
    add_mat(pg,'steel','EXAMPLE angle iron','2.5','3')
    ok(pg.locator('#wjJob').count()==1 and pg.locator('#wjMat').count()==0,'save steel closes onto the job')
    add_mat(pg,'steel','EXAMPLE angle iron','2.5','1.5')
    ok(pg.locator('.wjRow',has_text='EXAMPLE angle iron').count()==2,'repeated steel is kept as two entries')
    tot=pg.inner_text('#wjTot')
    ok('4.5 m' in tot and pg.locator('.wjRow',has_text='EXAMPLE angle iron').count()==2,'steel totals add the repeated lengths: %s'%tot.replace('\n',' '))
    add_mat(pg,'rope','EXAMPLE rope',None,'12.5')
    ok('12.5 m' in pg.inner_text('#wjTot'),'decimal rope length 12.5 m is kept')
    pg.click('#wjAddRope');pg.wait_for_timeout(200);pg.click('#wjSaveM');pg.wait_for_timeout(300)
    ok(pg.locator('#wjMat').count()==1 and not (pg.locator('.wjBuyName').first.input_value() or '').strip(),'save with no item stays on the form')
    pick_buy(pg,'EXAMPLE rope',0);pg.click('#wjSaveM');pg.wait_for_timeout(300)
    ok(pg.locator('#wjMat').count()==1 and 'EXAMPLE rope' in pg.locator('.wjBuyName').first.input_value(),'save with no length stays on the form and keeps the picked item')
    pg.click('#view .navBack');pg.wait_for_timeout(200)
    if pg.locator('#navAsk').count():pg.click('#navYes');pg.wait_for_timeout(200)
    ok(pg.locator('#wjJob').count()==1,'Back from a bad entry returns to the job')
    add_mat(pg,'rope','EXAMPLE rope',None,'4.25')
    rope=pg.inner_text('#wjTot')
    ok('16.75 m' in rope,'decimal rope length 4.25 adds to 16.75 m')
    ok(pg.locator('.wjRow',has_text='EXAMPLE rope').count()==2,'repeated rope lengths are both listed')
    when=pg.inner_text('#wjHist')
    ok(re.search(r'\b(?:[01]\d|2[0-3]):[0-5]\d\b',when) and not re.search(r'\b[AP]M\b',when),'material history uses 24h time')
    pg.click('#wjOpenPh');pg.wait_for_timeout(200)
    ok(pg.locator('#wjPhPick .phCam').count()==1 and pg.locator('#wjPhPick .phGal').count()==1,'completed photo has Take photo and Upload photo')
    err=pg.evaluate("""()=>{document.getElementById('wjSavePh').click();const e=document.getElementById('wjErr');return {on:!!document.getElementById('wjPhoto'),err:e?e.textContent:''}}""")
    ok(err['on'] and ('photo' in err['err'].lower() or 'foto' in err['err'].lower()),'save with no photo stays on the form: %s'%err)
    pg.set_input_files('#wjPhPick .phGal input',files=[{'name':'job.png','mimeType':'image/png','buffer':PNG}])
    pg.wait_for_function("document.querySelector('#wjPic')&&document.querySelector('#wjPic').src.indexOf('data:image')===0",timeout=8000)
    pg.click('#wjSavePh');pg.wait_for_timeout(500)
    ok(pg.locator('#wjJob').count()==1 and 'Completed' in pg.inner_text('#wjJob'),'photo save closes and marks the job completed')
    ok(pg.locator('#wjPic').count()==1 and pg.evaluate("document.querySelector('#wjPic').src.indexOf('data:image')===0"),'completed photo shows on the job')
    ok(pg.evaluate("TMC.all('p').length")>=1 and pg.evaluate("TMC.all('j').every(j=>!j.photo&&!j.stock)"),'photo is its own record; the job is not a stock card')
    new_job(pg,'EXAMPLE Pump stand','repair')
    work(pg)
    names=pg.evaluate("[...document.querySelectorAll('.wjOpen .n')].map(e=>e.textContent)")
    ok(names and names[0]=='EXAMPLE Pump stand','newest job is first in the history')
    pg.click('[data-flt=repair]');pg.wait_for_timeout(200)
    shown=pg.evaluate("[...document.querySelectorAll('.wjOpen .n')].map(e=>e.textContent)")
    ok(shown==['EXAMPLE Pump stand'],'Repair filter hides Build jobs: %s'%shown)
    pg.click('[data-flt=build]');pg.wait_for_timeout(200)
    shown=pg.evaluate("[...document.querySelectorAll('.wjOpen .n')].map(e=>e.textContent)")
    ok(shown==['EXAMPLE Gate frame'],'Build filter hides Repair jobs: %s'%shown)
    pg.click('[data-flt=all]');pg.wait_for_timeout(200)
    ok(pg.locator('.wjOpen').count()==2,'All shows both jobs')
    open_job(pg,'EXAMPLE Gate frame')
    ok(pg.locator('.fixB').count()>=1,'Admin sees Fix on a saved job or material')
    n0=len(users(GP));synced(pg)
    ok(any(r['kind']=='j' and r['data'] and r['data'].get('name')=='EXAMPLE Gate frame' for r in dump(GP)['recs']),'job reached this app Sheet')
    # wiped phone: alias re-sign-in, same Admin, jobs come back, no second user
    y=ctx();w=y.new_page();w.goto(SHOP);w.wait_for_selector('#fName',timeout=15000)
    name(w,'J. A. Kirsten');ok(w.locator('#fPin').count()==1 and w.locator('#fPin2').count()==0,'reinstall: alias goes to PIN, not a new setup')
    pin(w,'2468');synced(w)
    ok(w.evaluate("TMC.me()&&TMC.me().admin&&TMC.me().name")=='JA Kirsten','reinstalled alias is the same Admin')
    ok(len(users(GP))==n0,'reinstall did not create another user')
    open_job(w,'EXAMPLE Gate frame')
    ok('16.75 m' in w.inner_text('#wjTot') and w.locator('.wjRow').count()>=4,'wiped phone pulled the steel and rope back')
    z=ctx();g=z.new_page();g.goto(SHOP);g.wait_for_selector('#fName')
    name(g,'Johan');ok('approval' in (g.inner_text('.card') or '').lower(),'Johan alone is not the Admin alias')
    # staff can add a rope length, cannot fix the job
    synced(pg);pg.click('nav [data-tab=users]');pg.wait_for_timeout(400)
    pg.locator('.ulr',has_text='Johan').locator('[data-ua=approve]').click();pg.wait_for_timeout(800)
    g.click('#fCheck');g.wait_for_selector('#fPin2',timeout=8000);setpin(g,'1357');synced(g)
    open_job(g,'EXAMPLE Gate frame')
    ok(g.locator('.fixB').count()==0,'staff has no Fix button')
    ok(g.evaluate("(()=>{const j=TMC.all('j')[0];return TMC.fix('j',j.id,'name','renamed')})()") is False,'staff cannot fix a saved job')
    add_mat(g,'rope','EXAMPLE rope',None,'2.5')
    ok(g.locator('.wjRow',has_text='EXAMPLE rope').count()==3,'staff allocated a rope length from workshop stock')
    ok(g.evaluate("TMC.wBal('rope','EXAMPLE rope').len")==20.75,'rope on hand dropped by exactly 2.5 m')
    ok(g.evaluate("[TMC.wBal('steel','EXAMPLE angle iron').qty,TMC.wBal('steel','EXAMPLE angle iron').len,TMC.wBal('rope','EXAMPLE rope').len].every(n=>n>=0)"),'stock does not go negative')
    s0=g.evaluate("JSON.stringify(TMC.wBal('steel','EXAMPLE angle iron'))")
    r0=g.evaluate("TMC.wBal('rope','EXAMPLE rope').len")
    g.click('#wjAddSteel');g.wait_for_timeout(200)
    pick_buy(g,'Hex bar 20 x 20',0,new=True);fill_buy(g,0,qty=1,used='1500',h=20,w=20,l=3000);g.click('#wjSaveM');g.wait_for_timeout(400)
    neu=g.evaluate("TMC.all('m').filter(m=>m.new)")
    ok(g.locator('#wjJob').count()==1 and neu and neu[-1]['desc']=='Hex bar 20 x 20' and neu[-1].get('new')==1 and neu[-1].get('hMm')==20 and neu[-1].get('wMm')==20 and neu[-1].get('lMm')==3000 and neu[-1].get('usedMm')==1500,'new item is saved on the job with new:1, dimensions and length used')
    ok(g.evaluate("JSON.stringify(TMC.wBal('steel','EXAMPLE angle iron'))")==s0 and g.evaluate("TMC.wBal('rope','EXAMPLE rope').len")==r0 and not g.evaluate("TMC.all('k').some(k=>k.dir==='out'&&k.desc==='Hex bar 20 x 20')"),'a new item takes nothing off Workshop stock')

    # other app on the same phone
    o=ctx();op=o.new_page();op.goto(OTHER);op.wait_for_selector('#fName')
    name(op,'Johan Kirsten');setpin(op,'9753');synced(op)
    op.evaluate("TMC.put('j','other1',{id:'other1',name:'OTHER APP MARKER',type:'build',by:'JA Kirsten',at:new Date().toISOString()})")
    op.wait_for_timeout(900);synced(op)
    shop_keys=pg.evaluate("Object.keys(localStorage)")
    oth_keys=op.evaluate("Object.keys(localStorage)")
    ok(all(k.startswith('tmcworkshop_') for k in shop_keys),'workshop storage keys stay on tmcworkshop_')
    ok(all(k.startswith('tmcother_') for k in oth_keys) and not any(k.startswith('tmcworkshop_') for k in oth_keys),'other app has no workshop keys')
    shop_dump=json.dumps(dump(GP));oth_dump=json.dumps(dump(OP))
    ok('EXAMPLE Gate frame' in shop_dump and 'OTHER APP MARKER' not in shop_dump,'workshop Sheet has the sample job only')
    ok('OTHER APP MARKER' in oth_dump and 'EXAMPLE Gate frame' not in oth_dump,'other Sheet does not receive workshop jobs')
    ok('tmc-workshop' in open(os.path.join(TMP,'shop','sw.js'),encoding='utf-8').read() and 'tmc-other' in open(os.path.join(TMP,'other','sw.js'),encoding='utf-8').read(),'cache names differ')
    ok(not errs,'no page errors %s'%errs[:3])
    b.close()
finally:
    for g_ in gas:
        try:g_.kill()
        except Exception:pass
    try:srv.shutdown()
    except Exception:pass
    shutil.rmtree(TMP,ignore_errors=True)
print('\nWORKSHOP: %d passed, %d failed'%(P,F));sys.exit(1 if F else 0)
