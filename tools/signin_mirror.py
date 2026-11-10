#!/usr/bin/env python3
"""Sign-in mirror test. python3 signin_mirror.py <app_dir> [--base DIR] [--shot OUT.png]
Opens the sign-in screen of the app and of the TMC base at 390x844 (storage cleared, Google Sheets blocked
so 'Not connected' shows), and compares them. Logo, app name and colour are masked.
FAIL if any element moves/resizes > 2px, if text differs (extra/missing text), or if the masked
grayscale-edge picture differs."""
import sys,os,re,threading,functools,http.server,socketserver,asyncio,io
from playwright.async_api import async_playwright
from PIL import Image,ImageFilter,ImageChops,ImageDraw
HERE=os.path.dirname(os.path.abspath(__file__));BASE=os.path.dirname(HERE)
CHROME=next((p for p in ["/usr/bin/google-chrome","/usr/bin/chromium","/usr/bin/chromium-browser"] if os.path.exists(p)),None)
PARTS=[("card",".tmcS .signin>.card"),("logo",".tmcS .tmcS-logo"),("title",".tmcS .tmcS-t"),("language",".tmcS .tmcS-lang"),
       ("name box",".tmcS .tmcS-name"),("Continue",".tmcS .tmcS-go"),("Not connected box",".tmcS .ncBox"),("Try again",".tmcS .ncBox button")]
TOL=2
def serve(d):
    class Q(http.server.SimpleHTTPRequestHandler):
        def log_message(self,*a):pass
    h=functools.partial(Q,directory=d)
    s=socketserver.ThreadingTCPServer(("127.0.0.1",0),h);s.daemon_threads=True
    threading.Thread(target=s.serve_forever,daemon=True).start();return s
JS="""(parts)=>{const r={};for(const [n,q] of parts){const e=document.querySelector(q);
 if(!e||getComputedStyle(e).display==='none'){r[n]=null;continue}const b=e.getBoundingClientRect();r[n]=[b.x,b.y,b.width,b.height]}
 const root=document.querySelector('.tmcS');const tx=[];
 if(root){const w=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);let n;while(n=w.nextNode()){const p=n.parentElement;
  if(!n.textContent.trim()||p.closest('.tmcS-t')||p.closest('option'))continue;const cs=getComputedStyle(p);
  if(cs.display==='none'||cs.visibility==='hidden'||!p.getClientRects().length)continue;tx.push(n.textContent.trim().replace(/\\s+/g,' '))}
  const s=root.querySelector('select');if(s)tx.push('[select] '+s.options[s.selectedIndex].text.trim());
  root.querySelectorAll('input:not([type=hidden])').forEach(i=>{if(i.offsetParent)tx.push('[input] '+i.placeholder)})}
 r._text=tx;r._lang=(document.querySelector('.tmcS select')||{}).value;return r}"""
async def grab(br,d,fake_url):
    srv=serve(d);port=srv.server_address[1]
    ctx=await br.new_context(viewport={"width":390,"height":844},device_scale_factor=1,service_workers="block",locale="en-US")
    pg=await ctx.new_page()
    await pg.route(re.compile(r"https://(script\.google|script\.googleusercontent|docs\.google|sheets\.googleapis)\..*"),lambda r:r.abort())
    if fake_url:  # the base has no sync link: give it a fake one (blocked) so it shows the same 'Not connected' box
        async def fix(route):
            resp=await route.fetch();b=await resp.text()
            await route.fulfill(response=resp,body=b.replace('"SYNC_URL": ""','"SYNC_URL": "https://script.google.com/macros/s/TEST/exec"',1))
        await pg.route(re.compile(r".*/(index\.html)?(\?.*)?$"),fix)
    await pg.goto(f"http://127.0.0.1:{port}/index.html");await pg.evaluate("()=>{localStorage.clear();sessionStorage.clear()}")
    await pg.reload()
    try:await pg.wait_for_selector(".tmcS .ncBox button",state="visible",timeout=12000)
    except Exception:pass
    await pg.wait_for_timeout(800)
    info=await pg.evaluate(JS,PARTS);png=await pg.screenshot()
    await ctx.close();srv.shutdown();return info,Image.open(io.BytesIO(png)).convert("RGB")
def edges(img,info):
    g=img.convert("L").filter(ImageFilter.FIND_EDGES).point(lambda v:255 if v>40 else 0);d=ImageDraw.Draw(g)
    for k in ("logo","title"):
        b=info.get(k)
        if b:d.rectangle([b[0]-3,b[1]-3,b[0]+b[2]+3,b[1]+b[3]+3],fill=0)
    return g
async def run(app,base,shot=None):
    async with async_playwright() as p:
        br=await p.chromium.launch(executable_path=CHROME) if CHROME else await p.chromium.launch()
        bi,bimg=await grab(br,base,True);ai,aimg=await grab(br,app,True);await br.close()
    if shot:aimg.save(shot)
    res=[]
    for n,_ in PARTS:
        a,b=ai.get(n),bi.get(n)
        if b is None:res.append((n+' (missing in base!)',False));continue
        if a is None:res.append((n+': not found',False));continue
        dv=max(abs(x-y) for x,y in zip(a,b))
        res.append((f"{n}: same place and size (off by {dv:.0f}px)",dv<=TOL))
    extra=[t for t in ai["_text"] if t not in bi["_text"]];miss=[t for t in bi["_text"] if t not in ai["_text"]]
    res.append(("text same as base"+(f" — extra {extra}" if extra else "")+(f" — missing {miss}" if miss else ""),not extra and not miss))
    ea,eb=edges(aimg,ai),edges(bimg,bi)
    for b in (ai.get("logo"),ai.get("title"),bi.get("logo"),bi.get("title")):
        if b:
            for e in (ea,eb):ImageDraw.Draw(e).rectangle([b[0]-3,b[1]-3,b[0]+b[2]+3,b[1]+b[3]+3],fill=0)
    diff=ImageChops.difference(ea,eb).filter(ImageFilter.MinFilter(3))  # ignore 1px anti-alias noise
    n=sum(1 for v in diff.tobytes() if v);res.append((f"masked picture same as base ({n} px differ)",n<=150))
    return res
def check(app,base=BASE,shot=None):return asyncio.run(run(os.path.abspath(app),os.path.abspath(base),shot))
if __name__=="__main__":
    a=sys.argv[1:];base=BASE;shot=None
    if "--base" in a:i=a.index("--base");base=a[i+1];del a[i:i+2]
    if "--shot" in a:i=a.index("--shot");shot=a[i+1];del a[i:i+2]
    r=check(a[0],base,shot);bad=[n for n,o in r if not o]
    for n,o in r:print(("  PASS " if o else "  FAIL ")+n)
    print("SIGN-IN MIRROR: %s (%d/%d)"%("OK" if not bad else "DIFFERS",len(r)-len(bad),len(r)));sys.exit(1 if bad else 0)
