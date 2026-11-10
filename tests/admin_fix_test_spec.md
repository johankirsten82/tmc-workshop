# Admin fix test (spec), required for the base and every TMC app

Written 2026-10-31 by Base (read-only audit). Not yet coded into run_all.py.

## Rule this test protects
Only the **role and the token** decide who may fix (edit, delete, reopen, undo) a saved record.
A saved team code must **never** turn a signed-in Admin into staff, either on the phone or on the server.

* Admin, signed in, token saved, **with or without** a team code saved: sees ✏️/Delete/Reopen/Undo, and the server **accepts** the fix.
* Staff, signed in with a token (with or without a code): no ✏️, and the server refuses (`admin_only_fix`).
* A code-only phone (team code, no token): no ✏️, and the server refuses (`admin_only_fix`).
* Phone and server must agree: if the phone shows ✏️, the server must accept. A silent bounce is a FAIL.

## Two ways this went wrong (seen 2026-10-31)
1. **Phone hides the button**: canFix() returns false when a code is saved, even with a token (Purchases pp5, Food fi-v33).
2. **Phone shows, server refuses**: the phone sends `code` *and* `token`, and the server checks `code` first, so the Admin is treated as staff (base v5, Fuel, GRV, Rotation, Service, Money, Production). The edit stays on that phone only, with no message.

## Required client behaviour (base pattern)
* `canFix()` = signed-in user is Admin **and** (`token saved` **or** `no team code saved`).
* The sync/report/export body sends **`token` when a token exists, `code` only when there is no token**.
* A signed-in Admin on a code phone gets a token (re-login with its own PIN hash), even when a code is saved.
* If the server answers `refusedWhy:"admin_only_fix"`, show a toast. Never drop it silently.

## Test cases (mock server = real sync/Code.gs in tests/gas_server.js with TEAM_CODE=TESTCODE)
Seed: an Admin "Template Admin" with a PIN, a staff user "Staff Test" with a PIN, and one saved record R (e.g. kind `x`).

### A. Server only (raw POST, no browser)
| # | Request | Expect |
|---|---------|--------|
| A1 | sync, Admin token only, change R | accepted=1, no refusedWhy, Fix log row written |
| A2 | sync, Admin token **+ team code**, change R | accepted=1, no refusedWhy (FAILS today on all servers: code wins) |
| A3 | sync, staff token, change R | accepted=0, refusedWhy=admin_only_fix |
| A4 | sync, staff token + team code, change R | accepted=0, refusedWhy=admin_only_fix |
| A5 | sync, team code only, change R | accepted=0, refusedWhy=admin_only_fix |
| A6 | sync, team code only, add new record | accepted=1 (staff may add) |
| A7 | sync, Admin token + wrong code | bad_code or accepted as token, never accepted as staff silently |

If the server is not changed, A2 may instead be covered by B3 (the phone never sends the code when it has a token). At least one of A2 or B3 must prove the Admin fix lands on the server.

### B. Phone (Playwright, phone viewport, two contexts)
| # | Phone state | Expect |
|---|-------------|--------|
| B1 | Admin signed in, token, no code | canFix()=true, ✏️/Delete/Reopen/Undo visible; fix syncs; server copy changed |
| B2 | Admin signed in, token, **team code saved** (Settings → Sync, or `#k=` link) | canFix()=true, buttons visible |
| B3 | same as B2, do a fix, Sync now | request body has `token` and **no `code`**; server copy changed; a 2nd phone sees the fix |
| B4 | Admin on a code phone with **no token** yet, Sync now | phone gets a token (login with its PIN hash), then B2/B3 pass |
| B5 | Staff signed in, token, with and without code | canFix()=false, no ✏️; a forced TMC.put/fix on an existing record is refused locally (fixOnly) |
| B6 | Code-only phone (no user token) | canFix()=false, no ✏️ |
| B7 | Admin fix refused by server (forced) | toast shown, record not left changed only on this phone |
| B8 | Log out, then log in as staff on the same phone | ✏️ gone (no leftover Admin state) |

Every app maps "✏️/Delete/Reopen/Undo" to its own buttons (Purchases: Paid history ✏️, Reopen batch, Undo last paid, order delete; Food: item edit/delete; GRV: canEdit buttons; base family: fixBtn/bindFix/remove).

## How to run
`python3 tests/run_all.py /path/app` must include a section `## Admin fix: token beats team code` with A1-A7 and B1-B8, and exit 0. Base runs it first; each bot runs it on its newest version before asking for "Signed off – go live".
