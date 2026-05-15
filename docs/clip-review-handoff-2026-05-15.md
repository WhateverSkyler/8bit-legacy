# Clip Review Editor — Handoff to laptop (2026-05-15 evening)

## What this is

Custom human-in-the-loop editor for picking shorts from podcast episodes.
Replaces the autonomous gauntlet (which kept producing bad clips for 12 rounds).

Flow: Claude proposes 50-100+ candidate clips per episode → you review them in
a custom web UI in your browser → drag handles to adjust boundaries, edit
titles, approve/skip → submit → renderer makes the videos.

Built today in `scripts/podcast/clips/`. Already pushed to GitHub at commit
`7bf4b25` (latest). Pull on laptop and you're current.

---

## Current state at handoff

**What's working:**
- Lightweight proposal generator (`propose.py`) with chunked parallel calls
  for long episodes — May 5 (67 min) generated 106 evenly-distributed
  proposals in ~30s for $0.26.
- Flask review server (`review_server.py`) — serves the editor UI, persists
  edits, range-supports audio playback.
- Editor frontend — full transcript with clip overlays, draggable handles,
  inline title editor, vibe selector, approve/skip toggle, "+ New Clip"
  by clicking start word then end word.
- Click any word to seek + play audio; shift-click clip word to focus its card.
- Drag handle: bright orange highlight on the word your boundary will snap
  to + floating tooltip showing the new duration in real time.
- Submit writes per-topic JSON in the renderer's exact contract +
  `.review_done` sentinel for the CLI to unblock the pipeline.

**What's NOT working / known issues:**
- Speaker color-coding requires pyannote diarization which isn't run yet on
  May 5 — all words show in default color. Not a blocker for usability;
  add pyannote as a follow-up if you want it.
- The proposals file at `data/podcast/proposals/` is local to this desktop
  and not committed. Laptop will need to either pull it from this machine
  or regenerate fresh ($0.26).
- The editor was tested on April 19 single-topic and started loading the
  May 5 full episode but you stopped before doing meaningful editing.
  No editorial work survives the handoff.

**Stopped processes:**
- Review server has been killed before this handoff. Nothing running.

---

## Resume on laptop — exact steps

### 1. Pull the latest code

```bash
cd ~/Projects/8bit-legacy   # or wherever the repo lives
git pull --ff-only
```

This brings in everything in `scripts/podcast/clips/` plus this handoff doc.

### 2. Install Python deps the editor needs

```bash
# Flask for the editor server
pip install --user --break-system-packages flask anthropic
# (anthropic is probably already installed; flask probably not)
```

### 3. Pull the May 5 source files from TrueNAS

```bash
# Grabs full-episode mp4 (~970MB, 5-10 min over wifi) + transcript JSON
python3 scripts/podcast/clips/fetch_from_nas.py "Episode May 5 2026"
```

Wait — `fetch_from_nas.py` currently fetches per-TOPIC files. For the full
episode, you'll want to fetch the full transcript + mp4 specifically:

```bash
mkdir -p /tmp/Episode_May_5_2026/transcripts /tmp/Episode_May_5_2026/audio /tmp/Episode_May_5_2026/proposals /tmp/Episode_May_5_2026/state /tmp/Episode_May_5_2026/clips_plan

rsync -az --info=progress2 -e "ssh -i ~/.ssh/id_ed25519" \
  'truenas_admin@192.168.4.2:/mnt/pool/apps/8bit-pipeline/data/podcast/transcripts/8-Bit Podcast May 5 2026 FULL FINAL V2_1080p.json' \
  /tmp/Episode_May_5_2026/transcripts/

rsync -az --info=progress2 -e "ssh -i ~/.ssh/id_ed25519" \
  'truenas_admin@192.168.4.2:/mnt/pool/apps/8bit-pipeline/data/podcast/source/1080p/8-Bit Podcast May 5 2026 FULL FINAL V2_1080p.mp4' \
  /tmp/Episode_May_5_2026/audio/
```

### 4. Generate proposals (or skip if you copy from desktop)

Cheapest: regenerate fresh on the laptop. ~30 seconds, $0.26.

```bash
set -a && source config/.env && set +a
python3 scripts/podcast/clips/propose.py \
  "/tmp/Episode_May_5_2026/transcripts/8-Bit Podcast May 5 2026 FULL FINAL V2_1080p.json"
cp 'data/podcast/proposals/8-Bit Podcast May 5 2026 FULL FINAL V2_1080p.json' \
   /tmp/Episode_May_5_2026/proposals/
```

Should print: `[propose] ... 67.6min → 5 parallel chunk(s)` then
`[propose] ... 100+ proposals ($0.~25)`.

### 5. Start the review server + open the editor

```bash
python3 scripts/podcast/clips/review_cli.py "Episode May 5 2026" \
  --episode-dir /tmp/Episode_May_5_2026 \
  --skip-propose
```

This:
- Starts Flask on http://127.0.0.1:8765/
- Opens your default browser
- Blocks until you click "Submit reviewed plan" in the UI

### 6. Edit in the browser

- **Click any word** → audio jumps there and starts playing
- **Hover over highlighted clips** → tooltip shows the clip title
- **Click a clip card on the right** → focuses that clip in the transcript
- **Drag the orange handles** at clip start/end → bright orange highlight
  shows where the boundary will land + tooltip shows the new duration
- **Click the title** on a clip card → edit inline
- **Toggle the green checkmark** → unapprove a clip (red strikethrough)
- **Click "+ New Clip"** → click START word, then END word
- **Click ✕** → delete a clip (with confirm)
- All changes auto-save as you go. Safe to close + reopen the tab.

### 7. Hit "Submit reviewed plan" when done

Writes `/tmp/Episode_May_5_2026/clips_plan/<stem>.json` in the renderer's
exact format + `.review_done` sentinel. The CLI exits.

### 8. Render (still on the NAS)

The reviewed plan needs to get back to the NAS for rendering. Quickest:

```bash
# Push reviewed plan to NAS
rsync -az -e "ssh -i ~/.ssh/id_ed25519" \
  /tmp/Episode_May_5_2026/clips_plan/ \
  truenas_admin@192.168.4.2:/mnt/pool/apps/8bit-pipeline/data/podcast/clips_plan/

# Trigger render via existing test infrastructure
# (or write a small render-only docker run command — see deploy/test-on-episode.sh)
```

---

## Files in the new editor (all under scripts/podcast/clips/)

| File | What it does |
|---|---|
| `propose.py` | One Sonnet call per chunk, returns 50-100+ proposals per episode |
| `review_server.py` | Flask backend — episode/save/submit/audio endpoints |
| `review_cli.py` | Orchestrator — runs propose, starts server, opens browser, blocks until Submit |
| `fetch_from_nas.py` | rsyncs episode files from TrueNAS to /tmp |
| `static/index.html` | Editor UI shell |
| `static/app.js` | All editor behavior (vanilla JS, no build step) |
| `static/style.css` | Editor styling (8-bit orange/sky-blue brand palette) |
| `README.md` | Full usage docs |

---

## Recent commits (latest first)

```
7bf4b25 clips/review: chunked proposals + click-to-play + live drag feedback
cab01cc clips/review: fix word spacing + horizontal overflow + reading width
e0ceca9 clips/review: render full transcript with overlapping clip overlays
6b57e37 clips/review: human-in-the-loop clip editor for shorts pipeline
6d9baba Revert "shorts pipeline: greenfield rebuild — replace 6-layer gauntlet ..."
```

The revert commit (`6d9baba`) brought the old `pick_clips.py` gauntlet back
in case you ever want to fall back to it. It's untouched and still callable.

---

## Open issues to consider on laptop

1. **Speaker color-coding** — needs pyannote diarization run on the source mp4
   to populate `speaker` field per word in the transcript. Currently all words
   appear in the default color. Pyannote-audio is already in the container
   deps but isn't wired up to the editor yet.

2. **The drag still might feel laggy on a 14k-word transcript** — only tested
   briefly. If it's slow, the bottleneck will be `document.elementFromPoint`
   + `requestAnimationFrame` throttling. We'd need to throttle harder or
   render only the visible viewport.

3. **No keyboard shortcuts yet** — would be nice to have:
   - Space to play/pause
   - Arrow keys to navigate clips
   - Delete to remove focused clip
   - Cmd/Ctrl-Enter to submit

4. **Audio file is 970MB** — every browser refresh re-downloads the audio
   (Range requests are supported but the browser still re-validates).
   If this gets annoying, add `Cache-Control` headers to the audio endpoint.

5. **Renderer integration is manual** — after Submit, you currently have to
   rsync the plan back to NAS and trigger render yourself. The pipeline
   stage `pipeline.py` could be wired to call review_cli automatically and
   then continue to render — that's the proper integration but I haven't
   built it yet.

---

## Quick sanity checklist on laptop

- [ ] `git pull` shows commit `7bf4b25` or later as HEAD
- [ ] `flask` and `anthropic` Python packages importable
- [ ] `~/.ssh/id_ed25519` works to truenas_admin@192.168.4.2
- [ ] `config/.env` has `ANTHROPIC_API_KEY` set
- [ ] `/tmp/Episode_May_5_2026/transcripts/8-Bit Podcast...json` exists after rsync
- [ ] `/tmp/Episode_May_5_2026/audio/8-Bit Podcast...mp4` exists (~970MB)
- [ ] `python3 scripts/podcast/clips/propose.py ...` writes the proposals JSON
- [ ] `python3 scripts/podcast/clips/review_cli.py ...` opens browser to localhost:8765

If any step fails, the error message will point at what's missing.

---

## What I'd do first when you're back at the laptop

1. Pull + install deps (5 min)
2. rsync the May 5 mp4 from NAS (10 min over wifi, faster on ethernet)
3. Run propose (30s, $0.26)
4. Open the editor, hard-refresh, look at the 100+ proposals
5. Test: click a word, does audio play? Drag a handle, do you see the live tooltip + orange word highlight?
6. If any of those don't work, open browser dev console (F12), share the red errors, and I'll fix.

Once the basic flow works, do a real review pass on May 5 and submit.
