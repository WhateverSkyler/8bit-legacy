# Shorts pipeline — EOD handoff 2026-05-14 (post-round-18)

Final state at end of day 2026-05-14. Picks up from morning handoff at
`docs/handoff/SHORTS-PIPELINE-2026-05-14-MORNING.md` and supersedes the
mid-afternoon version (rounds 13–17).

## TL;DR

- All 9 rounds (13.5 through 18) **committed + pushed to remote**. Final HEAD: `0580edf`.
- **Container is running Round 17 code** (deployed earlier today).
- **Round 18 is NOT yet deployed** — its deterministic safety nets for setup/pivot detection live on local + remote but not on the NAS container.
- Speaker profile cache + silence map cache + YuNet model all present on NAS.
- **Next action when you resume:** deploy Round 18 then run ONE test on May 5.

## What's stacked into the end-completion gate right now

Four layers, each defends against a different failure mode:

| Layer | Source | What it catches |
|---|---|---|
| 1. Audio silence alignment | Round 14 | Mid-word cuts (mathematically impossible — clip always ends in a real silence period) |
| 2. Claude bidirectional gate | Rounds 15 + 16 + 17 | Setup→payoff (EXTEND) and topic-pivot endings (SHORTEN) via judgment |
| 3. SETUP safety net | Round 18 | Deterministic regex override — forces EXTEND if CURRENT BEFORE ends with `?` or contains "guess which / specifically thinking / there's one / wait until / etc". Bypasses Claude's PASS. |
| 4. PIVOT safety net | Round 18 | Deterministic regex override — forces SHORTEN if CURRENT AFTER starts with "anyway / moving on / by the way / switching topics / etc". Bypasses Claude's PASS. |

Floor/ceiling enforced at every layer — a safety-net override that would push the clip below `DURATION_FLOOR_SEC = 25s` or above `DURATION_CEILING_SEC = 54s` is disabled and Claude's verdict stands.

**Smoke-tested regex coverage:** 4/4 setup true positives, 1/1 setup true negative, 5/5 pivot true positives, 1/1 pivot true negative. The Yoshi/Kirby ("there's one I'm specifically thinking of") and Madison-pivot ("oh by the way") user-reported cases both fire on the new regexes.

## Camera state

User said "ignore camera for now, will center myself on next podcast." Speaker profile architecture is in place and tested:
- 3 speakers detected on May 5 at canonical X = 650, 954, 1167
- Cache lives at `/mnt/pool/apps/8bit-pipeline/data/podcast/source/1080p/8-Bit Podcast May 5 2026 FULL FINAL V2_1080p.speakers.json` on NAS
- YuNet ONNX model installed on host at `/mnt/pool/apps/8bit-pipeline/data/podcast/_models/face_detection_yunet_2023mar.onnx`
- `deploy/deploy-to-truenas.sh` now auto-copies the model on every deploy (committed in `149a054`)

## Resume command

```bash
cd ~/Projects/8bit-legacy
git pull --ff-only origin main  # already up-to-date

# Deploy Round 18 code to the container (~8-12 min full build)
export TRUENAS_API_KEY="$(grep ^TRUENAS_API_KEY config/.env | cut -d= -f2- | tr -d '"')"
bash deploy/deploy-to-truenas.sh
# Foreground polling caps at 4 min; the actual build takes ~10-15 min.
# Watch /tmp/8bit-pipeline-build.log on NAS for fresh DEPLOY_SUCCESS.

# Once DEPLOY_SUCCESS, run ONE validation test:
bash deploy/test-on-episode.sh "Episode May 5 2026"
# MP4s land in /tmp/Episode_May_5_2026/ when done.
```

## What to look for in the next test

```
[silence] cached 654 silence periods (audio=...)
[profile] speakers: #0 x=650, #1 x=954, #2 x=1167
[cold-opener] N picks → M kept (X adjusted, Y rejected)
[end-check] N picks → X extended, Y shortened
```

If any of these fire, the new gate is working:
- `[end-check] SAFETY-NET EXTEND: ... (setup detected: 'there's one I'm specifically thinking of'...)` — round 18 setup net fired
- `[end-check] SAFETY-NET SHORTEN: ... (pivot detected: 'oh by the way, did you see...'...)` — round 18 pivot net fired
- Either confirms the deterministic override is catching what Claude missed.

## Architecture component table

| Component | Status | File |
|---|---|---|
| Per-episode speaker profile | ✅ working | `scripts/podcast/_speaker_profile.py` |
| Audio-silence end placement | ✅ working | `scripts/podcast/_silence_detect.py` |
| Cold-opener gate (ADJUST) | ✅ working | `pick_clips.py:_cold_opener_gate` |
| End-completion gate (PASS/EXTEND/SHORTEN/REJECT) | ✅ r17 on container | `pick_clips.py:_end_completion_gate` |
| Setup/pivot safety nets | ✅ committed, NOT YET deployed | `pick_clips.py:_is_setup`, `_is_pivot` |
| Title rewriter (REWRITE/REJECT) | ✅ working | `pick_clips.py:_post_pick_enrichment` |
| Gate 2 caption sync | ⚠️ `rerender_with_offset` not wired (TODO from 2026-05-07) | `render_clip.py` |
| Gate 3 framing | ⚠️ binary `reject_reframe`; deferred per user | `render_clip.py` |
| Audio fade out (0.60s) + music ramp | ✅ working ("nice now") | `render_clip.py:_build_ffmpeg_cmd` |
| Title size/position | ✅ working (font 124 max, +2px nudge) | `render_clip.py` |

## Inherent limitations

- **SHORTEN requires a silence boundary** at the spot you want to land. If Madison rolls straight from "real ending of topic A" → "pivot to topic B" with zero audible pause between them, the gate has no silence to land on. Real-world conversations almost always have a beat — but if not, no fix.
- **EXTEND can't exceed `DURATION_CEILING_SEC = 54s`**. If a payoff lands past 54s from clip start, the gate refuses the extension. Raising the cap risks YouTube Shorts 60s limit (dialog + 5s CTA = 59s).
- **Safety-net regexes are conservative.** They only fire on obvious patterns. Subtle setups (e.g., "I have one specific game in mind" — different from the regexed phrases) still rely on Claude. Add more phrases to `_SETUP_KEYWORDS_RE` / `_PIVOT_LEAD_RE` if you spot recurring misses.

## What's deferred (not in scope this session)

- Gate 3 framing AI-directed fix — user said skip
- Gate 2 `rerender_with_offset` wiring — separate workstream
- Pre-warm speaker profile at deploy time so first short on new episode renders fast
- Generalize the "AI tells script how to fix" pattern beyond gates that already have it

## Recent commits (all pushed)

```
0580edf ROUND 18 — deterministic safety nets for end-completion gate
3ac4f4d docs: EOD handoff for shorts pipeline rounds 13-17
58863a8 round 17: tighter end-gate silence threshold + prompt cleanup
b33304e ROUND 16 — bidirectional end-completion gate (SHORTEN + EXTEND)
149a054 round 15 followups: depth-limited bisection + YuNet model deploy
b10aa9a ROUND 15 — per-speaker fixed crop_x + payoff-aware end gate
c497cbc ROUND 14 — rip-and-rebuild: audio-silence ends, YuNet per-scene camera, fixed fade
925eec4 ROUND 13.5 — c3 safety margin, audio fade, title size/nudge
57dc967 ROUND 13 — three user-flagged regressions from round-12 review
fdf8cd3 fix(pick_clips): cold-opener gate 4-tuple unpack regression
```

## One-paragraph mental model for next time

The clip end is decided in TWO stages now: a hard-deterministic placement layer that lands the cut inside a real audio silence (no mid-word cuts ever), and an LLM judgment layer that decides which silence among 8 candidates is the most narratively-satisfying landing. Round 18 added two deterministic regex safety nets that override the LLM when an unambiguous setup ("there's one I'm thinking of") or pivot ("oh by the way") is present at the chosen end. The system can only fail if (a) the source audio has no silence near the target end, in which case the pick is rejected; or (b) a setup/pivot uses phrasing not in the regex AND Claude misjudges, in which case add phrases to the regex.
