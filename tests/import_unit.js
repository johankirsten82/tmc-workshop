// Mocked Food importStockTransfer checks. No live Sheet.
const fs = require('fs'), path = require('path'), vm = require('vm');
const props = { STOCK_IMPORT_CODE: 'test-import-workshop' };
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
const ctx = { console, JSON, Date, Number, String, Object, Math,
  PropertiesService: { getScriptProperties: () => ({ getProperty: k => (k in props ? props[k] : null), setProperty: (k, v) => { props[k] = String(v); }, deleteProperty: k => { delete props[k]; }, getProperties: () => Object.assign({}, props) }) },
  SpreadsheetApp: { getActiveSpreadsheet: () => { throw new Error('no views in unit'); }, getActive: () => { throw new Error('no views'); } },
  LockService: { getScriptLock: () => ({ tryLock: () => true, waitLock() {}, releaseLock() {} }) } };
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(process.env.GAS_FILE || path.join(__dirname, '..', 'sync', 'Code.gs'), 'utf8'), ctx);
function store() { return { map: {}, sh: new Sheet() }; }
function data(st, kind) { return Object.keys(st.map).filter(k => st.map[k].kind === kind && !st.map[k].del).map(k => JSON.parse(st.map[k].data)); }
function thou(st, itemId) { return data(st, 'k').filter(k => k.itemId === itemId && k.dir === 'in').reduce((s, k) => s + (k.qThou || 0) + (k.lThou || 0), 0); }
function xfer(id, lines, extra) { return Object.assign({ action: 'importStockTransfer', code: 'test-import-workshop', transfer: Object.assign({ id: id, v: 1, sourceApp: 'fi', sourceIssueId: id, destinationApp: 'tmcworkshop', at: '2026-11-08T09:00:00.000Z', by: 'EXAMPLE Food', qtyScale: 3, lines: lines }, extra || {}) }); }
function line(id, item, name, unit, qty) { return { id: id, sourceItemId: item, name: name, unit: unit, qty: qty }; }
const st = store();
const body = xfer('EX-FOOD-0001', [line('EX-LN-STEEL-PC', 'FI-ANGLE-PC', 'EXAMPLE angle iron', 'piece', '2.5'), line('EX-LN-ROPE', 'FI-ROPE-M', 'EXAMPLE rope', 'm', '12.500')]);
const a1 = ctx.importStockTransfer_(st, body);
const dup = ctx.importStockTransfer_(st, body);
const canonBefore = data(st, 'hj').find(h => h.id === 'EX-FOOD-0001').canon;
const altered = ctx.importStockTransfer_(st, xfer('EX-FOOD-0001', [line('EX-LN-STEEL-PC', 'FI-ANGLE-PC', 'EXAMPLE angle iron', 'piece', '9'), line('EX-LN-ROPE', 'FI-ROPE-M', 'EXAMPLE rope', 'm', '12.5')]));
const canonAfter = data(st, 'hj').find(h => h.id === 'EX-FOOD-0001').canon;
const badQty = ctx.importStockTransfer_(st, xfer('EX-FOOD-0002', [line('EX-LN-BAD', 'FI-BAD', 'EXAMPLE bad', 'kg', '1e2')]));
const hj = data(st, 'hj').find(h => h.id === 'EX-FOOD-0001');
const torn = store();
ctx.importStockTransfer_(torn, body);
const hjRec = torn.map['hj:EX-FOOD-0001'];
const hjData = JSON.parse(hjRec.data); hjData.status = 'pending'; hjRec.data = JSON.stringify(hjData);
delete torn.map['k:kl_EX-LN-ROPE'];
const recovered = ctx.importStockTransfer_(torn, body);
const pending = store();
ctx.importStockTransfer_(pending, body);
const pRec = pending.map['hj:EX-FOOD-0001'];
const pData = JSON.parse(pRec.data); pData.status = 'pending'; pRec.data = JSON.stringify(pData);
Object.keys(pending.map).filter(k => k.indexOf('k:') === 0).forEach(k => delete pending.map[k]);
const clash = ctx.importStockTransfer_(pending, xfer('EX-FOOD-0001', [line('EX-LN-STEEL-PC', 'FI-ANGLE-PC', 'EXAMPLE angle iron', 'piece', '8')]));
const amb = store();
['a', 'b'].forEach(id => { amb.map['si:' + id] = { key: 'si:' + id, kind: 'si', id: id, u: 1, del: 0, data: JSON.stringify({ id: id, name: 'EXAMPLE bolt', unit: 'piece' }) }; });
const ambRes = ctx.importStockTransfer_(amb, xfer('EX-FOOD-AMB', [line('EX-LN-AMB', 'FI-BOLT', 'EXAMPLE bolt', 'piece', '1')]));
const bind = store();
ctx.importStockTransfer_(bind, xfer('EX-FOOD-B1', [line('EX-LN-B1', 'FI-ANGLE-PC', 'EXAMPLE angle iron', 'piece', '1')]));
const item = data(bind, 'si')[0]; item.name = 'Renamed angle';
bind.map['si:' + item.id].data = JSON.stringify(item);
const b2 = ctx.importStockTransfer_(bind, xfer('EX-FOOD-B2', [line('EX-LN-B2', 'FI-ANGLE-PC', 'Totally other name', 'piece', '1.5')]));
const unit = ctx.importStockTransfer_(bind, xfer('EX-FOOD-B3', [line('EX-LN-B3', 'FI-ANGLE-PC', 'EXAMPLE angle iron', 'bag', '1')]));
const applied = data(torn, 'hj').find(h => h.id === 'EX-FOOD-0001');
const out = {
  accepted: a1.result === 'accepted' && a1.ok === true,
  decimals: thou(st, 'si_fi_FI-ANGLE-PC') === 2500 && thou(st, 'si_fi_FI-ROPE-M') === 12500,
  duplicate: dup.result === 'duplicate' && thou(st, 'si_fi_FI-ANGLE-PC') === 2500,
  altered: altered.ok === false && altered.error === 'bad_request' && altered.result !== 'duplicate' && thou(st, 'si_fi_FI-ANGLE-PC') === 2500 && canonBefore === canonAfter,
  badQty: badQty.error === 'bad_qty' && !data(st, 'hj').some(h => h.id === 'EX-FOOD-0002'),
  journal: hj && hj.status === 'applied' && hj.canon,
  recover: recovered.ok === true && data(torn, 'k').filter(k => k.lineId === 'EX-LN-ROPE').length === 1 && thou(torn, 'si_fi_FI-ROPE-M') === 12500 && applied && applied.status === 'applied',
  clash: clash.ok === false && clash.result !== 'duplicate' && data(pending, 'k').length === 0,
  ambiguous: ambRes.error === 'ambiguous_item' && !data(amb, 'hj').length && !data(amb, 'k').length,
  binding: b2.result === 'accepted' && data(bind, 'si').length === 1 && thou(bind, item.id) === 2500,
  unit: unit.ok === false && data(bind, 'k').every(k => k.unit !== 'bag') && thou(bind, item.id) === 2500
};
console.log(JSON.stringify(out));
if (!Object.keys(out).every(k => out[k])) process.exit(1);
