/**
 * TMC BASE — Google Sheet sync (generic: users + records). One Sheet + one script PER APP.  (base VER 4)
 * SERVER CHANGE base VER 7 (31 Oct 2026): Admin Block/Reject DISCARDS the user (del record {discarded:1}), Admin token only,
 *   never yourself, never the last Admin; the discarded user's tokens are deleted. Deploy only after phones are on VER 7.
 * Setup:
 *  1) Make a new Google Sheet for this app → Extensions → Apps Script → paste this file.
 *  2) OPTIONAL: Project Settings → Script properties → TEAM_CODE = <old-style sync code>.
 *     Not needed any more: phones without a code sign in with name + PIN and get a session token.
 *     Keep it only if older app versions still send a code. (Never write a code in this file.)
 *  2b) EASIEST: run setupOnce() once from the editor (Run → Allow). It names the Sheet, makes the tabs,
 *     adds the first Admin (JA Kirsten, no PIN yet), installs TRIGGERS and, only if TEAM_CODE_SETUP
 *     was replaced, stores TEAM_CODE in Script Properties. Safe to run again (changes nothing twice).
 *  2c) SAFE SIGN-IN ONLY: Script property STRICT_TOKEN = 1 → the old team code may no longer change
 *     users ("u" records); those changes need a signed-in token. Default off (old phones keep working).
 *  3) Deploy → New deployment → Web app (Execute as: Me, Who has access: Anyone).
 *     Put the /exec link in the app's CONFIG SYNC_URL (public, safe). Leave SYNC_CODE empty.
 *     After ANY change to this file: Deploy → Manage deployments → Edit → Version: NEW version → Deploy
 *     (the /exec link stays the same; without a new version the old code keeps running).
 * Open actions (no code, no token; script lock + per-name / per-hour caps):
 *   status {name}               → {ok,state:none|pending|active|rejected|blocked|setup,id,name,salt,hasPin}
 *   register {name,device}      → creates a PENDING user (Admin must approve) → status
 *   login {id,pinH,device}      → pinH = SHA256(salt+":"+pin) computed on the phone → {ok,token}; 5 wrong / hour / name
 *   setpin {id|setup,name,salt,pinH,device} → first PIN of an approved user (or very first Admin) → {ok,token}
 * Protected: sync {token | code, device, since, changes} → {ok,now,accepted,records}. Last write (u) wins.
 *   With a token, only an Admin may change other users ("u" records); a staff token may only
 *   change its own user record without touching status/admin.
 * ADMIN FIX RULE: staff may only ADD new records. Changing or deleting an existing record (any kind
 *   except their own "u" record) is refused unless the token belongs to an Admin. Old team-code phones
 *   have no name, so they are treated as staff (add only). Every Admin change is written to the
 *   "Fix log" tab: Time, Admin, Kind, Id, Old value, New value.
 * PERMISSIONS: user record .perms = ticked ids (missing = PERM_DEFAULT). Staff need 'add' to add a kind,
 *   'view' to receive it, 'reports'/'export' for those actions. Only an Admin can change .perms.
 * Kind "u" = users {id,name,status:pending|active|rejected|blocked,admin,salt,pinH,dev,at}.
 * Approval is stored on the user record (by name), NOT bound to a device, so a reinstalled phone
 * signs in again with name + PIN and no new approval.
 */
var APP_ID = 'tmcworkshop'; /* public id, not a secret. Food's WORKSHOP_APP_ID placeholder uses this exact value. */
var ADMIN_NAME = 'JA Kirsten';
var ADMIN_ALIASES = ['jakirsten', 'johankirsten', 'johanakirsten', 'jkirsten', 'templateadmin', 'templateadmintwo', 'templateadminthree', 'templateadminfour'];
var MAX_FAIL = 5, FAIL_WIN = 3600000, MAX_REG_HOUR = 30;
/* PERMISSIONS: keep these the SAME as CONFIG.PERMS / PERM_DEFAULT in index.html.
   PERM_KINDS: record kind → which tick is needed to see it (view) and to add it (add).
   Kinds not listed are open to every approved user. Fix + approving users are always Admin-only. */
var PERMS = ['view', 'add', 'reports', 'export'];
var PERM_DEFAULT = ['view', 'add'];
var PERM_KINDS = { x: { view: 'view', add: 'add' }, j: { view: 'view', add: 'add' }, m: { view: 'view', add: 'add' }, p: { view: 'view', add: 'add' }, k: { view: 'view', add: 'add' }, si: { view: 'view', add: 'add' }, hj: { view: 'view', add: 'add' }, sb: { view: 'view', add: 'add' } };
var REC = '_Records';
var REC_HEAD = ['Key', 'Kind', 'Id', 'UpdatedAt', 'Deleted', 'ServerTime', 'Device', 'Json'];

function teamCode_() { return String(PropertiesService.getScriptProperties().getProperty('TEAM_CODE') || '').trim(); }
function strict_() { return String(props_().getProperty('STRICT_TOKEN') || '').trim() === '1'; }
function out_(o) { return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON); }
function sheet_(name, head) {
  var ss = SpreadsheetApp.getActiveSpreadsheet(), sh = ss.getSheetByName(name) || ss.insertSheet(name);
  if (sh.getLastRow() === 0) { sh.appendRow(head); sh.setFrozenRows(1); }
  return sh;
}
function readAll_() {
  var sh = sheet_(REC, REC_HEAD), n = sh.getLastRow(), map = {}, rows = [];
  if (n > 1) rows = sh.getRange(2, 1, n - 1, REC_HEAD.length).getDisplayValues();  /* text as typed: never Sheets' Date objects */
  rows.forEach(function (r, i) {
    var key = String(r[0]), kind = String(r[1]), id = key.indexOf(kind + ':') === 0 ? key.slice(kind.length + 1) : String(r[2]);  /* Id from Key: exact even if Sheets once turned '2099-01-01' into a date */
    map[key] = { key: key, kind: kind, id: id, u: Number(r[3]), del: Number(r[4]) ? 1 : 0, s: Number(r[5]), dev: String(r[6]), data: String(r[7]), row: i + 2 };
  });
  return { sh: sh, map: map };
}
function merge_(store, changes, device, now) {
  var acc = 0;
  (changes || []).forEach(function (c) {
    if (!c || !c.kind || c.id === undefined || c.id === null) return;
    /* users are never removed by a sync/restore; only an explicit purge:1 delete (never sent by the app) removes one */
    if (String(c.kind) === 'u' && !(c.del && (c.purge === 1 || c._discard === 1)) && (c.del || c.data == null || typeof c.data !== 'object')) return;
    var key = c.kind + ':' + c.id, old = store.map[key], u = Number(c.u) || 0;
    if (old && old.u >= u) return;
    store.map[key] = { key: key, kind: String(c.kind), id: String(c.id), u: u, del: c.del ? 1 : 0, s: now, dev: device || '',
      data: c.del ? (c._discard === 1 ? JSON.stringify({ discarded: 1, at: new Date(now).toISOString() }) : '') : JSON.stringify(c.data == null ? null : c.data), row: old ? old.row : 0, dirty: true };
    acc++;
  });
  return acc;
}
function writeRecs_(store) {
  var sh = store.sh, add = [];
  Object.keys(store.map).forEach(function (k) {
    var r = store.map[k]; if (!r.dirty) return;
    var v = [r.key, r.kind, r.id, r.u, r.del, r.s, r.dev, r.data];
    if (r.row) sh.getRange(r.row, 1, 1, v.length).setNumberFormat('@').setValues([v]); else add.push(v);
    delete r.dirty;
  });
  if (add.length) sh.getRange(sh.getLastRow() + 1, 1, add.length, REC_HEAD.length).setNumberFormat('@').setValues(add);  /* plain text: Ids like 2099-01-01 stay text */
}
/* NEVER send PIN secrets in a sync: only the signed-in phone's own record keeps them (viewerId); team code gets none */
var SECRET_U = ['pinH', 'salt', 'pin'];
function stripUser_(data, viewerId) {
  try { var d = JSON.parse(data); if (!d || typeof d !== 'object') return data;
    if (viewerId && d.id === viewerId) return data;
    d.hasPin = d.pinH ? 1 : 0; SECRET_U.forEach(function (f) { delete d[f]; }); return JSON.stringify(d);
  } catch (e) { return ''; }
}
function changedSince_(store, since, me, viewerId) {
  return Object.keys(store.map).map(function (k) { return store.map[k]; }).filter(function (r) { return r.s > since && canKind_(me, r.kind, 'view'); })
    .map(function (r) {
      var data = r.data;
      if (r.kind === 'u' && data) data = stripUser_(data, viewerId);
      return { kind: r.kind, id: r.id, u: r.u, del: r.del, data: data };
    });
}
/* token phones don't hold other users' PIN hashes: keep the stored one unless the Admin asked for a PIN reset */
function keepPins_(store, changes) {
  return (changes || []).map(function (c) {
    if (!c || c.kind !== 'u' || c.del || !c.data || c.data.pinH) return c;
    var old = userById_(store, c.id); if (!old || !old.pinH || c.data.pinReset) return c;
    var d = JSON.parse(JSON.stringify(c.data)); d.pinH = old.pinH; d.salt = old.salt; delete d.hasPin;
    return { kind: c.kind, id: c.id, u: c.u, del: c.del, data: d };
  });
}
/** Readable "Users" tab (the app never reads it). Apps add their own tabs in rebuildViews_. */
function rebuildViews_(store) {
  var rows = [];
  Object.keys(store.map).forEach(function (k) {
    var r = store.map[k]; if (r.kind !== 'u' || r.del) return;
    var d = {}; try { d = JSON.parse(r.data) || {}; } catch (e) {}
    rows.push([d.name || '', d.status || '', d.admin ? 'yes' : '', d.pinH ? 'yes' : 'no', d.at || '', d.dev || '', d.admin ? 'ALL (Admin)' : perms_(d).join(', ')]);
  });
  rows.sort(function (a, b) { return String(a[0]).localeCompare(String(b[0])); });
  var sh = sheet_('Users', ['Name', 'Status', 'Admin', 'PIN set', 'Requested', 'Device', 'Permissions']);
  if (sh.getRange(1, 7).getValues()[0][0] !== 'Permissions') sh.getRange(1, 1, 1, 7).setValues([['Name', 'Status', 'Admin', 'PIN set', 'Requested', 'Device', 'Permissions']]);
  if (sh.getLastRow() > 1) sh.getRange(2, 1, sh.getLastRow() - 1, 7).clearContent();
  if (rows.length) sh.getRange(2, 1, rows.length, 7).setValues(rows);
  /* APP VIEWS GO HERE — Workshop jobs, materials and completed-photo links. Not a stock list. */
  var jobs = [], mats = [], pics = [], stock = [];
  Object.keys(store.map).forEach(function (k) {
    var r = store.map[k]; if (r.del) return;
    var d = {}; try { d = JSON.parse(r.data) || {}; } catch (e) {}
    if (r.kind === 'j') jobs.push([d.name || '', d.type || '', d.by || '', d.at || '', d.example ? 'EXAMPLE' : '']);
    if (r.kind === 'm') mats.push([d.jobId || '', d.mat || '', d.desc || '', d.qty || '', d.len || '', d.unit || '', d.by || '', d.at || '', d.example ? 'EXAMPLE' : '']);
    if (r.kind === 'p') pics.push([d.jobId || '', d.ph || '', d.by || '', d.at || '', d.example ? 'EXAMPLE' : '']);
    if (r.kind === 'k') stock.push([d.dir || '', d.desc || '', d.qty || '', d.len || '', d.unit || '', d.jobId || '', d.ref || '', d.at || '', d.example ? 'EXAMPLE' : '']);
  });
  wsView_('Jobs', ['Name', 'Type', 'By', 'When', 'Sample'], jobs);
  wsView_('Materials', ['Job', 'Material', 'Description', 'Pieces', 'Length', 'Unit', 'By', 'When', 'Sample'], mats);
  wsView_('Photos', ['Job', 'Photo id', 'By', 'When', 'Sample'], pics);
  wsView_('Stock', ['Move', 'Item', 'Pieces', 'Length', 'Unit', 'Job', 'Ref', 'When', 'Sample'], stock);
}
function wsView_(name, head, rows) {
  var sh = sheet_(name, head);
  if (sh.getLastRow() > 1) sh.getRange(2, 1, sh.getLastRow() - 1, head.length).clearContent();
  if (rows.length) sh.getRange(2, 1, rows.length, head.length).setValues(rows);
}
function props_() { return PropertiesService.getScriptProperties(); }
function nk_(x) { var n = String(x || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().replace(/[\s.]+/g, ''); return ADMIN_ALIASES.indexOf(n) >= 0 ? ADMIN_ALIASES[0] : n; }
function clean_(x) { return String(x || '').trim().replace(/\s+/g, ' ').slice(0, 60); }
function users_(store) {
  var o = [];
  Object.keys(store.map).forEach(function (k) { var r = store.map[k]; if (r.kind !== 'u' || r.del) return; var d = null; try { d = JSON.parse(r.data); } catch (e) {} if (d && d.id) o.push(d); });
  return o;
}
function userById_(store, id) { return users_(store).filter(function (u) { return u.id === String(id || ''); })[0] || null; }
function putUser_(store, u, device) { merge_(store, [{ kind: 'u', id: u.id, u: Math.max(Date.now(), ((store.map['u:' + u.id] || {}).u || 0) + 1), del: 0, data: u }], device, Date.now()); writeRecs_(store); try { rebuildViews_(store); } catch (e) {} }
/* same name rules as the app: lowercase, no spaces/dots, Admin aliases; one approved match only */
function status_(store, raw, device) {
  var name = clean_(raw), K = nk_(name); if (!K) return { ok: false, error: 'need_name' };
  var U = users_(store), all = U.filter(function (u) { return nk_(u.name) === K; }), ok = all.filter(function (u) { return u.status === 'active'; });
  if (ok.length === 1) return { ok: true, state: 'active', id: ok[0].id, name: ok[0].name, salt: ok[0].pinH ? ok[0].salt : '', hasPin: !!ok[0].pinH, admin: !!ok[0].admin };
  if (ok.length === 0) {
    if (all.some(function (u) { return u.status === 'blocked'; })) return { ok: true, state: 'blocked' };
    if (all.some(function (u) { return u.status === 'rejected'; })) return { ok: true, state: 'rejected' };
    var hasAdmin = U.some(function (u) { return u.status === 'active' && u.admin; });
    if (!hasAdmin && K === ADMIN_ALIASES[0]) return { ok: true, state: 'setup', name: ADMIN_NAME };
  }
  var own = U.filter(function (u) { return u.status === 'pending' && nk_(u.name) === K && (ok.length < 2 || (u.dev === device && clean_(u.name).toLowerCase() === name.toLowerCase())); })[0];
  return own ? { ok: true, state: 'pending', id: own.id, name: own.name, other: !!(device && own.dev && own.dev !== device) } : { ok: true, state: 'none' };
}
function fails_(K) { var p = props_(), now = Date.now(), a = []; try { a = JSON.parse(p.getProperty('FAIL_' + K) || '[]'); } catch (e) {} return a.filter(function (t) { return now - t < FAIL_WIN; }); }
function newToken_(u, device) {
  var p = props_(), all = p.getProperties(), tok = Utilities.getUuid().replace(/-/g, '') + Utilities.getUuid().replace(/-/g, '');
  Object.keys(all).forEach(function (k) { if (k.indexOf('TOK_') !== 0) return; try { var v = JSON.parse(all[k]); if (v.uid === u.id && v.dev === String(device || '')) p.deleteProperty(k); } catch (e) {} });
  p.setProperty('TOK_' + tok, JSON.stringify({ uid: u.id, dev: String(device || ''), at: Date.now() }));
  return tok;
}
function session_(store, tok) {
  if (!tok || !/^[a-f0-9]{32,80}$/i.test(String(tok))) return null;
  var v = props_().getProperty('TOK_' + tok); if (!v) return null;
  var s; try { s = JSON.parse(v); } catch (e) { return null; }
  var u = userById_(store, s.uid);
  return u && u.status === 'active' ? u : { blocked: true };
}
/* ONE request per person per app: a pending or active user with the same name key already exists */
function dupReq_(store, name, exceptId) { var K = nk_(clean_(name)), U = users_(store);
  if (U.filter(function (u) { return nk_(u.name) === K && u.status === 'active'; }).length >= 2) return false;  /* 2+ approved share the name: a new request is how a 3rd person asks */
  return !!K && U.some(function (u) { return String(u.id) !== String(exceptId || '') && nk_(u.name) === K && (u.status === 'pending' || u.status === 'active'); }); }
function noDupReq_(store, changes, refused) {
  return (changes || []).filter(function (c) {
    if (!c || c.kind !== 'u' || c.del || !c.data || userById_(store, c.id) || c.data.status !== 'pending') return true;
    if (dupReq_(store, c.data.name, c.id)) { refused.dup = (refused.dup || 0) + 1; return false; } return true;
  });
}
/* SERVER CHANGE (base VER 7): DISCARD a user = Admin token only, never self, never the last Admin. Old tokens are deleted. */
function discard_(store, me, changes, refused) {
  return (changes || []).filter(function (c) {
    /* SERVER CHANGE (base VER 7): the main Admin (an APPROVED Admin whose name key is jakirsten or any ADMIN_ALIASES name) is never removed,
       blocked, demoted or renamed away from the main name, by anyone. Reset PIN / other fields stay allowed.
       A pending request using an alias is not protected (it can still be rejected). */
    if (c && c.kind === 'u') { var mu = userById_(store, c.id), nd = c.data;
      if (mu && mu.admin && mu.status === 'active' && nk_(mu.name) === ADMIN_ALIASES[0] &&
          (c.del || !nd || !nd.admin || nd.status !== 'active' || nk_(nd.name) !== ADMIN_ALIASES[0])) {
        refused.disc = refused.disc || []; refused.disc.push(String(c.id)); refused.discWhy = 'main_admin'; return false; } }
    if (!c || c.kind !== 'u' || !c.del || !c.data || c.data.discarded !== 1) return true;
    var u = userById_(store, c.id); if (!u) return false;
    var why = !me || !me.admin ? 'admin_only_fix' : String(u.id) === String(me.id) ? 'self' :
      (u.admin && !users_(store).some(function (x) { return x.id !== u.id && x.admin && x.status === 'active'; })) ? 'last_admin' : '';
    if (why) { refused.disc = refused.disc || []; refused.disc.push(String(c.id)); refused.discWhy = why; return false; }
    var p = props_(), all = p.getProperties();
    Object.keys(all).forEach(function (k) { if (k.indexOf('TOK_') !== 0) return; try { if (JSON.parse(all[k]).uid === u.id) p.deleteProperty(k); } catch (e) {} });
    c._discard = 1; return true;
  });
}
/* a staff token may only change non-user records and its own user record (not status/admin) */
function allowed_(store, me, changes) {
  if (me.admin) return changes || [];
  return (changes || []).filter(function (c) {
    if (!c || c.kind !== 'u') return true;
    if (String(c.id) !== me.id || c.del || !c.data) return false;
    return c.data.status === me.status && !!c.data.admin === !!me.admin && sameList_(perms_(c.data), perms_(me));
  });
}
/* ADMIN FIX RULE: non-admins may only add NEW records (never change/delete an existing one). */
var FIX_LOG = 'Fix log', FIX_HEAD = ['Time', 'Admin', 'Kind', 'Id', 'Old value', 'New value'];
function addOnly_(store, changes, refused) {
  return (changes || []).filter(function (c) {
    if (!c || !c.kind || c.kind === 'u') return true;
    var old = store.map[c.kind + ':' + c.id];
    if (!c.del && !old) { if (canKind_(refused.me, c.kind, 'add')) return true; refused.n++; return false; }
    if (old && !c.del && old.data === JSON.stringify(c.data == null ? null : c.data)) return true;  // same add sent again
    refused.n++; return false;
  });
}
function logFixes_(store, me, changes) {
  var rows = [], now = new Date().toISOString();
  (changes || []).forEach(function (c) {
    if (!c || !c.kind || c.kind === 'u') return;
    var old = store.map[c.kind + ':' + c.id]; if (!old || old.u >= (Number(c.u) || 0)) return;
    var nv = c.del ? 'DELETED' : JSON.stringify(c.data == null ? null : c.data);
    if (nv === old.data) return;
    rows.push([now, me ? me.name : 'team code', c.kind, String(c.id), old.del ? 'DELETED' : old.data, nv]);
  });
  if (rows.length) { var sh = sheet_(FIX_LOG, FIX_HEAD); sh.getRange(sh.getLastRow() + 1, 1, rows.length, FIX_HEAD.length).setValues(rows); }
}
function perms_(u) { return Array.isArray(u && u.perms) ? u.perms : PERM_DEFAULT; }
function can_(me, p) { return !me || !!me.admin || perms_(me).indexOf(p) >= 0; }  /* me=null = old team code (full, as before) */
function canKind_(me, kind, what) { var k = PERM_KINDS[kind]; return !k || !k[what] || can_(me, k[what]); }
function sameList_(a, b) { return JSON.stringify((a || []).slice().sort()) === JSON.stringify((b || []).slice().sort()); }
function open_(req, store) {
  var a = req.action, dev = String(req.device || '').slice(0, 40);
  if (a === 'status') return status_(store, req.name, dev);
  if (a === 'register') {
    var st = status_(store, req.name, dev); if (!st.ok || st.state !== 'none') return st;
    if (dupReq_(store, req.name)) return { ok: true, state: 'dup', refusedWhy: 'duplicate_request' };  /* ONE request per name per app */
    var p = props_(), now = Date.now(), regs = []; try { regs = JSON.parse(p.getProperty('REG_HOUR') || '[]'); } catch (e) {}
    regs = regs.filter(function (t) { return now - t < 3600000; });
    if (regs.length >= MAX_REG_HOUR) return { ok: false, error: 'too_many_requests' };
    regs.push(now); p.setProperty('REG_HOUR', JSON.stringify(regs));
    putUser_(store, { id: 'r' + now + Math.floor(Math.random() * 1000), name: clean_(req.name), status: 'pending', dev: dev, at: new Date(now).toISOString() }, dev);
    return status_(store, req.name, dev);
  }
  if (a === 'login') {
    var u = userById_(store, req.id); if (!u) return { ok: false, error: 'no_user' };
    if (u.status !== 'active') return { ok: false, error: 'not_active', state: u.status };
    var K = nk_(u.name), F = fails_(K);
    if (F.length >= MAX_FAIL) return { ok: false, error: 'locked', until: F[0] + FAIL_WIN };
    if (!u.pinH || String(req.pinH || '') !== u.pinH) { F.push(Date.now()); props_().setProperty('FAIL_' + K, JSON.stringify(F)); return { ok: false, error: F.length >= MAX_FAIL ? 'locked' : 'bad_pin', until: F[0] + FAIL_WIN }; }
    props_().deleteProperty('FAIL_' + K);
    return { ok: true, token: newToken_(u, dev), id: u.id };
  }
  if (a === 'setpin') {
    if (!/^[a-f0-9]{64}$/.test(String(req.pinH || '')) || !req.salt) return { ok: false, error: 'bad_pin' };
    var v;
    if (req.setup) {
      var s2 = status_(store, req.name, dev); if (s2.state !== 'setup') return { ok: false, error: 'not_allowed' };
      v = { id: 'u' + Date.now(), name: ADMIN_NAME, status: 'active', admin: 1, dev: dev, at: new Date().toISOString() };
    } else {
      v = userById_(store, req.id); if (!v || v.status !== 'active' || v.pinH) return { ok: false, error: 'not_allowed' };
    }
    v.salt = String(req.salt).slice(0, 40); v.pinH = String(req.pinH); delete v.pinReset; delete v.hasPin; putUser_(store, v, dev);
    return { ok: true, token: newToken_(v, dev), id: v.id };
  }
  return null;
}
/* ===== VER 9 PHOTOS TO DRIVE (Johan 1 Nov 2026) =====
   action 'photo'    {id,d:'data:image/jpeg;base64,…',at,ref} (any signed-in phone) → saved in THIS app's own Drive folder
                     (made here, id kept in this script's PHOTO_FOLDER_ID; never looked up by name, so apps never mix).
                     Adds a server-only 'pl' record {id,fid,url,at,by,ref} that syncs to all phones. Same id twice = no copy.
   action 'photoget' {id} → Admin token only → {d:dataUrl} for the big View photo button.
   photoCleanup (daily trigger, added by setupOnce): photos older than PHOTO_KEEP_DAYS go to the Drive bin; the record stays,
   marked removed, and the Sheet shows 'photo removed'. Apps: show a photo id in a view with photoCell_(store, id). */
var PHOTO_KIND = 'pl', PHOTO_KEEP_DAYS = 60, PHOTO_MAX = 400000, PHOTO_TRIGGER = { fn: 'photoCleanup', hour: 3 };
function photoFolder_() {
  var p = props_(), id = p.getProperty('PHOTO_FOLDER_ID');
  if (id) { try { var f = DriveApp.getFolderById(id); if (!f.isTrashed()) return f; } catch (e) {} }
  var nf = DriveApp.createFolder(String(APP_SHEET_NAME).replace(/ Sheet$/, '') + ' photos');
  p.setProperty('PHOTO_FOLDER_ID', nf.getId()); return nf;
}
function photoCell_(store, id) {
  id = String(id || ''); if (!id) return '';
  var r = store.map[PHOTO_KIND + ':' + id]; if (!r || r.del) return id;
  try { var d = JSON.parse(r.data || '{}'); return d.removed ? 'photo removed' : (d.url || id); } catch (e) { return id; }
}
function noPhotoRecs_(changes) { return (changes || []).filter(function (c) { return !(c && c.kind === PHOTO_KIND); }); }  /* 'pl' is written by the server only */
function photo_(store, me, req) {
  var id = String(req.id || '');
  if (!/^[A-Za-z0-9_-]{3,60}$/.test(id)) return { ok: false, error: 'bad_id' };
  var key = PHOTO_KIND + ':' + id, old = store.map[key], od = null;
  try { od = old && !old.del ? JSON.parse(old.data || 'null') : null; } catch (e) { od = null; }
  if (req.action === 'photoget') {
    if (!(me && me.admin)) return { ok: false, error: 'admin_only' };
    if (!od) return { ok: false, error: 'no_photo' };
    if (od.removed || !od.fid) return { ok: false, error: 'photo_removed' };
    try { return { ok: true, id: id, d: 'data:image/jpeg;base64,' + Utilities.base64Encode(DriveApp.getFileById(od.fid).getBlob().getBytes()) }; }
    catch (e) { return { ok: false, error: 'photo_removed' }; }
  }
  if (od) return { ok: true, id: id, url: od.url || '', dup: 1, removed: od.removed ? 1 : 0 };
  var m = /^data:image\/jpeg;base64,([A-Za-z0-9+\/=]+)$/.exec(String(req.d || ''));
  if (!m) return { ok: false, error: 'bad_photo' };
  if (m[1].length > PHOTO_MAX) return { ok: false, error: 'too_big' };
  var at = Date.parse(req.at) || Date.now(), now = Date.now();
  if (now - at > PHOTO_KEEP_DAYS * 864e5) return { ok: true, id: id, skipped: 'old' };
  var f = photoFolder_().createFile(Utilities.newBlob(Utilities.base64Decode(m[1]), 'image/jpeg', id + '.jpg'));
  var data = { id: id, fid: f.getId(), url: f.getUrl(), at: new Date(at).toISOString(), by: me ? me.name : '', ref: String(req.ref || '').slice(0, 80) };
  merge_(store, [{ kind: PHOTO_KIND, id: id, u: now, del: 0, data: data }], req.device, now); writeRecs_(store);
  try { rebuildViews_(store); } catch (ve) {}
  return { ok: true, id: id, url: data.url };
}
function photoCleanup() {
  var lock = LockService.getScriptLock(); lock.waitLock(30000);
  try {
    var store = readAll_(), now = Date.now(), cut = now - PHOTO_KEEP_DAYS * 864e5, n = 0, ch = [];
    Object.keys(store.map).forEach(function (k) {
      var r = store.map[k]; if (r.kind !== PHOTO_KIND || r.del) return;
      var d; try { d = JSON.parse(r.data || '{}'); } catch (e) { return; }
      if (d.removed || (Date.parse(d.at) || now) >= cut) return;
      try { if (d.fid) DriveApp.getFileById(d.fid).setTrashed(true); } catch (e) {}
      d.removed = 1; d.url = ''; d.removedAt = new Date(now).toISOString(); ch.push({ kind: PHOTO_KIND, id: r.id, u: Math.max(now, r.u + 1), del: 0, data: d }); n++;
    });
    try { var it = photoFolder_().getFiles(); while (it.hasNext()) { var f = it.next(); if (f.getDateCreated().getTime() < cut) { f.setTrashed(true); } } } catch (e) {}  /* strays */
    if (ch.length) { merge_(store, ch, 'cleanup', now); writeRecs_(store); try { rebuildViews_(store); } catch (ve) {} }
    return n;
  } finally { lock.releaseLock(); }
}
/* Food stock transfer v1 (sync/stock-transfer-contract-v1.md). This code only credits stock.
   It cannot sync, change users, or run any other action. STOCK_IMPORT_CODE stays empty until Johan approves a deployment.
   Same transfer id is credited once. A journal is staged before stock counts, so a retry after a partial write finishes the same plan or refuses it. */
function stockCode_() { return String(props_().getProperty('STOCK_IMPORT_CODE') || '').trim(); }
function foldName_(s) { return String(s || '').trim().normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().replace(/\s+/g, ' '); }
function foldUnit_(s) { return String(s || '').trim().toLowerCase(); }
function recData_(store, kind, id) { var r = store.map[kind + ':' + id]; if (!r || r.del) return null; try { return JSON.parse(r.data) || null; } catch (e) { return null; } }
function qtyThou_(s) {
  var t = String(s == null ? '' : s).trim();
  if (!/^\d+(\.\d{1,3})?$/.test(t)) return null;
  var p = t.split('.'), w = p[0].replace(/^0+/, '') || '0', f = ((p[1] || '') + '000').slice(0, 3);
  var n = Number(w) * 1000 + Number(f);
  if (!isFinite(n) || n <= 0 || n > 1e15) return null;
  return n;
}
function canonTransfer_(t) {
  var lines = (t.lines || []).map(function (ln) {
    return { id: String(ln.id), sourceItemId: String(ln.sourceItemId), name: foldName_(ln.name), unit: foldUnit_(ln.unit), thou: qtyThou_(ln.qty) };
  }).sort(function (a, b) { return a.id < b.id ? -1 : a.id > b.id ? 1 : 0; });
  return JSON.stringify({ id: String(t.id), v: 1, sourceApp: 'fi', sourceIssueId: String(t.id), destinationApp: APP_ID, at: String(t.at), by: String(t.by || ''), qtyScale: 3, lines: lines });
}
function validateTransfer_(t) {
  if (!t || typeof t !== 'object' || Array.isArray(t)) return 'bad_request';
  var idOk = /^[A-Za-z0-9_-]{4,64}$/;
  if (t.v !== 1 || t.sourceApp !== 'fi' || !idOk.test(String(t.id || '')) || String(t.sourceIssueId || '') !== String(t.id)) return 'bad_request';
  if (String(t.destinationApp || '') !== APP_ID) return 'wrong_app';
  if (t.qtyScale !== 3 || !Array.isArray(t.lines) || !t.lines.length || t.lines.length > 40) return 'bad_request';
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,3})?Z$/.test(String(t.at || ''))) return 'bad_request';
  if (String(t.by || '').length > 120) return 'bad_request';
  var seen = {};
  for (var i = 0; i < t.lines.length; i++) {
    var ln = t.lines[i];
    if (!ln || typeof ln !== 'object') return 'bad_request';
    if (!idOk.test(String(ln.id || '')) || !idOk.test(String(ln.sourceItemId || ''))) return 'bad_request';
    if (seen[ln.id]) return 'bad_request'; seen[ln.id] = 1;
    var name = String(ln.name || ''), unit = String(ln.unit || '');
    if (!name.trim() || name.length > 120 || !unit.trim() || unit.length > 20) return 'bad_request';
    if (qtyThou_(ln.qty) == null) return 'bad_qty';
  }
  return '';
}
function lenUnit_(u) { u = foldUnit_(u); return u === 'm' || u === 'cm' || u === 'mm'; }
function pieceUnit_(u) { u = foldUnit_(u); return u === 'piece' || u === 'pieces' || u === 'pc' || u === 'pcs'; }
function listKind_(store, kind) {
  var o = [];
  Object.keys(store.map).forEach(function (k) {
    var r = store.map[k]; if (r.kind !== kind || r.del) return;
    var d = null; try { d = JSON.parse(r.data); } catch (e) {} if (d) o.push(d);
  });
  return o;
}
function buildPlan_(store, t) {
  var items = listKind_(store, 'si'), binds = listKind_(store, 'sb'), plan = [], created = [];
  for (var i = 0; i < t.lines.length; i++) {
    var ln = t.lines[i], thou = qtyThou_(ln.qty), unit = foldUnit_(ln.unit), name = String(ln.name).trim();
    var bind = null;
    binds.forEach(function (b) { if (b.sourceApp === 'fi' && b.sourceItemId === String(ln.sourceItemId)) bind = b; });
    var item = null;
    if (bind) {
      items.forEach(function (it) { if (it.id === bind.itemId) item = it; });
      if (!item || foldUnit_(item.unit) !== unit) return { error: 'bad_request' }; /* bound unit must not change under our feet */
    } else {
      var hits = [];
      items.forEach(function (it) {
        if (foldUnit_(it.unit) !== unit || foldName_(it.name) !== foldName_(name)) return;
        var taken = binds.some(function (b) { return b.itemId === it.id && !(b.sourceApp === 'fi' && b.sourceItemId === String(ln.sourceItemId)); });
        if (!taken) hits.push(it);
      });
      if (hits.length > 1) return { error: 'ambiguous_item' };
      if (hits.length === 1) item = hits[0];
      else {
        item = { id: 'si_fi_' + String(ln.sourceItemId), name: name, unit: unit, sourceApp: 'fi', sourceItemId: String(ln.sourceItemId), created: 1 };
        items.push(item); created.push(item);
      }
      binds.push({ id: 'sb_fi_' + String(ln.sourceItemId), sourceApp: 'fi', sourceItemId: String(ln.sourceItemId), itemId: item.id, unit: unit });
    }
    plan.push({ lineId: String(ln.id), sourceItemId: String(ln.sourceItemId), itemId: item.id, name: item.name, unit: unit, thou: thou, create: !!item.created, mat: pieceUnit_(unit) ? 'steel' : (lenUnit_(unit) ? 'rope' : 'other') });
  }
  return { plan: plan };
}
function rememberRows_(store) {
  var sh = store.sh, n = sh.getLastRow(); if (n < 2) return;
  sh.getRange(2, 1, n - 1, 1).getDisplayValues().forEach(function (row, i) { var rec = store.map[row[0]]; if (rec) rec.row = i + 2; });
}
function putRec_(store, kind, id, data, now) {
  var old = store.map[kind + ':' + id];
  var u = Math.max(now, old ? (Number(old.u) || 0) + 1 : now);
  merge_(store, [{ kind: kind, id: id, u: u, del: 0, data: data }], 'import', now);
}
function importStockTransfer_(store, req) {
  var code = stockCode_(), team = String(teamCode_() || ''), got = String(req && req.code || '').trim();
  if (!code || got !== code || (team && got === team)) return { ok: false, error: 'bad_code' };
  var t = req.transfer, verr = validateTransfer_(t);
  if (verr) return { ok: false, error: verr };
  var canon = canonTransfer_(t), prev = recData_(store, 'hj', t.id), now = Date.now();
  if (prev && prev.canon !== canon) return { ok: false, error: 'bad_request' }; /* same id, different body: not a duplicate, no credit */
  var plan = prev && prev.plan;
  if (prev && prev.status === 'applied' && plan && plan.every(function (ln) { return !!recData_(store, 'k', 'kl_' + ln.lineId); })) return { ok: true, transferId: String(t.id), result: 'duplicate' };
  if (!plan) {
    var built = buildPlan_(store, t);
    if (built.error) return { ok: false, error: built.error };
    plan = built.plan;
    putRec_(store, 'hj', String(t.id), { id: String(t.id), status: 'pending', canon: canon, plan: plan, sourceApp: 'fi', at: String(t.at), by: String(t.by || '') }, now);
    writeRecs_(store); /* pending does not count as stock */
    rememberRows_(store);
  }
  var finishing = !!(prev && prev.status === 'applied');
  plan.forEach(function (ln) {
    if (ln.create && !recData_(store, 'si', ln.itemId)) putRec_(store, 'si', ln.itemId, { id: ln.itemId, name: ln.name, unit: ln.unit, sourceApp: 'fi', sourceItemId: ln.sourceItemId }, now);
    var bid = 'sb_fi_' + ln.sourceItemId;
    if (!recData_(store, 'sb', bid)) putRec_(store, 'sb', bid, { id: bid, sourceApp: 'fi', sourceItemId: ln.sourceItemId, itemId: ln.itemId, unit: ln.unit }, now);
    var kid = 'kl_' + ln.lineId;
    if (!recData_(store, 'k', kid)) {
      var piece = pieceUnit_(ln.unit), len = lenUnit_(ln.unit), dec = ln.thou / 1000;
      putRec_(store, 'k', kid, { id: kid, dir: 'in', ref: String(t.id), lineId: ln.lineId, itemId: ln.itemId, mat: ln.mat, desc: ln.name, unit: ln.unit, qty: piece || !len ? dec : 0, len: len ? dec : 0, qThou: piece || !len ? ln.thou : 0, lThou: len ? ln.thou : 0, at: String(t.at), by: String(t.by || ''), jobId: '', sourceApp: 'fi', sourceItemId: ln.sourceItemId }, now);
    }
  });
  putRec_(store, 'hj', String(t.id), { id: String(t.id), status: 'applied', canon: canon, plan: plan, sourceApp: 'fi', at: String(t.at), by: String(t.by || ''), appliedAt: new Date(now).toISOString() }, now + 1);
  writeRecs_(store);
  try { rebuildViews_(store); } catch (e) {}
  return { ok: true, transferId: String(t.id), result: finishing ? 'duplicate' : 'accepted' };
}
function handle_(req) {
  if (!req) return { ok: false, error: 'bad_request' };
  var lock = LockService.getScriptLock();
  if (!lock.tryLock(25000)) return { ok: false, error: 'busy_try_again' };
  try {
    var store = readAll_();
    if (req.action === 'importStockTransfer') return importStockTransfer_(store, req);
    var sc = stockCode_();
    if (sc && String(req.code || '').trim() === sc) return { ok: false, error: 'bad_code' }; /* import code cannot sync or change users */
    var o = open_(req, store); if (o) return o;
    var code = teamCode_(), changes = noPhotoRecs_(req.changes), me = null, refused = { n: 0 };
    var viewerId = '';
    if (code && req.code && String(req.code).trim() === code) {
      if (strict_()) changes = (changes || []).filter(function (c) { if (c && c.kind === 'u') { refused.strict = (refused.strict || 0) + 1; return false; } return true; });  /* STRICT_TOKEN: users only via token */
      changes = keepPins_(store, addOnly_(store, discard_(store, null, changes, refused), refused)); /* old team-code access: add only, no discard */
      var tu = req.token ? session_(store, req.token) : null; if (tu && !tu.blocked) viewerId = tu.id; }
    else if (req.token) {
      me = session_(store, req.token);
      if (!me) return { ok: false, error: 'bad_token' };
      if (me.blocked) return { ok: false, error: 'not_active' };
      changes = keepPins_(store, allowed_(store, me, discard_(store, me, changes, refused)));
      refused.me = me; viewerId = me.id;
      if (!me.admin) changes = addOnly_(store, changes, refused); else logFixes_(store, me, changes);
    } else return { ok: false, error: req.code ? 'bad_code' : 'need_login' };
    changes = noDupReq_(store, changes, refused);
    if (req.action === 'photo' || req.action === 'photoget') return photo_(store, me, req);  /* VER 9 */
    if (req.action === 'report' || req.action === 'export') {  /* ticked actions, checked here on the server */
      var need = req.action === 'report' ? 'reports' : 'export';
      if (!can_(me, need)) return { ok: false, error: 'not_allowed', perm: need };
      var cnt = {}, rows = [];
      Object.keys(store.map).forEach(function (k) { var r = store.map[k]; if (r.kind === 'u' || r.del || !canKind_(me, r.kind, 'view')) return;
        cnt[r.kind] = (cnt[r.kind] || 0) + 1; if (req.action === 'export') rows.push({ kind: r.kind, id: r.id, data: JSON.parse(r.data || 'null') }); });
      return req.action === 'report' ? { ok: true, counts: cnt } : { ok: true, rows: rows };
    }
    var now = Date.now(), since = Number(req.since) || 0;
    var acc = merge_(store, changes, req.device, now), warn = '';
    if (acc) { writeRecs_(store); try { rebuildViews_(store); } catch (ve) { warn = 'views: ' + String(ve && ve.message || ve).slice(0, 200); } }
    var res = { ok: true, now: now, accepted: acc, records: changedSince_(store, since, me, viewerId) };
    if (refused.disc) { res.refused = refused.disc.length + (refused.n || 0); res.refusedWhy = refused.discWhy; res.refusedDiscard = refused.disc; }  /* SERVER CHANGE VER 7 */
    else if (refused.n) { res.refused = refused.n; res.refusedWhy = 'admin_only_fix'; }
    else if (refused.strict) { res.refused = refused.strict; res.refusedWhy = 'need_token'; }
    else if (refused.dup) { res.refused = refused.dup; res.refusedWhy = 'duplicate_request'; }
    if (warn) res.warn = warn;
    return res;
  } finally { lock.releaseLock(); }
}
function doPost(e) {
  try {
    var body = e && e.postData && e.postData.contents;
    if (!body) return out_({ ok: false, error: 'empty_request' });
    var req; try { req = JSON.parse(body); } catch (pe) { return out_({ ok: false, error: 'bad_json' }); }
    return out_(handle_(req));
  } catch (err) { return out_({ ok: false, error: String(err && err.message || err).slice(0, 300) }); }
}
function doGet() { return out_({ ok: true, app: 'TMC Workshop sync', hint: 'running' }); }
/* ===== ONE-TIME SETUP (standard in every app): open the editor, pick setupOnce, Run, Allow. =====
   TMC Base replaces the placeholder with the real team code ONLY in the copy pasted into Google
   (never commit a real code). Left as the placeholder → TEAM_CODE is not touched (token-only app). */
var APP_SHEET_NAME = 'TMC Workshop Sheet';  /* this app's own Sheet placeholder — not shared, not live */
var TEAM_CODE_SETUP = '__TMC_TEAM_CODE__';
/* Time triggers this app needs, e.g. { fn: 'dailyJob', hour: 5 }. Base has none. */
var TRIGGERS = [];
function renameSheetOnce_() { try { var ss = SpreadsheetApp.getActive(); if (ss.getName() !== APP_SHEET_NAME) { ss.rename(APP_SHEET_NAME); return 'renamed'; } return 'ok'; } catch (e) { return 'skip'; } }
function installTriggers_() {
  var have = {}, out = [];
  ScriptApp.getProjectTriggers().forEach(function (t) { var f = t.getHandlerFunction(); if (have[f]) ScriptApp.deleteTrigger(t); else have[f] = 1; });  /* drop duplicates */
  TRIGGERS.concat([PHOTO_TRIGGER]).forEach(function (t) {  /* VER 9: + daily photo cleanup */
    if (have[t.fn]) { out.push(t.fn + ':kept'); return; }
    ScriptApp.newTrigger(t.fn).timeBased().everyDays(1).atHour(t.hour || 5).nearMinute(t.minute || 0).create(); have[t.fn] = 1; out.push(t.fn + ':added');
  });
  return out;
}
function setupOnce() {
  var lock = LockService.getScriptLock(); lock.waitLock(20000);
  try {
    var p = props_(), out = { sheet: renameSheetOnce_() };
    if (TEAM_CODE_SETUP && TEAM_CODE_SETUP.indexOf('__') !== 0) { p.setProperty('TEAM_CODE', String(TEAM_CODE_SETUP).trim()); out.teamCode = 'set'; }
    else out.teamCode = teamCode_() ? 'kept' : 'none (token sign-in only)';
    var store = readAll_(); sheet_(FIX_LOG, FIX_HEAD);
    if (!users_(store).some(function (u) { return u.admin && u.status === 'active'; })) {
      putUser_(store, { id: 'u' + Date.now(), name: ADMIN_NAME, status: 'active', admin: 1, dev: 'setup', at: new Date().toISOString() }, 'setup'); out.admin = 'added';
    } else { rebuildViews_(store); out.admin = 'kept'; }
    try { out.photos = photoFolder_().getName(); } catch (e) { out.photos = 'error: ' + String(e && e.message || e).slice(0, 120); }  /* VER 9: creates this app's photo folder + asks Google for Drive */
    out.triggers = installTriggers_();
    out.strict = strict_() ? 'on' : 'off';
    return JSON.stringify(out);
  } finally { lock.releaseLock(); }
}
if (typeof module !== 'undefined') module.exports = { handle_: handle_, merge_: merge_, setupOnce: setupOnce, photoCleanup: photoCleanup, importStockTransfer_: importStockTransfer_ };
