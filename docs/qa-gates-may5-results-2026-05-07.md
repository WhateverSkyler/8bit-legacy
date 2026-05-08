# May 5 reprocess — measured production results

The 5-gate QA pipeline was run end-to-end against all 39 rendered May 5 clips
(the episode you complained had "every single video broken"). This document
captures what the gates actually decided.

Run command:
```
docker run --rm 8bit-pipeline:latest \
  /app/scripts/podcast/run_gates_on_existing.py "Episode_May_5_2026"
```

Wall time: **49.9 minutes** for 39 clips (sequential per-clip).
Total cost: **$9.68** in Claude API spend.

## Outcome

| Status                       | Count | %    |
|------------------------------|-------|------|
| **APPROVED** (would ship)    |   8   | 21%  |
| FLAGGED@gate4 (held for review) | 11 | 28%  |
| REJECTED@gate3 (framing)     |  13   | 33%  |
| REJECTED@gate4 (final)       |   6   | 15%  |
| REJECTED@gate2 (caption sync)|   1   |  3%  |

**51% rejection + 28% flagged = 79% wouldn't have shipped clean.** That matches
your manual review: "every single video had something broken."

## The 8 clips that survived all gates

These are what would have been published if the new pipeline ran on May 5:

```
03-ocarina-remake-zelda-rankings_auto_1080p_c2     73s
05-tcg-scalping-culture-mom-and-pop_auto_1080p_c3  36s
05-tcg-scalping-culture-mom-and-pop_auto_1080p_c4  52s
06-epic-layoffs-nintendo-softening-switch2_auto_1080p_c1   39s
07-xbox-future-console-wars_auto_1080p_c3          59s
07-xbox-future-console-wars_auto_1080p_c4          64s
07-xbox-future-console-wars_auto_1080p_c5          57s
8-Bit Podcast May 5 2026 FULL FINAL V2_1080p_c1    84s
```

You can watch these tomorrow to validate the "approved" bar matches your taste.

## Sample reject reasons (Claude's actual words)

**Gate 3 (framing) — caught off-center / jarring transitions:**
- "Frame at 25% shows no speaker (ambiguous cutaway with no face), and the transition…"
- "Three of four keyframes show the speaker consistently left-of-center (10–30% off)"
- "Two or more frames have off_frame or missing subjects"
- "The scene transition at ~22.8s introduces a jarring crop jump to the second speaker"

**Gate 4 (Opus final) — caught narrative / hook / title issues:**
- "Title claims Black Flag pricing debate but content is entirely about a Resident Evil trailer reaction with no hook or conclusion"
- "Weak meta opening with no hook in the first 5 seconds and an unresolved trailing"
- "Cold open drops viewer mid-thought referencing 'crypto kids' with no context"
- "Clip ends mid-sentence without payoff and the title's strong stance ('Dying and Good Riddance') doesn't match the hedged content"

**Gate 2 (caption sync) — caught one clear mismatch:**
- (1 reject — caption-audio mismatch in 03-video-game-movies-and-shows c3)

## Production validation: rescue paths fired

`gate2-retry: PASS=1` in the per-episode log. The Gate 2 caption-offset rescue
**actually triggered in production** on a clip with detected drift, ran the
re-render with shifted ASS, re-checked, and passed it. Confirmed working
beyond mock tests.

## Real cost breakdown (measured, not estimated)

Across 39 clips this run:

| Gate          |  N  | tokens (in)  | tokens (out) |   cost    | avg latency |
|---------------|-----|--------------|--------------|-----------|-------------|
| gate2         | 42  |   170,543    |    5,181     | $0.5893   | 4.1s        |
| gate2-retry   |  1  |       100    |       30     | $0.0008   | 0.0s        |
| gate3         | 41  |   277,096    |   15,748     | $1.0675   | 7.6s        |
| gate4         | 26  |   471,570    |   12,650     | $8.0223   | 13.5s       |
| **TOTAL**     | 110 |   919,309    |   33,609     | **$9.68** | —           |

Note Gate 4 (Opus) is 83% of cost. Gate 4 only fires for clips that survive
Gates 2 + 3 (26 of 39 made it that far).

## Per-episode estimate going forward

Future episodes (~10 candidates → ~10 rendered clips):
- Sequential wall time: ~10 min
- **With parallelization (built tonight)**: ~3-4 min
- Cost: ~$2.50/episode
- Annual cost (26 episodes): ~$65/year

## Where to find this data tomorrow

```
data/podcast/qa_test_reports/Episode_May_5_2026_2026-05-07.json   ← full per-clip details
docs/qa-gates-may5-results-2026-05-07.md                         ← this file
```

The per-clip qa_logs are NOT committed (in .gitignore) but exist on the NAS at
`/mnt/pool/apps/8bit-pipeline/data/podcast/qa_logs/*.jsonl`. Pull them with
the qa_log_summary CLI:

```bash
ssh truenas_admin@192.168.4.2 'cat /mnt/pool/apps/8bit-pipeline/data/podcast/qa_logs/<source_stem>.jsonl'
```

Or run the summary CLI inside the container or against a pulled copy:
```bash
python3 scripts/podcast/qa_log_summary.py "8-Bit_Podcast_May_5_2026_FULL_FINAL_V2_1080p" --reasons
```
