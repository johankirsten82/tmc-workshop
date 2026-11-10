> Workshop packaging: read WORKSHOP_REFERENCE_READ_FIRST.md first. No deployment or language migration is authorized.

# TMC bot rules (every TMC app bot works exactly the same way)
1. Build only on the TMC base (/workspace/tmc-base). Same sign-in, Home, Reports, Settings, languages, sync, update flow, white house-style logo (one-word label), "TMC <App>" under the icon, unique manifest id.
2. Own data only: own Sheet, Code.gs, storage keys, cache, users, PINs. Never touch another app's files or data.
3. Every change: run the base suite + app tests, then send to TMC Base for sign-off. Publish only after "Signed off – go live". Server Code.gs goes live only after phones have updated.
4. Talking to Johan: short, plain, his language. One message when a change is live. Never send setup steps, trial-and-error phone steps, or tech details; TMC Base sends the one fixed setup card.
5. Ask Johan only what only he knows; get everything else from files or other TMC bots.
6. Fixes found in one app go to TMC Base first, then to every app.
