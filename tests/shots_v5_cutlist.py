#!/usr/bin/env python3
"""360px EN/AR screenshots for Workshop v5 cut list + Assets. Sample only."""
import json,os,re,shutil,socket,subprocess,tempfile,threading
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from functools import partial
from playwright.sync_api import sync_playwright
APP=os.path.abspath(__file__).rsplit('/tests/',1)[0]
OUT=os.path.join(APP,'screenshots')
os.makedirs(OUT,exist_ok=True)
TMP=tempfile.mkdtemp(prefix='wshots-v5-')
shutil.copytree(APP,os.path.join(TMP,'app'),ignore=shutil.ignore_patterns('tests','.git','uploads','screenshots','archive'))
def free():
    s=socket.socket();s.bind(('127.0.0.1',0));p=s.getsockname()[1];s.close();return p
GP,WP=free(),free()
gas=subprocess.Popen(['node',os.path.join(APP,'tests','gas_server.js'),str(GP),'-'],stdout=subprocess.PIPE,env=dict(os.environ,GAS_FILE=os.path.join(APP,'sync','Code.gs')))
gas.stdout.readline()
ip=os.path.join(TMP,'app','index.html');src=open(ip,encoding='utf-8').read()
C=json.loads(re.search(r'/\*CONFIG\*/(.*?)/\*END\*/',src,re.S).group(1))
C['SYNC_URL']='http://127.0.0.1:%d/exec'%GP;C['SYNC_CODE']=''
src=re.sub(r'/\*CONFIG\*/.*?/\*END\*/','/*CONFIG*/'+json.dumps(C,ensure_ascii=False)+'/*END*/',src,flags=re.S)
open(ip,'w',encoding='utf-8').write(src)
class Q(SimpleHTTPRequestHandler):
    def log_message(self,*a):pass
srv=ThreadingHTTPServer(('127.0.0.1',WP),partial(Q,directory=os.path.join(TMP,'app')))
threading.Thread(target=srv.serve_forever,daemon=True).start()
URL='http://127.0.0.1:%d/'%WP
CHROME='/usr/bin/google-chrome' if os.path.exists('/usr/bin/google-chrome') else None
SHOTS=[]
def shot(pg,name):
    path=os.path.join(OUT,name)
    pg.evaluate('TMC.fitTabs&&TMC.fitTabs()')
    pg.wait_for_timeout(150)
    pg.screenshot(path=path)
    SHOTS.append(path)
    print('wrote',path, 'tab', pg.evaluate("()=>(document.querySelector('nav .on')||{}).dataset.tab"), 'screen', pg.evaluate("()=>(TMC.ws()||{}).screen"))
def go_lang(pg,lang):
    pg.select_option('#hLang',lang);pg.wait_for_timeout(250)
def work_tab(pg):
    pg.click('nav [data-tab=work]');pg.wait_for_timeout(250)
def open_cut(pg):
    work_tab(pg)
    pg.evaluate("""()=>{
      const WS=TMC.ws();
      WS.jobId='jbeds';WS.screen='cut';
      WS.cutDesc='Square tubing 40×40';
      WS.cutRows=[{qty:'4',len:'1',unit:'m'},{qty:'5',len:'300',unit:'mm'}];
      WS.cutUnits='2';WS.cutItem='Bed';WS.cutPad={row:1,field:'len'};
      TMC.render();
    }""")
    pg.wait_for_timeout(250)
try:
    with sync_playwright() as pw:
        b=pw.chromium.launch(executable_path=CHROME,args=['--no-sandbox'])
        ctx=b.new_context(viewport={'width':360,'height':844},device_scale_factor=3,is_mobile=True,has_touch=True,locale='en-US')
        ctx.on('dialog',lambda d:d.accept())
        pg=ctx.new_page()
        pg.goto(URL)
        pg.wait_for_selector('#langSel')
        pg.fill('#fName','Johan Kirsten');pg.click('#fName2');pg.wait_for_selector('#fPin2')
        pg.fill('#fPin','2468');pg.fill('#fPin2','2468');pg.click('#fSet');pg.wait_for_selector('header')
        pg.evaluate('TMC.syncNow()');pg.wait_for_timeout(600)
        pg.evaluate("""()=>{
          const at=new Date().toISOString();
          TMC.put('k','kin-sq-m',{id:'kin-sq-m',ref:'',dir:'in',mat:'steel',desc:'Square tubing 40×40',qty:0,len:18,unit:'m',qThou:0,lThou:18000,at:at,by:'JA Kirsten',jobId:'',sourceApp:'admin',note:''});
          TMC.put('sl','sl-square-tubing-40x40',{id:'sl-square-tubing-40x40',desc:'Square tubing 40×40',stockLenMm:6000,at:at,by:'JA Kirsten'});
          TMC.put('j','jbeds',{id:'jbeds',name:'Ward beds',type:'build',item:'Bed',units:2,size:'',by:'JA Kirsten',at:at});
          TMC.syncNow();
        }""")
        pg.wait_for_timeout(500)
        work_tab(pg)
        LANGS=(('en','en'),('fr','fr'),('ar','ar'),('af','af'))
        for lang,prefix in LANGS:
            go_lang(pg,lang)
            open_cut(pg)
            # pad shot (EN/AR only — unchanged this round)
            if prefix in ('en','ar'):
                pg.evaluate("""()=>{
                  const rows=document.getElementById('wjCutRows');
                  if(rows) rows.scrollIntoView({block:'start'});
                  const add=document.getElementById('wjAddRow'), pad=document.getElementById('wjPadWrap');
                  if(add&&pad){
                    const ar=add.getBoundingClientRect(), pr=pad.getBoundingClientRect();
                    if(ar.bottom>pr.top-8){
                      const need=ar.bottom-(pr.top-8);
                      const first=document.querySelector('.wjCutRow');
                      if(!first||first.getBoundingClientRect().top-need>=80) scrollBy(0,need);
                    }
                  }
                }""")
                pg.wait_for_timeout(180)
                shot(pg,'%s-cut-pad-360.png'%prefix)
            # totals: headline (total taken off stock) + per item + lengths above the pad
            pg.evaluate("()=>{const s=document.getElementById('wjCutSum');if(s)s.scrollIntoView({block:'start'})}")
            pg.wait_for_timeout(180)
            shot(pg,'%s-cut-total-360.png'%prefix)
        # save records once, then shoot stock / assets / forms
        go_lang(pg,'en')
        open_cut(pg)
        pg.evaluate("""()=>{
          const at=new Date().toISOString();
          const id='c-demo';
          TMC.put('c',id,{id:id,jobId:'jbeds',desc:'Square tubing 40×40',mat:'steel',
            rows:[{qty:4,lenMm:1000,unit:'m',len:1},{qty:5,lenMm:300,unit:'mm',len:300}],
            perMm:5500,units:2,totalMm:11000,stockLenMm:6000,bars:2,item:'Bed',size:'',by:'JA Kirsten',at:at});
          TMC.put('k','kout'+id,{id:'kout'+id,ref:'',dir:'out',mat:'steel',desc:'Square tubing 40×40',qty:0,len:11,unit:'m',qThou:0,lThou:11000,at:at,by:'JA Kirsten',jobId:'jbeds',cutId:id,sourceApp:'cut'});
          TMC.put('fa','fa-jbeds',{id:'fa-jbeds',jobId:'jbeds',name:'Bed',qty:2,size:'',jobName:'Ward beds',at:at,by:'JA Kirsten',status:'waiting',builtBefore:0,camp:'10 Alfa',sourceApp:'tmcworkshop'});
          TMC.put('fa','fa-btable',{id:'fa-btable',jobId:'',name:'Table',qty:3,size:'old stock',jobName:'',at:at,by:'JA Kirsten',status:'waiting',builtBefore:1,camp:'10 Alfa',sourceApp:'tmcworkshop'});
          TMC.syncNow();
        }""")
        pg.wait_for_timeout(400)
        def open_job():
            work_tab(pg)
            pg.evaluate("()=>{const w=TMC.ws();w.screen='job';w.jobId='jbeds';TMC.render()}")
            pg.wait_for_timeout(250)
        # Admin delete-cut-list confirm in EN/FR/AR/AF (No each time so the list stays)
        for lang,prefix in LANGS:
            go_lang(pg,lang)
            open_job()
            pg.evaluate("()=>{const el=document.getElementById('wjDelCutAsk');if(el)el.remove()}")
            pg.locator('.wjDelCut').first.click()
            pg.wait_for_selector('#wjDelCutAsk',timeout=3000)
            pg.wait_for_timeout(150)
            shot(pg,'%s-del-cut-confirm-360.png'%prefix)
            pg.click('#wjDelCutNo');pg.wait_for_timeout(150)
        # Confirm delete once, then stock after delete (metres stay used: 7 m on hand, 11 m still out)
        go_lang(pg,'en');open_job()
        pg.locator('.wjDelCut').first.click();pg.wait_for_selector('#wjDelCutAsk')
        pg.click('#wjDelCutYes');pg.wait_for_timeout(400)
        for lang,prefix in LANGS:
            go_lang(pg,lang)
            work_tab(pg)
            pg.evaluate("()=>{TMC.ws().screen='stock';TMC.render()}")
            pg.wait_for_timeout(250)
            pg.evaluate("""()=>{
              const hand=document.getElementById('wjOnHand');
              const last=document.querySelector('#wjAudit .wjAud:last-child')||document.getElementById('wjAudit');
              if(hand) hand.scrollIntoView({block:'start'});
              if(last){ last.style.scrollMarginBottom='80px'; last.scrollIntoView({block:'end'}); }
            }""")
            pg.wait_for_timeout(150)
            shot(pg,'%s-stock-after-delete-360.png'%prefix)
        # existing stock-after (same 7 m / 11 m used) and assets / built-before, EN/AR
        for lang,prefix in (('en','en'),('ar','ar')):
            go_lang(pg,lang)
            work_tab(pg)
            # also a saved-cut totals shot? already have form totals. stock after:
            pg.evaluate("()=>{TMC.ws().screen='stock';TMC.render()}")
            pg.wait_for_timeout(250)
            # keep On hand in view and bring the 11 m 'used on a job' line above the tab bar
            pg.evaluate("""()=>{
              const hand=document.getElementById('wjOnHand');
              const last=document.querySelector('#wjAudit .wjAud:last-child')||document.getElementById('wjAudit');
              if(hand) hand.scrollIntoView({block:'start'});
              if(last){ last.style.scrollMarginBottom='80px'; last.scrollIntoView({block:'end'}); }
            }""")
            pg.wait_for_timeout(150)
            shot(pg,'%s-stock-after-360.png'%prefix)
            # assets list with both items
            pg.evaluate("()=>{TMC.ws().screen='assets';TMC.render()}");pg.wait_for_timeout(200);pg.evaluate('scrollTo(0,0)');pg.wait_for_timeout(100)
            shot(pg,'%s-assets-360.png'%prefix)
            pg.evaluate("()=>{TMC.ws().screen='before';TMC.render()}");pg.wait_for_timeout(200);pg.evaluate('scrollTo(0,0)');pg.wait_for_timeout(100)
            shot(pg,'%s-built-before-form-360.png'%prefix)
            pg.evaluate("()=>{TMC.ws().screen='assets';TMC.render()}");pg.wait_for_timeout(200);pg.evaluate('scrollTo(0,0)');pg.wait_for_timeout(100)
            shot(pg,'%s-built-before-list-360.png'%prefix)
        b.close()
finally:
    gas.kill();srv.shutdown()
print('SHOTS',SHOTS)
