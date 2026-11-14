#!/usr/bin/env python3
"""SHOTS v1.7.0 (360px, en/fr/ar/af) of the add-material screen into screenshots/v1.7.0/.
  (1) name typed, drop-down of matches open with Add new item
  (2) stock item selected: greyed name/H/W/L, Qty + Length used filled
  (3) new item: editable name/H/W/L filled
  Demo data only, nothing published.
  python3 tests/shots_v170.py /path/to/workshop
"""
import os,sys,re,json,shutil,socket,subprocess,tempfile,threading
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from functools import partial
from playwright.sync_api import sync_playwright
APP=os.path.abspath(sys.argv[1] if len(sys.argv)>1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
def free():
    s=socket.socket();s.bind(('127.0.0.1',0));p=s.getsockname()[1];s.close();return p
HERE=os.path.dirname(os.path.abspath(__file__));BASE=os.path.dirname(HERE)
sys.path.insert(0,os.path.join(BASE,'tools'));import apply_config
TMP=tempfile.mkdtemp(prefix='wj-v170shots-');GP,WP=free(),free()
def prep(sub,app_id,port,cp=None):
    d=os.path.join(TMP,sub)
    shutil.copytree(APP,d,ignore=shutil.ignore_patterns('tests','shots*','.git','*.zip','archive','screenshots'))
    ip=os.path.join(d,'index.html');s=open(ip,encoding='utf-8').read()
    C=json.loads(re.search(r'/\*CONFIG\*/(.*?)/\*END\*/',s,re.S).group(1))
    C.update(APP_ID=app_id,SYNC_URL='http://127.0.0.1:%d/exec'%port,SYNC_CODE='',SHARE_URL='')
    if cp:C['CACHE_PREFIX']=cp
    s=re.sub(r'/\*CONFIG\*/.*?/\*END\*/','/*CONFIG*/'+json.dumps(C,ensure_ascii=False,indent=1)+'/*END*/',s,flags=re.S)
    open(ip,'w',encoding='utf-8').write(s);apply_config.main(d);return C
prep('shop','tmcworkshop',GP,'tmcworkshop')
gas=subprocess.Popen(['node',os.path.join(APP,'tests','gas_server.js'),str(GP),'-'],stdout=subprocess.PIPE,env=dict(os.environ,GAS_FILE=os.path.join(APP,'sync','Code.gs')))
gas.stdout.readline()
class Q(SimpleHTTPRequestHandler):
    def log_message(self,*a):pass
srv=ThreadingHTTPServer(('127.0.0.1',WP),partial(Q,directory=TMP));threading.Thread(target=srv.serve_forever,daemon=True).start()
SHOP='http://127.0.0.1:%d/shop/'%WP
CHROME='/usr/bin/google-chrome' if os.path.exists('/usr/bin/google-chrome') else None
OUT=os.path.join(APP,'screenshots','v1.7.0');os.makedirs(OUT,exist_ok=True)
SH=[]
ITEM='Square Tubing 40 x 40 x 6m'
NEW='Hex bar 25 x 25'
def shot(pg,n,l):
    p=os.path.join(OUT,'%s_%s.png'%(n,l))
    pg.screenshot(path=p);SH.append(p)
def open_add(pg):
    pg.click('nav [data-tab=work]');pg.wait_for_timeout(150)
    pg.evaluate("""()=>{const w=TMC.ws();w.screen='job';w.jobId='j170';TMC.render()}""")
    pg.wait_for_timeout(200)
    pg.click('#wjAddSteel');pg.wait_for_timeout(250)
def leave(pg):
    pg.click('#view .navBack');pg.wait_for_timeout(200)
    if pg.locator('#navAsk').count():pg.click('#navYes');pg.wait_for_timeout(200)
try:
  with sync_playwright() as pw:
    b=pw.chromium.launch(executable_path=CHROME,args=['--no-sandbox'])
    c=b.new_context(viewport={'width':360,'height':780},device_scale_factor=3,is_mobile=True,has_touch=True)
    c.on('dialog',lambda d:d.accept())
    pg=c.new_page();pg.goto(SHOP);pg.wait_for_selector('#langSel')
    pg.fill('#fName','Johan Kirsten');pg.click('#fName2');pg.wait_for_selector('#fPin2')
    pg.fill('#fPin','2468');pg.fill('#fPin2','2468');pg.click('#fSet');pg.wait_for_selector('header',timeout=8000)
    pg.evaluate("""item=>{const at=new Date().toISOString();
      TMC.put('k','kin-sq',{id:'kin-sq',ref:'',dir:'in',mat:'steel',desc:item,qty:0,len:24,unit:'m',qThou:0,lThou:24000,at:at,by:'JA Kirsten',jobId:'',sourceApp:'admin',note:''});
      TMC.put('k','kin-ang',{id:'kin-ang',ref:'',dir:'in',mat:'steel',desc:'Angle iron 50 x 50 x 6m',qty:0,len:18,unit:'m',qThou:0,lThou:18000,at:at,by:'JA Kirsten',jobId:'',sourceApp:'admin',note:''});
      TMC.put('k','kin-flat',{id:'kin-flat',ref:'',dir:'in',mat:'steel',desc:'Flat bar 30 mm',qty:0,len:12,unit:'m',qThou:0,lThou:12000,at:at,by:'JA Kirsten',jobId:'',sourceApp:'admin',note:''});
      TMC.put('j','j170',{id:'j170',name:'Ben Bed',type:'build',by:'JA Kirsten',at:at,example:0})}""",ITEM)
    pg.evaluate("TMC.syncNow()");pg.wait_for_timeout(600)
    for l in ('en','fr','ar','af'):
        pg.select_option('#hLang',l);pg.wait_for_timeout(250)
        open_add(pg)
        # (1) type a query that matches two items, keep the drop-down open
        name=pg.locator('.wjBuyName').first
        name.click();name.fill('x');pg.wait_for_timeout(200)
        pg.evaluate("""()=>{const i=document.querySelector('.wjBuyName');i.focus();i.dispatchEvent(new Event('input',{bubbles:true}));}""")
        pg.wait_for_timeout(200)
        if pg.locator('.sug').count():pg.locator('.sug').first.scroll_into_view_if_needed()
        pg.evaluate("scrollTo(0,0)");pg.wait_for_timeout(120)
        shot(pg,'1_dropdown',l)
        # (2) select stock item, fill qty + length used
        pg.locator('.sug div[data-n]:not(.wjSugNew)',has_text=ITEM).first.click();pg.wait_for_timeout(200)
        row=pg.locator('.wjBuy[data-r="0"]')
        row.locator('.wjBuyQty').fill('2')
        row.locator('.wjBuyUsed').fill('1500')
        row.scroll_into_view_if_needed();pg.wait_for_timeout(150)
        shot(pg,'2_stock_selected',l)
        # (3) add a new item row
        pg.click('#wjAddMatRow');pg.wait_for_timeout(150)
        row=pg.locator('.wjBuy[data-r="1"]')
        row.locator('.wjBuyName').click();row.locator('.wjBuyName').fill(NEW);pg.wait_for_timeout(200)
        row.locator('.wjSugNew').click();pg.wait_for_timeout(200)
        row=pg.locator('.wjBuy[data-r="1"]')
        row.locator('.wjBuyH').fill('25');row.locator('.wjBuyW').fill('25');row.locator('.wjBuyL').fill('4000')
        row.locator('.wjBuyQty').fill('1');row.locator('.wjBuyUsed').fill('1200')
        row.scroll_into_view_if_needed();pg.wait_for_timeout(150)
        shot(pg,'3_new_item',l)
        leave(pg)
    b.close()
finally:
    try:gas.terminate()
    except Exception:pass
    srv.shutdown();shutil.rmtree(TMP,ignore_errors=True)
print('SHOTS',len(SH));[print(p) for p in SH]
