# Shorts Pipeline — Handoff EOD 2026-05-15

## State at session end

- **Round 20** (commit `04e3ba9`) + **Round 20.1 fix** (commit `e62dcc1`) — both deployed to TrueNAS, validated end-to-end via `test-on-episode.sh "Episode May 5 2026"`.
- Pipeline currently produces **0 final clips** on May 5 episode because Layer C (coherence) is strict enough to reject every survivor.
- This is technically the system **working as designed** — the user said quality > quantity, and Layer C found real problems with all 3 survivors. But 0 clips/episode is too aggressive for the "3 reels/day" goal in `feedback_shorts_pipeline_goals.md`.

## What's running now

```
candidates (Claude initial pick, 25/chunk × 2 chunks = 50)
  ↓ Gate 1 narrative coherence       50 → 39
  ↓ Layer F single_topic_check       39 → 30   (multi-topic clips killed)
  ↓ snap_and_validate + de_overlap   30 → 4
  ↓ cold_opener gate                 4  → 3
  ↓ end_completion_gate              3  → 3   (Layer A sentence-end silence preferred; Layer D REJECT on FLOOR works)
  ↓ Layer E grammar_guard            3  → 3   (sentence-end map; correctly rejects mid-sentence emphasis pauses post-20.1)
  ↓ Layer C clip_coherence_check     3  → 0   ← all 3 rejected as having real problems
  ↓ render
```

## The unresolved question — Layer C strictness

Three options on the table when user goes back online:

### (a) Accept 0 clips on this episode
- Trust the layers — Layer C is catching real issues.
- Pipeline waits for an episode with cleaner content.
- Risk: producing fewer than 3 reels/day on some weeks.

### (b) Loosen Layer C — require 2+ failures (not just any failure) to reject
- Layer C prompt currently rejects if `stands_alone`, `ends_on_payoff`, or `single_topic` is ANY false.
- Change: only reject if **2 or more** are false.
- Result: probably ~2 clips would survive (Black Flag and Pokemon Scalpers had only one issue each; GameStop-eBay had a real mid-thought ending that 2+ failures would still catch).
- File: `scripts/podcast/pick_clips.py` — `_clip_coherence_check` function.

### (c) Bump initial candidate count from Claude
- Currently 25 picks per chunk → 50 total per episode.
- Try 40 per chunk → 80 total. Gives downstream gates more candidates to find clean ones.
- Cost: ~2x Claude tokens for the initial pick stage (small absolute cost — ~$0.10/run).
- File: `scripts/podcast/pick_clips.py` — `PICKS_REQUESTED` constant (line ~21 region).

**Recommendation when user picks**: try (c) first since it's cheapest behaviorally — gives more raw material. If still 0 clips, then (b).

## Round 20 / 20.1 — what shipped this session

### Layer A — silence classifier (`_silence_detect.py`)
- `classify_silence(silence, words)` returns `"sentence-end"` or `"mid-sentence"` using combined audio (duration) + transcript (terminal-punct + next-word gap) signals.
- `sentence_end_silences(map, tx)` filters the raw silence map.
- **20.1 priority guard**: if next word starts <0.10s after silence ends, ALWAYS classify mid-sentence regardless of duration. Catches emphasis pauses (the c1 Black Flag bug: 0.66s pause inside "this is a game ... that is like over a decade old" was duration-classified as sentence-end pre-fix).
- May 5 hit ratio after 20.1: 187 of 654 (29%).

### Layer B — `[SE]` markers in TOPIC_CONCLUSION_TEST_V1
- Each sentence in the end-gate prompt window is annotated with `[SE]` when its end timestamp aligns with a sentence-end silence in the audio. Claude told to pick only `[SE]`-tagged timestamps as `conclusion_timestamp`.

### Layer C — `_clip_coherence_check` in `pick_clips.py`
- Post-end second-opinion gate. One Claude call per finalized clip. Rejects when `ok=false`.
- Currently STRICT — see (b) above.
- Prompt: `CLIP_COHERENCE_TEST_V1`.

### Layer D — REJECT on FLOOR in `_end_completion_gate`
- When the semantic conclusion target lands `< DURATION_FLOOR_SEC` (25s), pick is DROPPED instead of falling back to original end. Prior round-19.5 behavior silently shipped fragments (the c2 Wind Waker disaster).

### Layer E — `_last_sentence_grammar_guard`
- Deterministic backstop. Clip ships only if last word ends with `.!?` OR silence ≥0.60s starts within ±0.30s of clip end.
- **20.1**: now uses `sentence_end_map` (not raw silence_map) so the long-tail-silence path only triggers on real conversational boundaries.

### Layer F — `_single_topic_check`
- Pre-snap multi-topic guard. Rejects candidates that span multiple unrelated conversational topics. On May 5: killed 9 picks (Wind Waker, Tears of the Kingdom variants, Donkey Kong Country, Sega/Xbox, DualSense, etc.).
- Prompt: `SINGLE_TOPIC_TEST_V1`.

## Files modified this session

```
scripts/podcast/_silence_detect.py     — Layer A classifier + 20.1 priority guard
scripts/podcast/pick_clips.py          — Layers C, D, E, F + wiring
scripts/podcast/qa_prompts.py          — TOPIC_CONCLUSION_TEST_V1 [SE] markers, CLIP_COHERENCE_TEST_V1, SINGLE_TOPIC_TEST_V1
```

## How to resume

1. Read this doc + `memory/project_shorts_pipeline_state.md`.
2. Ask user which of (a)/(b)/(c) above to try first.
3. Implement that change.
4. Redeploy + retest:
   ```bash
   set -a && source config/.env && set +a
   bash deploy/deploy-to-truenas.sh
   # WAIT for DEPLOY_SUCCESS in /tmp/8bit-pipeline-build.log (the deploy script's
   # 4-min polling sometimes returns BEFORE the build finishes — use this until-loop
   # to be safe before kicking off the test:
   until scp -i ~/.ssh/id_ed25519 -q truenas_admin@192.168.4.2:/tmp/8bit-pipeline-build.log /tmp/_build.log 2>/dev/null && tail -1 /tmp/_build.log | grep -q DEPLOY_SUCCESS; do sleep 20; done
   bash deploy/test-on-episode.sh "Episode May 5 2026"
   ```
5. Pull run.log + rendered MP4s:
   ```bash
   scp -i ~/.ssh/id_ed25519 -q truenas_admin@192.168.4.2:/tmp/test-on-episode-runner.out /tmp/Episode_May_5_2026/run.log
   ls /tmp/Episode_May_5_2026/*.mp4
   ```
6. Review the rendered MP4s with user — visual check for clean opens, clean ends, single topic, comprehensible to cold viewer.

## Validation tests on disk

These remain useful for re-checking Layer A + E logic locally without burning API:

- `/tmp/r20_smoke.py` — imports + synthetic-data smoke tests
- `/tmp/r20_grammar_test.py` — grammar-guard against the r19.5 May 5 picks (expects c2/c3 REJECTED, c4/c5 KEPT)
- `/tmp/r20_se_markers_test.py` — confirms `[SE]` markers attach correctly in end-gate window text

## What's NOT done

- **Gate 3 camera framing** — still rejects many picks because of off-center camera shot. User said "I'll just center my camera shot for the next podcast" — defer until next recording (biweekly Tue, next is ~2026-05-19).
- **Audio-distribution / Spotify+Apple** — separate workstream, see `project_audio_distribution.md`.
- **Ad campaign re-enable canary** — separate workstream, see `project_ads_launch_state.md`.

## Memory updates this session

- `project_shorts_pipeline_state.md` — bumped to "Round 20.1 deployed", added Layer breakdown + classifier thresholds.
- `MEMORY.md` index entry updated to point at the new state.
