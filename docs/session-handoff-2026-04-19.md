# Session Handoff — 2026-04-19 (Podcast Automation Build)

## TL;DR

Podcast + social automation pipeline is built end-to-end and dry-run green.
**Three user steps unblock the first live run.** See "What you need to do" below.

First podcast episode ("Episode April 14th 2026" — 74 min, 7 topic cuts + full episode)
is ready to ship once Zernio accounts, YouTube OAuth, and a music bed folder are provided.

## What got built today

### Scripts (12 files)
| File | Purpose |
|---|---|
| `scripts/zernio_client/` | Vendored client (auth tested, 13 endpoints) |
| `scripts/setup_zernio.py` | Smoke test |
| `scripts/podcast/prepare_sources.py` | USB → 1080p downscale |
| `scripts/podcast/prepare_music.py` | Normalize music beds to -18 LUFS |
| `scripts/podcast/transcribe.py` | faster-whisper large-v3 word-level JSON |
| `scripts/podcast/pick_clips.py` | Claude → 4-5 viral moments per topic |
| `scripts/podcast/generate_thumbnail.py` | Pillow 1280×720 YT thumbnails |
| `scripts/podcast/generate_metadata.py` | Claude → title/desc/tags |
| `scripts/podcast/youtube_upload.py` | Google YT Data API v3 resumable upload |
| `scripts/podcast/render_clip.py` | ffmpeg 1080×1920 + ASS karaoke + music + end-card |
| `scripts/podcast/schedule_shorts.py` | Zernio multi-platform (TikTok + YT + IG) |
| `scripts/podcast/pipeline.py` | Resumable orchestrator with per-stage checkpoint |
| `scripts/social/schedule_photos.py` | 27 product photos → IG+FB, 2/day |

### Artifacts already generated

- **7 topic cuts downscaled** to 1080p → `data/podcast/source/1080p/` (~1.2 GB, gitignored)
- **7 transcripts** (word-level timestamps) → `data/podcast/transcripts/` (gitignored)
- **Episode schedule JSON** → `data/podcast/Episode_April_14th_2026/yt_schedule.json` (committed)

### Verified
- `scripts/setup_zernio.py` — Zernio API auth ✅ (returns 0 accounts, expected until you connect)
- `scripts/podcast/pipeline.py --dry-run` — all 8 stages wire correctly ✅
- Python venv at `.venv/` with 9 deps installed ✅

## What you need to do (tomorrow)

### 1. Zernio — connect accounts (~5 min)
- Go to https://zernio.com/dashboard
- Create Social Set "8-Bit Legacy"
- Connect: Instagram (Business), Facebook Page, TikTok, YouTube
- Verify: `source .venv/bin/activate && python3 scripts/setup_zernio.py`
  (should print 4 accounts with `health=ok`)

### 2. Google YouTube OAuth (~10 min)
- https://console.cloud.google.com → new project "8bit-legacy-podcast"
- APIs & Services → search "YouTube Data API v3" → **Enable**
- APIs & Services → Credentials → Create Credentials → **OAuth 2.0 Client ID**
  - Application type: **Desktop app**
- Download the JSON → save as `config/oauth2client.json`
- First upload script run opens a browser — approve `@8bitlegacypodcast` channel once

### 3. Music beds — pick one
- **(a)** Existing folder: tell me the path, I'll run
  `python3 scripts/podcast/prepare_music.py --source <path>`
- **(b)** CD rip: hand me a stack of retro game soundtrack CDs
- **(c)** Skip music: first batch of shorts go out with dialogue-only audio

### 4. Kick the pipeline

Once 1-3 are done:
```bash
cd ~/Projects/8bit-legacy
source .venv/bin/activate
python3 scripts/podcast/pipeline.py \
    --episode "Episode April 14th 2026" \
    --source "/run/media/tristan/TRISTAN/8-bit podcast/Episode April 14th 2026/Topic Cuts" \
    --full-video "/run/media/tristan/TRISTAN/8-bit podcast/Episode April 14th 2026/8-Bit Podcast April 14 2026 FULL FINAL.mp4" \
    --yt-start-date 2026-04-20 \
    --shorts-start-date 2026-04-20
```

Stages 1-4 (sources/transcribe/thumbnails/metadata) are already cached — will skip.
Pipeline will resume from `yt_upload` onward.

### 5. Product photos (independent of podcast)

```bash
python3 scripts/social/schedule_photos.py --start-date 2026-04-20 --preview
# review captions; if good:
python3 scripts/social/schedule_photos.py --start-date 2026-04-20 --execute
```

## Key design locks (don't re-ask)

- **Real Nintendo/Sega OSTs** in shorts — user accepted Content ID risk
- **Full auto-pilot** — AI picks clips, renders, schedules, no review gate
- **Captions** — Bebas Neue all-caps, white default + orange `#ff9526` active word,
  thick black stroke, bottom-third (ASS per-word karaoke, 3-word groups)
- **YT schedule** — full ep day 1 18:00 ET, topics day 2-8 12:00 ET (1/day)
- **Shorts schedule** — 3/day at 09:00 / 13:00 / 19:00 ET, all 3 platforms per post
- **Music volume** — -18 LUFS normalized, mixed at 15% (-17 dB) under dialogue

## Rollback

- YouTube: scheduled videos are `privacyStatus=private` + `publishAt` — unschedule via
  YT Studio or delete via API before the publish time
- Zernio: post IDs logged in `data/podcast/clips/<episode>/schedule_log.json` —
  `ZernioClient().delete_post(post_id)` cancels a scheduled post

## Files generated/committed this session

- `docs/podcast-automation-runbook.md` — long-form ops doc
- `docs/session-handoff-2026-04-19.md` — this file
- `scripts/podcast/*.py` + `scripts/social/*.py` + `scripts/zernio_client/*.py`
- Pipeline state: `data/podcast/Episode_April_14th_2026/{pipeline_state,yt_schedule}.json`
- `.gitignore` — added oauth secrets + podcast binary artifacts
