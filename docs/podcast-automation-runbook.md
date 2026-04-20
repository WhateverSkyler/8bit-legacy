# Podcast + Social Automation — Runbook

End-to-end automation for releasing a podcast episode: uploads the full video + 7 topic
segments to YouTube, auto-picks viral short-form moments, renders vertical shorts with
karaoke captions and music beds, schedules them across TikTok / YT Shorts / IG Reels via
Zernio, and ships product photos to IG/FB on a separate track.

## One-time setup

### 1. Python env
```bash
cd ~/Projects/8bit-legacy
python3 -m venv .venv
source .venv/bin/activate
pip install faster-whisper google-api-python-client google-auth-oauthlib \
            google-auth-httplib2 Pillow anthropic requests python-dotenv
```

### 2. Secrets in `config/.env`
```
ANTHROPIC_API_KEY=sk-ant-...
ZERNIO_API_KEY=sk_...
ZERNIO_BASE_URL=https://zernio.com/api/v1
GOOGLE_YT_CLIENT_ID=...        # optional; only used if you prefer env over oauth2client.json
GOOGLE_YT_CLIENT_SECRET=...
YOUTUBE_CHANNEL_ID=UC...       # 8-Bit Legacy Podcast channel
```

### 3. Zernio accounts (user-driven)
- Log in at https://zernio.com/dashboard
- Create a Social Set "8-Bit Legacy"
- Connect Instagram (Business), Facebook Page, TikTok, YouTube
- Verify: `python3 scripts/setup_zernio.py` — prints 4 accounts with `health=ok`

### 4. Google YouTube OAuth (one-time)
- GCP Console → new project "8bit-legacy-podcast" → enable YouTube Data API v3
- Create OAuth 2.0 Client ID, type **Desktop**
- Download JSON → save as `config/oauth2client.json`
- First `python3 scripts/podcast/youtube_upload.py ...` will open a browser to complete auth
- Refresh token cached at `config/.yt_token.json`

### 5. Music bed library
- Gather a folder of retro game OSTs (WAV/MP3/FLAC — at least ~30 tracks)
- `python3 scripts/podcast/prepare_music.py --source ~/Music/retro-game-osts`
- Produces normalized -18 LUFS WAVs in `data/music-beds/` + `index.json`

## Running an episode (happy path)

```bash
source .venv/bin/activate

# Single-command orchestrator
python3 scripts/podcast/pipeline.py \
    --episode "Episode April 14th 2026" \
    --source "/run/media/tristan/TRISTAN/8-bit podcast/Episode April 14th 2026/Topic Cuts" \
    --full-video "/run/media/tristan/TRISTAN/8-bit podcast/Episode April 14th 2026/8-Bit Podcast April 14 2026 FULL FINAL.mp4" \
    --yt-start-date 2026-04-20 \
    --shorts-start-date 2026-04-20
```

Resumable — safe to Ctrl-C and re-run with `--resume`. Per-stage: `--stage transcribe`.

### Stage map
| Stage | Script | Output |
|---|---|---|
| sources | prepare_sources.py | `data/podcast/source/1080p/*.mp4` |
| transcribe | transcribe.py | `data/podcast/transcripts/*.json` |
| thumbnails | generate_thumbnail.py | `data/podcast/thumbnails/*.jpg` |
| metadata | generate_metadata.py | `data/podcast/metadata/*.json` |
| yt_upload | youtube_upload.py | YouTube Scheduled queue, log in `youtube_uploads.json` |
| pick_clips | pick_clips.py | `data/podcast/clips_plan/*.json` + `_all.json` |
| render_clips | render_clip.py | `data/podcast/clips/<episode>/*.mp4` |
| schedule | schedule_shorts.py | Zernio scheduled queue, log in `clips/<episode>/schedule_log.json` |

### Schedule
- Full episode: day 1 at 18:00 ET
- Topic videos: day 2..8 at 12:00 ET (1/day)
- Shorts: day 1..N at 09:00, 13:00, 19:00 ET (3/day until pool exhausted)

## Product photos (Track B, independent)

```bash
# 27 PNGs in data/social-media/final/
python3 scripts/social/schedule_photos.py --start-date 2026-04-20 --preview
python3 scripts/social/schedule_photos.py --start-date 2026-04-20 --execute
```
2 posts/day (10:00 ET + 18:00 ET) to IG + FB as a single multi-platform post.
Captions generated once per photo via Claude; cached in
`data/social-media/captions_cache.json`.

## Rollback

- YouTube: scheduled videos are `privacyStatus=private` + `publishAt` — unschedule via
  YT Studio or delete via API before the publish time
- Zernio: `client.delete_post(post_id)` — post IDs in the schedule_log.json

## Copyright risk

Real Nintendo/Sega music in shorts → expect Content ID matches. Mitigations:
- music mixed at ~15% volume (`volume=0.15` in render_clip.py)
- `data/music-beds/` should prefer obscure tracks over iconic themes
- Reserved fallback (not yet wired): royalty-free chiptune lib if strikes pile up
