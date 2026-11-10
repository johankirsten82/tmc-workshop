#!/usr/bin/env python3
"""Mocked importStockTransfer checks. Nothing is deployed or sent to Google."""
import json, os, shutil, socket, subprocess, urllib.parse, urllib.request
APP = os.path.abspath(__file__).rsplit('/tests/', 1)[0]
HERE = os.path.dirname(os.path.abspath(__file__))
P = F = 0
def ok(c, m):
    global P, F
    P += 1 if c else 0
    F += 0 if c else 1
    print(('  PASS ' if c else '  FAIL ') + m, flush=True)
def free():
    s = socket.socket(); s.bind(('127.0.0.1', 0)); p = s.getsockname()[1]; s.close(); return p
def start(port, gs=None):
    env = dict(os.environ, GAS_FILE=gs or os.path.join(APP, 'sync', 'Code.gs'))
    p = subprocess.Popen(['node', os.path.join(HERE, 'gas_server.js'), str(port), '-'], stdout=subprocess.PIPE, env=env)
    p.stdout.readline(); return p
def prop(port, k, v):
    urllib.request.urlopen('http://127.0.0.1:%d/_prop?%s=%s' % (port, k, urllib.parse.quote(v)))
def post(port, body):
    return json.load(urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:%d/exec' % port, data=json.dumps(body).encode(), method='POST')))
def dump(port):
    return json.load(urllib.request.urlopen('http://127.0.0.1:%d/_dump' % port))
def xfer(dest, tid='EX-FOOD-0099', qty='1.25', code='test-import-workshop'):
    return {'action': 'importStockTransfer', 'code': code, 'transfer': {'id': tid, 'v': 1, 'sourceApp': 'fi', 'sourceIssueId': tid, 'destinationApp': dest, 'at': '2026-11-08T09:00:00.000Z', 'by': 'EXAMPLE Food', 'qtyScale': 3, 'lines': [{'id': 'EX-LN-0099', 'sourceItemId': 'FI-RICE', 'name': 'EXAMPLE rice', 'unit': 'kg', 'qty': qty}]}}
WP, SP = free(), free()
procs = [start(WP)]
prop(WP, 'STOCK_IMPORT_CODE', 'test-import-workshop')
prop(WP, 'TEAM_CODE', 'team-not-import')
try:
    unit = subprocess.run(['node', os.path.join(HERE, 'import_unit.js')], capture_output=True, text=True, env=dict(os.environ, GAS_FILE=os.path.join(APP, 'sync', 'Code.gs')))
    info = json.loads(unit.stdout or '{}')
    ok(unit.returncode == 0 and info.get('accepted') and info.get('decimals'), 'unit: decimal pieces 2.5 and rope 12.5 credit once %s' % info)
    ok(info.get('duplicate') and info.get('altered') and info.get('badQty'), 'unit: identical retry is duplicate; altered payload is refused %s' % info)
    ok(info.get('recover') and info.get('clash'), 'unit: partial write resumes the same plan; a different body does not %s' % info)
    ok(info.get('ambiguous') and info.get('binding') and info.get('unit'), 'unit: ambiguous name, source binding, unit change %s' % info)
    ok(post(WP, xfer('tmcworkshop', code='nope')).get('error') == 'bad_code' and not dump(WP)['recs'], 'wrong import code writes nothing')
    ok(post(WP, xfer('tmcworkshop', code='team-not-import')).get('error') == 'bad_code', 'team code cannot import')
    ok(post(WP, {'action': 'sync', 'code': 'test-import-workshop', 'device': 't', 'since': 0, 'changes': [{'kind': 'j', 'id': 'nope', 'u': 1, 'data': {'id': 'nope'}}]}).get('error') == 'bad_code', 'import code cannot sync')
    ok(post(WP, xfer('tmcservice')).get('error') == 'wrong_app' and not any(r['kind'] == 'hj' for r in dump(WP)['recs']), 'wrong app writes nothing')
    ok(post(WP, xfer('tmcworkshop', 'EX-FOOD-0099', '1.250')).get('result') == 'accepted', 'decimal qty 1.250 accepted')
    ok(post(WP, xfer('tmcworkshop', 'EX-FOOD-0099', '1.25')).get('result') == 'duplicate', 'same thousandths is a duplicate')
    alt = xfer('tmcworkshop', 'EX-FOOD-0099', '9')
    refused = post(WP, alt)
    ok(refused.get('ok') is False and refused.get('result') != 'duplicate' and refused.get('error') == 'bad_request', 'altered payload is not returned as duplicate')
    rows = [r for r in dump(WP)['recs'] if r['kind'] == 'k' and not r['del']]
    ok(len(rows) == 1 and rows[0]['data'].get('qThou') == 1250, 'altered payload did not change the credit')
    other = os.path.join('/tmp', 'tmc-service-code.gs')
    shutil.copy(os.path.join(APP, 'sync', 'Code.gs'), other)
    s = open(other, encoding='utf-8').read().replace("var APP_ID = 'tmcworkshop';", "var APP_ID = 'tmcservice';", 1)
    open(other, 'w', encoding='utf-8').write(s)
    procs.append(start(SP, other))
    prop(SP, 'STOCK_IMPORT_CODE', 'test-import-service')
    ok(post(SP, xfer('tmcworkshop', 'EX-FOOD-0099', '1.25', 'test-import-service')).get('error') == 'wrong_app', 'service receiver rejects a workshop destination')
    ok(post(SP, xfer('tmcservice', 'EX-FOOD-SVC', '2', 'test-import-service')).get('result') == 'accepted', 'service receiver accepts its own destination')
    wok = json.dumps(dump(WP)); sok = json.dumps(dump(SP))
    ok('EX-FOOD-SVC' not in wok and 'EX-FOOD-0099' not in sok and 'EX-FOOD-0099' in wok and 'EX-FOOD-SVC' in sok, 'each receiver keeps only its own transfer')
finally:
    for p in procs:
        p.kill()
print('\nIMPORT: %d passed, %d failed' % (P, F))
raise SystemExit(1 if F else 0)
