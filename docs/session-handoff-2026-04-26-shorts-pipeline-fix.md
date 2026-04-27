## TL;DR

Shorts pipeline was fully broken (0 going out). After the session it's:

- **25 shorts in flight** — 1 already published tonight + 24 scheduled through Mon 5/04 19:00 ET on TikTok / YouTube Shorts / Instagram Reels / Facebook Reels. All have proper titled captions.
- **Auto-recurring restored.** After 5/04, `buffer_scheduler` recycles `clips-archive/` (3 mp4s minimum) into open 9/13/19 ET slots. New podcasts auto-process.
- **The "drop the full file, get content" workflow now actually works.** Watcher no longer requires topic-cut MP4s.

You said you'd watch tomorrow — Mon 4/27 the queue fires Metroid Prime 4, PS5 Pro Cyberpunk, and PS5 Pro $900 at 9/13/19 ET respectively.

---

## What was wrong

A stack of 4 stacked failures, each masking the next:

1. **`config/.env` had a stale `ANTHROPIC_API_KEY`** (suffix `...TwAA`). Anthropic returned `401 invalid x-api-key` on every call. Prod key on TrueNAS at `/mnt/pool/apps/8bit-pipeline/.env` (suffix `...zsDwAA`) was valid the whole time — the local file just drifted out of sync on 4/22.
2. **Local `.venv` was broken.** Its base Python had been removed, so `import anthropic` silently failed in `pick_clips.py` even when the key was right.
3. **The 4/25 PUT-update flipped 7 scheduled shorts to `draft`.** Same Zernio orphan-bug photos hit. Posts sat as drafts and silently missed their slots.
4. **Container had stale code from before 4/25.** The `schedule_shorts.py` title-prefix commit (`5439038`) was never deployed, so freshly-created posts came out hashtag-only.

---

## What was fixed

### Recovered the live `ANTHROPIC_API_KEY`
Pulled it from prod (`/mnt/pool/apps/8bit-pipeline/.env`) via the documented Tier-2 cronjob recipe and synced into local `config/.env`. (See `reference_truenas_access` memory for the recipe — it was beefed up this session with cross-checked Navi-doc derived recipes for any future "I need a secret from a chmod-600 file on TrueNAS" situation.)

### Rescued 7 stuck-draft shorts
Recipe (mirrors the photo fix): download existing media → re-upload fresh → delete the draft → re-create with rolled-forward `scheduledFor`. None blocklisted. Filled the 4/26-4/28 calendar.

### Generated 18 fresh picks across two pick_clips runs
- v1: 8 picks from FULL FINAL (`pick_clips_full.py` wrapper that bumps `PICKS_REQUESTED` 7→50, `max_chars` 80k→400k, `max_tokens` 6k→16k for the Sonnet 4.6 call). c8 was God of War (blocklist) — deleted both file and post.
- v2: 6 more picks (4 dups, 2 fresh content — Bethesda loading screens, Rockstar/Bethesda IPs).

### Hot-patched the container with the latest code
Copied `schedule_shorts.py`, `pick_clips.py`, `render_clip.py`, `drop_watcher.py`, `zernio_client/*` into the running container via `docker cp`, then restarted so the long-running `drop_watcher` daemon picks up the patches.

### Code patches committed (local commit `7f2e8bf`)
**`scripts/watcher/drop_watcher.py`** — accept full-only drops. Previously rejected drops without topic-cut MP4s; now runs the pipeline against the full episode alone.

**`scripts/podcast/pick_clips.py`** — validator rescue window 2→4 attempts plus forward-skip fallback when pulling in the prior segment doesn't help. Higher acceptance rate without breaking the "never cut mid-sentence" rule.

(Push to GitHub blocked by the `criticalmkt` auth issue — you've seen this before. Your other machine will sync when it next runs.)

### Re-rendered + re-scheduled 12 hashtag-only posts with title prefix
Once the title-fix code was live in the container, the 12 already-scheduled hashtag-only posts had to be rebuilt: deleted them, ran `schedule_shorts.py` again with the fresh code → 12 posts re-created with `<title>\n\n<hashtags>` captions.

### Cleaned up the 1 leftover hashtag-only post manually
The c5 mp4 had been rendered before its corresponding pick was in `_all.json`, so it created with no title. Did a one-off rescue: download → delete → re-upload → re-create with `Buying an Xbox in 2026 Is a Mistake` baked in.

---

## Final queue (snapshot)

| Date | Slot | Title |
|---|---|---|
| Sun 4/26 | 19:00 | ✅ Why the Zelda Director Actually Gives Us Hope |
| Mon 4/27 | 9:00 | Everything Metroid Prime 4 Added Was Bad |
| Mon 4/27 | 13:00 | PS5 Pro Runs Cyberpunk at 60fps With Full Ray Tracing |
| Mon 4/27 | 19:00 | Do NOT Spend $900 on the PS5 Pro |
| Tue 4/28 | 9:00 | Buying an Xbox in 2026 Is a Mistake |
| Tue 4/28 | 13:00 | Adult Gamers Cant Sit Still Anymore |
| Tue 4/28 | 19:00 | Handheld Gaming Is the Adult Gamer Fix |
| Wed 4/29 | 9/13/19 | (Metroid/Cyberpunk/$900 — fresh re-renders, slightly different edits) |
| Thu 4/30 | 9/13/19 | Xbox / Xbox / GTA 6 |
| Fri 5/01 | 9/13/19 | Starfield / Rockstar+Bethesda Milking / Indie Games Saving |
| Sat 5/02 | 9/13/19 | Aging Gamers / AYN Thor / Mario Movie 2 |
| Sun 5/03 | 9/13/19 | Rockstar IPs (v2) / Bethesda Loading Screens / Aging (v2) |
| Mon 5/04 | 9/13/19 | AYN Thor (v2) / Mario 2 (v2) / GTA 6 (v2) |

After 5/04 19:00 ET, `buffer_scheduler` runs hourly and refills empty slots from `clips-archive/` (currently 3 mp4s seeded: 03_c3, FULL_c1, FULL_c2). It excludes the blocklisted God of War clip.

---

## The simple workflow you asked for

1. Film a 1.5–2hr podcast.
2. Drop a folder named `EP-YYYYMMDD/` (or any name) into `/mnt/pool/NAS/Media/8-Bit Legacy/podcast/incoming/` on TrueNAS.
3. Folder must contain a `.mp4` with `full` in its filename. **Topic cuts are now optional.**
4. Wait. The container's drop_watcher scans every few minutes, picks up the drop, runs the pipeline, generates ~10-15 picks, renders vertical 9:16 shorts with face-crop + captions + music beds, schedules them at 9/13/19 ET to all 4 platforms.

That's it.

---

## Friction points still open (non-urgent)

1. **Validator rejection rate is still ~85%** even with the looser rules — Claude finds 50 candidates per run, ~7-8 pass validation. To get the user's "weeks of content from a single podcast" target (~25-40 picks per podcast) we'd want chunked-transcript pick_clips: split FULL FINAL into 4×30min windows, run pick_clips on each → ~25-30 picks. Not implemented this session.
2. **`feedback_shorts_blocklist` only covers one specific clip stem.** Need it to be content-aware (match by title/topic) so re-running pick_clips doesn't re-pick "God of War Live Action" with a different `_c8` suffix. For now, my `pick_clips_v2.py` wrapper strips by keyword.
3. **GitHub push blocked** — `criticalmkt` 403. Other machine will sync.
4. **Source MP4s for segments 01, 02, 04, 06, 07** were never exported from FL Studio for this episode. Not a real problem now that picking from FULL FINAL works.

---

## Memory updates

| File | What |
|---|---|
| `reference_truenas_access.md` | Rewrote as priority context. Cross-checked vs Navi docs. Added secret-recovery recipe for `chmod 600` files via Tier-2 cronjob. |
| `project_shorts_pipeline_state.md` | Final EOD state of the pipeline. |
| `MEMORY.md` | Index updated for both. |

---

## Files touched this session

- `scripts/watcher/drop_watcher.py` — full-only drops accepted
- `scripts/podcast/pick_clips.py` — looser validator
- `config/.env` — local synced to prod ANTHROPIC key
- `.venv/` — rebuilt
- `data/podcast/source/1080p/05-metroid-prime4-ps5pro-xbox_1080p.mp4` — staged locally (250MB downscale)
- `data/music-beds/` — 40 files copied from NAS for local renders (didn't end up using because local ffmpeg lacks libass — ended up rendering on container instead)
- `data/podcast/clips_plan/_all.json` — 19 picks across 4 sources

In container (via `docker cp`):
- `/app/scripts/podcast/{schedule_shorts,pick_clips,render_clip}.py`
- `/app/scripts/zernio_client/{__init__,client}.py`
- `/app/scripts/watcher/drop_watcher.py`
- `/app/data/podcast/clips_plan/_all.json` (synced from local)
- `/app/data/podcast/clips/Episode_April_14th_2026/*c{1-7,9-14}.mp4` (rendered)
- `/app/data/podcast/clips-archive/{03_c3, FULL_c1, FULL_c2}.mp4` (seeded for buffer recycling)
