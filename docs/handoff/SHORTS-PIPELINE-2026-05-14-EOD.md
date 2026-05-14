# Shorts pipeline — EOD handoff 2026-05-14 (post-round-17)

Picking up from the morning handoff at `docs/handoff/SHORTS-PIPELINE-2026-05-14-MORNING.md`.

## State right now

- **All 9 rounds committed AND pushed to remote** (final HEAD: `58863a8`).
- **r17 deploy NOT yet kicked off.** Code is on local + remote; container is running r16 code (which is r15 + SHORTEN verdict).
- **Speaker-profile cache exists on NAS** at `/mnt/pool/apps/8bit-pipeline/data/podcast/source/1080p/8-Bit Podcast May 5 2026 FULL FINAL V2_1080p.speakers.json` — 3 speakers at canonical_x = 650, 954, 1167.
- **YuNet ONNX model installed on NAS host** at `/mnt/pool/apps/8bit-pipeline/data/podcast/_models/face_detection_yunet_2023mar.onnx`. `deploy-to-truenas.sh` now copies it on every deploy (committed in `149a054`).
- **Silence map cached** at `/mnt/pool/apps/8bit-pipeline/data/podcast/source/1080p/8-Bit Podcast May 5 2026 FULL FINAL V2_1080p.silence.json` — 654 silence periods at -35dB:d=0.20.

## What r17 changed (just pushed, untested)

Commit `58863a8` makes two small refinements on top of r16:

1. **GATE_END_MIN_SILENCE_SEC = 0.22** (vs strict 0.30 for `_snap_and_validate`). The end-completion gate now considers slightly shorter pauses as candidate landings. Reason: the c3 Yoshi/Kirby user feedback ("ended right as Ryan was about to give the answer") suggests the answer-landing silence may have been <0.30s and invisible to the gate. Strict 0.30 stays for first-pass placement.

2. **Dropped a redundant `last_sentence` block** from `END_COMPLETION_TEST_V1`. The `<-- CURRENT` marker on the bidirectional candidate list conveys the same info.

## How to resume

```bash
cd ~/Projects/8bit-legacy
git pull --ff-only origin main  # should already be up-to-date

# Deploy r17 to the container (re-copies scripts, picks up new threshold)
export TRUENAS_API_KEY="$(grep ^TRUENAS_API_KEY config/.env | cut -d= -f2- | tr -d '"')"
bash deploy/deploy-to-truenas.sh   # foreground polling caps at 4 min; the actual
                                    # build takes ~8-15 min. Wait for DEPLOY_SUCCESS
                                    # in /tmp/8bit-pipeline-build.log on NAS.

# Once DEPLOY_SUCCESS is in the build log, run ONE validation test:
bash deploy/test-on-episode.sh "Episode May 5 2026"
# Pulls MP4s to /tmp/Episode_May_5_2026/ when done.
```

## What to look for in the next test

Per user's stated complaints (round-15-v2 review):

1. **No mid-sentence cuts** — should be solid since r14 audio-silence-aligned ends.
2. **No pivot/tangent at end** — NEW r16 SHORTEN should fire if any clip's current end captures a Madison-style pivot. Log line:
   ```
   [end-check] SHORTEN: <title> end <old>s → <new>s (...pivot reason...)
   ```
3. **Setup → payoff** — NEW r15 EXTEND should fire for tease/question setups:
   ```
   [end-check] EXTEND: <title> end <old>s → <new>s (...payoff reason...)
   ```
4. **Speaker profile log** at the start of the render section:
   ```
   [profile] speakers: #0 x=650, #1 x=954, #2 x=1167
   ```
5. **Scene log** in new format (no more `bucketed by 100px`):
   ```
   [SCENES] N cuts → M scenes (ffmpeg only)
   ```

## Architecture summary (where things stand)

| Component | Status | File |
|---|---|---|
| Per-episode speaker profile | ✅ working | `scripts/podcast/_speaker_profile.py` |
| Audio-silence end placement | ✅ working | `scripts/podcast/_silence_detect.py` |
| Cold-opener gate (ADJUST) | ✅ working | `pick_clips.py:_cold_opener_gate` |
| End-completion gate (PASS/EXTEND/SHORTEN/REJECT) | ✅ r16 + r17 deployed code | `pick_clips.py:_end_completion_gate` |
| Title rewriter (REWRITE/REJECT) | ✅ working | `pick_clips.py:_post_pick_enrichment` |
| Gate 2 caption sync | ⚠️ `rerender_with_offset` not wired (TODO from 2026-05-07) | `render_clip.py` |
| Gate 3 framing | ⚠️ binary `reject_reframe`; rescue is generic threshold-tweak, not AI-directed | `render_clip.py` |
| Audio fade out (0.60s) + music ramp | ✅ working ("nice now") | `render_clip.py:_build_ffmpeg_cmd` |
| Title size/position | ✅ working (font 124max, +2px nudge) | `render_clip.py` |

## Inherent limitations (cannot fix without bigger changes)

- **SHORTEN requires a silence boundary** at the spot you want to land. If a speaker rolls straight from "real ending of topic A" → "Madison pivot to topic B" with no audible pause between them, the gate has no silence to land on. Real-world podcasts almost always have a beat between topics so this is rarely a problem.
- **EXTEND can't go past `DURATION_CEILING_SEC = 54.0s`**. If a payoff lands at 55-60s from clip start, the gate refuses the extension. Raising the cap means longer total clips (dialog + 5s CTA must stay ≤ 60s for YT Shorts).
- **Claude's judgment is non-deterministic.** Even with the bidirectional candidate list + payoff-aware prompt, Claude can occasionally pick a non-optimal candidate. The deterministic safety net is the silence-alignment itself: every candidate is a real audio pause, so the worst case is "ended at a real pause but not the optimal one" — never mid-word.

## What's NOT yet done (deferred)

- **End-to-end test of r17** — code merged + pushed but not tested. Run the deploy + test pair above.
- **Gate 3 AI-directed framing fix** — user said "ignore camera for now"; they'll center themselves on the next podcast shoot.
- **Gate 2 `rerender_with_offset` wiring** — separate workstream from 2026-05-07 plan.
- **Push the speaker-profile build into the deploy step itself** — currently the profile builds lazily on first render after a new episode is recorded. Could pre-warm it at deploy time so the first short for a new episode renders fast.

## Recent commits (all pushed)

```
58863a8 round 17: tighter end-gate silence threshold + prompt cleanup
b33304e ROUND 16 — bidirectional end-completion gate (SHORTEN + EXTEND)
149a054 round 15 followups: depth-limited bisection + YuNet model deploy
b10aa9a ROUND 15 — per-speaker fixed crop_x + payoff-aware end gate
c497cbc ROUND 14 — rip-and-rebuild: audio-silence ends, YuNet per-scene camera, fixed fade
925eec4 ROUND 13.5 — c3 safety margin, audio fade, title size/nudge
57dc967 ROUND 13 — three user-flagged regressions from round-12 review
fdf8cd3 fix(pick_clips): cold-opener gate 4-tuple unpack regression
```
