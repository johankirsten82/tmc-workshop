#!/usr/bin/env python3
"""SHOTS v1.7.1 (360px, en/fr/ar/af) of the add-material screen into screenshots/v1.7.1/.
  (1) typing 'squ' finds a previously entered 'Square Tubing' 40×40×6000 in the drop-down
  (2) that item selected: name and H/W/L greyed
  Demo data only (empty stock; the item was entered earlier). Nothing published.
  python3 tests/shots_v171.py /path/to/workshop
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
TMP=tempfile.mkdtemp(prefix='wj-v171shots-');GP,WP=free(),free()
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
OUT=os.path.join(APP,'screenshots','v1.7.1');os.makedirs(OUT,exist_ok=True)
SH=[]
ITEM='Square Tubing'
def shot(pg,n,l):
    p=os.path.join(OUT,'%s_%s.png'%(n,l))
    pg.screenshot(path=p);SH.append(p)
def open_add(pg):
    pg.click('nav [data-tab=work]');pg.wait_for_timeout(150)
    pg.evaluate("""()=>{const w=TMC.ws();w.screen='job';w.jobId='j171';TMC.render()}""")
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
    # empty Workshop stock; the item was typed earlier and kept (synced m record)
    pg.evaluate("""item=>{const at=new Date().toISOString();
      TMC.put('j','j171',{id:'j171',name:'Ben Bed',type:'build',by:'JA Kirsten',at:at,example:0});
      TMC.put('m','m-sq',{id:'m-sq',jobId:'j171',mat:'steel',desc:item,qty:1,len:6,unit:'m',usedMm:1500,hMm:40,wMm:40,lMm:6000,new:1,by:'JA Kirsten',at:at,example:0})}""",ITEM)
    pg.evaluate("TMC.syncNow()");pg.wait_for_timeout(600)
    for l in ('en','fr','ar','af'):
        pg.select_option('#hLang',l);pg.wait_for_timeout(250)
        open_add(pg)
        name=pg.locator('.wjBuyName').first
        name.click();name.fill('squ');pg.wait_for_timeout(200)
        pg.evaluate("""()=>{const i=document.querySelector('.wjBuyName');i.focus();i.dispatchEvent(new Event('input',{bubbles:true}));}""")
        pg.wait_for_timeout(200)
        if pg.locator('.sug').count():pg.locator('.sug').first.scroll_into_view_if_needed()
        pg.evaluate("scrollTo(0,0)");pg.wait_for_timeout(120)
        shot(pg,'1_dropdown',l)
        pg.locator('.sug div[data-n]:not(.wjSugNew)',has_text=ITEM).first.click();pg.wait_for_timeout(200)
        row=pg.locator('.wjBuy[data-r="0"]')
        row.scroll_into_view_if_needed();pg.wait_for_timeout(150)
        shot(pg,'2_selected',l)
        leave(pg)
    b.close()
finally:
    try:gas.terminate()
    except Exception:pass
    srv.shutdown();shutil.rmtree(TMP,ignore_errors=True)
print('SHOTS',len(SH));[print(p) for p in SH]
