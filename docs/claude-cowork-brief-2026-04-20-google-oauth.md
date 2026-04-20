# Claude Cowork Brief — 2026-04-20 (Google OAuth for YouTube Uploads)

**For:** Claude Code running on Tristan's Mac with browser/UI automation capability
**From:** Claude Opus running on the laptop (same repo, 8bit-legacy)
**Written:** 2026-04-20 12:56 PM EDT
**Goal:** Stand up the Google OAuth 2.0 credentials the 8bit-pipeline container needs to auto-upload the full podcast episode + 7 topic videos to YouTube. Download the `oauth2client.json`, ship it to the TrueNAS container config directory, verify via a test auth.

---

## Session start — mandatory

```bash
cd ~/Projects/8bit-legacy
git pull --ff-only
```

If pull fails, STOP and tell Tristan.

**Read these files:**
1. `CLAUDE.md` — project rules
2. `deploy/DEPLOY.md` — the broader pipeline deployment spec. Step 3 in the "One-time TrueNAS setup" section is what we're doing here.
3. `scripts/podcast/youtube_upload.py` — the script that will consume the credentials (worth skimming to understand what scopes are needed)
4. `docs/claude-cowork-brief-2026-04-20-zernio-setup.md` — the Zernio brief from earlier today. Same flow pattern (sign in → OAuth → drop credential into the right spot on TrueNAS → verify).
5. This brief.

---

## Context — what this credential is and why we need it

The 8bit-pipeline container on TrueNAS will auto-upload the full podcast episode + 7 topic videos directly to YouTube via Google's YouTube Data API v3. That requires an OAuth 2.0 Desktop Client credential — a JSON file with `client_id` + `client_secret`. On first use, the container prints an authorization URL to its logs; you (Tristan) visit that URL in a browser, approve the 8-Bit Legacy channel, paste the returned code, and the container caches a refresh token at `/app/config/.yt_token.json`. Subsequent uploads reuse the cached token.

**Zernio handles shorts + reels + tiktoks + YT Shorts.** This credential is *only* for full-episode + topic-video uploads (long form), which Zernio isn't built for. Manually editable via YouTube Studio after upload (thumbnails especially — Tristan said he'll replace those manually for now).

**Known ongoing friction:** Apps in "Testing" mode refresh tokens every 7 days. That's acceptable for now — when the pipeline's token expires, it emits a Navi task, and re-auth is a ~30 sec browser click. Publishing the app to "Production" removes this limit but takes 2-4 weeks of Google verification; defer that until the pipeline has been running smoothly for a while.

---

## Before you start — confirm with Tristan

**Google account for this OAuth credential:**
- The 8-Bit Legacy YouTube channel is `@8bitlegacyretro`, reported in prior cowork as a "brand channel via sideshowtristan@gmail.com" — meaning `sideshowtristan@gmail.com` is the owner of both the Google Cloud project AND the YouTube channel.
- **Confirm:** Should we use `sideshowtristan@gmail.com` for this OAuth app? Or did the channel move under `tristanaddi1@gmail.com` at some point?
- The account must have upload permission on the `@8bitlegacyretro` channel.

**Existing Google Cloud project:**
- Does Tristan already have a GCP project he wants to reuse (e.g., from other automation)? If yes, we can add the YouTube Data API to that existing project instead of creating a new one.
- If new is fine: proposed name `8-Bit Legacy Podcast Automation`.

**Do NOT proceed past Task 1 without these two answers.**

---

## Task 1 — Google Cloud Console setup (~10 min)

### 1a. Sign in + create / pick project

1. Open https://console.cloud.google.com in a fresh browser window
2. Sign in with the confirmed account (see pre-flight above)
3. Project dropdown in the top nav → either select existing `8-Bit Legacy Podcast Automation` (or equivalent) OR click "New Project":
   - Project name: `8-Bit Legacy Podcast Automation`
   - Organization / Location: default (No organization, if Tristan doesn't have a GCP Organization)
   - Create → wait for the notification → select the new project from the dropdown

### 1b. Enable YouTube Data API v3

1. Left nav → **APIs & Services** → **Library**
2. Search for `YouTube Data API v3`
3. Click the result → **Enable**
4. Wait for the "API enabled" confirmation (usually <10 sec)

### 1c. Configure the OAuth Consent Screen

1. Left nav → **APIs & Services** → **OAuth consent screen**
2. **User Type: External** (Internal requires Google Workspace; personal Gmail accounts don't qualify) → Create
3. Fill in the basics:
   - **App name:** `8-Bit Legacy Podcast Automation`
   - **User support email:** `sideshowtristan@gmail.com` (or whichever account Tristan confirmed)
   - **App logo:** skip for now (optional, not blocking)
   - **Application home page:** `https://8bitlegacy.com` (optional but looks more legit)
   - **Developer contact email:** same as user support
   - Save and Continue
4. **Scopes** page:
   - Click **Add or Remove Scopes**
   - Search and add:
     - `.../auth/youtube.upload` — upload videos (REQUIRED)
     - `.../auth/youtube` — manage YouTube account (needed for publishAt scheduling + thumbnail setting)
   - Update → Save and Continue
5. **Test users** page:
   - Click **Add Users**
   - Add `sideshowtristan@gmail.com` (the auth account)
   - Also add `tristanaddi1@gmail.com` as a backup — lets either account authorize if needed
   - Save and Continue
6. **Summary** page → Back to Dashboard

### 1d. Create the OAuth 2.0 Client ID

1. Left nav → **APIs & Services** → **Credentials**
2. Click **+ Create Credentials** → **OAuth client ID**
3. Application type: **Desktop app**
4. Name: `8bit-pipeline-desktop`
5. Create
6. A modal appears with the Client ID + Client Secret — click **Download JSON**
7. Save to Tristan's Downloads as `oauth2client.json` (or the default filename is fine — just know the path)

---

## Task 2 — Ship the JSON to TrueNAS (~2 min)

The container expects the file at `/mnt/pool/apps/8bit-pipeline/config/oauth2client.json` on TrueNAS. The `config/` directory already exists from this morning's setup.

In a Mac Terminal:

```bash
# Replace the path with wherever the download landed
scp -i ~/.ssh/id_ed25519 ~/Downloads/oauth2client.json \
  truenas_admin@192.168.4.2:/mnt/pool/apps/8bit-pipeline/config/oauth2client.json

# Verify it's there + permissions look OK
ssh -i ~/.ssh/id_ed25519 truenas_admin@192.168.4.2 \
  'ls -la /mnt/pool/apps/8bit-pipeline/config/oauth2client.json && \
   python3 -c "import json; d=json.load(open(\"/mnt/pool/apps/8bit-pipeline/config/oauth2client.json\")); print(\"client_type:\", list(d.keys())[0]); print(\"client_id prefix:\", d[list(d.keys())[0]][\"client_id\"][:20])"'
```

Expected output from the verify step:
```
-rw-r--r-- 1 truenas_admin truenas_admin ... /mnt/pool/.../oauth2client.json
client_type: installed
client_id prefix: <numbers>.apps.google
```

`client_type: installed` means it's a Desktop-type OAuth client (what we want). Web/Service-type would show something else and wouldn't work with our flow.

If the JSON is the wrong type, go back to Task 1d and re-create with Application type = **Desktop app** (not Web application).

---

## Task 3 — Verify end-to-end WITHOUT starting the full pipeline (~3 min)

The container isn't built yet — that's Tristan's next step after this brief. So we can't do a full upload test right now. But we CAN validate the OAuth JSON is loadable and the auth URL can be generated.

```bash
# Quick standalone check using google-auth libs locally (if installed on Mac)
.venv/bin/python3 -c "
import json, sys
with open('/tmp/oauth-check.json', 'w') as f:
    # Fetch the oauth JSON back from TrueNAS for local validation only — do NOT keep it on the Mac
    import subprocess
    subprocess.check_call(['scp', '-i', '/Users/tristanaddi1/.ssh/id_ed25519',
                           'truenas_admin@192.168.4.2:/mnt/pool/apps/8bit-pipeline/config/oauth2client.json',
                           '/tmp/oauth-check.json'])
d = json.load(open('/tmp/oauth-check.json'))
key = list(d.keys())[0]
assert key == 'installed', f'Expected Desktop app (key=installed), got key={key}'
creds = d[key]
print('client_id:', creds['client_id'][:30], '...')
print('project_id:', creds.get('project_id', '?'))
print('auth_uri:', creds.get('auth_uri', '?'))
print('token_uri:', creds.get('token_uri', '?'))
print('VALIDATION: OK — Desktop OAuth client ready for google-auth-oauthlib InstalledAppFlow')
import os; os.remove('/tmp/oauth-check.json')
print('scrubbed local copy at /tmp/oauth-check.json')
"
```

If the local check fails (e.g., `.venv` missing, google-auth not installed), skip it — the file's existence + correct JSON structure on TrueNAS is the gate. Full end-to-end verification happens when Tristan runs `./deploy/deploy-to-truenas.sh` and the container's first YT upload attempt prints the auth URL.

---

## Task 4 — Tell Tristan what happens next (his action, not yours)

On first deploy, the container will hit the YouTube upload stage and need a human-in-the-loop OAuth dance:

1. Tristan deploys: `./deploy/deploy-to-truenas.sh` from the repo root
2. Container starts, watcher idles until content is dropped
3. When the first podcast drop lands and hits stage `yt_upload`, the container logs print an auth URL like:
   ```
   Please visit this URL to authorize this application:
   https://accounts.google.com/o/oauth2/auth?...
   ```
4. Tristan visits the URL (can use any browser — the OAuth flow isn't tied to the TrueNAS host)
5. He signs in with `sideshowtristan@gmail.com`, picks the 8-Bit Legacy channel, grants upload + manage permissions
6. The page prints a code
7. He pastes the code back into the container console (via `docker attach 8bit-pipeline` or by writing a short file — `youtube_upload.py` reads stdin in its InstalledAppFlow.run_local_server fallback). ALTERNATIVE: modify the script to support a headless copy-paste flow; but for v1, Tristan runs the first upload interactively.
8. Container caches the refresh token at `/app/config/.yt_token.json` (persistent via bind mount)
9. Subsequent uploads (the other 7 topic videos of the same drop, plus all future drops) reuse the cached token silently

In this brief's handoff doc, spell the above out for Tristan so he's not surprised.

---

## Hard guardrails

- **Do NOT publish the OAuth app to Production** without Tristan's explicit go-ahead. That triggers Google's verification review (privacy policy URL, scoped use justification, 2-4 week wait). "Testing" mode works fine for our use case; accept the 7-day refresh.
- **Never post the `client_secret` in chat, in git, in Slack, anywhere.** The JSON stays on Tristan's Mac Downloads momentarily, then lives only on TrueNAS.
- **Do NOT add `/mnt/pool/apps/8bit-pipeline/config/oauth2client.json` to any git repo.** The 8bit-pipeline volume path is outside the repo, so this should be safe, but double-check nothing accidentally includes it.
- **Do NOT grant the OAuth app scopes beyond what's listed** (`.upload` + broader `youtube`). Broader scopes like `.force-ssl` or `.channel-memberships` are unnecessary and make Google's verification harder later.
- **Do NOT modify anything in the Google Ads account** while working inside Google Cloud Console — different product, different permissions model, out of scope for this brief.
- **If you hit a Google error asking for "app verification" to proceed** — that means the scope you added requires verification even in Testing mode. `youtube.upload` + `youtube` shouldn't trigger this, but if it does, stop and flag it for Tristan.

---

## When you're done

1. Commit this brief + your handoff doc to the repo:
   ```bash
   git add docs/claude-cowork-brief-2026-04-20-google-oauth.md \
           docs/cowork-session-2026-04-20-google-oauth.md
   git status   # verify no oauth2client.json staged
   git commit -m "Cowork 2026-04-20: Google OAuth for YouTube uploads"
   ```
   (Tristan will push at EOD — per his request, we're not pushing today.)

2. Write a handoff note at `docs/cowork-session-2026-04-20-google-oauth.md` with:
   - GREEN / BLOCKED per task
   - Which Google account ended up owning the OAuth app + the GCP project name
   - `client_id` **prefix only** (first 20 chars) for Tristan's reference
   - Exact file path where the JSON landed on TrueNAS
   - The "what happens next" handoff steps (Task 4 spelled out for Tristan)

3. Tell Tristan in chat:
   - OAuth JSON is live at `/mnt/pool/apps/8bit-pipeline/config/oauth2client.json`
   - Next manual step: `./deploy/deploy-to-truenas.sh` from the repo root when he's ready
   - First YT upload will need his 30-sec browser OAuth dance (visit URL, approve, paste code)
   - Token cache lives at `/app/config/.yt_token.json` after that — auto-refreshes for 7 days, then emits a Navi task on expiry

---

## Success criteria

- [ ] Google account for OAuth app confirmed with Tristan
- [ ] Google Cloud project exists (new or reused) with YouTube Data API v3 enabled
- [ ] OAuth Consent Screen configured (External, `youtube.upload` + `youtube` scopes, test users added)
- [ ] OAuth 2.0 Client ID created as **Desktop app** type
- [ ] `oauth2client.json` downloaded to Mac Downloads
- [ ] File SCP'd to `/mnt/pool/apps/8bit-pipeline/config/oauth2client.json` on TrueNAS
- [ ] Validation confirms `client_type: installed` (Desktop, not Web)
- [ ] Handoff note pushed; Tristan briefed on the first-deploy OAuth flow
