# EOD 2026-05-08 — Pick up tomorrow

User left at ~9:47 PM ET, frustrated after watching the 43 calibrated-gate
clips and finding they were still bad. Asked to stop everything until we
fix it. This doc captures exactly where we are + what's queued.

## Hard stop in place — nothing will publish

| Surface                | State                                                  |
|------------------------|--------------------------------------------------------|
| TrueNAS container      | **Stopped** (`Exited (0)`), `--restart=no` set          |
| drop_watcher           | Not running (entrypoint of stopped container)           |
| buffer_scheduler       | Not running + state locked (94 archive clips in 21d cooldown) |
| Zernio .mp4 queue      | **0 podcast shorts scheduled**                          |
| Zernio .png queue      | 18 photo posts (your separate pipeline, untouched)      |
| YouTube                | None of May 5 topic videos uploaded — see "Outstanding" |

Buffer_scheduler can't refill even if container restarts because the
state file marks every archive clip as recently-posted. To resume publishing
you'll need to (a) start the container AND (b) manually trigger a pipeline
re-run after we've verified the fixes locally.

## What happened today

### Morning
- Built calibrated 5 gates (0/1/2/3/4) + 3 enrichments (title/hashtag/audio mood)
  + whisperX integration + music bed catalog. Deployed.
- Re-ran May 5 with calibrated gates → 43 clips passed Gate 4 → scheduled
  to Zernio May 9-23.

### Afternoon
- You watched the 43 clips. They were still garbage:
  - Captions seconds ahead of audio
  - Speaker not centered (especially "in front of arcade" angle)
  - Clips starting mid-conversation with no context
  - Title "Donkey Kong Tropical Freeze" but first 10s doesn't mention DK

### Investigation revealed actual root causes
1. **whisperX never ran on existing transcripts.** transcribe.py skips on
   existing files; May 7 transcripts pre-dated whisperX integration. So
   captions used drift-prone Whisper-only timestamps.
2. **`BAD_OPENING_WORDS` missed contractions.** `"I'm"` stripped to `i'm`
   didn't match `i` in the set. Mid-conversation starts passed.
3. **`UNRESOLVED_PRONOUNS` only checked the FIRST word.** `"I'm impressed
   that THEY were able to keep..."` — `they` is 4 words in, not first.
4. **Gate 1 was confabulating context from the hook.** Claude saw
   title+hook+clip_text together and "explained" mid-conversation starts
   by inferring antecedents from the hook. Cold viewers don't see the hook.
5. **No mechanical "first 10s mentions topic" check.** Gate 1 said clip
   was OK even though "Donkey Kong" wasn't mentioned for 10 seconds.

### Fixes implemented (committed, deployed, NOT yet verified end-to-end)

Commit `b9dae70` — REAL fixes:
1. **Contractions in `BAD_OPENING_WORDS`** — i'm/they're/it's/don't/etc
2. **`_has_orphan_pronoun_in_opener()`** — scans first 10 words for
   he/she/they/it/that with no noun introduced earlier IN THE CLIP
3. **`_opener_mentions_topic()`** — mechanical: clip's first 10 sec must
   contain ≥1 keyword from title or topics
4. **Cold-viewer Gate 1 prompt** — title+hook stripped from prompt, Claude
   must judge clip standalone-ness from clip text alone
5. **`realign_transcript.py`** — one-shot whisperX wav2vec2 alignment on
   existing transcripts (no full re-transcribe). ~30-90s per source.

Commit `e3e3d61` — Operational fixes:
6. **Per-clip Navi spam silenced** — `emit_reject_navi`/`emit_flag_navi`
   default OFF (env: `QA_GATE_NAVI_ENABLED=1` to bring back). One Navi
   summary task per episode after schedule completes instead.
7. **Pipeline scoped to current episode** — `pick_clips.py` new
   `--mtime-within-days N` flag. `pipeline.py` passes `7`, so old
   transcripts (April 14, etc.) are no longer re-picked.

## What ran today and got stopped

Job 799 was running the full pipeline (realign → repick → rerender →
schedule) when you said "fix it" and "treat like real business." It got
through realign + pick_clips successfully (with the new strict checks
**actively rejecting** mid-conversation starts — 8 rejected of 25 candidates
on the May 5 V2 source, 3 final). Container was stopped before render +
schedule could finish, so nothing reached Zernio.

The fact that Gate 1 was rejecting clips with messages like:
- *"opens mid-sentence with an unresolved pronoun"*
- *"drops cold viewers into the middle of two separate conversations"*
- *"opens with unresolved pronouns mid-conversation"*

…is evidence the fixes are working — the new strict checks ARE catching
exactly the failure modes you complained about. We just didn't get to verify
the rendered output before stopping.

## Tomorrow's first move

Three options. I'd suggest #2:

**1. Verify-first rebuild (~3 hours, conservative)**
Start container → run pipeline → render only 3-5 sample clips → pull to
your laptop → watch them → decide if it's good enough → continue or iterate.

**2. Full re-run with the fixes (~4-5 hours unattended, ship-ready) ← suggested**
Start container → run the same `/tmp/owner-mode-run.sh` script (still on
NAS) which does realign + repick + rerender + schedule. Should produce
fewer but cleaner clips this time. Spot-check Zernio output before letting
anything go live by checking the queue.

**3. Step further back (1+ day)**
Discuss whether the gate architecture itself is the right approach.
Alternatives: LLM-authored cuts (Claude generates exact word-boundary
start/end), or whisperX + better face-tracker (yolov8-face) + sentence-
anchored boundaries with no Claude validation. Bigger rebuild.

## Outstanding (not yet done)

| Item | Why it matters |
|------|----------------|
| **YouTube topic video uploads** | None of the 8 approved May 5 topics + full episode are on YT. You need to authorize uploading them (saw the AskUserQuestion go unanswered). |
| **Render failures investigation** | 27 of 79 candidates failed to render in earlier run (ffmpeg errors). Pattern unknown. |
| **Camera framing (arcade angle)** | OpenCV Haar cascades miss the angled-pose. Need yolov8-face or pose-estimation. Not addressed in today's fixes. |
| **Sample inspection** | We never actually pulled rendered clips to your laptop and watched them with the new fixes applied. That's the right verification gate. |
| **GitHub push** | Still blocked autonomously. ~10 commits on local main. Run `git push origin main` when convenient. |

## Files for reference tomorrow

- `/tmp/owner-mode-run.sh` (on NAS) — the full re-run script, ready to trigger
- `/tmp/zernio-now.sh` (on NAS) — the surgical .mp4-only Zernio cleanup
- `/Users/tristanaddi1/Projects/8bit-legacy/scripts/podcast/realign_transcript.py` — whisperX align tool
- `/Users/tristanaddi1/Projects/8bit-legacy/scripts/podcast/pick_clips.py` — has new opener checks (`_has_orphan_pronoun_in_opener`, `_opener_mentions_topic`)
- Memory: `feedback_shorts_pipeline_goals.md`, `feedback_navi_qa_spam.md`, `feedback_pipeline_episode_scoping.md`, `feedback_shorts_scheduling.md`

## Honest closing

Two run cycles today produced zero shippable shorts. The gates kept saying
"approved" while you watched and saw garbage. The fixes I made tonight
(commit b9dae70) target the specific failure modes you described, but I
have no proof they actually produce watchable output until we verify with
real rendered clips. Tomorrow we should NOT push to Zernio until you've
seen sample MP4s and given the OK.
