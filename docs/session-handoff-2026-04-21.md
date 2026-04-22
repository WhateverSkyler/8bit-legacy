# Session Handoff — 2026-04-21 (~3:50 PM EDT)

**Resume from:** MacBook, after fixing the Google Ads OAuth token.
**Previous handoff:** `docs/session-handoff-2026-04-20.md`

---

## TL;DR

- **Podcast pipeline is auto-running on TrueNAS right now.** Full FINAL 25 GB upload was at 60% at 15:46 ET — projected to finish ~17:30 ET. Downstream stages (`pick_clips` → `render_clips` → `schedule`) will run automatically after that. Publish scheduled for **18:00 ET (2026-04-21T22:00:00Z)**.
- **Zernio social posts** have been cleaned of all Valdosta/Moultrie/Georgia location references — 25 posts fixed, 0 still need cleanup. Future posts are also blocked (see "Guardrails added" below).
- **Google Ads is BLOCKED** on a broken refresh token. Mac needs to re-auth in a way that actually writes the new token into `config/.env`. Details below.
- Two commits pushed today: `27cf49d` (podcast pipeline 4K/fuzzy-thumb fixes) and `c744a07` (location hashtag strip + Zernio PUT fix). One more uncommitted change in-tree: `youtube_upload.py` relative_to() fix.

---

## 0) What's queued to go out (the short answer)

| Content | Platforms | Scheduled time | State |
|---------|-----------|----------------|-------|
| **Topic 03 "Video Game Adaptations"** | YouTube | 2026-04-22 12:00 ET | ✅ Uploaded, scheduled |
| **Topic 05 "Metroid Prime 4"** | YouTube | 2026-04-23 12:00 ET | ✅ Uploaded, scheduled |
| **FULL FINAL podcast (25 GB)** | YouTube | 2026-04-21 18:00 ET | 🟡 Upload in flight (60% at 15:46) |
| **Short-form clips from FULL FINAL** | TikTok, YT Shorts, IG Reels | TBD (pick_clips decides) | ⏳ Waits for FULL FINAL upload to finish, then `pick_clips` → `render_clips` → `schedule` fire automatically |
| **Photo post #1 (Zelda TP & Wind Waker)** | Instagram, Facebook | 2026-04-21 12:00 ET | ✅ Already published today (first post fired) |
| **Photo posts #2–25** (25 posts, Tue/Thu/Sat 12:00 ET rotation) | Instagram, Facebook | 2026-04-23 → 2026-06-18 | ✅ Queued in Zernio |

### Terminology note on the 25 Zernio photo posts
When you look at Zernio's dashboard you'll see "draft" as the status. That's misleading — it's their label for "created but not yet published". The real state is on each platform entry: `"status": "pending"` + `"publishAttempts": 0` + a future `scheduledFor` timestamp. Zernio's scheduler auto-fires those at their scheduled time and flips them to `"published"`. Evidence: the 12:00 ET post today (Apr 21) went from top-status "draft" → "published" on its own when the time came. So: all 25 are real, and will auto-post.

---

## 1) 🟡 Podcast pipeline — live, self-driving on TrueNAS

Container: `8bit-pipeline` on TrueNAS 192.168.4.2. Episode being processed: `Episode April 14th 2026`.

### Stages completed
| Stage | Status |
|-------|--------|
| sources (ffmpeg 1080p working copies) | ✅ done |
| transcribe (faster-whisper large-v3 int8) | ✅ done — 3 transcripts in `/app/data/podcast/transcripts/` |
| thumbnails | ✅ done — fuzzy match worked for topic 03 (`video game movie adaptations.png` → `03-video-game-movies-and-shows.mp4`, score 0.29) |
| metadata | ✅ done — Claude-generated titles already in `/app/data/podcast/metadata/` |
| yt_upload (topic 03) | ✅ `youtu.be/x9OXQv37FHE` — publish 2026-04-22 16:00 UTC |
| yt_upload (topic 05) | ✅ `youtu.be/G8VkC5RU5GU` — publish 2026-04-23 16:00 UTC |
| yt_upload (FULL FINAL 25 GB) | 🟡 60% at 15:46 ET, projected ~17:30 ET finish |

### Stages still to run (after FULL FINAL upload completes)
- `pick_clips` — reads transcripts, picks 9:16 short-form candidate timestamps
- `render_clips` — ffmpeg renders the vertical clips
- `schedule` — pushes clips to Zernio (TikTok / YT Shorts / IG Reels)

### How to check progress from the MacBook
Use the TrueNAS API cronjob pattern. There's already a progress-check script at `/tmp/8bit-check-progress.sh` **on TrueNAS** (not on Mac). To re-trigger it:

```bash
TOKEN="1-6qf41BNM6EGRqGzMIweeNf4HNYnlZS9r9g9BJQYRRZsGCzmVzBAkPhSYyGpnYqHt"
RESP=$(curl -s -X POST "http://192.168.4.2/api/v2.0/cronjob" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"user":"root","command":"bash /tmp/8bit-check-progress.sh","description":"ad-hoc progress","schedule":{"minute":"0","hour":"0","dom":"1","month":"1","dow":"0"},"enabled":false}')
JOB_ID=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
curl -s -X POST "http://192.168.4.2/api/v2.0/cronjob/run" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d "{\"id\": $JOB_ID}" > /dev/null
sleep 8
ssh truenas_admin@192.168.4.2 'cat /tmp/8bit-check-progress.out'
curl -s -X DELETE "http://192.168.4.2/api/v2.0/cronjob/id/$JOB_ID" -H "Authorization: Bearer $TOKEN" > /dev/null
```

Look for: `[UPLOAD] 8-Bit Podcast April 14 2026 FULL FINAL.mp4 (25.23 GB)` followed by progress marks. When you see `[OK] ... → https://youtu.be/...` then the FULL FINAL is done.

### What to verify after FULL FINAL finishes
1. YouTube Studio → video is scheduled for `2026-04-21T22:00:00Z` (18:00 ET).
2. Downstream stages ran: re-trigger the progress check and look for `[pick_clips]`, `[render_clips]`, `[schedule]` blocks in the log tail.
3. Zernio dashboard shows clip posts scheduled to TikTok/YT Shorts/IG Reels.

### One known non-fatal bug, already fixed in-tree
`scripts/podcast/youtube_upload.py:202-211` used to raise `ValueError` when `video.relative_to(ROOT=/app)` was called on a video living under `/media/...`. The error was caught by the outer pipeline and logged as `[ERROR] ... is not in the subpath of '/app'` but the script still exited 0, so uploads still succeeded — just the log-append step was skipped. **Fix is already deployed to the container** (via `docker cp` this afternoon) and edited locally. **Not yet committed** — the edit is in your working tree.

---

## 2) 🔴 BLOCKED — Google Ads OAuth refresh token

Every call to `https://oauth2.googleapis.com/token` with the refresh_token in `config/.env` returns:
```json
{"error": "invalid_grant", "error_description": "Bad Request"}
```

### State as of 15:46 ET on Linux
- `config/.env` mtime: `2026-04-21 14:43:17 EDT` (Syncthing pulled a version from Mac, but that version's token is rejected)
- `dashboard/.env.local` mtime: `2026-04-08 23:09:04 EDT` (Syncthing has NOT updated this file at all — may still be excluded somewhere)
- Refresh token fingerprint on Linux:
  - prefix: `1//04_HCGPWTn_QO…`
  - suffix: `…cbybVLn471j8`
  - length: 103
  - sha256 (first 16 chars): `031085750cf0fdba`

### What probably happened on the Mac
The Google Ads client library often caches tokens to a file like `~/.google-ads/credentials.pickle`, `~/.config/google-ads/...`, or `~/.config/gcloud/...` — NOT back to `config/.env`. So re-auth on Mac updates the cache, but `config/.env` never gets rewritten. Syncthing sees no change in `config/.env` → nothing propagates to Linux.

### Two ways to unblock (pick one)

**Option A — Fix it on Mac (keep re-auth on Mac)**
1. Confirm: on Mac, `grep GOOGLE_ADS_REFRESH_TOKEN ~/Projects/8bit-legacy/config/.env` — if prefix/suffix match the fingerprint above, the Mac's `.env` is also stale.
2. Find where Google's library actually writes the token on Mac:
   - `ls -la ~/.google-ads/ ~/.config/google-ads/ 2>/dev/null`
   - `ls -la ~/Library/Application\ Support/google-ads/ 2>/dev/null`
   - grep for `refresh_token` in any recently modified files under `~/Library/` or `~/.config/`
3. Either (a) copy the new value into `config/.env` manually, or (b) change the re-auth script to write it there directly.
4. Also: on Mac, check `dashboard/.env.local` — that file hasn't synced at all on Linux, so it may be in `.stignore` on one side. Get that value updated too.

**Option B — Re-auth from Linux (simpler, cuts Mac out of the loop)**
1. On the Linux machine: `cd ~/Projects/8bit-legacy && python3 scripts/create-shopping-campaign.py --oauth-setup` (or whatever the re-auth entry point is — if none exists, it's a ~20-line OAuth installed-app flow with `access_type=offline&prompt=consent` to force a new refresh token).
2. This writes directly to `config/.env` and avoids Syncthing ambiguity.
3. Also update `dashboard/.env.local` with the same token + restart dashboard container (`pm2 restart 8bit-dashboard` or similar on the VPS).

**Important OAuth parameter:** whichever flow is used, the auth URL MUST include `prompt=consent` AND `access_type=offline`. Without both, Google returns the SAME refresh token that's already broken (or no refresh token at all). That may be why the Mac re-auth loop isn't producing a new token even when re-run.

### After fix, verify with
```bash
set -a; source ~/Projects/8bit-legacy/config/.env; set +a
curl -s -X POST https://oauth2.googleapis.com/token \
  -d "client_id=$GOOGLE_ADS_CLIENT_ID" \
  -d "client_secret=$GOOGLE_ADS_CLIENT_SECRET" \
  -d "refresh_token=$GOOGLE_ADS_REFRESH_TOKEN" \
  -d "grant_type=refresh_token" | python3 -m json.tool
```
Expect `access_token` + `expires_in: 3599`, not `invalid_grant`.

---

## 3) ✅ Done this session — Zernio location cleanup

User direction: **never mention Valdosta / Moultrie / Georgia / any geographic location in social media posts** — the store is a nationwide online shop, not a local brick-and-mortar.

### Cleanup script + results
- Script: `/tmp/zernio-cleanup-locations.py` — regex strips `#valdostaga`, `#valdosta`, `#moultrie`, `#moultriega`, `#southga`, `#southgeorgia`, `#georgiaga`, plus standalone `#ga` / `#georgia` when tag-adjacent, plus literal words `valdosta`, `valdosta ga`, `moultrie`, `south georgia` (case-insensitive).
- Ran with `--execute`: cleaned 24 of 25 scheduled posts. One was accidentally stomped during my Zernio PUT-method probe and was manually restored to the known-good caption before re-running cleanup.
- Follow-up scan: 0 posts still need cleanup ✅

### Guardrails added for future runs
1. `scripts/social/schedule_photos.py` line 64: removed `#valdostaga` from `CAPTION_HASHTAGS`, replaced with `#gamingcommunity`. Added explanatory comment.
2. `scripts/podcast/generate_metadata.py` SYSTEM prompt: explicitly forbids location hashtags in `episode_hashtags`, with examples.
3. `scripts/zernio_client/client.py` `update_post()`: switched from PATCH (which Zernio returns 405 on) to PUT (which works with partial bodies) — commented accordingly.

All three changes are in commit `c744a07`.

---

## 4) Commits pushed today

| SHA | Summary |
|-----|---------|
| `27cf49d` | Podcast pipeline: 4K YT upload support, fuzzy custom thumbnail matching, Bebas Neue font, container cache dir fix |
| `c744a07` | Strip location hashtags from social posts + fix Zernio update verb (PATCH → PUT) |

**Uncommitted in working tree:**
- `scripts/podcast/youtube_upload.py` — `relative_to()` fix (try/except ValueError around line 203). Already deployed to the container via docker cp, so pipeline has it, but not in git yet.
- Plus the existing sync-conflict files from 2026-04-20 (listed in `git status`) — those are pre-existing Syncthing conflicts unrelated to today's work.

When resuming, consider `git add scripts/podcast/youtube_upload.py && git commit -m "Fix non-fatal relative_to() error in youtube_upload logger"`.

---

## 5) Pending work (priority order)

1. **[BLOCKED on Google Ads token]** Plan + launch first Google Ads campaign. Brief at `docs/claude-cowork-brief-2026-04-20-ads-launch.md` still has Tasks 2-6 outlined. $700 promo expires 2026-05-31.
2. **[PASSIVE — self-completes]** Wait for FULL FINAL upload + downstream stages. Verify Zernio got clip posts + YT scheduled video shows on channel.
3. **[QUICK]** Commit the `youtube_upload.py` relative_to() fix (see above).
4. **[LATER]** Fix `dashboard/.env.local` sync — it's been frozen at 2026-04-08 for weeks. Once Google Ads token is fresh, both `config/.env` and `dashboard/.env.local` need the same value, and Syncthing must actually propagate the dashboard one.
5. **[LATER]** Website frontend revamp (homepage, banners, styling) — tracked in `project-website-todos.md`.

---

## 6) Useful references

- TrueNAS connection + API pattern: `docs/TRUENAS-ACCESS.md`
- Podcast pipeline architecture: memory file `project-podcast-pipeline.md`
- Zernio API quirks: `scripts/zernio_client/client.py` (PUT not PATCH, 600 req/min Accelerate limit)
- Google Ads cowork brief: `docs/claude-cowork-brief-2026-04-20-ads-launch.md`
- Store volume context (don't overbuild): `project-store-volume-reality.md`
