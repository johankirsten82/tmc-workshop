# Workshop build reference — READ FIRST

This is a sanitized packaging copy of the existing TMC Base VER 12, not a release or permission to deploy. Originals were not changed.

## Scope and overriding constraints
- Build a NEW, separate TMC Workshop sample: named build/repair jobs, every piece of steel/material and every rope length charged to its job, plus completed-job photo.
- Sample first; no publishing without Johan's explicit approval through TMC Base. Base has the last say. App bots report results/blockers only to Base.
- No live Sheet, deployment, server update, other-app edit, or shared data is authorized by this reference package.
- Unique app identity, storage keys, cache, manifest, users/PINs, Sheet, Code.gs and photo folder. Never reuse Base or another app's live configuration/data.
- Keep base house style and big buttons. Each button opens its own screen with grey Back. Successful Save closes form; failed Save keeps entered data. Fixes belong in Base first.
- Run base suite and Workshop-specific tests; show sharp phone-width samples (deviceScaleFactor 3, tightly cropped). Do not claim existing historical test counts as new verification.
- Server Code.gs changes remain held until phones update and Johan separately approves.
- PAUSED: the Arabic-to-Afrikaans migration in AFRIKAANS_CHANGE.md is NOT authorized Workshop work. That file is historical reference only. Preserve the supplied base language behavior; do not perform a language migration or propagate one to other apps.
- Historical README instructions (including "script first", deployment, cross-app migration, and old language examples) are reference, not authorization, and do not override these constraints.

## Sanitization
Included source, tests, tools, icons, shared assets, sync and all existing root rules/docs. Excluded backups, screenshots, test-output logs, caches and repository metadata. No staff records included. SYNC_URL, SYNC_CODE and SHARE_URL were already empty and remain empty; TEAM_CODE_SETUP remains __TMC_TEAM_CODE__. Admin identity/aliases replaced consistently with Template Admin/templateadmin (and numbered alias fixtures). These are placeholders, NOT authorized production identity configuration. No live deployment endpoints or credential-pattern values found in the included text. Mock-only test tokens, code strings and localhost/example URLs remain test fixtures. Existing base icons/logo remain reference assets; generate Workshop's own identity later.

## Existing reference docs
README.md: architecture, configuration, tests, reports, offline/sync, photo queue/Drive retention, grey Back, auto-update, successful-Save close.
BOT_RULES.md: common house style, strict data isolation, Base sign-off and server sequencing.
SAME_LOOK_FIX.md: shared UI/sign-in/sync rules and checks.
AFRIKAANS_CHANGE.md: PAUSED historical migration; not a task.
sync/SETUP_CARD.md: Base-only standard setup card; do not send or execute during sample work.
tests/admin_fix_test_spec.md: mock-server Admin-fix verification.

Packaging validation only; no runtime tests run or behavior investigation performed.
