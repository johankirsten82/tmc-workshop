#!/usr/bin/env python3
"""APP NAME spell-check (read-only). Checks each app's visible name against the approved list:
CONFIG NAME, <title>, apple-mobile-web-app-title, manifest name/short_name, sign-in heading, logo labels (svg text),
plus any near-miss word anywhere in index.html / manifest.json / sw.js / icons/*.svg (e.g. 'Purshes').
Usage: app_name_check.py DIR [DIR...]  -> exit 1 if any mistake."""
import sys,os,re,json,glob
APPROVED={'TMC Base App':'Base','TMC Sahara Purchases':'Purchases','TMC GRV':'GRV','TMC Food':'Food','TMC Fuel':'Fuel','TMC Rotation':'Rotation','TMC Production':'Production','TMC Money':'Money','TMC Workshop':'Workshop'}
OK_SHORT={'Base':['TMC Base','TMC Base App','Base'],'Purchases':['TMC Purchases','Purchases','TMC Sahara Purchases'],'GRV':['TMC GRV','GRV'],'Food':['TMC Food','Food'],'Fuel':['TMC Fuel','Fuel'],'Rotation':['TMC Rotation','Rotation'],'Production':['TMC Production','Production'],'Money':['TMC Money','Money'],'Workshop':['TMC Workshop','Workshop','TMC Work']}
WORDS=['Sahara','Purchases','Inventory','Rotation','Fuel','Food','GRV','TMC']
REAL={'share','shared','shares','safari','ration','rations','purchase','purchased','purchaseid','food','fuel','station','rotate','rotated','ratio','inventaire','salary','salaries','salaire','salaires','sales','sale','sahel','samara','fury','fuels','foods'}
def lev(a,b):
    p=list(range(len(b)+1))
    for i,x in enumerate(a,1):
        c=[i]
        for j,y in enumerate(b,1):c.append(min(p[j]+1,c[j-1]+1,p[j-1]+(x!=y)))
        p=c
    return p[-1]
def near(w):
    for g in WORDS:
        if w==g:return None
        lim=1 if len(g)<=4 else (3 if len(g)>=8 else 2)
        if w.lower()==g.lower() and g!='TMC' and w not in (g,g.lower(),g.upper()):return g
        if len(w)>=4 and len(g)>4 and w[0].lower()==g[0].lower() and w.lower() not in REAL and w.lower()!=g.lower() and lev(w.lower(),g.lower())<=lim and w.lower() not in ('food','fuel','foods','fueled','purchase','rotations','inventory'):return g
    return None
def fields(d):
    f={};ix=os.path.join(d,'index.html')
    s=open(ix,encoding='utf-8',errors='ignore').read() if os.path.exists(ix) else ''
    m=re.search(r'"NAME"\s*:\s*"([^"]*)"',s) or re.search(r'\bNAME\s*:\s*"([^"]*)"',s)
    if m:f['CONFIG NAME']=m.group(1)
    m=re.search(r'<title>([^<$]*)</title>',s)
    if m:f['<title>']=m.group(1).strip()
    m=re.search(r'apple-mobile-web-app-title"\s+content="([^"]*)"',s)
    if m:f['apple title']=m.group(1)
    try:
        mf=json.load(open(os.path.join(d,'manifest.json'),encoding='utf-8'))
        for k in('name','short_name'):
            if k in mf:f['manifest '+k]=mf[k]
    except Exception:pass
    if re.search(r'tmcS-t">\$\{esc\(C\.NAME\)\}|tmcS-t">\$\{esc\(CONFIG\.NAME\)\}',s):f['sign-in heading']=f.get('CONFIG NAME','')+' (from CONFIG)'
    else:
        m=re.search(r'class="tmcS-t"[^>]*>([^<$]+)<',s)
        if m:f['sign-in heading']=m.group(1)
    for svg in glob.glob(os.path.join(d,'icons','*.svg')):
        for t in re.findall(r'<text[^>]*>([^<]+)<',open(svg,encoding='utf-8',errors='ignore').read()):f['logo '+os.path.basename(svg)]=t.strip()
    return f,s
def check(d):
    f,s=fields(d);errs=[]
    full=f.get('CONFIG NAME') or f.get('manifest name') or ''
    app=min(APPROVED,key=lambda a:lev(a.lower(),full.lower())-(5 if a.split()[-1].lower()[:3]==full.split()[-1].lower()[:3] else 0)) if full else None
    for k,v in f.items():
        v0=v.replace(' (from CONFIG)','')
        if k=='manifest short_name' or k.startswith('logo'):good=OK_SHORT[APPROVED[app]] if app else []
        else:good=[app]
        if app and v0 not in good:errs.append('%s = "%s" (should be %s)'%(k,v0,' or '.join('"%s"'%g for g in good)))
    blobs=[('index.html',s)]
    for n in('manifest.json','sw.js'):
        p=os.path.join(d,n)
        if os.path.exists(p):blobs.append((n,open(p,encoding='utf-8',errors='ignore').read()))
    for svg in glob.glob(os.path.join(d,'icons','*.svg')):blobs.append(('icons/'+os.path.basename(svg),open(svg,encoding='utf-8',errors='ignore').read()))
    seen=set()
    for n,b in blobs:
        for i,line in enumerate(b.split('\n'),1):
            if re.search(r'APP_ID|CACHE_PREFIX|github\.io|"purshes"|pa_',line) and not re.search(r'NAME|title',line):continue  # technical ids (data keys) are not visible names
            for w in re.findall(r'[A-Za-z]{3,}',line):
                g=near(w)
                if g and (n,w) not in seen:
                    seen.add((n,w));errs.append('%s line %d: "%s" looks like a misspelling of "%s"'%(n,i,w,g))
    return app,f,errs
if __name__=='__main__':
    bad=0
    for d in sys.argv[1:]:
        app,f,e=check(d);print('== %s  (app: %s)'%(d,app))
        for x in e:print('  ✗ '+x)
        if not e:print('  ✓ all names spelled right and the same')
        bad+=bool(e)
    sys.exit(1 if bad else 0)
