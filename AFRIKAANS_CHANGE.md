> PAUSED / NOT AUTHORIZED for Workshop work. Historical reference only; do not execute this migration. See WORKSHOP_REFERENCE_READ_FIRST.md.

# Arabic out, Afrikaans in — steps for each app bot

Base did this first in TMC Base **VER 5** (cache `tmcbase-v5`). Base test: 367 passed, 0 failed.
Do the same in **your own app only**, from your **latest live version**. Never copy another app's data, Sheet, keys or users.

Languages after the change: **English (en), French (fr), Afrikaans (af)**. No Arabic. No right-to-left.

## Steps

1. **Start from your latest version.** Work in your own app folder only.

2. **Text tables.** In your texts object (`T`/`TMC.T`):
   - Delete the whole `ar:{...}` table.
   - Add an `af:{...}` table with **every key that `en` has**. Nothing missing, nothing empty.
   - The base keys: copy the `af:{...}` table from `/workspace/tmc-base/index.html` as-is (same words in every app).
   - Your own app keys: translate them yourself (see "How to write the Afrikaans" below).

3. **Every other `ar` text.** Search your files for `ar:`, `"ar"`, `'ar'` and Arabic letters (`grep -nP '[\x{0600}-\x{06FF}]'`).
   - Labels written as `{en:..,fr:..,ar:..}` (CONFIG `PERMS`, report titles, column names, tiles, item lists) → change `ar` to `af` with the Afrikaans word.
   - At the end, the grep must find **no** Arabic letters.

4. **Language pickers** (sign-in, Settings, header):
   - List `["en","fr","af"]`.
   - Names: `English`, `Français`, `Afrikaans`. Header short button shows `AF`.

5. **Fallback from `ar` to `en`.** Replace the start-language line with (keep your own storage helper):
   ```js
   let lang=L.get("lang");if(lang&&!T[lang]){lang="en";L.set("lang","en")}   // old "ar" or unknown → English, saved
   if(!lang){const nl=(navigator.language||"en").slice(0,2).toLowerCase();lang=T[nl]?nl:"en"}
   if(!T[lang])lang="en";
   ```
   A phone that had Arabic saved now opens in English and saves `en`.

6. **Remove right-to-left.**
   - `document.documentElement.dir=lang==="ar"?"rtl":"ltr"` → `document.documentElement.dir="ltr"`.
   - Remove any `direction:rtl`/`direction:ltr` fix-ups, `unicode-bidi`, `[dir=rtl]` CSS rules and Arabic fonts (`@font-face`, Google Fonts links for Arabic, Noto Arabic, etc.).
   - Dates: `"ar-TD"` → `lang==="af"?"af-ZA":lang==="fr"?"fr-FR":"en-GB"`.

7. **Apply the base Admin-fix (see tests/admin_fix_test_spec.md) in the same version.**
   - Sync body: send NO team code when a token exists (`code:sTok()?undefined:(sCode()||undefined)`), in sync AND in reports/export calls.
   - An Admin on a team-code phone with no token logs in with their own PIN hash to get a token; if that login fails, keep syncing by code (do not sign out).
   - `canFix()` = Admin role AND (token, or no team code at all). A team code alone never lets anyone fix.
   - When the server answers `refusedWhy:"admin_only_fix"`: show the plain message `fixRef` (en/fr/af) and pull the server copy back, so the phone never shows a fix that was not saved.
   - Log out always deletes the token.
   - Base VER 6 (`index.html`) has the exact code; copy it, keep your own app's texts. Base suite section 20 checks it (A1–A7, B1–B8).

8. **Bump the version** (`VER` +1) and the cache name, the normal way for your app (`tools/apply_config.py` or your own `sw.js`). Keep your own manifest id.

9. **Tests.**
   - Run the base suite against your app: `python3 /workspace/tmc-base/tests/run_all.py <your app folder>`.
     It now checks: af present, ar gone, no RTL, every en key has an af key, `ar` saved → English, pickers show AF.
   - Swap any Arabic checks in your own tests for Afrikaans (e.g. button `Gaan aan`, tab `Tuis`, banner `Nie gekoppel nie`, direction always `ltr`).
   - Everything must pass.

10. **Screenshots.** Phone size (390×844): sign-in and Home in Afrikaans, plus one of your own main screens in Afrikaans. Look at them: no word broken in the middle in the bottom tabs, nothing cut off.

11. **Send to TMC Base** for testing with the screenshots and test result. **Do not publish** until Base says "Signed off – go live". Server `Code.gs` is not part of this change.

## How to write the Afrikaans

For staff with little schooling. Everyday South African Afrikaans.
- Short, common words. One idea per sentence. Speak to the user as **jy**.
- Buttons: a short verb first: `Stoor`, `Stuur`, `Kies`, `Maak reg`, `Vee uit`, `Kyk weer`.
- Keep words staff already know from their phone: **Admin, PIN, Sheet, Excel, Sync, app**.
- Keep emojis, `%n`, `%m` and other placeholders exactly as in English.
- Bottom tab labels must fit: about 8 letters max per word (6 tabs at 360 px).

Use the same words as the base:

| English | Afrikaans |
|---|---|
| Home | Tuis |
| Work | Werk |
| Reports | Verslae |
| Users | Mense |
| Settings | Instel |
| What I can do | Wat ek mag doen |
| Save | Stoor |
| Continue | Gaan aan |
| Back | Terug |
| Log out | Teken uit |
| Sync now | Sync nou |
| Update now | Opdateer nou |
| Approve / Reject | Keur goed / Keur af |
| Block / Unblock | Blok / Ontblok |
| Fix (a mistake) | Maak reg |
| Delete | Vee uit |
| Today / This month / Pick dates | Vandag / Hierdie maand / Kies datums |
| Total / Count | Totaal / Aantal |
| Download Excel / Print | Laai Excel af / Druk |
| Not connected | Nie gekoppel nie |
| Waiting | Wag |
| Ask the Admin | Vra die Admin |
