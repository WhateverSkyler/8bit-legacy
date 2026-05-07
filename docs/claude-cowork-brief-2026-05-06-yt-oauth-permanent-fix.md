# Claude Cowork Brief — YT OAuth Permanent Fix (2026-05-06, late night)

**Goal:** Fix YouTube upload tonight + set it up so this NEVER expires again.

**Context:** Episode May 5 2026 ran tonight, rendered 11 shorts fine, but `youtube_upload.py` failed with `invalid_grant: Token has been expired or revoked`. Root cause: the OAuth consent screen is in **Testing** mode → Google expires refresh tokens after **7 days**. Last auth was April 21; today is May 6 (15 days). That's why it died.

We are doing TWO things in this session:
1. **Immediate:** get a working token tonight + push to the production container so the May 5 episode can be uploaded before morning.
2. **Permanent:** add a keep-alive cron + start the production-publish path so this never happens again.

The user (Tristan) needs to be at his Mac, signed into the 8-Bit Legacy Google account in his default browser. Working dir: `/Users/tristanaddi1/Projects/8bit-legacy`.

---

## Quick reference

| Thing | Value |
|---|---|
| GCP project | `cs-3335-286915` |
| OAuth client type | Desktop (`installed`) |
| Local secrets | `config/oauth2client.json`, `config/.yt_token.json` |
| Container path | `/mnt/pool/apps/8bit-pipeline/config/.yt_token.json` |
| TrueNAS SSH | `truenas_admin@192.168.4.2` (key at `~/.ssh/id_ed25519`) |
| Container mount | `/mnt/pool/apps/8bit-pipeline/config/` → `/app/config/` |
| YouTube channel | `@8bitlegacyretro` (8-Bit Legacy) |
| Failed pipeline | Episode May 5 2026 |

---

## STAGE 1 — Why tonight's auth dance got "400 malformed"

Almost certainly the user's Google account isn't on the **Test users** list of the consent screen. In Testing mode, Google blocks any account that isn't pre-listed. We need to verify this first.

### Step 1.1 — Check OAuth consent screen status (browser)

1. Open: https://console.cloud.google.com/apis/credentials/consent?project=cs-3335-286915
2. Confirm at top: **Publishing status: Testing** (expected)
3. Confirm: **User type: External**
4. Scroll to **Test users** section
5. Verify the Google account you're using is in the list. If it's not, click **+ ADD USERS**, add `tristanaddi1@gmail.com` (or whichever Gmail account owns the @8bitlegacyretro YouTube channel — that's the one that must be added). Save.

### Step 1.2 — Verify the account that owns the channel

If you're not sure which Gmail owns @8bitlegacyretro:

1. Open https://studio.youtube.com in an incognito window.
2. Sign in. If the wrong dashboard loads, switch accounts top-right until you see the 8-Bit Legacy channel.
3. Top-right avatar → note the email address shown. THAT is the address that must be in Test users.

### Step 1.3 — While you're in GCP, check the OAuth client itself

1. Open: https://console.cloud.google.com/apis/credentials?project=cs-3335-286915
2. Under **OAuth 2.0 Client IDs**, find the client matching the one in `config/oauth2client.json` (it's a Desktop client).
3. Confirm **Application type: Desktop app**. If it's "Web", that's the bug — delete it and create a new Desktop OAuth client, download the JSON, replace `config/oauth2client.json` AND `/mnt/pool/apps/8bit-pipeline/config/oauth2client.json`.

---

## STAGE 2 — Re-run the OAuth dance (terminal)

Once Test users includes the right account, re-run the auth flow.

```bash
cd /Users/tristanaddi1/Projects/8bit-legacy
.venv/bin/python -c "
import sys
sys.path.insert(0, 'scripts/podcast')
from youtube_upload import _get_service
yt = _get_service()
me = yt.channels().list(part='snippet', mine=True).execute()
items = me.get('items', [])
print('AUTHED AS CHANNEL:', items[0]['snippet']['title'] if items else '(none)')
"
```

Expected:
- Browser opens to Google sign-in
- Pick the @8bitlegacyretro-owning Google account
- "Google hasn't verified this app" → click **Advanced** → **Go to <project> (unsafe)**
- Grant the YouTube scopes
- Browser shows "The authentication flow has completed."
- Terminal prints: `AUTHED AS CHANNEL: 8-Bit Legacy`

A new file is now at `config/.yt_token.json`. Confirm:

```bash
ls -la config/.yt_token.json
```

Should be ~700-1000 bytes, mode 644.

If you STILL get a 400 on the Google page after adding test users, copy the URL from the address bar and we'll diagnose from the OAuth params (most common follow-up: `redirect_uri_mismatch` — solved by editing the OAuth client to add `http://localhost` AND `http://127.0.0.1` as authorized redirect URIs).

---

## STAGE 3 — Push the token to the container (terminal)

```bash
# 1. Copy fresh token to TrueNAS (overwrites the revoked one)
scp -i ~/.ssh/id_ed25519 \
  /Users/tristanaddi1/Projects/8bit-legacy/config/.yt_token.json \
  truenas_admin@192.168.4.2:/mnt/pool/apps/8bit-pipeline/config/.yt_token.json

# 2. Set perms (the container reads/writes this; must be uid 950 readable)
ssh -i ~/.ssh/id_ed25519 truenas_admin@192.168.4.2 \
  'chown 950:950 /mnt/pool/apps/8bit-pipeline/config/.yt_token.json && chmod 600 /mnt/pool/apps/8bit-pipeline/config/.yt_token.json && ls -la /mnt/pool/apps/8bit-pipeline/config/.yt_token.json'

# 3. Smoke test — verify the container can use it without re-prompting
ssh -i ~/.ssh/id_ed25519 truenas_admin@192.168.4.2 \
  'docker exec 8bit-pipeline python3 -c "
import sys
sys.path.insert(0, \"/app/scripts/podcast\")
from youtube_upload import _get_service
yt = _get_service()
me = yt.channels().list(part=\"snippet\", mine=True).execute()
print(\"CONTAINER AUTHED AS:\", me[\"items\"][0][\"snippet\"][\"title\"])
"'
```

Expected last line: `CONTAINER AUTHED AS: 8-Bit Legacy`. If you see a different channel name, the wrong Google account was used in Stage 2 — start over.

---

## STAGE 4 — Backfill the May 5 2026 episode upload

Now the container has a working token. Re-run just the `yt_upload` stage.

```bash
ssh -i ~/.ssh/id_ed25519 truenas_admin@192.168.4.2 \
  'docker exec 8bit-pipeline python3 /app/scripts/podcast/pipeline.py \
    --episode "Episode May 5 2026" \
    --source "/media/podcast/archive/Episode May 5 2026" \
    --full-video "/media/podcast/archive/Episode May 5 2026/8-Bit Podcast May 5 2026 FULL FINAL V2.mp4" \
    --yt-start-date 2026-05-07 \
    --stage yt_upload'
```

Notes:
- Source dir is now `archive/`, not `processing/` — the drop_watcher moved it after pipeline completion.
- `--yt-start-date 2026-05-07` schedules the full episode for 2026-05-07 18:00 ET (since episode is already published behind us, picking tomorrow is a sensible re-publish slot — adjust if user wants something else).
- No topic cuts on this episode, so only the full episode gets uploaded.

Verify in YouTube Studio: scheduled-private video should appear, set to publish 5/07 6 PM ET.

---

## STAGE 5 — Permanent fix Path A: keep-alive cron (the real fix, ~10 minutes)

This is the fix that actually keeps it from breaking again. Add a tiny job that refreshes the token every 6 days, well within Google's 7-day Testing-mode expiry.

### Step 5.1 — Add the refresh script

Create `/Users/tristanaddi1/Projects/8bit-legacy/scripts/podcast/refresh_yt_token.py`:

```python
#!/usr/bin/env python3
"""Refresh the YouTube OAuth token to keep it alive within Google's
7-day Testing-mode refresh-token expiry. Run on a 6-day cadence.

Reads/writes config/.yt_token.json. If refresh fails (revoked, etc.),
emits a Navi task so the user knows they need to re-auth.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
TOKEN = ROOT / "config" / ".yt_token.json"
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
]

sys.path.insert(0, str(ROOT / "scripts"))
try:
    from navi_alerts import emit_navi_task
except ImportError:
    emit_navi_task = None


def main() -> int:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    if not TOKEN.exists():
        print(f"[ERROR] no token at {TOKEN}", file=sys.stderr)
        return 1

    creds = Credentials.from_authorized_user_file(str(TOKEN), SCOPES)
    try:
        creds.refresh(Request())
    except Exception as exc:
        msg = f"YT token refresh FAILED: {exc}. User must re-auth via cowork brief 2026-05-06."
        print(f"[FAIL] {msg}", file=sys.stderr)
        if emit_navi_task is not None:
            try:
                emit_navi_task(
                    title="YouTube OAuth re-auth required",
                    description=msg,
                    priority="high",
                )
            except Exception:
                pass
        return 2

    TOKEN.write_text(creds.to_json())
    print(f"[OK] refreshed token, expires {creds.expiry.isoformat()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

### Step 5.2 — Schedule it on TrueNAS

The container already has a similar pattern; we'll run this as a host cron that exec's into the container:

```bash
ssh -i ~/.ssh/id_ed25519 truenas_admin@192.168.4.2

# On TrueNAS host: add a cron via the standard tier-2 method (per
# reference_truenas_access memory) or add a systemd timer.
# Simplest: cron that does docker exec.
```

Add this cron line on TrueNAS (every 6 days at 03:00 ET):

```cron
0 3 */6 * * docker exec 8bit-pipeline python3 /app/scripts/podcast/refresh_yt_token.py >> /mnt/pool/NAS/Media/8-Bit\ Legacy/logs/yt_token_refresh.log 2>&1
```

(Use the user's standard cron addition pattern — see `reference_truenas_access.md` memory for the Tier-2 cronjob pattern.)

### Step 5.3 — Smoke test the refresh

```bash
ssh -i ~/.ssh/id_ed25519 truenas_admin@192.168.4.2 \
  'docker exec 8bit-pipeline python3 /app/scripts/podcast/refresh_yt_token.py'
```

Expected: `[OK] refreshed token, expires 2026-05-14T...`. Tail the log to confirm.

### Step 5.4 — Commit & push

```bash
cd /Users/tristanaddi1/Projects/8bit-legacy
git add scripts/podcast/refresh_yt_token.py
git commit -m "podcast: add YT OAuth keep-alive script (6-day refresh)"
git push
```

After commit, the container will pick it up on next image rebuild — but until then, copy directly:

```bash
scp -i ~/.ssh/id_ed25519 \
  scripts/podcast/refresh_yt_token.py \
  truenas_admin@192.168.4.2:/tmp/refresh_yt_token.py
ssh -i ~/.ssh/id_ed25519 truenas_admin@192.168.4.2 \
  'docker cp /tmp/refresh_yt_token.py 8bit-pipeline:/app/scripts/podcast/refresh_yt_token.py'
```

---

## STAGE 6 — Permanent fix Path B: publish OAuth consent to Production (the *truly* permanent fix, takes weeks)

Path A keeps things working forever as long as the cron runs. Path B removes the 7-day expiry entirely. Worth starting now in parallel — verification takes ~2-6 weeks of back-and-forth with Google.

### Why this is annoying but worth it

`youtube.upload` is a **sensitive scope**. To go to Production, Google requires:

1. A public privacy policy URL on a verified domain you own
2. A public homepage URL on the same verified domain
3. Domain ownership verification (DNS record or HTML file)
4. App logo (120x120 PNG)
5. Scope justification text (1-2 paragraphs why each scope is needed)
6. **Demo video** (~2-3 min YouTube video) showing:
   - The consent screen with each requested scope
   - The OAuth flow completing
   - The exact functionality each scope enables in the app
7. Submission via Google's review form
8. Back-and-forth with Google's reviewer (usually 1-3 rounds)

### Steps to start

1. Open: https://console.cloud.google.com/apis/credentials/consent?project=cs-3335-286915
2. Make sure these are filled in correctly:
   - **App name**: 8-Bit Legacy Podcast Pipeline (or similar)
   - **User support email**: tristanaddi1@gmail.com (or business email)
   - **Logo**: upload `/Users/tristanaddi1/Projects/8bit-legacy/podcast-assets/8-Bit-Legacy-Logo-1-e1674598779406-1536x667.webp` (resize to 120x120 PNG first — see ImageMagick: `convert input.webp -resize 120x120 logo.png`)
   - **Application home page**: https://8bitlegacy.com
   - **Application privacy policy link**: https://8bitlegacy.com/policies/privacy-policy (Shopify auto-generates this — verify it loads)
   - **Authorized domains**: `8bitlegacy.com`
3. Verify domain ownership:
   - https://search.google.com/search-console — add `8bitlegacy.com` as a property if not already, complete DNS or HTML verification
4. Scroll down to **Scopes** → confirm both `youtube` and `youtube.upload` are listed → click "ADD OR REMOVE SCOPES" if they're not.
5. Add **scope justifications** under each scope:
   - `youtube`: "Used to set custom thumbnails on videos uploaded by the channel owner."
   - `youtube.upload`: "Used to upload long-form podcast episodes and short-form clips to the channel owner's own YouTube channel as part of an automated content pipeline."
6. Save the consent screen.
7. Click **PUBLISH APP** at the top of the consent screen page → confirm.
8. Google will say verification is required for sensitive scopes. Click "Prepare for verification" → fill out the form, paste in scope justifications.
9. Record demo video — see script below — and upload to YouTube as Unlisted.
10. Submit. Wait 2-6 weeks.

### Demo video script (~2 min)

> "Hi, this is the verification video for the 8-Bit Legacy Podcast Pipeline.
> [Show app on screen — terminal running the pipeline.]
> The app is an internal-use automation that uploads our podcast's own video content to our own YouTube channel @8bitlegacyretro.
> [Show the OAuth consent screen.]
> Here's the OAuth consent screen — we request `youtube.upload` to upload videos to the channel owner's account, and `youtube` to set the thumbnail on each upload.
> [Run a small upload.]
> Here we run an upload of a podcast episode. The video is uploaded as scheduled-private with the publishAt timestamp.
> [Show the resulting video in YouTube Studio.]
> And here it appears in YouTube Studio, scheduled. That's it — the app does only what's needed for our own channel automation. No third-party data, no other users, no public-facing surface."

### After approval

Refresh tokens never expire. Path A's cron becomes a redundant safety net (leave it running anyway).

---

## STAGE 7 — Memory + commit

Update memory so this is captured:

```bash
cat > /Users/tristanaddi1/.claude/projects/-Users-tristanaddi1-Projects-8bit-legacy/memory/project_yt_oauth_state.md <<'EOF'
---
name: YT OAuth permanent fix state
description: Keep-alive cron + production-publish status for the YouTube upload OAuth client (project cs-3335-286915)
type: project
---

YouTube uploads use OAuth via Desktop client at `config/oauth2client.json`
(GCP project `cs-3335-286915`). Refresh token cached at `config/.yt_token.json`
locally + `/mnt/pool/apps/8bit-pipeline/config/.yt_token.json` on TrueNAS.

**Why this is fragile:** the consent screen is in **Testing** mode, so Google
expires refresh tokens after 7 days. Episode May 5 2026 upload failed because
of this.

**Tier 1 fix (keep-alive cron):** `scripts/podcast/refresh_yt_token.py` runs
every 6 days via TrueNAS host cron, refreshes the token before it expires.
If it ever fails, emits a high-priority Navi task to re-auth.

**Tier 2 fix (production publish):** consent screen submission to Google for
verification. Status: [TODO update after submitting]. Expect 2-6 weeks. Once
approved, refresh tokens last indefinitely.

**Re-auth recipe** (if the cron fails AND we're locked out):
1. `cd ~/Projects/8bit-legacy && .venv/bin/python -c "...youtube_upload._get_service()..."` (see docs/claude-cowork-brief-2026-05-06-yt-oauth-permanent-fix.md)
2. `scp config/.yt_token.json truenas_admin@192.168.4.2:/mnt/pool/apps/8bit-pipeline/config/`
3. Smoke-test with the container exec command in that brief.

**Channel:** @8bitlegacyretro (8-Bit Legacy). The Google account that
authenticates MUST be the one that owns the channel.
EOF
```

Add to `MEMORY.md`:

```bash
echo "- [project_yt_oauth_state.md](project_yt_oauth_state.md) — YT OAuth keep-alive cron + production-publish status. Re-auth recipe lives in docs/claude-cowork-brief-2026-05-06-yt-oauth-permanent-fix.md" >> /Users/tristanaddi1/.claude/projects/-Users-tristanaddi1-Projects-8bit-legacy/memory/MEMORY.md
```

Commit the brief + the keep-alive script:

```bash
cd /Users/tristanaddi1/Projects/8bit-legacy
git add docs/claude-cowork-brief-2026-05-06-yt-oauth-permanent-fix.md \
        scripts/podcast/refresh_yt_token.py
git commit -m "YT OAuth permanent-fix brief + keep-alive refresh script"
git push
```

---

## Done criteria

- [ ] `config/.yt_token.json` exists locally (Stage 2)
- [ ] Container smoke-test prints `CONTAINER AUTHED AS: 8-Bit Legacy` (Stage 3)
- [ ] May 5 episode appears as scheduled-private in YouTube Studio (Stage 4)
- [ ] `refresh_yt_token.py` exists in repo + container (Stage 5)
- [ ] Cron is scheduled on TrueNAS host (Stage 5)
- [ ] Manual cron invocation prints `[OK] refreshed token...` (Stage 5)
- [ ] Production-publish form submitted (Stage 6)
- [ ] Memory file written + indexed (Stage 7)
- [ ] Brief + script committed and pushed (Stage 7)

If any step fails, paste the error back and we'll diagnose. The most likely failure points are:

1. Stage 1.1 — wrong Google account in test users → fix by adding the right one
2. Stage 2 — different 400 (e.g. `redirect_uri_mismatch`) → add `http://localhost` and `http://127.0.0.1` to OAuth client redirect URIs
3. Stage 3 — `chown 950:950` permission denied → run with sudo
4. Stage 4 — pipeline still fails → check that token file in container is non-empty and parseable JSON
5. Stage 5 — cron syntax doesn't fire → use systemd timer instead, or check TrueNAS-specific cron docs
