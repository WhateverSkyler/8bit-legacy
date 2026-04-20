# Cowork Session Handoff — 2026-04-20 Google OAuth for YouTube Uploads

**Session:** Claude in Cowork mode (Tristan's desktop)
**Started:** 2026-04-20 ~1:00 PM EDT
**Brief:** `docs/claude-cowork-brief-2026-04-20-google-oauth.md`
**Status:** Task 1 GREEN · Tasks 2+3 DEFERRED to Claude Code (see below)

---

## What's done (GREEN)

### Pre-flight
- **Google account owning `@8bitlegacyretro`:** `sideshowtristan@gmail.com` (confirmed by Tristan)
- **GCP project:** **Reused existing `CS 3335`** (project ID `cs-3335-286915`) — `sideshowtristan@gmail.com` hit the GCP project creation limit (existing: CS 3335, CS 3330). Reuse was the cheaper option and YouTube Data API v3 was already enabled on it from prior work.

### Task 1a — GCP project / API
- Project: `cs-3335-286915` (display name "CS 3335"), signed-in as `sideshowtristan@gmail.com` (authuser=2)
- YouTube Data API v3: already enabled (pre-existing on CS 3335)

### Task 1b — OAuth consent screen
- Publishing status: **Testing** (7-day refresh token limit accepted — see brief)
- User type: **External**
- App branding was pre-existing as "Navi" (left intact — it's Tristan's brand from other projects)
- Support email: `sideshowtristan@gmail.com`
- **Scopes added** (both required):
  - `https://www.googleapis.com/auth/youtube.upload`
  - `https://www.googleapis.com/auth/youtube`
- **Test users** (2/100):
  - `sideshowtristan@gmail.com` (the auth account)
  - `tristanaddi1@gmail.com` (backup)

### Task 1c — OAuth 2.0 Desktop Client
- **Name:** `8bit-pipeline-desktop`
- **Application type:** Desktop app (verified — generates `"installed"` JSON key)
- **Client ID prefix:** `90905522101-08vedc95...` (full ID ends with `.apps.googleusercontent.com`)
- **Created:** 2026-04-20 1:33:51 PM EDT
- **Status:** Enabled
- **JSON downloaded to:** Tristan's Mac `~/Downloads/` via the Download JSON button in the created-client dialog
- Pre-existing `Navi` Desktop client (Jan 31, 2026) left untouched

---

## What's NOT done — deferred to Claude Code

### Task 2 — SCP the JSON to TrueNAS
Cowork's sandbox can't reach the 192.168.4.2 LAN. Claude Code on the Mac should run:

```bash
scp -i ~/.ssh/id_ed25519 ~/Downloads/oauth2client.json \
  truenas_admin@192.168.4.2:/mnt/pool/apps/8bit-pipeline/config/oauth2client.json

# Verify
ssh -i ~/.ssh/id_ed25519 truenas_admin@192.168.4.2 \
  'ls -la /mnt/pool/apps/8bit-pipeline/config/oauth2client.json && \
   python3 -c "import json; d=json.load(open(\"/mnt/pool/apps/8bit-pipeline/config/oauth2client.json\")); print(\"client_type:\", list(d.keys())[0]); print(\"client_id prefix:\", d[list(d.keys())[0]][\"client_id\"][:20])"'
```

Expected: `client_type: installed`, `client_id prefix: 90905522101-08vedc95`.

### Task 3 — Local JSON validation
Optional — skip if `.venv` / google-auth aren't installed on the Mac. The `client_type: installed` + `client_id` prefix from the SSH verify above is the real gate.

---

## Client-created dialog values (for Tristan's reference only — DO NOT post in chat or commit)

The `client_secret` was shown in the dialog before it was closed. It is NOT reproduced here; it lives only inside the downloaded `~/Downloads/oauth2client.json` and (after SCP) inside `/mnt/pool/apps/8bit-pipeline/config/oauth2client.json`. If the Download JSON file is lost or looks wrong after SCP, the client must be re-created (deleting the old one) — the secret is not retrievable from the console after the creation dialog closes.

---

## What happens next (handoff for Tristan — Task 4 of the brief)

After Claude Code finishes the SCP + validation:

1. Deploy: from the repo root, run `./deploy/deploy-to-truenas.sh`.
2. Container starts, watcher idles until content drops.
3. When the first podcast drop lands and hits stage `yt_upload`, the container logs print:
   ```
   Please visit this URL to authorize this application:
   https://accounts.google.com/o/oauth2/auth?...
   ```
4. Visit the URL in any browser (the flow isn't tied to the TrueNAS host).
5. Sign in with `sideshowtristan@gmail.com` → pick the 8-Bit Legacy channel → grant upload + manage permissions.
6. The page prints a code; paste it back into the container console (via `docker attach 8bit-pipeline`).
7. The container caches the refresh token at `/app/config/.yt_token.json` (persistent via bind mount).
8. Subsequent uploads (the other 7 topic videos of the drop + all future drops) reuse the cached token silently.
9. **7-day refresh limit**: Testing-mode OAuth apps rotate refresh tokens every 7 days. When it expires, the pipeline emits a Navi task and re-auth is a ~30-sec browser click. Moving the app to "Production" removes this limit but triggers Google's 2–4 week verification review — defer until the pipeline has been running smoothly.

---

## Guardrail audit
- [x] OAuth app left in **Testing** (not published to Production)
- [x] `client_secret` not posted in chat / not committed / not in any log
- [x] `oauth2client.json` not staged in the repo (Cowork sandbox copy is at `/sessions/jolly-lucid-carson/oauth2client.json` — NOT in the repo tree and NOT committed)
- [x] Scopes limited to `youtube.upload` + `youtube` (no `.force-ssl`, no membership scopes)
- [x] Google Ads account untouched
- [x] No Google verification errors encountered during scope setup

---

## Issues encountered

- **Chrome extension sporadically returned "Cannot access a chrome-extension:// URL of different extension"** when attempting saves inside the GCP console. Worked around by navigating the tab fresh and using JavaScript click for the Add users → Save submission. Otherwise the flow was clean.
- **GCP project creation limit hit** on `sideshowtristan@gmail.com` — reused existing CS 3335 instead of creating a new `8-Bit Legacy Podcast Automation` project. Functionally equivalent; the console just shows the YouTube API sharing a project with whatever else lived there. Nothing in that project references 8-Bit Legacy by name, so there's no confusion risk.
