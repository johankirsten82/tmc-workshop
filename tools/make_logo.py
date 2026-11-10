"""TMC house-style logo generator (same layout as Purchases / GRV).
cream #ffffff square, green rounded frame (x=40..472, rx70, stroke 18), green Africa, symbol at (243.6,190),
dark-green label bar at y=390..448 with yellow Arial-bold label (auto-shrinks / bar widens for long labels).
Usage:  python3 make_logo.py <app_dir> <symbol> "<Label>"
  symbol = one of: box, coin, pot, fuel   or a path to a file holding an SVG fragment centred on 0,0 (~100px).
Writes <app>/icons/: icon.svg, icon-maskable.svg, icon-192.png, icon-512.png, icon-maskable-512.png (80% safe zone),
apple-touch-icon.png (180), favicon-32.png; and <app>/tools/logo.png (1024) so apply_config.py stays consistent.
Needs playwright + Chrome (/usr/bin/google-chrome) and Pillow."""
import os,sys,io
H=os.path.dirname(os.path.abspath(__file__))
AF=open(os.path.join(H,'africa_path.txt')).read().strip()
SYMS={
'box':'<rect x="-44" y="-30" width="88" height="66" rx="6" fill="#c08a4a" stroke="#fff" stroke-width="5"/><path d="M-44,-30 L-30,-48 L30,-48 L44,-30Z" fill="#d9a466" stroke="#fff" stroke-width="5"/><circle cx="34" cy="30" r="24" fill="#f5b301" stroke="#fff" stroke-width="5"/><path d="M22,30 l9,9 l16,-18" fill="none" stroke="#14532d" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"/>',
'coin':'<circle r="34" fill="#f5b301" stroke="#fff" stroke-width="6"/><circle r="24" fill="none" stroke="#b45309" stroke-width="4"/><text y="14" font-family="Arial" font-weight="700" font-size="38" text-anchor="middle" fill="#b45309">₣</text>',
'pot':''
 '<rect x="-60" y="-24" width="16" height="10" rx="4" fill="#f5b301" stroke="#fff" stroke-width="4"/><rect x="44" y="-24" width="16" height="10" rx="4" fill="#f5b301" stroke="#fff" stroke-width="4"/>'
 '<path d="M-46,-26 h92 v34 a24,24 0 0 1 -24,24 h-44 a24,24 0 0 1 -24,-24Z" fill="#f5b301" stroke="#fff" stroke-width="5"/>'
 '<rect x="-52" y="-40" width="104" height="14" rx="7" fill="#d97706" stroke="#fff" stroke-width="4"/><rect x="-9" y="-52" width="18" height="12" rx="5" fill="#d97706" stroke="#fff" stroke-width="4"/>',
'fuel':'<rect x="-40" y="-52" width="70" height="104" rx="10" fill="#f5b301" stroke="#fff" stroke-width="5"/><rect x="-30" y="-40" width="50" height="30" rx="5" fill="#14532d"/>'
 '<rect x="-50" y="48" width="90" height="14" rx="4" fill="#f5b301" stroke="#fff" stroke-width="4"/>'
 '<path d="M30,-30 h14 l10,12 v50 a8,8 0 0 0 16,0 v-48 l-12,-14" fill="none" stroke="#fff" stroke-width="12" stroke-linecap="round" stroke-linejoin="round"/>'
 '<path d="M30,-30 h14 l10,12 v50 a8,8 0 0 0 16,0 v-48 l-12,-14" fill="none" stroke="#f5b301" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>'
 '<path d="M-5,6 C-5,6 -18,22 -18,31 a13,13 0 0 0 26,0 C8,22 -5,6 -5,6Z" fill="#14532d"/>'}
def label_dims(label):
    # Arial bold ≈0.6em/char; keep 44px like GRV/Purchases, shrink to fit max bar 360 (frame inner ~ 400)
    fs=44; w=len(label)*fs*0.6
    while w>320 and fs>26: fs-=1; w=len(label)*fs*0.6
    bw=max(212,min(360,w+44)); return fs,bw
def inner(sym,label):
    fs,bw=label_dims(label)
    return ('<rect width="512" height="512" fill="#ffffff"/><rect x="40" y="40" width="432" height="432" rx="70" fill="none" stroke="#15803d" stroke-width="18"/>'
     f'<path d="{AF}" fill="#16a34a" stroke="#14532d" stroke-width="4" stroke-linejoin="round" paint-order="stroke"/>'
     f'<g transform="translate(243.6,190)">{sym}</g>'
     f'<rect x="{256-bw/2:.1f}" y="390" width="{bw:.1f}" height="58" rx="14" fill="#14532d"/>'
     f'<text x="256" y="{419+fs*0.36:.1f}" font-family="Arial" font-weight="700" font-size="{fs}" text-anchor="middle" fill="#f5b301">{label}</text>')
def main(app,symbol,label):
    sym=SYMS.get(symbol) or open(symbol).read()
    I=inner(sym,label); N='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">'
    full=N+I+'</svg>'
    mask=N+'<rect width="512" height="512" fill="#ffffff"/><g transform="translate(51.2 51.2) scale(0.8)">'+I+'</g></svg>'
    d=os.path.join(app,'icons');os.makedirs(d,exist_ok=True);os.makedirs(os.path.join(app,'tools'),exist_ok=True)
    open(os.path.join(d,'icon.svg'),'w').write(full);open(os.path.join(d,'icon-maskable.svg'),'w').write(mask)
    from playwright.sync_api import sync_playwright
    from PIL import Image
    def render(svg):
        g.set_content('<html><body style="margin:0">'+svg.replace('<svg ','<svg width="1024" height="1024" ',1)+'</body></html>')
        return Image.open(io.BytesIO(g.screenshot())).convert('RGB')
    with sync_playwright() as p:
        b=p.chromium.launch(executable_path='/usr/bin/google-chrome');g=b.new_page(viewport={'width':1024,'height':1024})
        F=render(full);M=render(mask);b.close()
    F.save(os.path.join(app,'tools','logo.png'))
    for n,s in [('icon-192.png',192),('icon-512.png',512),('apple-touch-icon.png',180),('favicon-32.png',32)]:
        F.resize((s,s),Image.LANCZOS).save(os.path.join(d,n),optimize=True)
    M.resize((512,512),Image.LANCZOS).save(os.path.join(d,'icon-maskable-512.png'),optimize=True)
    print('icons written to',d)
if __name__=='__main__':
    if len(sys.argv)!=4: sys.exit(__doc__)
    main(*sys.argv[1:])
