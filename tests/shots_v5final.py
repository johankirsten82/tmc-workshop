#!/usr/bin/env python3
"""Workshop v5 FINAL 360px screenshots, EN/FR/AR/AF, into screenshots/v5final/. Sample only, nothing published."""
import json,os,re,shutil,socket,subprocess,tempfile,threading
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from functools import partial
from playwright.sync_api import sync_playwright
APP=os.path.abspath(__file__).rsplit('/tests/',1)[0]
OUT=os.path.join(APP,'screenshots','v5final')
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
ONLY=[x for x in os.environ.get('ONLY','').split(',') if x]
def shot(pg,name):
    if ONLY and name not in ONLY:return
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

LANGS=('en','fr','ar','af')
TOAST={'en':'✅ Saved','fr':'✅ Enregistré','ar':'✅ تم الحفظ','af':'✅ Gestoor'}
def scroll_pad(pg):
    pg.evaluate("""()=>{const rows=document.getElementById('wjCutRows');if(rows)rows.scrollIntoView({block:'start'});
      const add=document.getElementById('wjAddRow'),pad=document.getElementById('wjPadWrap');
      if(add&&pad){const ar=add.getBoundingClientRect(),pr=pad.getBoundingClientRect();if(ar.bottom>pr.top-8){const need=ar.bottom-(pr.top-8);const first=document.querySelector('.wjCutRow');if(!first||first.getBoundingClientRect().top-need>=80)scrollBy(0,need)}}}""")
    pg.wait_for_timeout(180)
def scr(pg,screen):
    work_tab(pg);pg.evaluate("s=>{const w=TMC.ws();w.screen=s;if(s==='job')w.jobId='jbeds';TMC.render()}",screen);pg.wait_for_timeout(250)
def stock_view(pg):
    scr(pg,'stock')
    pg.evaluate("""()=>{const hand=document.getElementById('wjOnHand');const last=document.querySelector('#wjAudit .wjAud:last-child')||document.getElementById('wjAudit');
      if(hand)hand.scrollIntoView({block:'start'});if(last){last.style.scrollMarginBottom='80px';last.scrollIntoView({block:'end'})}}""")
    pg.wait_for_timeout(150)
try:
    with sync_playwright() as pw:
        b=pw.chromium.launch(executable_path=CHROME,args=['--no-sandbox'])
        ctx=b.new_context(viewport={'width':360,'height':780},device_scale_factor=3,is_mobile=True,has_touch=True,locale='en-US')
        ctx.on('dialog',lambda d:d.accept())
        pg=ctx.new_page()
        pg.goto(URL);pg.wait_for_selector('#langSel')
        pg.fill('#fName','Johan Kirsten');pg.click('#fName2');pg.wait_for_selector('#fPin2')
        pg.fill('#fPin','2468');pg.fill('#fPin2','2468');pg.click('#fSet');pg.wait_for_selector('header')
        pg.evaluate('TMC.syncNow()');pg.wait_for_timeout(600)
        pg.evaluate("""()=>{const at=new Date().toISOString();
          TMC.put('k','kin-sq-m',{id:'kin-sq-m',ref:'',dir:'in',mat:'steel',desc:'Square tubing 40×40',qty:0,len:18,unit:'m',qThou:0,lThou:18000,at:at,by:'JA Kirsten',jobId:'',sourceApp:'admin',note:''});
          TMC.put('sl','sl-square-tubing-40x40',{id:'sl-square-tubing-40x40',desc:'Square tubing 40×40',stockLenMm:6000,at:at,by:'JA Kirsten'});
          TMC.put('j','jbeds',{id:'jbeds',name:'Ward beds',type:'build',item:'Bed',units:2,size:'',by:'JA Kirsten',at:at});TMC.syncNow()}""")
        pg.wait_for_timeout(500)
        # 1-2: cut pad + cut total (headline fix)
        for lang in LANGS:
            go_lang(pg,lang);open_cut(pg);scroll_pad(pg);shot(pg,'%s-cut-pad-360.png'%lang)
            pg.evaluate("()=>{const s=document.getElementById('wjCutSum');if(s)s.scrollIntoView({block:'start'})}");pg.wait_for_timeout(180)
            shot(pg,'%s-cut-total-360.png'%lang)
            # popup: confirm dialog (leave without saving?) over the cut form
            pg.evaluate("()=>TMC.popupTest.nav()");pg.wait_for_selector('#navAsk');pg.wait_for_timeout(150)
            shot(pg,'%s-popup-confirm-360.png'%lang)
            pg.evaluate("()=>{const a=document.getElementById('navAsk');if(a)a.remove()}")
        # save the cut list for real (Save button) so stock really drops 11 m
        go_lang(pg,'en');open_cut(pg)
        pg.evaluate("()=>{const u=document.getElementById('wjCutUnits');if(u)u.value='2';const i=document.getElementById('wjCutItem');if(i)i.value='Bed'}")
        pg.click('#wjSaveCut');pg.wait_for_timeout(500)
        print('after save', pg.evaluate("TMC.wBal('steel','Square tubing 40×40')"), 'cuts', pg.evaluate("TMC.wCuts('jbeds').length"))
        # 3: stock after + popup save toast over stock
        for lang in LANGS:
            go_lang(pg,lang);stock_view(pg);shot(pg,'%s-stock-after-360.png'%lang)
            pg.evaluate("m=>TMC.popupTest.toast(m)",TOAST[lang]);pg.wait_for_timeout(150)
            shot(pg,'%s-popup-toast-360.png'%lang)
            pg.evaluate("()=>{const w=document.getElementById('tmcToast');if(w)w.style.display='none'}")
        # 4: delete-cut-list confirm (No each time)
        for lang in LANGS:
            go_lang(pg,lang);scr(pg,'job')
            pg.evaluate("()=>{const el=document.getElementById('wjDelCutAsk');if(el)el.remove()}")
            pg.locator('.wjDelCut').first.click();pg.wait_for_selector('#wjDelCutAsk',timeout=3000);pg.wait_for_timeout(150)
            shot(pg,'%s-del-cut-confirm-360.png'%lang)
            pg.click('#wjDelCutNo');pg.wait_for_timeout(150)
        go_lang(pg,'en');scr(pg,'job')
        pg.locator('.wjDelCut').first.click();pg.wait_for_selector('#wjDelCutAsk');pg.click('#wjDelCutYes');pg.wait_for_timeout(400)
        print('after delete', pg.evaluate("TMC.wBal('steel','Square tubing 40×40')"), 'cuts', pg.evaluate("TMC.wCuts('jbeds').length"))
        # 5: stock after delete
        for lang in LANGS:
            go_lang(pg,lang);stock_view(pg);shot(pg,'%s-stock-after-delete-360.png'%lang)
        # 6: assets list (job item marked ready)
        go_lang(pg,'en');scr(pg,'job')
        if pg.locator('#wjMarkReady').count():pg.click('#wjMarkReady');pg.wait_for_timeout(400)
        for lang in LANGS:
            go_lang(pg,lang);scr(pg,'assets');pg.evaluate('scrollTo(0,0)');pg.wait_for_timeout(100);shot(pg,'%s-assets-360.png'%lang)
        # 7: built-before form (filled), 8: built-before list
        NAMES={'en':'Table','fr':'Table','ar':'طاولة','af':'Tafel'}
        for lang in LANGS:
            go_lang(pg,lang);scr(pg,'before');pg.evaluate('scrollTo(0,0)')
            pg.fill('#wjFaName',NAMES[lang]);pg.fill('#wjFaQty','3');pg.fill('#wjFaSize','1.8 m × 0.9 m')
            pg.evaluate("()=>document.activeElement&&document.activeElement.blur()");pg.wait_for_timeout(120)
            shot(pg,'%s-built-before-form-360.png'%lang)
            if lang=='af':
                pg.click('#wjSaveFa');pg.wait_for_timeout(400)
            else:
                pg.evaluate("()=>{['wjFaName','wjFaQty','wjFaSize'].forEach(k=>{try{localStorage.removeItem('tmcworkshop_draft_'+k)}catch(e){}})}")
        for lang in LANGS:
            go_lang(pg,lang);scr(pg,'assets');pg.evaluate('scrollTo(0,0)');pg.wait_for_timeout(100);shot(pg,'%s-built-before-list-360.png'%lang)
        b.close()
finally:
    gas.kill();srv.shutdown()
print('SHOTS',len(SHOTS))
