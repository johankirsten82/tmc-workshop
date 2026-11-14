# TMC Workshop v5 sample (cut list + Send to Assets)

Sample only. Not published. Live phones stay on v4 until Johan says yes.

- Cut list per job: staff add Qty × Length with a big number pad and mm/m. Totals are running metres per item and for all items, plus how many full bar lengths (default 6 m, Admin can change). Saving takes those metres off Workshop stock as ordinary `k` out records linked to the job. No Code.gs change.
- Staff may only add a cut list. Admin may delete one; the metres taken off stock stay used and do NOT go back into stock.
- Send to Assets: Workshop-side list of finished items (Waiting for Assets). Source = the existing Build jobs (v4 job records read unchanged). Admin: **Job finished: send to Assets** (job with a cut list) or **Already built (in use)** (add materials + size; *Take off stock* switch, default OFF), with a suggested person taken from the job name (editable). Admin can also **Add item built before** (no job, no stock taken). The future link is designed in `sync/assets-transfer-design.md` and is not connected.
- Languages EN/FR/AR/AF. Cache `tmcworkshop-v5`. Storage keys still `tmcworkshop_`.

# TMC Workshop v1

Named Build and Repair jobs. Food credits Workshop stock only with `importStockTransfer` (`sourceApp` `fi`, `destinationApp` `tmcworkshop`). Staff allocate that stock onto a job.

GitHub Pages path: `/tmc-workshop/` (relative `./` scope, this folder only). Service worker cache `tmcworkshop-v1`. Phone storage `tmcworkshop_`. `SYNC_URL`, `SYNC_CODE` and `STOCK_IMPORT_CODE` stay empty until the Sheet is linked. Until then the phone shows **Not connected yet**.

- APP_ID: `tmcworkshop`
- Version: 1
- Local: `python3 -m http.server 41731`
- Tests: `python3 tests/run_all.py` (mocked Sheet only)

Contract: `sync/stock-transfer-contract-v1.md`. The base notes below are the template this sample was copied from. They are not permission to publish.

> Workshop packaging: read WORKSHOP_REFERENCE_READ_FIRST.md first. No deployment or language migration is authorized.

# TMC base app

This is the shared starting point for TMC phone apps (Purshes, GRV, Food Inventory and the next ones). It is a single `index.html` with no build step.

## What's in it
- **Sign-in**:
  - Staff type their name, then enter a 4–6 digit PIN.
  - New names wait for Admin approval.
  - First Admin setup runs when the Sheet has no Admin yet.
  - The v80 name rule matches names with lowercase, spaces removed and dots removed. If two approved users share the same key, there is no auto-match.
  - Admin aliases are set in `CONFIG.ADMIN_ALIASES`.
- **Reinstall**: a reinstalled phone signs in again with name + PIN and needs no new approval.
- **PIN lock**: 5 wrong PINs lock that name for 1 hour.
- **Inputs**: PIN inputs have no `type=password`. They use the `msk` class, so phones do not offer to save a password.
- **Logout** warns when changes are not sent yet.
- **Layout**: Home has big buttons, plus a bottom tab bar with Home / Work / Users (Admin only) / Settings.
- **Languages**: EN / FR / AR / AF (Afrikaans). Arabic uses a full right-to-left layout. Dates use `ar-TD-u-nu-latn` (Latin digits). A phone that had Arabic ("ar") saved stays in Arabic. Never remove a language.
- **Google Sheet sync**:
  - Changes are sent 800 ms after a change.
  - It retries when the phone is back online.
  - A red warning appears while changes are unsent: "Tap Sync before deleting the app".
- **Updates**: auto-update check, then an "Update now" banner.
- **Install**: a big Install button, and an iPhone "Share → Add to Home Screen" hint.
- **Share app**: a QR code, the phone's share sheet, and a copy link.
- **Drafts**: any field with `data-draft="key"` is saved while typing and restored after a reload.
- **Settings**:
  - language, sync status, version, update, share, install, logout;
  - "Clear this app" (this app only);
  - for Admin only: the hidden sync URL and code, with an eye button.
- **Isolation**: everything is named from `APP_ID` (caches from `CACHE_PREFIX`, which defaults to `APP_ID`), so many apps can share `templateadmintwo82.github.io` without mixing:
  - localStorage keys are `APP_ID_…`;
  - caches are `CACHE_PREFIX-v…` (e.g. `tmc-fuel-v1`); storage keys never use the hyphen prefix;
  - the service worker only handles its own folder and only deletes its own old caches;
  - the manifest `id` and `start_url` are `./?tmcapp=APP_ID`.
- **Sync script**: `sync/Code.gs` is the generic sync script. It handles users and records, uses last-write-wins, adds a readable "Users" tab, and has a `rebuildViews_` hook.

## Start a new app
1. Copy the folder: `cp -r tmc-base my-app`. Delete `my-app/tests/shots`.
2. Edit the **CONFIG block** at the top of `index.html`:
   - `APP_ID` must be new and unique. Use lowercase letters and digits, and never reuse or change it after go-live.
   - Optional `CACHE_PREFIX`: lowercase letters/digits with single hyphens inside (e.g. `tmc-fuel` → caches `tmc-fuel-v1`). It must not contain `-v<number>` and must be unique too. If left out, `APP_ID` is used.
   - Also set `NAME`, `SHORT`, `COLOR`, `COLOR_DARK`, `BG`, `ADMIN_NAME`, `ADMIN_ALIASES` and `SHARE_URL`.
   - Put `SYNC_URL` (the public /exec link) in CONFIG so a fresh install is connected at once. Leave `SYNC_CODE` empty (VER 4: name + PIN token sign-in).
   - Optional: put a square `my-app/tools/logo.png` to use as the icon.
3. Run `python3 tools/apply_config.py my-app` (or `python3 my-app/tools/apply_config.py`). It writes `manifest.json`, `sw.js`, icons and `qr.png` into `my-app`, using `my-app/tools/sw.template.js` and `my-app/tools/logo.png` when they exist, else the base copies.
4. Build the app's own screens **only between `APP FEATURES START` and `APP FEATURES END`** in `index.html`. Replace the example "Work" notes tab there.
   - Save data with `TMC.put(kind, id, data)`.
   - Read it with `TMC.all(kind)`.
   - Kind `u` is reserved for users.
   - Every new text needs an entry in `TMC.T` in en, fr and ar.
5. Set up **a new Google Sheet for this app**:
   - Paste `sync/Code.gs` into Extensions → Apps Script.
   - Optional: Script property `TEAM_CODE` (only for older app versions that send a code). Not needed from VER 4.
   - Deploy it as a Web app (Anyone).
   - Never share a Sheet or a code between apps.
6. For each release, raise `VER` in CONFIG and run `apply_config.py` again.
7. Run `python3 tests/run_all.py my-app`. **It must say `0 failed` before going live.** Screenshots go to `my-app/tests/shots/` only. If the app has replaced the demo Work notes box (`#exTxt`), the notes spellcheck check is skipped; the other tests that use the notes box (reinstall, offline, drafts, no-data-mixing) still need an equivalent box, so keep `#exTxt`/`#exAdd` or adapt those tests.
8. Publish it to its own folder, e.g. `templateadmintwo82.github.io/tmc-<name>/`.

## Carry a fix from the base to Purshes, GRV and Food Inventory
These three apps are older than the base and were not built from it. A fix has to be copied by hand (for v4 see "Carry v4 into Fuel" below):
1. Fix the base first, add a test for it in `tests/run_all.py`, and make sure all tests pass.
2. Find the same feature in the target app. The matching names are:

   | Base | Purshes | GRV | Food Inventory |
   |---|---|---|---|
   | storage prefix | `pa_` | `grv_` | none (`me`, `lang`, `cfg`…) |
   | name key | `NK` | | |
   | Admin aliases | `ADMIN_AL` | | `ADMIN0` |
   | sync | `pa_sy*` | | |

   Port the change, keeping the app's own prefixes and cache names.
3. In the target app, raise its version and its `sw.js` cache name, for example `pa-v81`.
4. Run that app's own tests, then do one phone check: install, sign in, add one record and see it reach the Sheet. Only then publish.
5. Apps built from the base later: copy the base `index.html` code **outside** the APP FEATURES block and `tools/sw.template.js`, then run `apply_config.py` and `tests/run_all.py`.

## Changes
- **v3**: optional `CACHE_PREFIX` (hyphens allowed, e.g. `tmc-fuel-v1`), APP_ID still letters/digits for storage keys; `apply_config.py` uses the target app's own `tools/` (falls back to base); tests write screenshots only to the app's `tests/shots/`, notes spellcheck check skipped if `#exTxt` is missing; test app B now uses a hyphen cache prefix `test-b`.
  - Porting to an app built on base v2: change `const CACHE_PREFIX=C.APP_ID+"-v";` to `const CACHE_PREFIX=(C.CACHE_PREFIX||C.APP_ID)+"-v";` in index.html and copy `tools/apply_config.py`, `tools/sw.template.js`, `tests/run_all.py`.

- **v4 — "ready to go" sync (no code for staff).** A fresh install with only `SYNC_URL` in CONFIG connects at once:
  name → the script answers who it is (`status`) → new names are saved as PENDING on the server (`register`) →
  Admin approves on his own phone → staff sets/enters PIN → the script checks the PIN hash (`setpin`/`login`) and
  returns a **session token**, stored as `<APP_ID>_tok`. Every data/admin call needs that token **or** the old team code.
  - Open calls (`status`, `register`, `login`, `setpin`) run under the script lock; `login` locks a name after 5 wrong PINs per hour (server side, as well as on the phone); `register` is capped at 30 new requests per hour per app.
  - Token phones only receive their **own** PIN hash; other users come with `hasPin` instead. Admin block/unblock keeps a user's PIN; "Reset PIN" sends `pinReset`.
  - A staff token can't change other users, statuses or Admin rights. A blocked user's token stops working at once.
  - `TEAM_CODE` in Script Properties is now OPTIONAL and still accepted, so apps that send a code keep working.
  - Red **Not connected** banner (EN/FR/AR) with Try again, on the sign-in card and in the app, only when the script can't be reached or refuses us, or when `SYNC_URL` is missing. Queued records are sent as soon as it connects.
  - Optional join link `https://…/app/#k=CODE`: the code is saved for this app only and wiped from the address bar.
  - `apply_config.py`: QR with the app logo in the centre (error correction H, logo 22% on a white rounded pad, plain QR if no logo).
  - Tests: sections 12–14 (fresh install with no code, Admin approval on another phone, record sync, rejected calls without token/code, staff can't change approvals, server PIN lock, reinstall re-sign-in, no data mixing, banner in 3 languages) plus the QR decode check. 111 passed.

### Carry v4 into Fuel (then Purchases, GRV, Food — one app at a time, Johan's OK before publishing)
1. **Script first.** Open the app's Apps Script, replace `Code.gs` with the base `sync/Code.gs`, but keep the app's own `rebuildViews_` tabs (the part under `APP VIEWS GO HERE`) and check `ADMIN_NAME` / `ADMIN_ALIASES` at the top.
   Keep `TEAM_CODE` in Script Properties for now (live phones still send it).
   **Deploy → Manage deployments → Edit (pencil) → Version: New version → Deploy.** Saving the file is NOT enough; without a new version the old code keeps running. The /exec link does not change.
   Check: open the /exec link in a browser → `{"ok":true,…}`.
2. **App.** In the app's `index.html`, copy from the base everything outside CONFIG and outside APP FEATURES START/END (or diff and port these blocks: join link after `window.TMC={P:P,L:L}`, the `sTok/tokMode/syncOn/api` block, `syncNow` (relog + token), `signOut`, `srvLookup/gotToken/lookup`, `checkPin`, `setPin`, `bindSignin` fCheck, `bindUsers` reset, `usersHTML` reset button, `paintNc/paintSync`, the `ncW` divs in `card()` and `render()`, `.ncW` CSS, texts `ncT/ncH/ncOff` in EN/FR/AR, the probe at the end).
   Apps that wrap `bindMain`/`bindWork`/`workHTML` (Fuel does) keep their wrappers in the features block.
3. CONFIG: `SYNC_URL` = the app's /exec link, **`SYNC_CODE` = ""**. Raise `VER`. Run `python3 tools/apply_config.py` (copy the base `tools/apply_config.py` for the logo QR).
4. Copy `tests/run_all.py` and `tests/gas_server.js` from the base and run `python3 tests/run_all.py <app>` — must be 0 failed.
5. Send screenshots to Johan, publish only after his OK. Phone check: fresh install, new name → pending → Admin approves → PIN → add one record → see it in the Sheet.
6. Phones that already have a code saved in Settings keep using it. To move everyone to tokens later: remove `TEAM_CODE` from Script Properties and deploy a new version (phones with an old code then show "Not connected"; Admin clears the code in Settings and signs in again).
   Purchases/GRV/Food have different internal names (table above); port the same steps by hand there.

## App logo (house style)
All TMC apps use one logo layout: cream background, green rounded frame, green Africa, a small symbol, dark-green label bar.
Make it with: `python3 tools/make_logo.py <app_dir> <symbol> "<Label>"` (symbols: box, coin, pot, fuel, or a file with an SVG fragment).
It writes every icon file (icon.svg, icon-maskable.svg, icon-192/512, icon-maskable-512, apple-touch-icon, favicon-32) and tools/logo.png,
so a later apply_config.py run uses the same logo. Bump the app version afterwards so phones pick it up.

## Same look rule
Every app must pass `python3 tools/same_look.py <app>` (also run inside tests/run_all.py). Apps must use the base CSS, sign-in card, header, bottom menu, tiles, language picker, banners and v4 token sync.

## Update request rule (Johan, 25 Oct 2026)
Every app bot asks Johan for go-live in exactly this format, every time:

🔄 Update request: [App] v[number]
What's new: [1-2 short lines]
Your data and sync: stay the same / change
Tests: passed
Put it live? Yes / No

## Standard Reports screen (📊 Reports)
- `TMC.addReport({id,title,cols:[{key,label,num,d,sum}],rows:(from,to)=>[...]})` — apps plug in their own reports; the base demo is "Notes per person" (inside APP FEATURES).
- Tab + Home tile come from the one `tabsOf()` list; shown only to Admin or users with the 📊 Reports tick (`TMC.repOk`).
- Screen: Today / This month / Pick dates → green REPORT_COLOR table (totals row) → 📥 Download Excel (no-library .xlsx, green, SUM formulas) / 🖨️ Print (buttons hidden in print) / ⬅ Back. EN/FR/AR, fits 360px.
- Tests: section 19 in `tests/run_all.py`.

- **v7 — Block / Reject = DISCARD (Johan, 31 Oct 2026).** On the Users screen ❌ Reject and ⛔ Block open a red confirm card
  (big "🗑️ Yes, remove" / "↩️ Back"). Yes takes the user record off the list, off the phone store and off the Sheet. There is no
  Removed list and no Unblock any more. The person's old PIN and token stop working, and a phone signed in as that person is signed out on its next sync.
  The person can later send a fresh request ("Not approved, send a new request" screen), which arrives as Pending. Guards: never yourself, never the last
  Admin, and only an Admin with a token (staff or team code are refused). Older blocked or rejected records show "🗑️ Remove". Cache `tmcbase-v7` (the base has no icon `?v=`).
  - **SERVER CHANGE (sync/Code.gs, base copy only, NOT deployed):** `discard_()` accepts a user delete marked `data.discarded:1`
    only from an Admin token (not self, not the last Admin), deletes that user's `TOK_` tokens and stores the delete. Refusals return
    `refusedWhy` and `refusedDiscard`. Deploy the new Code.gs only after the phones are on v7. Until then, old phones still show Block/Reject the old way.
  - Tests: `tests/run_all.py` section 3 and the token section, plus `tests/discard_unit.js` (last-Admin, self, staff and team-code guards).
  - Also in v7: **redraw guard** (from tmc-service/patches/redraw-guard.patch). Once the user types, ticks or picks in a form, a background sync no longer redraws and wipes it.
    The new data shows on the next screen change. Fields marked `data-nodirty` and the language picker don't count. Checked by `tests/test_redraw_guard.py`, which runs as suite section 21.
  - Also in v7: **the main Admin can never be removed or blocked** (`templateadmin` and every `ADMIN_ALIASES` name). The phone shows no Remove/Block button for them.
    The server (SERVER CHANGE in `discard_()`) refuses any delete, purge or blocked/rejected/removed status for that user from anyone, with `refusedWhy: "main_admin"`. Tests: section 3b, the token section and `tests/discard_unit.js`.
  - Main Admin rule, part 2: also **never demoted** (admin off) **or renamed away** from the main name, on the phone (`put()` refuses) and on the server (`main_admin`). Reset PIN and re-spelling with an alias name are still allowed.
    Only an **approved** Admin is protected, so a pending request using an alias name can still be rejected.

- **v9 — photos to Drive (Johan, 1 Nov 2026).** Photos are made small (max 800px, JPEG 0.5, stepping down to 0.4/0.3 until about 100 KB at most), kept in this app's own phone queue (IndexedDB `<APP_ID>_photos`) until the upload works, then sent with `action:"photo"`. The server keeps them in a Drive folder that only this app makes and knows (Script Property `PHOTO_FOLDER_ID`, never searched by name) and writes a `pl` record holding the Drive link. Phones can never write `pl` records. Admins get a big **View photo** button (`TMC.phBtn(id)`), which fetches the picture with `action:"photoget"` using an Admin token only. The daily `photoCleanup` trigger (added by `setupOnce`) puts photos older than 60 days in the Drive bin. The rows stay, marked "photo removed". `TMC.phBackfill(list)` sends old phone photos in batches of 2 and skips any older than 2 months. The app calls `TMC.phKeep(dataUrl, ref)` and stores the returned id in its own record (for example `meterPh`). **Adds the Drive permission**, so Johan must run `setupOnce` once and click Allow before the new server version is deployed. Tests: section 22.
- **v10 — big "← Back" at the top (Johan, 1 Nov 2026).** Every screen except Home has a large, full-width "← Back" bar as the first thing in `#view` (EN/FR/AF, plus AR when the app has it). It goes one level up inside a screen first (report detail → report list, plus app hooks in `TMC.nav.ups`), and reuses a screen's own top Back button when the app lists it in `TMC.nav.sel` (made big; that button keeps its own action). Otherwise it goes to the previous screen, or Home when there is no history. Typed but unsaved input (still unsaved after a redraw of the same screen) asks "Leave without saving?" Yes / No first. Yes drops that screen's drafts. The bottom tabs are unchanged. Apps extend this with `TMC.nav.keys`/`sets` for their own sub-screens, and with `dirty` and `clear`. Block: `/* VER 10 BACK */` before the first `render();`. Tests: section 23 (`tests/test_back.py`). Server code is unchanged.

**v10.1 (style only):** Back bar is light grey (#E5E7EB) with dark (#1F2937) bold centred text, same size and rounding as the app's big buttons; hidden when printing.


## VER 12 — Save closes the form (Johan, 5 Nov 2026)
After a **successful** Save, the form closes and the app returns to the previous screen (same as the grey ← Back). If Save fails (validation or `put`/`remove` returned false), stay on the form and keep what was typed. Offline saves that are queued on the phone count as success.

**Helper:** `TMC.afterSave(ok)` in the `/* VER 10 BACK */` block. Call it from the form Save handler after `put(...)!==false` (and clear drafts). Do **not** auto-go-back from `put` itself — only form Saves. `put`/`remove` now return `true` on success and `false` on refuse.

**Apps copy:** after each successful form Save, replace `render()` with `TMC.afterSave(true)` (or `afterSave(true)` inside the base IIFE). On validation fail, `return` without calling it. Carry the `afterSave` function + `window.TMC.afterSave` export from the base block. Tests: section 25 (`tests/test_save_close.py`). Server code is unchanged.

## VER 11 — Auto-update on open (Johan, 2 Nov 2026)
On open and when the app comes back to the front it checks for a new version. If one is found: saves are
blocked (`TMC.put`/`TMC.remove` return false with a toast), a full-screen "Updating… please wait" shows
(`#updGo`, strings `updGo`/`updGo2`), the new service worker is activated (`skip` message → skipWaiting +
clients.claim) and the page reloads. Offline or check fails: nothing happens, app works, retry next open.
A stuck download frees the lock after 45 s. Saved records stay in localStorage/IndexedDB (APP_ID_ keys), so
queued unsynced work survives. sw.js / cache names unchanged. Test: tests/test_autoupdate.py (run_all §24).
Server (Code.gs) updates can go out once the staff who are at work have opened the app.
