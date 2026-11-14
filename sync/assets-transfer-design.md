# Workshop → TMC Assets transfer (design only)

**Not connected. Not deployed. Not agreed.**

This is a proposed server-to-server contract, in the same shape as `stock-transfer-contract-v1.md` (Food → Workshop/Service stock). Workshop would send finished items to TMC Assets. Assets would assign a tent and a person. Camp is **10 Alfa**.

It needs **the TMC Assets bot's agreement** and **Johan's yes** before anyone writes Code.gs, turns a link on, or sends a real item. Until then the Workshop phone only keeps a local "Send to Assets" list. Nothing is posted.

## Apps

| Role | App | `APP_ID` / `sourceApp` |
| --- | --- | --- |
| Sender | TMC Workshop | `tmcworkshop` |
| Receiver | TMC Assets | The Assets app's own public `APP_ID` (Workshop does not invent one) |

Do not share a Sheet, cache, user list, or PIN. Do not reuse the Food stock-transfer import code, the team code, or any other app's `/exec` URL.

## What Workshop would send

A finished item already on the Workshop "Send to Assets" list. Both kinds go to Assets **the same way**, with the **same action and the same payload shape**:

- **A finished Build job** (the main source). The existing jobs in the Work list are the source, read unchanged (v4 job records `{id, name, type:"build", by, at, example}` included). Two ways for Admin to finish one:
  - **Job finished: send to Assets** on a job with a cut list (`builtBefore: false`, with `jobId` / `jobName`). The cut list already took its metres off stock.
  - **Already built (in use)** on an existing job that was built before (e.g. Shaun Bed, Johan Side Table). Admin adds the materials and the size, then taps Send to Assets (`builtBefore: true`, **with** `jobId` / `jobName`). By default no stock is taken. A **Take off stock** switch (default OFF) takes the metres off Workshop stock like a cut list (`tookStock: true`).
- **Added by Admin as Built before** with no job (`builtBefore: true`, `jobId` and `jobName` empty, no stock taken).

A built-before item **may carry a `jobId`** when it comes from an existing job. `builtBefore` with an empty `jobId` means it was added without a job.

The job record itself is never changed or rewritten. The finished state comes from the queued item (`fa` record id `fa-<jobId>`, one per job).

**Suggested person.** The person in the job name is sent as `suggestedPerson`: the leading word(s) before the item word ("Shaun Bed" → `Shaun` + `Bed`, "Johan Side Table" → `Johan` + `Side Table`). Admin can edit the item name and the person before saving. It is only a suggestion; Assets staff still choose who has it.

The "Send to Assets" list treats them the same: both sit on the list with status `waiting` ("Waiting for Assets") and are sent with this contract. The `builtBefore` flag only records how the item was added. It is not a different transfer.

Each item is sent once. A retry uses the same id and must not create a second item in Assets.

## How Workshop would send (future)

Same shape as Food's stock handover: the Workshop Apps Script POSTs `text/plain` JSON to the Assets `/exec`. The phone never holds the Assets URL or import code.

Script properties (all empty until Johan approves a deployment):

| Property | Meaning |
| --- | --- |
| `ASSETS_URL` | Assets web app `/exec` URL |
| `ASSETS_CODE` | Assets import code for this action only |
| `ASSETS_APP_ID` | Assets public `APP_ID` |

If any of these is empty, Workshop keeps the item `waiting` and does not mark it sent.

Proposed action name: `importFinishedItem` (Assets may choose another name when they agree).

## Request

`POST` the Assets `/exec` with `Content-Type: text/plain;charset=utf-8`.

```json
{
  "action": "importFinishedItem",
  "code": "<Assets import code>",
  "item": {
    "id": "stable-item-id",
    "v": 1,
    "sourceApp": "tmcworkshop",
    "sourceItemId": "stable-item-id",
    "destinationApp": "<assets-app-id>",
    "at": "2026-11-11T17:00:00.000Z",
    "by": "Staff display name",
    "camp": "10 Alfa",
    "name": "Bed",
    "qty": "2",
    "size": "optional size or description",
    "jobId": "j1234567890",
    "jobName": "Ward beds",
    "suggestedPerson": "",
    "materials": [],
    "builtBefore": false
  }
}
```

An existing job that was already built (in use) uses the same body with `builtBefore: true`, the job id and name, the suggested person, the size and its materials:

```json
{
  "action": "importFinishedItem",
  "code": "<Assets import code>",
  "item": {
    "id": "stable-item-id",
    "v": 1,
    "sourceApp": "tmcworkshop",
    "sourceItemId": "stable-item-id",
    "destinationApp": "<assets-app-id>",
    "at": "2026-11-11T17:00:00.000Z",
    "by": "Staff display name",
    "camp": "10 Alfa",
    "name": "Bed",
    "qty": "1",
    "size": "2 m x 1 m",
    "jobId": "j1794300000001",
    "jobName": "Shaun Bed",
    "suggestedPerson": "Shaun",
    "materials": [
      { "type": "Square tubing 40×40", "qty": "12", "unit": "m" },
      { "type": "Rope 10 mm", "qty": "8", "unit": "m" }
    ],
    "tookStock": false,
    "builtBefore": true
  }
}
```

Rules:

- `item.id` and `sourceItemId` are the same stable Workshop finished-item id (the `fa` record id). A retry sends the same id.
- `sourceApp` is always `tmcworkshop`. The receiver rejects any other value with `wrong_app` and writes nothing.
- `destinationApp` is the configured Assets app id. The receiver rejects any other value with `wrong_app` and writes nothing.
- `camp` is `10 Alfa`.
- `qty` is a decimal string. Dot is the separator. No exponent. The value must be greater than 0.
- `name` is at most 120 characters. `size` is at most 120.
- `builtBefore` is a boolean on this same payload. A job item with a cut list is `false`. A built-before item is `true`; it **may** carry `jobId` / `jobName` (from an existing job) or have them as empty strings (added without a job). There is no second endpoint or a different item body.
- `suggestedPerson` is a string (may be empty), at most 120 characters. It is a suggestion for who has the item; Assets decides.
- `materials` is a list (may be empty) of `{type, qty, unit}`: `type` is the steel type or rope (stock name or free text, at most 120 characters), `qty` is a decimal string like `qty` above, `unit` is `m`, `mm` or `pcs`. For an Already built job the list is pre-filled from that job's existing Add steel / Add rope records (Johan 14 Nov 02:45). Those rows were already taken off Workshop stock when they were added, so Workshop never deducts them again, even with Take off stock ON.
- `tookStock` (optional boolean) says whether Workshop took these metres off its own stock. Information only; Assets never changes Workshop stock.
- Ids match `^[A-Za-z0-9_-]{4,64}$`.
- `at` is ISO-8601 UTC. `by` is a display name for the audit line only.

The body must not contain PINs, PIN hashes, session tokens, team codes, user records, permissions, stock movements, or instructions to edit anything except this finished item.

## Response

Always JSON.

Accepted, including a retry of an item Assets already applied:

```json
{ "ok": true, "itemId": "stable-item-id", "result": "accepted" }
```

```json
{ "ok": true, "itemId": "stable-item-id", "result": "duplicate" }
```

`duplicate` means the item is already there. It is success for Workshop. It must not add a second item.

Refused. Assets has written nothing for this item:

```json
{ "ok": false, "error": "bad_code" }
```

`error` is one of `bad_code`, `wrong_app`, `bad_request`, `bad_qty`, `busy_try_again`.

## Sender status (Workshop)

| Situation | Workshop status | Item in Assets |
| --- | --- | --- |
| On the phone list, or the link is not configured, or the network failed | `waiting` (Waiting for Assets) for both job items and built-before items. Built-before items also show a "Built before" mark. | Not sent |
| Assets refused | `rejected` | Not sent |
| Assets returned `accepted` or `duplicate` | `sent` | Received once |

Workshop must not show the item as already in Assets while the status is `waiting` or `rejected`.

## What Assets would do (for agreement)

Inside Assets, in one lock, all or nothing:

1. If `item.id` was already applied, return `duplicate` and do not add it again.
2. Check `code`, `sourceApp`, `destinationApp`, `qty`, and the id shape.
3. Create the finished item once, with camp **10 Alfa**. A built-before item is stored the same way as a job item. The `builtBefore` flag and empty job fields are kept on the record; Assets does not treat it as a different kind of transfer.
4. Assets staff later assign a **tent** and a **person**. Workshop does not send tent or person. This is the same for job items and built-before items.
5. Return `accepted`.

## Open until Assets and Johan agree

- The exact action name and property names on the Assets script.
- When Workshop actually posts (Admin tap, or automatic after "Mark ready" / after adding a built-before item).

Settled on the Workshop side (Johan 11 Nov 2026, and 14 Nov 2026 02:27–02:29): built-before items use this same payload with `builtBefore: true`. Items from existing finished Build jobs keep the job id and name and add `suggestedPerson`, `size` and `materials`. They are not a separate contract.

Until that agreement and Johan's yes, do not change live `Code.gs` and do not connect this list.
