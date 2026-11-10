#!/usr/bin/env python3
"""Phone screenshots of the Workshop sample. Mock import only. No live Food or Sheet."""
import json, os, re, shutil, socket, subprocess, tempfile, threading, urllib.parse, urllib.request
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from functools import partial
from playwright.sync_api import sync_playwright
from PIL import Image, ImageDraw
APP = os.path.abspath(__file__).rsplit('/tests/', 1)[0]
OUT = '/opt/cursor/artifacts'
os.makedirs(OUT, exist_ok=True)
TMP = tempfile.mkdtemp(prefix='wshots-')
shutil.copytree(APP, os.path.join(TMP, 'app'), ignore=shutil.ignore_patterns('tests', '.git', 'uploads'))
def free():
    s = socket.socket(); s.bind(('127.0.0.1', 0)); p = s.getsockname()[1]; s.close(); return p
GP, WP = free(), free()
gas = subprocess.Popen(['node', os.path.join(APP, 'tests', 'gas_server.js'), str(GP), '-'], stdout=subprocess.PIPE, env=dict(os.environ, GAS_FILE=os.path.join(APP, 'sync', 'Code.gs')))
gas.stdout.readline()
urllib.request.urlopen('http://127.0.0.1:%d/_prop?STOCK_IMPORT_CODE=%s' % (GP, urllib.parse.quote('test-import-workshop')))
ip = os.path.join(TMP, 'app', 'index.html'); src = open(ip, encoding='utf-8').read()
C = json.loads(re.search(r'/\*CONFIG\*/(.*?)/\*END\*/', src, re.S).group(1))
C['SYNC_URL'] = 'http://127.0.0.1:%d/exec' % GP; C['SYNC_CODE'] = ''
src = re.sub(r'/\*CONFIG\*/.*?/\*END\*/', '/*CONFIG*/' + json.dumps(C, ensure_ascii=False) + '/*END*/', src, flags=re.S)
open(ip, 'w', encoding='utf-8').write(src)
srv = ThreadingHTTPServer(('127.0.0.1', WP), partial(SimpleHTTPRequestHandler, directory=os.path.join(TMP, 'app')))
threading.Thread(target=srv.serve_forever, daemon=True).start()
im = Image.new('RGB', (640, 480), '#9a3412')
d = ImageDraw.Draw(im)
d.rectangle((40, 40, 600, 440), fill='#fef3c7')
from PIL import ImageFont
font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 42)
d.text((70, 180), 'EXAMPLE', font=font, fill='#7c2d12')
d.text((70, 240), 'completed gate', font=font, fill='#7c2d12')
png = os.path.join('/tmp', 'example-job.png'); im.save(png)
body = {"action": "importStockTransfer", "code": "test-import-workshop", "transfer": {"id": "EX-FOOD-0001", "v": 1, "sourceApp": "fi", "destinationApp": "tmcworkshop", "sourceIssueId": "EX-FOOD-0001", "at": "2026-11-08T09:00:00.000Z", "by": "EXAMPLE Food", "qtyScale": 3, "lines": [
    {"id": "EX-LN-STEEL-PC", "sourceItemId": "FI-ANGLE-PC", "name": "EXAMPLE angle iron", "unit": "piece", "qty": "20"},
    {"id": "EX-LN-STEEL-M", "sourceItemId": "FI-ANGLE-M", "name": "EXAMPLE angle iron", "unit": "m", "qty": "30"},
    {"id": "EX-LN-ROPE", "sourceItemId": "FI-ROPE-M", "name": "EXAMPLE rope", "unit": "m", "qty": "40"}]}}
urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:%d/exec' % GP, data=json.dumps(body).encode(), method='POST'))
def crop(pg, name, reset=True):
    if reset: pg.evaluate('scrollTo(0,0)')
    box = pg.evaluate('''() => {
      const header = document.querySelector('header');
      const view = document.getElementById('view');
      const nav = document.querySelector('nav.tabs').getBoundingClientRect().top;
      const top = header ? Math.max(0, header.getBoundingClientRect().top) : 0;
      let bot = top;
      view.querySelectorAll('h2,h3,p,button,.urow,img,label').forEach(e => {
        const r = e.getBoundingClientRect();
        if (r.bottom > top + 8 && r.top < nav - 2) bot = Math.max(bot, Math.min(nav - 4, r.bottom));
      });
      return { x: 0, y: Math.floor(top), width: 390, height: Math.max(160, Math.ceil(bot - top) + 8) };
    }''')
    pg.screenshot(path=os.path.join(OUT, name), clip=box)
try:
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        c = b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=3, is_mobile=True, has_touch=True)
        c.on('dialog', lambda d: d.accept())
        pg = c.new_page()
        pg.goto('http://127.0.0.1:%d/' % WP)
        pg.fill('#fName', 'Johan Kirsten'); pg.click('#fName2'); pg.wait_for_selector('#fPin2')
        pg.fill('#fPin', '2468'); pg.fill('#fPin2', '2468'); pg.click('#fSet'); pg.wait_for_selector('header')
        pg.evaluate('TMC.syncNow()'); pg.wait_for_timeout(900)
        pg.click('nav [data-tab=work]'); pg.wait_for_timeout(300)
        pg.click('#wjNew'); pg.fill('#wjName', 'EXAMPLE Gate frame'); pg.click('#wjSave'); pg.wait_for_timeout(400)
        pg.click('#wjNew'); pg.fill('#wjName', 'EXAMPLE Pump stand'); pg.click('#wjTyR'); pg.wait_for_timeout(150); pg.click('#wjSave'); pg.wait_for_timeout(400)
        pg.click('#wjStock'); pg.wait_for_timeout(300); crop(pg, 'workshop-stock.png')
        pg.click('#view .navBack'); pg.wait_for_timeout(250)
        pg.locator('.wjOpen', has_text='EXAMPLE Gate frame').click(); pg.wait_for_timeout(250)
        pg.click('#wjAddSteel'); pg.wait_for_timeout(200)
        pg.fill('#wjDesc', 'EXAMPLE angle iron'); pg.fill('#wjPcs', '2.5'); pg.fill('#wjLen', '3'); pg.select_option('#wjUnit', 'm')
        pg.evaluate('scrollTo(0,0)'); pg.wait_for_timeout(100)
        gap=pg.evaluate('''()=>{const s=document.getElementById('wjSaveM').getBoundingClientRect();const n=document.querySelector('nav.tabs').getBoundingClientRect();return Math.round(n.top-s.bottom)}''')
        if gap<8: raise SystemExit('Save still under the nav, gap %s'%gap)
        crop(pg, 'workshop-steel-entry.png')
        pg.click('#wjSaveM'); pg.wait_for_timeout(400)
        pg.click('#wjAddRope'); pg.wait_for_timeout(200)
        pg.fill('#wjDesc', 'EXAMPLE rope'); pg.fill('#wjLen', '12.5'); pg.select_option('#wjUnit', 'm')
        crop(pg, 'workshop-rope-entry.png')
        pg.click('#wjSaveM'); pg.wait_for_timeout(400)
        pg.click('#wjOpenPh'); pg.wait_for_timeout(200)
        pg.set_input_files('#wjPhPick .phGal input', png); pg.wait_for_timeout(400); pg.click('#wjSavePh'); pg.wait_for_timeout(500)
        pg.evaluate('''()=>{
          const header=document.querySelector('header').getBoundingClientRect().bottom;
          const name=document.querySelector('#wjJob h2').getBoundingClientRect().top;
          scrollBy(0, Math.max(0, name-header-8)+18);
        }''')
        pg.wait_for_timeout(150)
        crop(pg, 'workshop-job-details.png', False)
        pg.evaluate("document.getElementById('wjPic').scrollIntoView({block:'center'})"); pg.wait_for_timeout(150)
        crop(pg, 'workshop-completed-photo.png', False)
        pg.evaluate("TMC.ws().screen='list'"); pg.click('nav [data-tab=work]'); pg.wait_for_timeout(300)
        crop(pg, 'workshop-job-list.png')
        b.close()
finally:
    gas.kill(); srv.shutdown(); shutil.rmtree(TMP, ignore_errors=True)
print('shots', OUT)
