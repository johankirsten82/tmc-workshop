#!/usr/bin/env python3
"""Cut list + Send to Assets + built-before tests. Mock Sheet only. Sample, not published.
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
NEW_KEYS=["wjCut","wjCutNew","wjCutH","wjCutMat","wjNeedMat","wjAddRow","wjDelRow","wjNeedCut",
 "wjNeedQtyLen","wjPerUnit","wjAllUnits","wjLengths","wjMm","wjM","wjPadOk","wjSaveCut","wjNoCut",
 "wjCuts","wjStockLen","wjStockLenH","wjStockLenT","wjSaveLen","wjNeedStockLen","wjSetLen","wjNoneM",
 "wjYouUsed","wjOf","wjMade","wjMadeH","wjUnits","wjSize","wjSizeH","wjAssets","wjAssetsH","wjNoneFa",
 "wjWaitAssets","wjMarkReady","wjMarked","wjDelCut","wjFaJob","wjBuiltBefore","wjAddBefore",
 "wjAddBeforeH","wjSaveBefore","wjNeedBefore","wjNeedBeforeQty","wjNoJob","wjDelCutQ","wjStayUsed","wjUsedHead","wjPerItem"]
CHROME='/usr/bin/google-chrome' if os.path.exists('/usr/bin/google-chrome') else None
try:
  with sync_playwright() as pw:
    b=pw.chromium.launch(executable_path=CHROME,args=['--no-sandbox'])
    def ctx():
        c=b.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True,service_workers='allow')
        c.on('dialog',lambda d:d.accept())
        return c
    c=ctx();pg=c.new_page()
    pg.goto(SHOP);pg.wait_for_selector('#langSel')
    # --- keys in all 4 languages ---
    keys=pg.evaluate("""keys=>{const T=TMC.T,out={};keys.forEach(k=>out[k]={en:!!(T.en&&T.en[k]),fr:!!(T.fr&&T.fr[k]),ar:!!(T.ar&&T.ar[k]),af:!!(T.af&&T.af[k])});return out}""",NEW_KEYS)
    missing=[k for k,v in keys.items() if not all(v[l] for l in ('en','fr','ar','af'))]
    ok(not missing,'every new cut/assets key exists in en/fr/ar/af %s'%missing)
    # --- exact 5.5 m example (integer mm) ---
    plan=pg.evaluate("""()=>TMC.cutPlan([{qty:4,len:1,unit:'m'},{qty:5,len:300,unit:'mm'}],1,6000)""")
    ok(plan['perMm']==5500 and abs(plan['perM']-5.5)<1e-9,'4×1 m + 5×300 mm = 5.5 m per unit %s'%plan)
    ok(plan['bars']==1 and plan['stockLenMm']==6000,'5.5 m rounds up to 1 × 6 m length %s'%plan)
    plan2=pg.evaluate("""()=>TMC.cutPlan([{qty:4,len:1,unit:'m'},{qty:5,len:300,unit:'mm'}],2,6000)""")
    ok(plan2['totalMm']==11000 and abs(plan2['totalM']-11)<1e-9,'2 units = 11 m %s'%plan2)
    ok(plan2['bars']==2,'11 m rounds up to 2 × 6 m lengths %s'%plan2)
    mix=pg.evaluate("""()=>TMC.cutPlan([{qty:1,len:1500,unit:'mm'},{qty:2,len:2,unit:'m'}],1,6000)""")
    ok(mix['perMm']==5500,'mm/m mixing: 1×1500 mm + 2×2 m = 5.5 m %s'%mix)
    up=pg.evaluate("""()=>({a:TMC.cutPlan([{qty:1,len:6,unit:'m'}],1,6000).bars,b:TMC.cutPlan([{qty:1,len:6.1,unit:'m'}],1,6000).bars,c:TMC.cutPlan([{qty:1,len:0,unit:'m'}],1,6000).bars})""")
    ok(up['a']==1 and up['b']==2 and up['c']==0,'rounding up: 6 m → 1 length, 6.1 m → 2, 0 → 0 %s'%up)
    # locale number display
    fmt=pg.evaluate("""()=>{const o={};['en','fr','af','ar'].forEach(l=>{TMC.T&&0;const prev=document.documentElement.lang;return});return 0}""")
    fmt=pg.evaluate("""()=>{
      const hold=document.documentElement.lang;
      const run=l=>{const ev=new Event('change'); /* set via apply by selecting */ return l};
      return {
        en:(()=>{const lang='en';const wFmt=TMC.wFmt; /* we'll swap by setting #hLang later */ return null})()
      };
    }""")
    name(pg,'Johan Kirsten');pg.wait_for_selector('#fPin2')
    setpin(pg,'2468')
    # locale via signed-in language select
    def fmtof(lang,n=5.5):
        pg.select_option('#hLang',lang);pg.wait_for_timeout(150)
        return pg.evaluate("(n)=>TMC.wFmt(n)",n)
    en=fmtof('en');fr=fmtof('fr');af=fmtof('af');ar=fmtof('ar')
    ok(en=='5.5','EN uses a dot: %r'%en)
    ok(fr=='5,5' and af=='5,5','FR and AF use a comma: fr=%r af=%r'%(fr,af))
    ok(ar=='5.5' and not re.search(r'[\u0660-\u0669\u06F0-\u06F9]',ar),'AR uses Latin digits and a dot: %r'%ar)
    pg.select_option('#hLang','en');pg.wait_for_timeout(150)
    # --- add metre stock ---
    work(pg);pg.click('#wjStock');pg.wait_for_timeout(200)
    pg.click('#wjAddStock');pg.wait_for_timeout(200)
    pg.fill('#wjItem','Square tubing 40×40');pg.click('#wjAdTysteel');pg.wait_for_timeout(100)
    pg.click('#wjAdUnm');pg.wait_for_timeout(100)
    pg.fill('#wjAddQty','18');pg.click('#wjSaveAdd');pg.wait_for_timeout(500)
    bal=pg.evaluate("TMC.wBal('steel','Square tubing 40×40')")
    ok(abs(bal.get('len',0)-18)<1e-9,'on-hand is 18 m of Square tubing 40×40 %s'%bal)
    sl=pg.evaluate("TMC.wStockLenMm('Square tubing 40×40')")
    ok(sl==6000,'default bar length is 6 m (%s mm)'%sl)
    pg.click('#view .navBack');pg.wait_for_timeout(250)
    pg.click('#wjNew');pg.wait_for_timeout(200)
    pg.fill('#wjName','Ward beds');pg.fill('#wjMade','Bed');pg.fill('#wjUnits','2');pg.click('#wjSave');pg.wait_for_timeout(400)
    ok(pg.locator('#wjList').count()==1 and 'Ward beds' in pg.inner_text('#wjList'),'job saved and listed')
    pg.locator('.wjOpen',has_text='Ward beds').click();pg.wait_for_timeout(250)
    pg.click('#wjCutNew');pg.wait_for_timeout(250)
    ok(pg.locator('#wjCut').count()==1 and pg.locator('#wjPad').count()==1,'cut list form shows a big number pad')
    # pick material, set two rows (4×1 m and 5×300 mm, 2 beds)
    pg.evaluate("""()=>{
      const WS=TMC.ws();
      WS.cutDesc='Square tubing 40×40';
      WS.cutRows=[{qty:'4',len:'1',unit:'m'},{qty:'5',len:'300',unit:'mm'}];
      WS.cutUnits='2';WS.cutItem='Bed';WS.cutPad={row:0,field:'qty'};
      TMC.render();
    }""")
    pg.wait_for_timeout(200)
    if pg.locator('#wjCutUnits').count():
        pg.fill('#wjCutUnits','2');pg.fill('#wjCutItem','Bed')
        pg.evaluate("TMC.ws().cutUnits='2';TMC.ws().cutItem='Bed';TMC.ws().cutDesc='Square tubing 40×40'")
    txt=pg.inner_text('#wjCutSum') if pg.locator('#wjCutSum').count() else pg.inner_text('#wjCut')
    flat=' '.join(txt.split())
    ok('You used 11 m of Square tubing 40×40' in flat,'headline is the TOTAL taken off stock (11 m), not per item: %s'%flat)
    ok('5.5 m per item' in flat,'under the headline: 5.5 m per item: %s'%flat)
    ok('2 × 6 m' in flat or '2 × 6 m' in txt,'cut form shows 2 × 6 m lengths: %s'%flat)
    ok('4 × 1 m + 5 × 300 mm = 5.5 m per item' in flat,'per-item line shows the sum: 4 × 1 m + 5 × 300 mm = 5.5 m per item: %s'%flat)
    geo=pg.evaluate("""()=>{const b=document.querySelector('#wjCutSum .wjBig'),p=document.querySelector('#wjCutSum .wjPer');if(!b||!p)return null;const rb=b.getBoundingClientRect(),rp=p.getBoundingClientRect();return {big:parseFloat(getComputedStyle(b).fontSize),per:parseFloat(getComputedStyle(p).fontSize),below:rp.top>=rb.bottom-1,perTxt:p.innerText,bigTxt:b.innerText}}""")
    ok(bool(geo) and geo['per']<geo['big'] and geo['below'] and '11 m' in geo['bigTxt'] and '5.5 m' in geo['perTxt'] and '11' not in geo['perTxt'],'headline is the 11 m total, per-item 5.5 m sits underneath in smaller text %s'%geo)
    # same headline in FR / AF (comma) and AR (Latin digits)
    heads={}
    for lang in ('fr','af','ar'):
        pg.select_option('#hLang',lang);pg.wait_for_timeout(150)
        heads[lang]=' '.join((pg.inner_text('#wjCutSum') if pg.locator('#wjCutSum').count() else '').split())
    ok('4 × 1 m + 5 × 300 mm = 5,5 m par article' in heads['fr'] and '4 × 1 m + 5 × 300 mm = 5,5 m per item' in heads['af'] and '4 × 1 m + 5 × 300 mm = 5.5 m' in heads['ar'],'FR/AF/AR per-item sum line: %s'%heads)
    ok('Vous avez utilisé 11 m de Square tubing 40×40' in heads['fr'] and '5,5 m par article' in heads['fr'] and '2 × 6 m' in heads['fr'],'FR total box uses 11 m headline and 5,5: %s'%heads['fr'])
    ok('Julle het 11 m van Square tubing 40×40 gebruik' in heads['af'] and '5,5 m per item' in heads['af'] and '2 × 6 m' in heads['af'],'AF total box uses 11 m headline and 5,5: %s'%heads['af'])
    ok('استُخدم' in heads['ar'] and '11 m' in heads['ar'] and 'Square tubing 40×40' in heads['ar'] and '5.5 m' in heads['ar'] and 'لكل قطعة' in heads['ar'],'AR total box uses 11 m headline and Latin digits: %s'%heads['ar'])
    pg.select_option('#hLang','en');pg.wait_for_timeout(150)
    pg.click('#wjSaveCut');pg.wait_for_timeout(500)
    ok(pg.locator('#wjJob').count()==1 and pg.locator('#wjCut').count()==0,'Save cut list closes onto the job')
    cuts=pg.evaluate("()=>TMC.wCuts(TMC.ws().jobId||TMC.all && 0).length||TMC.wCuts((TMC.all?null:null))")
    # get job id
    info=pg.evaluate("""()=>{
      const jobs=(window.TMC.ws&&1);
      const allC=TMC.wCuts?null:null;
      const recs=Object.keys(window).length;
      const cuts=document.querySelectorAll('.wjCutSaved');
      const bal=TMC.wBal('steel','Square tubing 40×40');
      const k=TMC.wStockItems();
      return {nCuts:cuts.length,txt:document.getElementById('wjCutsBox')?document.getElementById('wjCutsBox').innerText:'',bal,hasOut:true};
    }""")
    # more precise from records via evaluate of all k
    rec=pg.evaluate("""()=>{
      const ks=TMC.wStockItems();
      const bal=TMC.wBal('steel','Square tubing 40×40');
      const box=(document.getElementById('wjCutsBox')||{innerText:''}).innerText;
      return {len:bal.len,qty:bal.qty,box};
    }""")
    ok(abs(rec['len']-7)<1e-9,'stock deducted 11 m (18-11=7) now %s'%rec)
    ok('5.5' in rec['box'] and '11' in rec['box'],'saved cut list shows 5.5 m and 11 m: %s'%rec['box'].replace('\n',' / '))
    ok(pg.locator('.wjDelCut').count()==1,'Admin sees Delete cut list')
    # job cap: another 2 beds would need 11 m but only 7 left
    pg.click('#wjCutNew');pg.wait_for_timeout(200)
    pg.evaluate("""()=>{const WS=TMC.ws();WS.cutDesc='Square tubing 40×40';WS.cutRows=[{qty:'4',len:'1',unit:'m'},{qty:'5',len:'300',unit:'mm'}];WS.cutUnits='2';WS.cutItem='Bed';TMC.render()}""")
    pg.wait_for_timeout(200)
    if pg.locator('#wjCutUnits').count():pg.fill('#wjCutUnits','2')
    pg.click('#wjSaveCut');pg.wait_for_timeout(300)
    ok(pg.locator('#wjCut').count()==1 and 'Not enough' in (pg.inner_text('#wjErr') if pg.locator('#wjErr').count() else ''),'job cap: not enough stock to save a second 11 m cut list')
    rec2=pg.evaluate("TMC.wBal('steel','Square tubing 40×40')")
    ok(abs(rec2['len']-7)<1e-9,'failed cut list does not deduct stock (still 7 m) %s'%rec2)
    # back to job, mark ready (leave the unsaved cap-fail form)
    back(pg)
    if pg.locator('#wjJob').count()==0:
        if pg.locator('.wjOpen',has_text='Ward beds').count():
            pg.locator('.wjOpen',has_text='Ward beds').click();pg.wait_for_timeout(250)
        else:
            work(pg);pg.locator('.wjOpen',has_text='Ward beds').click();pg.wait_for_timeout(250)
    pg.click('#wjMarkReady');pg.wait_for_timeout(300)
    if pg.locator('#wjSaveReady').count():pg.click('#wjSaveReady');pg.wait_for_timeout(400)
    # afterSave may return to the list; open Assets
    ok(pg.locator('#wjJob').count()==1,'Save on the finished form returns to the job')
    if pg.locator('#wjAssetsBox').count()==0:
        if pg.locator('#wjAssets').count()==0:
            pg.evaluate("(()=>{const w=TMC.ws();w.screen='list';w.jobId=null;TMC.render()})()");pg.wait_for_timeout(200)
        if pg.locator('#wjList').count() and pg.locator('#wjAssets').count():
            pg.click('#wjAssets');pg.wait_for_timeout(300)
    atxt=pg.inner_text('#wjAssetsBox') if pg.locator('#wjAssetsBox').count() else pg.inner_text('body')
    ok('Bed' in atxt and 'Waiting for Assets' in atxt,'marked-ready item is on Send to Assets list: %s'%atxt.replace('\n',' / ')[:240])
    ok(pg.locator('#wjAddBefore').count()==1,'Admin sees Add item built before')
    # built before
    pg.click('#wjAddBefore');pg.wait_for_timeout(250)
    ok(pg.locator('#wjBeforeBox').count()==1 and pg.locator('#wjSaveFa').count()==1,'built-before form opened')
    pg.fill('#wjFaName','Table');pg.fill('#wjFaQty','3');pg.fill('#wjFaSize','old stock')
    before_bal=pg.evaluate("TMC.wBal('steel','Square tubing 40×40')")
    pg.click('#wjSaveFa');pg.wait_for_timeout(400)
    ok(pg.locator('#wjAssetsBox').count()==1 and pg.locator('#wjBeforeBox').count()==0,'Save built-before closes onto the Assets list')
    ltxt=pg.inner_text('#wjAssetsBox')
    ok('Table' in ltxt and 'Built before' in ltxt and 'Waiting for Assets' in ltxt,'list treats built-before the same (Waiting for Assets + Built before mark): %s'%ltxt.replace('\n',' / ')[:300])
    after_bal=pg.evaluate("TMC.wBal('steel','Square tubing 40×40')")
    ok(abs(after_bal['len']-before_bal['len'])<1e-9,'stock unchanged after adding a built-before item (%s -> %s)'%(before_bal,after_bal))
    # --- staff cannot edit cut list or add built-before ---
    synced(pg)
    z=ctx();g=z.new_page();g.goto(SHOP);g.wait_for_selector('#fName')
    name(g,'Pieter');g.wait_for_timeout(400)
    synced(pg);pg.click('nav [data-tab=users]');pg.wait_for_timeout(400)
    row=pg.locator('.ulr',has_text='Pieter')
    if row.locator('.uopen').count()==0:
        row.locator('.uli').click();pg.wait_for_timeout(200)
    pg.locator('.ulr',has_text='Pieter').locator('[data-ua=approve]').click();pg.wait_for_timeout(800)
    if g.locator('#fCheck').count():
        g.click('#fCheck');g.wait_for_selector('#fPin2',timeout=8000)
    if g.locator('#fPin2').count():
        setpin(g,'1357')
    elif g.locator('#fPin').count():
        pin(g,'1357')
    g.wait_for_selector('header',timeout=8000)
    synced(g)
    ok(g.evaluate("TMC.me()&&!TMC.me().admin"),'Pieter is not Admin')
    g.evaluate("(()=>{const w=TMC.ws();w.screen='list';w.jobId=null})()")
    g.click('nav [data-tab=work]');g.wait_for_timeout(250)
    g.locator('.wjOpen',has_text='Ward beds').click();g.wait_for_timeout(250)
    ok(g.locator('.wjDelCut').count()==0,'staff cannot see Delete cut list')
    still=g.evaluate("""()=>{
      const id=(TMC.ws()||{}).jobId;
      const cuts=TMC.wCuts(id);
      const r=cuts[0]?TMC.remove('c',cuts[0].id):false;
      return {n:TMC.wCuts(id).length,fix:TMC.canFix(),r:r};
    }""")
    ok(still.get('n',0)>=1 and still.get('fix') is False and still.get('r') is False,'staff cannot edit/delete a saved cut list (canFix=%s, cuts=%s, remove=%s)'%(still.get('fix'),still.get('n'),still.get('r')))
    g.evaluate("(()=>{const w=TMC.ws();w.screen='list';w.jobId=null})()")
    g.click('nav [data-tab=work]');g.wait_for_timeout(250)
    g.click('#wjAssets');g.wait_for_timeout(300)
    ok(g.locator('#wjAddBefore').count()==0 and 'Add item built before' not in g.inner_text('#wjAssetsBox'),'staff cannot see or use Add item built before')
    bounced=g.evaluate("()=>{TMC.ws().screen='before';TMC.render();return {before:!!document.getElementById('wjBeforeBox'),assets:!!document.getElementById('wjAssetsBox')}}")
    ok(not bounced['before'] and bounced['assets'],'staff who open the built-before form are sent back to the Assets list %s'%bounced)
    # Admin deletes the cut list: record is removed, stock 'k' out stays (metres do not come back)
    pg.evaluate("(()=>{const w=TMC.ws();w.screen='list';w.jobId=null})()")
    work(pg)
    if pg.locator('.wjOpen',has_text='Ward beds').count():
        pg.locator('.wjOpen',has_text='Ward beds').click();pg.wait_for_timeout(250)
    before=pg.evaluate("""()=>{
      const bal=TMC.wBal('steel','Square tubing 40×40');
      const ks=TMC.all('k').filter(k=>k.dir==='out'&&k.desc==='Square tubing 40×40');
      const cuts=TMC.wCuts((TMC.ws()||{}).jobId);
      return {len:bal.len,k:ks.length,kids:ks.map(k=>k.id),cuts:cuts.length,cutIds:cuts.map(c=>c.id)};
    }""")
    ok(abs(before['len']-7)<1e-9 and before['k']>=1 and before['cuts']>=1,'pre-delete: 7 m on hand, a k out and a cut list %s'%before)
    pg.locator('.wjDelCut').first.click();pg.wait_for_timeout(200)
    ask=pg.locator('#wjDelCutAsk')
    atxt=ask.inner_text() if ask.count() else ''
    ok(ask.count()==1 and 'Delete this cut list?' in atxt and 'The metres stay used' in atxt,'Admin delete confirm does not promise metres come back: %s'%atxt.replace('\n',' / '))
    stay=pg.evaluate("()=>({en:TMC.T.en.wjStayUsed,fr:TMC.T.fr.wjStayUsed,ar:TMC.T.ar.wjStayUsed,af:TMC.T.af.wjStayUsed})")
    ok('do not go back into stock' in stay['en'] and 'ne retournent pas dans le stock' in stay['fr'] and 'nie terug in voorraad nie' in stay['af'] and 'لا تعود إلى المخزون' in stay['ar'],'delete confirm says plainly the metres do NOT go back into stock in EN/FR/AR/AF %s'%stay)
    ok('do not go back into stock' in atxt and 'go back into stock.' not in atxt.replace('do not go back into stock.',''),'EN confirm text shows the no-return line: %s'%atxt.replace('\n',' / '))
    pg.click('#wjDelCutYes');pg.wait_for_timeout(400)
    after=pg.evaluate("""()=>{
      const bal=TMC.wBal('steel','Square tubing 40×40');
      const ks=TMC.all('k').filter(k=>k.dir==='out'&&k.desc==='Square tubing 40×40');
      const cuts=TMC.wCuts((TMC.ws()||{}).jobId);
      return {len:bal.len,k:ks.length,kids:ks.map(k=>k.id),cuts:cuts.length};
    }""")
    ok(after['cuts']==0,'cut list record is gone after Admin deletes it %s'%after)
    ok(abs(after['len']-before['len'])<1e-9 and after['k']==before['k'] and after['kids']==before['kids'],
       'stock unchanged after Admin deletes a cut list (metres stay used): before %s after %s'%(before,after))
    # --- Base VER 15 folded in: popups/toasts at 360px stay on screen and never cover the bottom menu ---
    pg.set_viewport_size({'width':360,'height':740});pg.wait_for_timeout(200)
    MEAS="""(sel)=>{const nav=document.querySelector('nav.tabs');const nr=nav?nav.getBoundingClientRect():null;const el=document.querySelector(sel);if(!el)return {miss:1};const st=getComputedStyle(el);if(st.display==='none')return {miss:1};const r=el.getBoundingClientRect();
      const inside=r.left>=-1&&r.right<=innerWidth+1&&r.top>=-1&&r.bottom<=innerHeight+1;const over=nr?(r.bottom>nr.top+1&&!el.closest('.modal')):false;
      let wide=0;el.querySelectorAll('*').forEach(c=>{if(c.scrollWidth>c.clientWidth+1&&getComputedStyle(c).overflowX!=='auto'&&getComputedStyle(c).overflowX!=='scroll'&&c.clientWidth>0)wide++});return {inside,over,wide,r:[Math.round(r.left),Math.round(r.top),Math.round(r.right),Math.round(r.bottom)],nav:nr?Math.round(nr.top):null}}"""
    LONG={'en':'Saved. This is a long message to check the bottom menu stays free on a small phone.','fr':'Enregistré. Ceci est un long message pour vérifier que le menu du bas reste libre sur un petit téléphone.','ar':'تم الحفظ. هذه رسالة طويلة للتأكد من أن القائمة السفلية تبقى ظاهرة على هاتف صغير.','af':"Gestoor. Dit is 'n lang boodskap om te kyk dat die onderste kieslys vry bly op 'n klein foon."}
    for lang in ('en','fr','ar','af'):
        pg.select_option('#hLang',lang);pg.wait_for_timeout(200)
        pg.evaluate("m=>TMC.popupTest.toast(m)",LONG[lang]);pg.wait_for_timeout(100)
        m=pg.evaluate(MEAS,'#tmcToast')
        ok(not m.get('miss') and m['inside'] and not m['over'],'%s 360px: toast fully on screen and above the bottom menu %s'%(lang,m))
        pg.evaluate("()=>{const w=document.getElementById('tmcToast');if(w)w.style.display='none'}")
        pg.evaluate("()=>TMC.popupTest.nav()");pg.wait_for_timeout(100)
        m=pg.evaluate(MEAS,'#navAsk .card')
        ok(not m.get('miss') and m['inside'] and m['wide']==0,'%s 360px: confirm card fully on screen, no text spills %s'%(lang,m))
        pg.evaluate("()=>{const a=document.getElementById('navAsk');if(a)a.remove()}")
        th=pg.evaluate("()=>{const n=document.querySelector('nav.tabs');return {tabh:getComputedStyle(document.documentElement).getPropertyValue('--tabh').trim(),nav:n?n.offsetHeight:0,wrap:[...document.querySelectorAll('nav.tabs .tlab')].some(e=>e.getClientRects().length>1||e.offsetHeight>e.scrollHeight+2||e.getBoundingClientRect().height>parseFloat(getComputedStyle(e).fontSize)*2)}}")
        ok(th['tabh']==('%dpx'%(th['nav']+12)) and not th['wrap'],'%s: --tabh follows the real menu height and tab labels stay on one line %s'%(lang,th))
    pg.select_option('#hLang','en');pg.wait_for_timeout(150)
    b.close()
finally:
    for gproc in gas:gproc.terminate()
    srv.shutdown();shutil.rmtree(TMP,ignore_errors=True)
print('CUT LIST: %d passed, %d failed'%(P,F))
sys.exit(1 if F else 0)
