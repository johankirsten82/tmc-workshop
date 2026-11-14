// v1.6.0 Send to TMC Assets: Code.gs with a mocked UrlFetchApp (fake Assets). No live Sheet, no network.
const fs = require('fs'), path = require('path'), vm = require('vm');
const props = {};
const calls = []; let mode = 'ok'; const seen = {};
function reply(o, code) { return { getResponseCode: () => code || 200, getContentText: () => JSON.stringify(o) }; }
const UrlFetchApp = { fetch(url, opt) { const b = JSON.parse(opt.payload); calls.push({ url, b, opt });
  if (mode === 'down') throw new Error('Address unavailable'); if (mode === 'http500') return reply({}, 500);
  if (b.action === 'listLocations') return reply(b.code === 'rd' ? { ok: true, locations: [{ id: 'c1', name: '10 Alfa', camp: '10 Alfa', places: [{ id: 'p1', name: 'Store A' }] }, { id: 'c2', name: 'Bravo', camp: 'Bravo', places: [] }, { bad: 1 }] } : { ok: false, error: 'bad_code' });
  if (mode === 'busy') return reply({ ok: false, error: 'busy_try_again' });
  if (b.code !== 'wc') return reply({ ok: false, error: 'bad_code' });
  const it = b.item; if (!it.campId || it.campId === 'nope') return reply({ ok: false, error: 'bad_camp' });
  if (seen[it.id]) return reply({ ok: true, itemId: 'wsf-' + it.id, placeId: seen[it.id], result: 'duplicate' });
  seen[it.id] = it.placeId || 'np-' + it.placeName; return reply({ ok: true, itemId: 'wsf-' + it.id, placeId: seen[it.id], result: 'accepted' }); } };
const cache = {}; const CacheService = { getScriptCache: () => ({ get: k => cache[k] || null, put: (k, v) => { cache[k] = v; } }) };
function Sheet() { this.rows = []; this.fmt = {}; }
Sheet.prototype = {
  getLastRow() { return this.rows.length; },
  getRange(r, c, nr, nc) {
    const s = this; nr = nr || 1; nc = nc || 1;
    return {
      setNumberFormat() { return this; },
      getDisplayValues() { const o = []; for (let i = 0; i < nr; i++) { const row = s.rows[r - 1 + i] || []; o.push(Array.from({ length: nc }, (_, j) => row[c - 1 + j] == null ? '' : String(row[c - 1 + j]))); } return o; },
      setValues(v) { v.forEach((row, i) => { const R = s.rows[r - 1 + i] || (s.rows[r - 1 + i] = []); row.forEach((x, j) => { R[c - 1 + j] = x; }); }); }
    };
  }
};
const ctx = { console, JSON, Date, Number, String, Object, Math, Array, RegExp, UrlFetchApp, CacheService,
  PropertiesService: { getScriptProperties: () => ({ getProperty: k => (k in props ? props[k] : null), setProperty: (k, v) => { props[k] = String(v); }, deleteProperty: k => { delete props[k]; }, getProperties: () => Object.assign({}, props) }) },
  SpreadsheetApp: { getActiveSpreadsheet: () => { throw new Error('no views in unit'); }, getActive: () => { throw new Error('no views'); } },
  LockService: { getScriptLock: () => ({ tryLock: () => true, waitLock() {}, releaseLock() {} }) } };
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(process.env.GAS_FILE || path.join(__dirname, '..', 'sync', 'Code.gs'), 'utf8'), ctx);

function store() { return { map: {}, sh: new Sheet() }; }
function rec(st, kind, id, d) { st.map[kind + ':' + id] = { key: kind + ':' + id, kind, id, u: 5, del: 0, data: JSON.stringify(d) }; }
function fa(st, id) { return JSON.parse(st.map['fa:' + id].data); }
function item(id, x) { return Object.assign({ id, jobId: 'j1', name: 'Bunk bed', qty: 2, size: '2 x 1 m', jobName: 'Bunk bed - Pieter', suggestedPerson: 'Pieter', by: 'Sipho', at: '2026-11-14T05:00:00.000Z', builtBefore: 0, status: 'waiting', campId: 'c1', campName: '10 Alfa', placeId: 'p1', placeName: 'Store A', photo: 'ph1', materials: [{ type: 'Angle iron 40', qty: 3.5, unit: 'm' }] }, x || {}); }
const out = {};
// 1. not configured: nothing sent, item stays waiting
let st = store(); rec(st, 'fa', 'fa-j1', item('fa-j1'));
props.ASSETS_URL = ''; let r = ctx.assetsSend_(st, null);
out.notConfigured = r.skipped === 'not_configured' && calls.length === 0 && fa(st, 'fa-j1').status === 'waiting';
delete props.ASSETS_URL; r = ctx.assetsSend_(st, null);
out.noCode = r.skipped === 'not_configured' && calls.length === 0;
// 2. accepted -> sent, payload mapping
props.ASSETS_WORKSHOP_CODE = 'wc';
rec(st, 'pl', 'ph1', { id: 'ph1', url: 'https://drive.google.com/file/d/X/view', at: 1 });
rec(st, 'fa', 'fa-b2', item('fa-b2', { name: 'Kitchen table', photo: 'ph2', placeId: '', placeName: 'Workshop yard', builtBefore: 1, by: 'JA Kirsten' }));
rec(st, 'pl', 'ph2', { id: 'ph2', url: 'data:image/jpeg;base64,AAAA' });
rec(st, 'fa', 'fa-b3', item('fa-b3', { campId: 'nope', name: 'Tente', photo: 'zz' }));
rec(st, 'fa', 'fa-b4', item('fa-b4', { name: 'Shelf', status: 'sent' }));
r = ctx.assetsSend_(st, null);
const c1 = calls.find(c => c.b.item && c.b.item.id === 'fa-j1'), c2 = calls.find(c => c.b.item && c.b.item.id === 'fa-b2'), c3 = calls.find(c => c.b.item && c.b.item.id === 'fa-b3');
out.post = c1 && c1.url === ctx.ASSETS.URL && c1.opt.method === 'post' && /text\/plain/.test(c1.opt.contentType) && c1.b.action === 'importFinishedItem' && c1.b.code === 'wc';
out.fields = c1 && c1.b.item.destinationApp === 'tmcassets' && c1.b.item.sourceApp === 'tmcworkshop' && c1.b.item.qty === '2' && c1.b.item.type === 'bed' && c1.b.item.campId === 'c1' && c1.b.item.campName === '10 Alfa' && c1.b.item.placeId === 'p1' && c1.b.item.placeName === 'Store A' && c1.b.item.by === 'Sipho' && c1.b.item.suggestedPerson === 'Pieter' && c1.b.item.jobId === 'j1' && c1.b.item.size === '2 x 1 m' && c1.b.item.builtBefore === false && c1.b.item.materials[0].qty === '3.5';
out.photoHttps = c1 && c1.b.item.photo === 'https://drive.google.com/file/d/X/view';
out.photoNoDataUrl = c2 && c2.b.item.photo === '' && c3 && c3.b.item.photo === '';
out.newPlace = c2 && c2.b.item.placeId === '' && c2.b.item.placeName === 'Workshop yard' && c2.b.item.type === 'table' && c2.b.item.builtBefore === true && c2.b.item.by === 'JA Kirsten';
out.sent = fa(st, 'fa-j1').status === 'sent' && fa(st, 'fa-j1').assetsItemId === 'wsf-fa-j1' && fa(st, 'fa-j1').assetsResult === 'accepted' && st.map['fa:fa-j1'].u > 5;
out.placeIdBack = fa(st, 'fa-b2').status === 'sent' && fa(st, 'fa-b2').placeId === 'np-Workshop yard';
out.rejected = fa(st, 'fa-b3').status === 'rejected' && fa(st, 'fa-b3').rejectWhy === 'bad_camp';
out.skipNotWaiting = !calls.some(c => c.b.item && c.b.item.id === 'fa-b4') && r.sent === 2 && r.rejected === 1;
out.written = st.sh.rows.length >= 3;
// 3. idempotent: a second run sends nothing; a resend after a lost reply gives duplicate -> sent
let n = calls.length; ctx.assetsSend_(st, null); out.idempotent = calls.length === n;
const lost = store(); rec(lost, 'fa', 'fa-j1', item('fa-j1')); ctx.assetsSend_(lost, null);
out.duplicate = fa(lost, 'fa-j1').status === 'sent' && fa(lost, 'fa-j1').assetsResult === 'duplicate';
// 4. network failure, http error, busy, bad code: still waiting
['down', 'http500', 'busy'].forEach(m => { mode = m; const s2 = store(); rec(s2, 'fa', 'fa-x' + m, item('fa-x' + m)); rec(s2, 'fa', 'fa-y' + m, item('fa-y' + m)); ctx.assetsSend_(s2, null); out['waiting_' + m] = fa(s2, 'fa-x' + m).status === 'waiting' && fa(s2, 'fa-y' + m).status === 'waiting'; });
mode = 'ok'; props.ASSETS_WORKSHOP_CODE = 'wrong'; n = calls.length;
const s3 = store(); rec(s3, 'fa', 'fa-z1', item('fa-z1')); rec(s3, 'fa', 'fa-z2', item('fa-z2')); r = ctx.assetsSend_(s3, null);
out.badCodeWaits = fa(s3, 'fa-z1').status === 'waiting' && fa(s3, 'fa-z2').status === 'waiting' && calls.length === n + 1 && r.error === 'bad_code';
props.ASSETS_WORKSHOP_CODE = 'wc';
// 5. ids filter (sync sends only the items that came in)
const s4 = store(); rec(s4, 'fa', 'fa-i1', item('fa-i1')); rec(s4, 'fa', 'fa-i2', item('fa-i2')); ctx.assetsSend_(s4, ['fa-i2']);
out.idsOnly = fa(s4, 'fa-i1').status === 'waiting' && fa(s4, 'fa-i2').status === 'sent';
// 6. retry trigger
out.retryTrigger = typeof ctx.assetsRetry === 'function' && ctx.TRIGGERS.some(t => t.fn === 'assetsRetry' && t.hours === 1);
// 7. phones cannot set the status; edits keep the server's status
const s5 = store(); rec(s5, 'fa', 'fa-s1', item('fa-s1', { status: 'sent', sentAt: 'T', assetsItemId: 'wsf-fa-s1', placeId: 'p9' }));
const k1 = ctx.keepAssets_(s5, [{ kind: 'fa', id: 'fa-n1', u: 9, data: item('fa-n1', { status: 'sent' }) }, { kind: 'fa', id: 'fa-s1', u: 9, data: item('fa-s1', { status: 'waiting', name: 'Bunk bed (edited)' }) }]);
out.newIsWaiting = k1[0].data.status === 'waiting';
out.editKeepsSent = k1[1].data.status === 'sent' && k1[1].data.assetsItemId === 'wsf-fa-s1' && k1[1].data.name === 'Bunk bed (edited)' && k1[1].data.placeId === 'p9';
// 8. type mapping (4 languages)
out.types = ['Bunk bed', 'Lit superposé', 'Stapelbed', 'سرير', 'Kitchen table', 'Tafel', 'طاولة', 'Tente', 'خيمة', 'Conteneur', 'Houer', 'Shelf'].map(ctx.assetsType_).join() === 'bed,bed,bed,bed,table,table,table,tent,tent,container,container,other';
// 9. locations: no read code -> no fetch, []; with code -> fetched, cleaned, cached
n = calls.length; let L1 = ctx.assetsLocations_(false);
out.locNoCode = L1.ok === true && Array.isArray(L1.locations) && L1.locations.length === 0 && calls.length === n;
props.ASSETS_LOCATIONS_READ = 'rd'; L1 = ctx.assetsLocations_(false);
const lc = calls[calls.length - 1];
out.locFetch = lc.b.action === 'listLocations' && lc.b.code === 'rd' && L1.locations.length === 2 && L1.locations[0].places[0].name === 'Store A' && L1.locations[1].places.length === 0 && L1.locations[0].camp === '10 Alfa';
n = calls.length; const L2 = ctx.assetsLocations_(false);
out.locCached = calls.length === n && L2.locations.length === 2;
mode = 'down'; const L3 = ctx.assetsLocations_(true); mode = 'ok';
out.locOfflineKeepsCache = L3.locations.length === 2;
out.noSecretsInPhoneReply = !/rd|wc|script\.google/.test(JSON.stringify(L3));
console.log(JSON.stringify(out));
if (!Object.keys(out).every(k => out[k])) process.exit(1);
