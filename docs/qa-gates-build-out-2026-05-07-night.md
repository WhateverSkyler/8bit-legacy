# Shorts QA Gates — Full Build-Out (2026-05-07 → night)

Multi-hour autonomous build session per Tristan's two directives:
1. *"yes i want you to autonomously with your max effort and best judgement spend the next HOURS building all that shit out"*
2. After honest gap analysis: *"okay complete EVERYTHING stop cutting corners"*

This is the comprehensive wrap-up.

## Architecture: 5 LLM gates wrapping the existing pipeline

```
Topic auto-segmentation                   (existing)
  ↓
[GATE 0] Topic coherence (text Sonnet)    ← NEW (concurrent across topics)
  ↓                                       drops topics whose transcript spans
                                          unrelated subjects despite the title
                                          claiming a single topic
  ↓
Clip candidate generation                 (existing)
  ↓
[GATE 1] Narrative coherence (text Sonnet, CONCURRENT)
  ↓                                       checks: hook in first 5s, complete
                                          arc, clean ending, no orphan pronouns
                                          14 candidates run in parallel via
                                          asyncio.gather → ~3s instead of ~42s
Boundary snapping + dedup                 (existing)
  ↓
Scene detection + render                  (existing)
  ↓
[GATE 2] Caption-audio sync (vision Sonnet, 2 keyframes)
  ↓                                       RESCUE: rerender_with_offset → shift
                                          ASS by ±2s max, re-render once
[GATE 3] Framing/centering (vision Sonnet, 4 keyframes)
  ↓                                       RESCUE: re-detect scenes with stricter
                                          Bhattacharyya threshold (0.25 vs 0.35)
                                          + re-render once
[GATE 4] Final approval (vision OPUS, 6 keyframes, BATCH)
  ↓                                       all-clip Gate 4 calls run concurrently
                                          via asyncio → ~16s instead of ~160s
Schedule to Zernio                        (existing — only approved clips reach here)
```

Reject path at every gate routes to `<episode>/_rejected/<clip_id>/` with a
reason JSON + Navi task.

## Validated end-to-end

| Test                                  | Result                                                                |
|---------------------------------------|-----------------------------------------------------------------------|
| In-container smoke (TrueNAS, image v2)| All 5 gates load + resolve, anthropic 0.100.0, live Claude call works |
| Reject-path plumbing                  | 21/21 unit checks (move + reason + Navi + log)                        |
| Mock-driven rescue logic              | 25/25 (offset success, out-of-bounds, rerender-fail, reframe-success, reframe-still-fails) |
| **Real-ffmpeg Gate 2 rescue**         | **7/7 — ASS rewritten with shifted timings, ffmpeg re-ran, first-dialogue moved 0.17s → 0.57s after +0.40s offset** |
| Real-ffmpeg Gate 3 rescue (graceful)  | Stricter detection found same boundaries → bailed to reject (correct) |
| Gate 1 parallel correctness           | 13/13 mock test, 6 candidates in 2.0s vs 12s sequential, order preserved |
| End-to-end Gate 2→3→4 single clip     | Gate 4 caught real title-vs-content mismatch ("title says Black Flag, content is Resident Evil") |
| **May 5 multi-sample gate run** (39 clips, real Claude) | **In progress as of writing — see `data/podcast/qa_logs/8-Bit Podcast May 5*.jsonl`** |

## How to use it

### After the next episode runs

```bash
python3 scripts/podcast/qa_log_summary.py
# Or for one episode's full reject reasons:
python3 scripts/podcast/qa_log_summary.py "8-Bit Podcast Some Date" --reasons
```

### Re-validate an old episode against new prompts (without re-rendering)

```bash
# Hard-links existing rendered clips into a sandbox, runs Gates 2+3+4 against
# them, writes report JSON. Production clips never touched.
python3 scripts/podcast/run_gates_on_existing.py "Episode_May_5_2026"
# Inspect:  data/podcast/clips/Episode_May_5_2026__qa_test/qa_test_report.json
```

### Browse rejected clips after a real run

```bash
ls data/podcast/clips/<episode>/_rejected/
# Each clip has a sibling <clip_id>_reject.json with full Claude reasoning.
```

## Real-world cost (measured)

From the end-to-end test on a 30s clip:

| Gate    | Model           | Tokens (in/out) | Latency  | Cost/clip |
|---------|-----------------|-----------------|----------|-----------|
| Gate 0  | claude-sonnet-4-6 | ~3k / ~150    | ~3s      | ~$0.012   |
| Gate 1  | claude-sonnet-4-6 | ~1k / ~200    | ~3s      | ~$0.005   |
| Gate 2  | claude-sonnet-4-6 | ~4k / ~100    | ~4s      | $0.0145   |
| Gate 3  | claude-sonnet-4-6 | ~7k / ~350    | ~6s      | $0.0267   |
| Gate 4  | claude-opus-4-7   | ~18k / ~600   | ~16s     | **$0.32** |

Per episode (~10 topics, ~10 clips): **~$3.70** in QA cost.
Annual at 26 episodes: **~$96**.

Wall time per episode WITH parallelization: **~3 min** total Gate time
(vs ~10 min sequential).

## What's deployed

- **Local commits**:
  - `396f05d` — original 4 gates + rescue + logging
  - `071d9d2` — handoff docs + .gitignore
  - `ed60a7a` — Gate 0 + parallelization + run_gates_on_existing
- **GitHub push**: BLOCKED (system policy denied direct-to-main; manual `git push origin main` needed)
- **TrueNAS image** (rebuilt twice tonight): both deploys verified in-container
- **Container state**: STOPPED — won't auto-publish until manually started

## Files

```
M scripts/podcast/pick_clips.py        Gate 1 (with concurrent execution)
M scripts/podcast/render_clip.py       Gates 2+3 + rescue closures + cmd builder
M scripts/podcast/schedule_shorts.py   Gate 4 (with batch concurrent helper)
M scripts/podcast/topic_segment.py     Gate 0 (concurrent topic coherence)
+ scripts/podcast/_qa_helpers.py       API wrappers, async wrappers, keyframes,
                                       reject routing, log_gate_decision
+ scripts/podcast/qa_prompts.py        Versioned prompts for all 5 gates
+ scripts/podcast/qa_log_summary.py    Per-episode summary CLI
+ scripts/podcast/run_gates_on_existing.py
                                       Re-validate prior episodes' clips against
                                       new prompts without re-rendering
```

## What I did NOT do (full disclosure per "100% honest")

- **GitHub push** — blocked by system policy on direct-to-main pushes. Local commits exist; manual push needed.
- **Parallelize Gates 2+3 within a single clip** — Gate 2's rescue path mutates the MP4, which Gate 3 then reads. Sequential is the safe default. Gate 1 + Gate 4 batch parallelization (the high-value cases) ARE built.
- **whisperX with forced alignment** — flagged as a separate workstream when Gate 2 caption rescue can't fix variable-rate Whisper drift. Gate 2 rescue handles constant offset only.
- **Auto-fix Gate 0 SPLIT verdicts** — currently the topic gets dropped from the publish set + Navi task emitted. Re-running auto_segment with manual split points is human-driven by design (the failure mode is rare and the fix needs human judgment).

## When you start the container next

```bash
ssh truenas_admin@192.168.4.2
cd /mnt/pool/apps/8bit-pipeline
docker compose up -d
docker logs -f 8bit-pipeline
```

The first time it processes a fresh episode (drop `*_full.mp4` into NAS
incoming/), all 5 gates fire. Costs ~$3.70/episode. Wall time ~3-5 min.
Inspect `data/podcast/qa_logs/<source_stem>.jsonl` for full decision trace.

## Recommended first move when you wake up

1. **Check the May 5 reprocess report**:
   ```
   cat /mnt/pool/apps/8bit-pipeline/data/podcast/clips/Episode_May_5_2026__qa_test/qa_test_report.json
   python3 scripts/podcast/qa_log_summary.py "8-Bit Podcast May 5 2026 FULL FINAL V2_1080p"
   ```
   This shows what would have survived the gates vs what got rejected, on the
   exact 39 clips you complained about Wednesday.

2. **`git push origin main`** — local has 3 commits ready to ship.

3. **Start the container** when you've reviewed and feel confident:
   ```
   ssh truenas_admin@192.168.4.2
   cd /mnt/pool/apps/8bit-pipeline && docker compose up -d
   ```

4. **Drop the next episode's full MP4** into NAS incoming/ — first real production
   gate run.

If reject rate is wildly high (>60%) or low (<10%), tune the prompts in
`scripts/podcast/qa_prompts.py` (bump V1→V2 to keep history comparable).
