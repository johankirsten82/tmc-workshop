# Workshop → TMC Assets transfer, v2 (Workshop v1.6.0)

**Status: the contract is agreed with TMC Assets (14 Nov 2026, 06:17–06:32). Code.gs is a DRAFT and is NOT deployed.** It goes live only after phones are on v1.6.0, the two codes are filled in, and Johan says yes.

The style follows `stock-transfer-contract-v1.md`: server-to-server, `text/plain` JSON POST, idempotent by id, and each app keeps its own data (no shared Sheet, cache, users or PINs).

v2 changes since v1: location fields (camp + place), photo (https only), `by` = the worker who sends it, `type`, the final reply and error codes, the Script Property names, and `wsf-<id>`.

## Apps and settings

| | Value | Where |
| --- | --- | --- |
| Sender | TMC Workshop, `sourceApp: "tmcworkshop"` | `APP_ID` in Code.gs |
| Receiver | TMC Assets, `destinationApp: "tmcassets"` | `ASSETS.APP_ID` (can be overridden by the property `ASSETS_APP_ID`) |
| Assets URL | `https://script.google.com/macros/s/AKfycbx4YSwRNb7fRIWeaU3RZyTslblvkYwDcGn5TPzODOB-GKffBOt8ds9oOK1hx1DExUq5/exec` (public) | `ASSETS.URL` (can be overridden by `ASSETS_URL`) |
| Item code | for `importFinishedItem` | Script Property `ASSETS_WORKSHOP_CODE` (**empty in the draft**) |
| Locations read code | for `listLocations` | Script Property `ASSETS_LOCATIONS_READ` (**empty in the draft**) |

All Assets names (actions, property names, result and error words, field mapping) live in **one place**: the `ASSETS` object and `assetsItem_()` in `sync/Code.gs`. The phone never holds the Assets URL, the codes or the Assets action names.

If the URL, the app id or the item code is empty, nothing is sent and every item stays `waiting`.

## 1. Locations (read only)

The Workshop server asks Assets:

```
POST text/plain  {"action":"listLocations","code":"<ASSETS_LOCATIONS_READ>"}
→ {"ok":true,"locations":[{"id":"…","name":"10 Alfa","camp":"10 Alfa","places":[{"id":"…","name":"Store A"}]}]}
```

There is one row per camp, and `places` is `[]` when a camp has none. Camp names are shown exactly as Assets gives them in `name` (e.g. `HQ - Headquarters`, `GZ - Ground Zero`, `10 Alfa`, `Production`). The app hard-codes no camp names.

- **Server:** the action `assetsLocations` (signed-in token only) returns `{ok, locations, at}` from the Script cache, with a Script Property copy as the fallback. It refreshes from Assets at most once an hour. If Assets is offline, the last list is kept. With no read code it returns the cached list, or `[]`.
- **Phone:** it stores the list in `tmcworkshop_assetsLoc` (`{at, locations}`) and re-asks at most every 10 minutes while online. Camps and places are shown **A–Z, case-insensitive** (Johan 06:24). Assets already sends them sorted; the phone sorts again anyway.
- **Forms:** location is required on the worker finish form, the Admin "Already built (in use)" form, the "Add item built before" form and the Edit form. It is a big camp pick list, then the camp's places, plus an optional typed **Place** (max 60 characters).
  - A typed name that matches an existing place (same name, ignoring case and accents) reuses that place's id. Otherwise it is a new place: `placeId: ""` and `placeName` filled in.
  - A new place joins the phone's local list right away (re-sorted A–Z) until the next list comes from Assets.
- **No list** (empty or offline): saving is blocked with "Location list not loaded yet, try again with network". The message exists in all 4 languages.

## 2. Finished items

Sources (all go out the same way):

- **Worker:** "Job finished: send to Assets", the one button a worker sees on a Build job. `by` = the signed-in worker. The worker's added materials **always** come off Workshop stock; there is no switch.
  - Rows pre-filled from the v4 Add steel/rope records were already deducted then, so they are never deducted again.
  - A material not in stock, or more than is on hand, is refused with the existing message.
- **Admin, Build job with a cut list:** "Job finished: send to Assets" (unchanged; the cut list already took the metres off stock).
- **Admin only, old job:** "Already built (in use)", with `builtBefore: true`. Nothing comes off stock, and there is no switch.
- **Admin only:** "Add item built before" with no job.

There is no Admin check: saving puts the item on Send to Assets as `waiting` ("Waiting for Assets"). Admin can still Edit it, and **`by` stays the original worker**. The job record is never changed.

The phone record is `fa` (`fa-<jobId>` or `fa-b<time>`). Its status (`waiting` / `sent` / `rejected`) is **set only by the server**. The phone sees it through normal sync and shows "Waiting for Assets", "In Assets" or "Refused by Assets".

### Request

```
POST text/plain {"action":"importFinishedItem","code":"<ASSETS_WORKSHOP_CODE>","item":{
  "id":"fa-j1794300000002", "v":2, "sourceApp":"tmcworkshop", "sourceItemId":"fa-j1794300000002", "destinationApp":"tmcassets",
  "at":"2026-11-14T05:00:00.000Z", "by":"Pieter",
  "campId":"…", "campName":"10 Alfa", "placeId":"…", "placeName":"Store A",
  "name":"Bed", "type":"bed", "qty":"1", "size":"2 m x 1 m",
  "jobId":"j1794300000002", "jobName":"Ben Bed", "suggestedPerson":"Ben",
  "materials":[{"type":"Square tubing 40×40","qty":"3","unit":"m"}],
  "builtBefore":false, "photo":"https://…" }}
```

- **`by`:** the worker who sent it. Assets sets the item's **"Who has it" from `item.by`**. `suggestedPerson` (from the job name) is kept by Assets **as a note only** (Johan 06:32).
- **`type`:** mapped from the item name (en/fr/af/ar words). The order is table, bed, tent, container; anything else is `other`.
- **`qty`:** a decimal string with no exponent. One item carries its quantity; it is not split.
- **Fields:** `materials`, `jobId`, `size`, `builtBefore` and `suggestedPerson` go into Assets' More details.
- **Location:** `campId`, `campName`, `placeId`, `placeName`. A new place has `placeId:""` and `placeName` filled in (max 60), and Assets reuses a same-name place.
- **`photo`:** **an https URL only, never a data URL**, otherwise `""`.
  - Workshop photos are uploaded by the phone to *this* app's Drive folder (action `photo`). The `pl` record keeps `DriveFile.getUrl()`, and the item's `photo` (a photo id) is resolved to that URL.
  - The photo is optional. The finish form reuses the job's photo; if the job has none, it shows the same Add photo button and stores the photo like job photos.

### Reply and what Workshop does

| Reply | Workshop status |
| --- | --- |
| `{ok:true, itemId:"wsf-<id>", placeId, result:"accepted"}` | `sent` (keeps `assetsItemId`, and `placeId` from Assets) |
| `{ok:true, …, result:"duplicate"}` (already there, e.g. a lost reply) | `sent` |
| `{ok:false, error:"bad_request" \| "bad_qty" \| "bad_camp"}` (or another item refusal) | `rejected` (+ `rejectWhy`) |
| `{ok:false, error:"busy_try_again"}` | stays `waiting`; the run stops |
| `{ok:false, error:"bad_code" \| "wrong_app"}` (our settings) | stays `waiting`; the run stops |
| network error, non-2xx, bad JSON | stays `waiting` |

Assets stores the item as `wsf-<id>`, so sending the same id again returns `duplicate` and never creates a second item.

### When it sends

- On sync: the `fa` items that just came in with `waiting` are sent straight after the write.
- Time trigger `assetsRetry` every hour (added to `TRIGGERS`, installed by `setupOnce`): it sends every `waiting` item, at most 20 per run.
- Items already `sent` or `rejected` are never sent again. A phone resend cannot change the server-owned fields (`status`, `sentAt`, `assetsResult`, `assetsItemId`, `rejectWhy`, …); `keepAssets_` keeps them.

## Open points (TMC Assets / deploy)

1. Fill `ASSETS_WORKSHOP_CODE` and `ASSETS_LOCATIONS_READ` at deploy, then run `setupOnce` to add the hourly trigger. Deploy only after phones are on v1.6.0, and only with Johan's yes.
2. Photo links are Drive file URLs owned by the Workshop script. Assets can only show them if the file is shared (e.g. anyone with the link), and Workshop's `photoCleanup` trashes photos after 60 days. Assets should copy the image if it must keep it.
3. If Assets renames a field, change it in `assetsItem_()` only.
4. The `type` word list is a guess from item names; Assets can map `other` itself.
