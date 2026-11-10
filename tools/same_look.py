#!/usr/bin/env python3
"""Same-look check: does an app folder use the TMC base look + v4 sync?  python3 same_look.py <app_dir>"""
import os,re,sys,json
MARK=[  # TMC look = Purchases look (pa-v85). Colour is an app setting (CONFIG COLOR) and is NOT checked.
 ('grey page background #f1f5f9',r'#f1f5f9'),
 ('base font system-ui',r'font-family:system-ui'),
 ('white cards (radius 14px)',r'\.card\{[^}]*background:#fff;border-radius:14px'),
 ('sticky coloured header',r'header\{[^}]*position:sticky|header\{[^}]*sticky'),
 ('bottom menu bar nav.tabs',r'class="tabs"'),
 ('menu buttons = icon + short label (ticon/tlab)',r'ticon.*tlab'),
 ('home: 2-column big tiles',r'grid-template-columns:1fr 1fr'),
 ('language dropdown with globe',r'<select[^>]*(id="lang|id="langSel|aria-label="Language")'),
 ('update banner',r'id="(updW|updBar)"'),
 ('not-connected banner',r'id="ncW"'),
 ('v4 sync token (_tok)',r"_tok"),
 ('v4 no-code login calls (register/login/setpin)',r"['\"]register['\"].*['\"]setpin['\"]|['\"]setpin['\"].*['\"]register['\"]"),
 ('spellcheck on text boxes',r'spellcheck'),
 ('sign-in card centred vertically (.full flex align-items:center + .signin wrapper)',r'\.full\{[^}]*align-items:center[^}]*\}.*class="signin"'),
 ('not-connected in own box below card (ncBox, not inside card) + status check on load',r'class="signin"><div class="card">(?:(?!id="ncW").)*?</div><div id="ncW" class="[^"]*ncBox.*action:"status"'),
 ('CONFIG block (own APP_ID, COLOR)',r'/\*CONFIG\*/.*?/\*END\*/'),
]
def check(app):
    p=os.path.join(app,'index.html');s=open(p,encoding='utf-8',errors='ignore').read()
    out=[(n,re.search(r,s,re.S) is not None) for n,r in MARK]
    m=re.search(r'/\*CONFIG\*/(.*?)/\*END\*/',s,re.S);v=None
    if m:
        try:v=json.loads(m.group(1)).get('VER')
        except Exception:pass
    out.append(('version is set',isinstance(v,(int,float)) and v>=1))
    css=' '.join(re.findall(r'<style[^>]*>(.*?)</style>',s,re.S))
    small=[int(x) for x in re.findall(r'min-height:(\d+)px',css) if int(x)<56]
    out.append(('simple: no buttons/fields under 56px tall (found %d small sizes)'%len(small),len(small)<=3))
    txt=re.sub(r'<script.*?</script>|<style.*?</style>|<[^>]+>',' ',s,flags=re.S)
    return out
if __name__=='__main__':
    a=sys.argv[1];r=check(a);bad=[n for n,o in r if not o]
    for n,o in r:print(('  PASS ' if o else '  FAIL ')+n)
    print('SAME LOOK: %s (%d/%d)'%('OK' if not bad else 'DIFFERS',len(r)-len(bad),len(r)));sys.exit(1 if bad else 0)
