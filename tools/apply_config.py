#!/usr/bin/env python3
"""Reads the CONFIG block at the top of index.html and writes everything that
must match it: manifest.json, sw.js (cache name = CACHE_PREFIX-vVER, default APP_ID), icons, QR code,
theme colour. Run after every CONFIG change and every version bump:
    python3 tools/apply_config.py
    python3 tools/apply_config.py /path/to/app     (any app folder)
The target app is the folder given, else the folder this script lives in.
sw.template.js and logo.png are taken from <app>/tools/ first, then the base.
Optional: put a square logo at <app>/tools/logo.png to use it as the icon."""
import json,os,re,sys
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CP_RE=r'^[a-z][a-z0-9]*(-[a-z0-9]+)*$'
def src(root,name):
    p=os.path.join(root,'tools',name)
    return p if os.path.exists(p) else os.path.join(ROOT,'tools',name)
def cache_prefix(C):
    cp=C.get('CACHE_PREFIX') or C['APP_ID']
    assert re.match(CP_RE,cp) and 2<=len(cp)<=30,'CACHE_PREFIX: lowercase letters/digits, single hyphens inside'
    assert not re.search(r'-v\d+(-|$)',cp),'CACHE_PREFIX must not contain -v<number>'
    return cp
def cfg(root=ROOT):
    s=open(os.path.join(root,'index.html'),encoding='utf-8').read()
    return json.loads(re.search(r'/\*CONFIG\*/(.*?)/\*END\*/',s,re.S).group(1))
def main(root=ROOT):
    C=cfg(root);A=C['APP_ID']
    assert re.match(r'^[a-z][a-z0-9]{1,19}$',A),'APP_ID: lowercase letters/numbers only'
    CP=cache_prefix(C)
    ip=os.path.join(root,'index.html');s=open(ip,encoding='utf-8').read()
    s=re.sub(r'<meta name="theme-color" content="[^"]*">','<meta name="theme-color" content="%s">'%C['COLOR'],s)
    s=re.sub(r'<title>[^<]*</title>','<title>%s</title>'%C['NAME'],s);open(ip,'w',encoding='utf-8').write(s)
    json.dump({"id":"./?tmcapp="+A,"name":C['NAME'],"short_name":C['SHORT'],"start_url":"./?tmcapp="+A,"scope":"./","display":"standalone",
      "background_color":C['BG'],"theme_color":C['COLOR'],"icons":[{"src":"icons/icon-192.png","sizes":"192x192","type":"image/png"},
      {"src":"icons/icon-512.png","sizes":"512x512","type":"image/png"},{"src":"icons/icon-maskable-512.png","sizes":"512x512","type":"image/png","purpose":"maskable"}]},
      open(os.path.join(root,'manifest.json'),'w'),indent=1,ensure_ascii=False)
    sw=open(src(root,'sw.template.js')).read().replace('__APP__',CP).replace('__VER__',str(int(C['VER']))).replace('__QR__',',"icons/qr.png"' if C.get('SHARE_URL') else '')
    open(os.path.join(root,'sw.js'),'w').write(sw)
    icons(root,C)
    print('applied',A,'cache %s-v%s'%(CP,C['VER']),'in',root)
def icons(root,C):
    from PIL import Image,ImageDraw,ImageFont
    d=os.path.join(root,'icons');os.makedirs(d,exist_ok=True)
    logo=src(root,'logo.png')
    def make(sz,mask=False):
        if os.path.exists(logo):
            bg=Image.new('RGBA',(sz,sz),C['BG']);l=Image.open(logo).convert('RGBA');k=int(sz*(0.8 if mask else 1));l=l.resize((k,k));bg.alpha_composite(l,((sz-k)//2,(sz-k)//2));return bg.convert('RGB')
        im=Image.new('RGB',(sz,sz),C['COLOR']);dr=ImageDraw.Draw(im)
        txt=''.join(w[0] for w in C['SHORT'].split()[:3]).upper() or 'T'
        try:f=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',int(sz*(0.28 if mask else 0.34)))
        except Exception:f=ImageFont.load_default()
        b=dr.textbbox((0,0),txt,font=f);dr.text(((sz-(b[2]-b[0]))/2-b[0],(sz-(b[3]-b[1]))/2-b[1]),txt,fill='white',font=f);return im
    make(192).save(os.path.join(d,'icon-192.png'));make(512).save(os.path.join(d,'icon-512.png'))
    make(512,True).save(os.path.join(d,'icon-maskable-512.png'));make(180).save(os.path.join(d,'apple-touch-icon.png'));make(32).save(os.path.join(d,'favicon-32.png'))
    q=os.path.join(d,'qr.png')
    if C.get('SHARE_URL'):
        qr_logo(C['SHARE_URL'],q,logo if os.path.exists(logo) else os.path.join(d,'icon-512.png'))
    elif os.path.exists(q):os.remove(q)
def qr_logo(url,q,logo):
    """QR with the app logo in the centre: error correction H (30% may be covered), logo 22% on a
    white rounded pad (26%). Falls back to a plain QR if there is no logo or anything fails."""
    import qrcode;from PIL import Image,ImageDraw
    qq=qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H,box_size=24,border=4);qq.add_data(url);qq.make(fit=True)
    im=qq.make_image(fill_color='black',back_color='white').convert('RGB');W=im.size[0]
    try:
        if logo and os.path.exists(logo):
            k=int(W*0.22);pd=int(W*0.26);x=(W-pd)//2;ImageDraw.Draw(im).rounded_rectangle((x,x,x+pd,x+pd),radius=pd//5,fill='white')
            l=Image.open(logo).convert('RGBA').resize((k,k),Image.LANCZOS);im.paste(l,((W-k)//2,(W-k)//2),l)
    except Exception as e:
        print('QR logo skipped (plain QR):',e);im=qq.make_image(fill_color='black',back_color='white').convert('RGB')
    im.save(q)
if __name__=='__main__':main(sys.argv[1] if len(sys.argv)>1 else ROOT)
