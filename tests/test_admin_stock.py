#!/usr/bin/env python3
"""Admin Add stock / Set count sample tests. Mock Sheet only. Nothing is published.
  python3 tests/test_admin_stock.py /path/to/workshop
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
TMP=tempfile.mkdtemp(prefix='wj-admin-stock-');GP,OP,WP=free(),free(),free()
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
OTHER='http://127.0.0.1:%d/other/'%WP
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
def stock(pg):
    pg.evaluate("(()=>{const w=TMC.ws();w.screen='list';w.jobId=null;w.mat=null})()")
    pg.click('nav [data-tab=work]');pg.wait_for_timeout(250)
    pg.click('#wjStock');pg.wait_for_timeout(250)
def demo_words(txt):
    low=txt.lower()
    return [w for w in ('sample only','queue example','example from food','exemple seulement','voorbeeld','queue an example','not connected') if w in low]
try:
  with sync_playwright() as pw:
    b=pw.chromium.launch(executable_path='/usr/bin/google-chrome' if os.path.exists('/usr/bin/google-chrome') else None,args=['--no-sandbox'])
    def ctx():
        c=b.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True,service_workers='allow')
        c.on('dialog',lambda d:d.accept())
        return c
    x=ctx();pg=x.new_page();errs=[];pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.goto(SHOP);pg.wait_for_selector('#fName')
    name(pg,'Johan Kirsten');setpin(pg,'2468');synced(pg)
    stock(pg)
    box=pg.inner_text('#wjStockBox')
    ok(pg.locator('#wjAddStock').count()==1 and 'Add stock' in box,'Admin sees the Add stock button')
    ok(not demo_words(box),'stock screen has no example/demo wording: %s'%demo_words(box))
    ok('No stock yet' in pg.inner_text('#wjOnHand'),'empty on-hand says No stock yet')
    # Add Square tubing 10 pieces Steel
    pg.click('#wjAddStock');pg.wait_for_timeout(250)
    ok(pg.locator('#wjAddBox').count()==1 and pg.locator('#wjSaveAdd').count()==1,'Add stock form opened')
    pg.fill('#wjItem','Square tubing');pg.click('#wjAdTysteel');pg.wait_for_timeout(150)
    pg.fill('#wjAddQty','10');pg.click('#wjAdUnpiece');pg.wait_for_timeout(100)
    pg.click('#wjSaveAdd');pg.wait_for_timeout(500)
    ok(pg.locator('#wjStockBox').count()==1 and pg.locator('#wjAddBox').count()==0,'Save stock closes onto the stock screen')
    hold=pg.inner_text('#wjOnHand')
    ok('Square tubing' in hold and '10 pieces' in hold,'on-hand shows Square tubing 10 pieces: %s'%hold.replace('\n',' / '))
    ok(pg.evaluate("TMC.wBal('steel','Square tubing').qty")==10,'wBal Square tubing is 10')
    # Set Angle iron to 0
    pg.click('#wjAddStock');pg.wait_for_timeout(200)
    pg.fill('#wjItem','Angle iron');pg.fill('#wjAddQty','1');pg.click('#wjSaveAdd');pg.wait_for_timeout(400)
    # we need set-to-0, so open Set count on Angle iron (or if add created 1, set to 0)
    # Better: use Set count only — if Angle iron isn't there yet, we can still set it by going through set after a 0-qty... Set is on a row.
    # So add was 1, now set to 0.
    pg.locator('.wjSet',has_text='Set count').nth(0)  # may be either row
    row=pg.locator('.wjHold',has_text='Angle iron')
    ok(row.count()==1,'Angle iron row is on the stock list after add')
    row.locator('.wjSet').click();pg.wait_for_timeout(250)
    ok(pg.locator('#wjSetBox').count()==1,'Set count form opened')
    pg.fill('#wjAddQty','0');pg.click('#wjSaveSet');pg.wait_for_timeout(500)
    ok(pg.locator('#wjStockBox').count()==1,'Save count closes onto the stock screen')
    hold=pg.inner_text('#wjOnHand')
    ang=pg.locator('#wjOnHand .wjHold',has_text='Angle iron').inner_text()
    sq=pg.locator('#wjOnHand .wjHold',has_text='Square tubing').inner_text()
    ok('0 pieces' in ang and 'Angle iron' in ang,'Angle iron shows 0 pieces: %s'%ang.replace('\n',' / '))
    ok('10 pieces' in sq and 'Square tubing' in sq,'Square tubing still 10 pieces: %s'%sq.replace('\n',' / '))
    ok(pg.evaluate("TMC.wBal('steel','Angle iron').qty")==0,'wBal Angle iron is 0')
    ok(pg.evaluate("TMC.wBal('steel','Square tubing').qty")==10,'wBal Square tubing still 10 after set')
    synced(pg)
    kinds=pg.evaluate("TMC.all('k').map(k=>({dir:k.dir,desc:k.desc,src:k.sourceApp}))")
    ok(any(k['dir']=='in' and k['desc']=='Square tubing' and k['src']=='admin' for k in kinds)
       and any(k['dir']=='set' and k['desc']=='Angle iron' and k['src']=='admin' for k in kinds),
       'admin add/set used ordinary k records (in + set), no new kind')
    # Job can use 10, not 11
    pg.click('#view .navBack');pg.wait_for_timeout(250)
    pg.click('#wjNew');pg.wait_for_timeout(200)
    pg.fill('#wjName','Gate');pg.click('#wjSave');pg.wait_for_timeout(400)
    pg.locator('.wjOpen',has_text='Gate').first.click();pg.wait_for_timeout(250)
    pg.click('#wjAddSteel');pg.wait_for_timeout(200)
    pg.fill('#wjDesc','Square tubing');pg.fill('#wjPcs','11');pg.click('#wjSaveM');pg.wait_for_timeout(300)
    ok(pg.locator('#wjMat').count()==1 and 'Not enough' in pg.inner_text('#wjErr'),'job cannot take 11 Square tubing')
    ok(pg.evaluate("TMC.wBal('steel','Square tubing').qty")==10,'failed 11 does not deduct stock')
    pg.click('#view .navBack');pg.wait_for_timeout(200)
    if pg.locator('#navAsk').count():pg.click('#navYes');pg.wait_for_timeout(200)
    pg.click('#wjAddSteel');pg.wait_for_timeout(200)
    pg.fill('#wjDesc','Square tubing');pg.fill('#wjPcs','10');pg.click('#wjSaveM');pg.wait_for_timeout(400)
    ok(pg.locator('#wjJob').count()==1,'job can use exactly 10 Square tubing')
    ok(pg.evaluate("TMC.wBal('steel','Square tubing').qty")==0,'on-hand dropped to 0 after using 10')
    # put 10 back so reinstall can still show the items clearly — already used. Balances should restore.
    # Reinstall Admin
    n0=len(users(GP));synced(pg)
    y=ctx();w=y.new_page();w.goto(SHOP);w.wait_for_selector('#fName',timeout=15000)
    name(w,'JA Kirsten');ok(w.locator('#fPin').count()==1 and w.locator('#fPin2').count()==0,'reinstall Admin goes to PIN, not a new setup')
    pin(w,'2468');synced(w)
    ok(w.evaluate("TMC.me()&&TMC.me().admin&&TMC.me().name")=='JA Kirsten','reinstalled Admin is the same person')
    ok(len(users(GP))==n0,'reinstall did not create another user')
    stock(w)
    ok(w.locator('#wjAddStock').count()==1,'reinstalled Admin still sees Add stock')
    ok(w.evaluate("TMC.wBal('steel','Square tubing').qty")==0 and w.evaluate("TMC.wBal('steel','Angle iron').qty")==0,'reinstall pulled Square tubing and Angle iron counts back')
    ok('Square tubing' in w.inner_text('#wjOnHand') and 'Angle iron' in w.inner_text('#wjOnHand'),'reinstall shows both stock rows')
    # Staff: no Add stock / Set count
    z=ctx();g=z.new_page();g.goto(SHOP);g.wait_for_selector('#fName')
    name(g,'Pieter');ok('approval' in (g.inner_text('.card') or '').lower(),'staff waits for approval')
    synced(pg);pg.click('nav [data-tab=users]');pg.wait_for_timeout(400)
    pg.locator('.ulr',has_text='Pieter').locator('[data-ua=approve]').click();pg.wait_for_timeout(800)
    g.click('#fCheck');g.wait_for_selector('#fPin2',timeout=8000);setpin(g,'1357');synced(g)
    ok(g.evaluate("TMC.me()&&!TMC.me().admin"),'Pieter is not Admin')
    stock(g)
    gbox=g.inner_text('#wjStockBox')
    ok(g.locator('#wjAddStock').count()==0 and 'Add stock' not in gbox,'non-Admin does not see the Add stock button')
    ok(g.locator('.wjSet').count()==0 and g.locator('#wjAddStock').count()==0,'non-Admin does not see a Set count button')
    ok('Square tubing' in g.inner_text('#wjOnHand') and 'Angle iron' in g.inner_text('#wjOnHand'),'staff can see on-hand stock')
    ok(not demo_words(gbox),'staff stock screen has no example/demo wording')
    # no data mixing
    o=ctx();op=o.new_page();op.goto(OTHER);op.wait_for_selector('#fName')
    name(op,'Johan Kirsten');setpin(op,'9753');synced(op)
    op.evaluate("TMC.put('k','otherk',{id:'otherk',dir:'in',mat:'steel',desc:'OTHER APP TUBING',qty:99,len:0,unit:'piece',qThou:99000,lThou:0,at:new Date().toISOString(),by:'JA Kirsten',sourceApp:'admin'})")
    op.wait_for_timeout(900);synced(op);synced(pg)
    shop_keys=pg.evaluate("Object.keys(localStorage)")
    oth_keys=op.evaluate("Object.keys(localStorage)")
    ok(all(k.startswith('tmcworkshop_') for k in shop_keys),'workshop storage keys stay on tmcworkshop_')
    ok(all(k.startswith('tmcother_') for k in oth_keys) and not any(k.startswith('tmcworkshop_') for k in oth_keys),'other app has no workshop keys')
    shop_dump=json.dumps(dump(GP));oth_dump=json.dumps(dump(OP))
    ok('Square tubing' in shop_dump and 'OTHER APP TUBING' not in shop_dump,'workshop Sheet has workshop stock only')
    ok('OTHER APP TUBING' in oth_dump and 'Square tubing' not in oth_dump,'other Sheet does not receive workshop stock')
    sw=open(os.path.join(TMP,'shop','sw.js'),encoding='utf-8').read()
    ok('APP="tmcworkshop"' in sw and '-v4' in sw,'sample cache name is tmcworkshop-v4')
    ok('tmcother-v' in open(os.path.join(TMP,'other','sw.js'),encoding='utf-8').read(),'other app cache name differs')
    ok(not errs,'no page errors %s'%errs[:3])
    b.close()
finally:
    for g_ in gas:
        try:g_.kill()
        except Exception:pass
    try:srv.shutdown()
    except Exception:pass
    shutil.rmtree(TMP,ignore_errors=True)
print('\nADMIN STOCK: %d passed, %d failed'%(P,F));sys.exit(1 if F else 0)
