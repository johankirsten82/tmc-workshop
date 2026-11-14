#!/usr/bin/env python3
"""Workshop v5 FINAL 360px screenshots (v4 jobs -> Already built -> Send to Assets), EN/FR/AR/AF, into screenshots/v5final/. Sample only, nothing published."""
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
V4=['Shaun Bed','Ben Bed','Alex Bed','Elton Bed','Johan Side Table','Cliff Bed']
def scr(pg,screen,jid=None):
    work_tab(pg);pg.evaluate("([s,j])=>{const w=TMC.ws();w.screen=s;if(j)w.jobId=j;TMC.render()}",[screen,jid]);pg.wait_for_timeout(250)
def fill_form(pg):
    if os.environ.get('PREFILL'):
        pg.fill('#wjIu_size','2 m x 1 m');pg.evaluate("()=>document.activeElement&&document.activeElement.blur()");pg.wait_for_timeout(120);return
    pg.fill('.wjIuType[data-r="0"]','Square tubing 40×40');pg.click('.wjIuCell[data-r="0"]');pg.click('[data-iupad="1"]');pg.click('[data-iupad="2"]')
    pg.click('#wjIuAdd');pg.wait_for_timeout(150)
    pg.fill('.wjIuType[data-r="1"]','Rope 10 mm');pg.click('.wjIuCell[data-r="1"]');pg.click('[data-iupad="8"]')
    pg.fill('#wjIu_size','2 m x 1 m');pg.evaluate("()=>document.activeElement&&document.activeElement.blur()");pg.wait_for_timeout(120)
try:
    with sync_playwright() as pw:
        b=pw.chromium.launch(executable_path=CHROME,args=['--no-sandbox'])
        ctx=b.new_context(viewport={'width':360,'height':780},device_scale_factor=3,is_mobile=True,has_touch=True,locale='en-US')
        ctx.on('dialog',lambda d:d.accept())
        pg=ctx.new_page();pg.goto(URL);pg.wait_for_selector('#langSel')
        pg.fill('#fName','Johan Kirsten');pg.click('#fName2');pg.wait_for_selector('#fPin2')
        pg.fill('#fPin','2468');pg.fill('#fPin2','2468');pg.click('#fSet');pg.wait_for_selector('header')
        pg.evaluate('TMC.syncNow()');pg.wait_for_timeout(600)
        pg.evaluate("""names=>{const at=new Date().toISOString();
          TMC.put('k','kin-sq-m',{id:'kin-sq-m',ref:'',dir:'in',mat:'steel',desc:'Square tubing 40×40',qty:0,len:18,unit:'m',qThou:0,lThou:18000,at:at,by:'JA Kirsten',jobId:'',sourceApp:'admin',note:''});
          TMC.put('k','kin-rope',{id:'kin-rope',ref:'',dir:'in',mat:'rope',desc:'Rope 10 mm',qty:0,len:20,unit:'m',qThou:0,lThou:20000,at:at,by:'JA Kirsten',jobId:'',sourceApp:'admin',note:''});
          names.forEach((n,i)=>TMC.put('j','j179430000000'+(i+1),{id:'j179430000000'+(i+1),name:n,type:'build',by:'JA Kirsten',at:'2026-11-11T'+String(8+i).padStart(2,'0')+':00:00.000Z',example:0}));
          [['m1794300000101','steel','Square tubing 40×40',2,12],['m1794300000102','rope','Rope 10 mm',0,8]].forEach(([id,mat,desc,q,l],i)=>{const t='2026-11-11T08:1'+i+':00.000Z';
            TMC.put('m',id,{id:id,jobId:'j1794300000001',mat:mat,desc:desc,qty:q,len:l,unit:'m',by:'JA Kirsten',at:t,example:0});
            TMC.put('k','kout'+id,{id:'kout'+id,ref:'',dir:'out',mat:mat,desc:desc,qty:q,len:l,unit:'m',qThou:q*1000,lThou:l*1000,at:t,by:'JA Kirsten',jobId:'j1794300000001',example:0})});
          TMC.put('fa','fa-btable',{id:'fa-btable',jobId:'',name:'Table',qty:3,size:'old stock',jobName:'',at:'2026-11-12T08:00:00.000Z',by:'JA Kirsten',status:'waiting',builtBefore:1,camp:'10 Alfa',sourceApp:'tmcworkshop'});
          TMC.syncNow()}""",V4)
        pg.wait_for_timeout(500)
        for lang in LANGS:
            go_lang(pg,lang)
            scr(pg,'list');pg.evaluate("()=>{const l=document.querySelector('.wjOpen');if(l)l.scrollIntoView({block:'start'});scrollBy(0,-70)}");pg.wait_for_timeout(120)
            shot(pg,'%s-jobs-list-360.png'%lang)
            scr(pg,'job','j1794300000001');pg.evaluate("()=>{const b=document.getElementById('wjReadyJob');if(b){b.style.scrollMarginBottom='80px';b.scrollIntoView({block:'end'})}}");pg.wait_for_timeout(120)
            shot(pg,'%s-job-already-built-360.png'%lang)
            pg.click('#wjInUse');pg.wait_for_timeout(250);fill_form(pg)
            pg.evaluate('scrollTo(0,0)');pg.wait_for_timeout(100);shot(pg,'%s-inuse-form-360.png'%lang)
            pg.evaluate("()=>{const r=document.querySelector('.wjIuRow');if(r){r.scrollIntoView({block:'start'});scrollBy(0,-52)}}") if os.environ.get('PREFILL') else pg.evaluate("()=>{const t=document.querySelector('.wjTakeTxt');if(t){t.style.scrollMarginBottom='12px';t.scrollIntoView({block:'end'});const p=document.getElementById('wjPadWrap'),r=t.getBoundingClientRect();if(p&&r.bottom>p.getBoundingClientRect().top-8)scrollBy(0,r.bottom-p.getBoundingClientRect().top+8)}}");pg.wait_for_timeout(150)
            shot(pg,'%s-inuse-materials-360.png'%lang)
            if lang=='af':
                pg.click('#wjSendIu');pg.wait_for_timeout(400)
            else:
                pg.click('#view .navBack');pg.wait_for_timeout(200)
                if pg.locator('#navAsk').count():pg.click('#navYes');pg.wait_for_timeout(200)
        print('fa', pg.evaluate("()=>TMC.all('fa').map(f=>[f.name,f.suggestedPerson,f.size,(f.materials||[]).length,f.builtBefore,f.jobId])"),'stock',pg.evaluate("TMC.wBal('steel','Square tubing 40×40')"))
        for lang in LANGS:
            go_lang(pg,lang);scr(pg,'assets');pg.evaluate("()=>{const r=document.querySelector('.wjFaRow');if(r)r.scrollIntoView({block:'start'});scrollBy(0,-130)}");pg.wait_for_timeout(120)
            shot(pg,'%s-assets-360.png'%lang)
            pg.evaluate("()=>{const r=[...document.querySelectorAll('.wjFaRow')].pop();if(r){r.style.scrollMarginBottom='80px';r.scrollIntoView({block:'end'})}}");pg.wait_for_timeout(120)
            shot(pg,'%s-built-before-list-360.png'%lang)
        b.close()
finally:
    gas.kill();srv.shutdown()
print('SHOTS',len(SHOTS))
