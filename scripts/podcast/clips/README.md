# Clip Review Editor

Human-in-the-loop short-form clip extraction. Replaces the autonomous
6-layer gauntlet (still in `pick_clips.py` if you want it) with a flow
where Claude proposes, *you* curate.

## TL;DR

```bash
# 1. Pull this episode's topic transcripts + audio from TrueNAS to /tmp
python3 scripts/podcast/clips/fetch_from_nas.py "Episode May 5 2026"

# 2. Open the editor in your browser. First run also generates Claude proposals.
python3 scripts/podcast/clips/review_cli.py "Episode May 5 2026"
```

The editor opens at `http://127.0.0.1:8765/`. Adjust clips. Hit
**Submit reviewed plan**. The script unblocks; render with the existing
`render_clip.py` against the per-topic JSONs in `/tmp/Episode_May_5_2026/clips_plan/`.

## What you'll see

- **Topic tabs** on the left — switch between the 7-ish topics in the episode.
- **Transcript** in the middle. Each speaker is color-coded
  (auto-detected from the transcript's `speaker` field if present).
- **Clip ranges** appear as colored highlights inside the transcript.
  Each highlight has draggable orange handles at its start and end —
  drag them to extend or trim. Snaps to word boundaries automatically.
- **Clip cards** on the right — one per proposed/added clip. Edit the
  title, change the music vibe, toggle approval, play preview, delete.
- **+ New Clip** in the toolbar — click to mark a START word, then an
  END word. Boom, new clip.
- **Audio player** at the top — click any word in the transcript to
  jump there. Click ▶ Play on a clip card to preview just that range.

## What gets written when you Submit

`/tmp/<EpisodeName>/clips_plan/<source_stem>.json` — one per topic,
in the exact shape `render_clip.py` expects:

```json
{
  "clip_id":     "02-adult-gaming-and-handhelds_1080p_c1",
  "source_stem": "02-adult-gaming-and-handhelds_1080p",
  "start_sec":   12.5, "end_sec": 47.4,
  "title":       "...",
  "_audio_mood": "reflective",
  "_audio_music_volume": 0.10,
  "duration_sec": 34.9,
  "platform_eligibility": [...],
  "review_source": "human"
}
```

Plus a flattened `_all.json` and a `.review_done` sentinel that the CLI
watches for.

## Files

- `propose.py` — ONE Sonnet call per topic, returns 15-30 candidate
  moments. Lightweight. No filter gauntlet.
- `review_server.py` — Flask backend. `/api/episode`, `/api/save/<stem>`,
  `/api/submit`, `/audio/<stem>` (range-supported).
- `review_cli.py` — orchestrator: runs propose if needed, starts the
  server, opens the browser, blocks until you Submit.
- `fetch_from_nas.py` — rsyncs an episode's topic mp4s + transcripts
  from TrueNAS so the editor has audio to play.
- `static/{index.html,app.js,style.css}` — the editor UI. Vanilla JS, no
  build step.

## Auto-save

Every change you make POSTs to `/api/save/<stem>` immediately (or after
a 500ms debounce for typing). Safe to close the tab and re-open —
your edits are persisted to `state/<stem>.json` per topic. Re-running
`review_cli.py` for the same episode resumes where you left off.

## Common workflows

**Resume an in-progress review** — just re-run `review_cli.py`. It
re-uses the existing proposals and state.

**Regenerate proposals from scratch** — `python3 scripts/podcast/clips/review_cli.py
"Episode X" --reset`. Wipes state, clips_plan, and the sentinel. Then
delete `proposals/<stem>.json` files manually before re-running if you
want fresh Claude picks too.

**Skip Claude entirely** — `--skip-propose`. Editor opens with no
proposals; you build the plan from scratch using "+ New Clip."

**Custom episode dir** — `--episode-dir /path/to/whatever`.
