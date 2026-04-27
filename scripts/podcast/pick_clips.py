#!/usr/bin/env python3
"""Pick stand-alone short-form moments from a podcast transcript using Claude.

QUALITY BAR (per user direction 2026-04-20): every clip must make sense to a viewer who
has NEVER heard the podcast before. No mid-thought starts. No unresolved pronouns in the
opening. Complete setup → payoff arc.

DURATION POLICY (2026-04-23): 45-65 sec sweet spot, 30s floor, 85s ceiling —
biased toward completion rate over absolute length.

Input:  data/podcast/transcripts/<stem>.json  (from transcribe.py — word-level timestamps)
Output: data/podcast/clips_plan/<stem>.json   with 4-5 validated picks per topic:
    [
      {
        "clip_id": "01-aaa-gaming-debate_c1",
        "source_stem": "01-aaa-gaming-debate_1080p",
        "start_sec": 47.3,
        "end_sec": 128.5,
        "duration_sec": 81.2,
        "title": "AAA Gaming Is Cooked",
        "hook": "Publishers want $80 games but refuse to ship anything worth $80.",
        "topics": ["aaa gaming", "game pricing"],
        "stand_alone_score": 0.9,
        "quality_score": 0.85,
        "validation": "ok",
        "boundary_adjusted": true
      }, ...
    ]

Usage:
    python3 scripts/podcast/pick_clips.py <transcript.json>
    python3 scripts/podcast/pick_clips.py --batch data/podcast/transcripts/
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent.parent
CLIPS_PLAN_DIR = ROOT / "data" / "podcast" / "clips_plan"

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / "config" / ".env")
except ImportError:
    pass


# --- Duration policy (2026-04-23: biased toward completion rate) ---
# TikTok/Reels reward near-full watches. A 75s clip watched 70% through beats a
# 50s clip watched 40%, BUT shorter clips have a meaningful completion-rate
# advantage, so we bias toward the lower end of a still-standalone arc.
DURATION_FLOOR_SEC = 30.0      # below this the clip feels like a fragment
DURATION_TARGET_LO = 45.0      # sweet-spot lower bound
DURATION_TARGET_HI = 65.0      # sweet-spot upper bound
DURATION_CEILING_SEC = 85.0    # hard cap — longer clips tank watch-through rate

# --- Stand-alone validators ---
BAD_OPENING_WORDS = {
    # Continuation conjunctions — imply prior context
    "so", "and", "but", "then", "because", "anyway", "also", "plus",
    # Filler agreement — implies responding to something
    "yeah", "yep", "right", "exactly", "totally", "absolutely",
    # Mid-thought markers
    "like", "you", "i",  # "like I was saying", "you know what", "I mean"
    "oh",
}
UNRESOLVED_PRONOUNS = {
    "he", "she", "they", "it", "that", "this", "those", "these", "him", "her", "them",
}
SENTENCE_END_PUNCT = {".", "!", "?"}

PICKS_REQUESTED = 7  # ask Claude for a few extra so validation can prune aggressively


SYSTEM_PROMPT = """You are an elite short-form content editor (TikTok / Instagram Reels / YouTube Shorts) for The 8-Bit Legacy Podcast, a retro gaming show.

YOUR PRIMARY TEST — apply to every clip candidate:
> "If this is the FIRST thing someone ever sees from 8-Bit Legacy — never heard the show, no prior context — does this clip make complete sense and deliver a satisfying beat?"

If the answer is no, the clip fails. No exceptions.

STAND-ALONE REQUIREMENTS (non-negotiable):
1. **Opening sets its own context.** The first sentence must introduce what's being discussed — no "so then...", "yeah exactly...", "and that's why...", "like I said...", "he was saying that...". If the opening uses a pronoun (he/she/they/it/that), the pronoun's antecedent must be named immediately after, inside the clip.
2. **Complete arc.** Setup → payoff. A punchline without setup, or a setup without payoff, is a reject.
3. **Clean end.** Ends on a conclusion, punchline, strong claim, or a "tell me what you think" callout. Does NOT fade out mid-thought, trail off into filler, or cut on a "yeah, I don't know, whatever."

DURATION TARGET (optimized for TikTok/Reels completion rate):
- Sweet spot: 45–65 seconds
- Floor: 30 seconds (below this feels like a fragment, no payoff)
- Ceiling: 85 seconds (above this watch-through tanks on algorithm)
Err shorter if the arc lands cleanly; longer videos lose more viewers proportionally than they gain.

WHAT MAKES A STRONG PICK:
- Confident opinion with stakes ("Nintendo is making a mistake with X because...")
- Surprising fact or sharp numerical claim
- Shared bit that genuinely lands (not just nervous laughter)
- Clear hot take that invites comment
- Origin story / "how did we get here" with a payoff

WHAT TO REJECT EVEN IF IT SOUNDS FUNNY:
- Inside jokes that need prior episodes
- Tangent intros that pay off 30 seconds later (cut to the payoff)
- Anything where the first 5 seconds are filler before the real thought starts (push start later)
- Clips that reference "earlier we were saying" or "as I mentioned"

Return strict JSON ONLY — a JSON ARRAY of picks, no prose, no markdown fences. Each pick:
{
  "start_sec": <float>,
  "end_sec": <float>,
  "title": "4-7 word title case, no clickbait punctuation",
  "hook": "one sentence, first-person or direct address, no hashtags",
  "topics": ["2-4 lowercase tags"],
  "stand_alone_score": <float 0-1, 1 = passes the primary test perfectly>,
  "quality_score": <float 0-1, 1 = strong scroll-stopper>,
  "reasoning": "one sentence explaining why this clip stands alone"
}

Start/end seconds should match word-level timestamps and land on sentence boundaries.
Err on the side of giving MORE context at the start if it helps stand-alone comprehension."""


USER_TEMPLATE = """Topic segment: {topic_name}

Word-level transcript with timestamps below. Segment boundaries are marked [SEG-N start=<s> end=<s>] — these are pause-detected sentence-ish units; your start_sec/end_sec should align to these when possible.

{transcript_blob}

Return a JSON ARRAY of {n} clip picks in the format described. Do not include any prose, explanation, or markdown fences outside the JSON."""


def _format_transcript_for_prompt(tx: dict, max_chars: int = 80000) -> str:
    """Emit a compact transcript representation with segment markers so Claude can align to boundaries."""
    lines: list[str] = []
    total = 0
    for i, seg in enumerate(tx.get("segments", [])):
        header = f"\n[SEG-{i} start={seg['start']:.2f} end={seg['end']:.2f}]\n{seg['text'].strip()}\n"
        if total + len(header) > max_chars:
            lines.append("\n[…transcript truncated…]\n")
            break
        lines.append(header)
        total += len(header)
    return "".join(lines)


# --- Boundary snapping + validation -----------------------------------------

def _find_segment_containing(t_sec: float, segments: list[dict]) -> int | None:
    """Return index of the segment whose [start, end] contains t_sec (or the nearest preceding one)."""
    if not segments:
        return None
    # First pass: exact containment
    for i, seg in enumerate(segments):
        if seg["start"] <= t_sec <= seg["end"]:
            return i
    # Fallback: nearest segment preceding t_sec
    best = None
    for i, seg in enumerate(segments):
        if seg["start"] <= t_sec:
            best = i
    if best is None:
        # t_sec before all segments → use first segment
        return 0
    return best


def _first_content_word(seg: dict) -> str:
    words = seg.get("words") or []
    if not words:
        # Fallback to parsing text
        m = re.search(r"[A-Za-z']+", seg.get("text", ""))
        return (m.group(0) if m else "").lower()
    w = (words[0].get("word") or "").strip().lower()
    # Strip punctuation
    return re.sub(r"[^a-z']", "", w)


def _segment_ends_cleanly(seg: dict) -> bool:
    text = (seg.get("text") or "").strip()
    return bool(text) and text[-1] in SENTENCE_END_PUNCT


def _snap_and_validate(
    pick: dict,
    segments: list[dict],
) -> tuple[dict, bool, str]:
    """Snap start/end to segment boundaries, then validate stand-alone + duration rules.

    Returns (updated_pick, is_valid, reason).
    If stand-alone fails, tries extending back/forward one segment to rescue before rejecting.
    """
    start_idx = _find_segment_containing(pick["start_sec"], segments)
    end_idx = _find_segment_containing(pick["end_sec"], segments)

    if start_idx is None or end_idx is None:
        return pick, False, "no matching segments"

    if start_idx > end_idx:
        return pick, False, "start after end"

    # --- Validation loop with rescue: try current boundaries, then extend back/forward ---
    # 2026-04-26: bumped max_extensions 2→4 and added forward-skip fallback for
    # bad openings (previously only pulled in prior segment, which often failed
    # if the prior segment also opened with filler). Higher acceptance rate
    # without sacrificing the "never cut mid-sentence" rule.
    max_extensions = 4
    tried_forward_skip = False
    for attempt in range(max_extensions + 1):
        start_seg = segments[start_idx]
        end_seg = segments[end_idx]
        new_start = start_seg["start"]
        new_end = end_seg["end"]
        duration = new_end - new_start

        if duration > DURATION_CEILING_SEC:
            # Too long — try trimming one segment off whichever end is less critical (the start, usually context)
            if start_idx < end_idx:
                start_idx += 1
                continue
            return pick, False, f"too long after snap: {duration:.1f}s"

        if duration < DURATION_FLOOR_SEC:
            # Too short — extend end first (pay-off matters more than extra context)
            if end_idx + 1 < len(segments):
                end_idx += 1
                continue
            if start_idx > 0:
                start_idx -= 1
                continue
            return pick, False, f"too short after snap: {duration:.1f}s"

        first_word = _first_content_word(start_seg)
        opens_bad = first_word in BAD_OPENING_WORDS or first_word in UNRESOLVED_PRONOUNS
        ends_clean = _segment_ends_cleanly(end_seg)

        if opens_bad and attempt < max_extensions:
            # Try pulling in the previous segment first (gives more context).
            # If that's not possible OR we've already tried it once unsuccessfully,
            # fall back to skipping forward past the filler-opening segment.
            if start_idx > 0 and not tried_forward_skip:
                start_idx -= 1
                continue
            if start_idx + 1 <= end_idx:
                start_idx += 1
                tried_forward_skip = True
                continue
        if not ends_clean and end_idx + 1 < len(segments) and attempt < max_extensions:
            end_idx += 1
            continue

        # Accept / reject
        if opens_bad:
            return pick, False, f"opens with unresolved '{first_word}' after rescue attempts"
        if not ends_clean:
            return pick, False, f"end not sentence-terminal after rescue attempts"

        adjusted = (
            abs(new_start - pick["start_sec"]) > 0.3
            or abs(new_end - pick["end_sec"]) > 0.3
        )
        out = {
            **pick,
            "start_sec": round(new_start, 2),
            "end_sec": round(new_end, 2),
            "duration_sec": round(duration, 2),
            "boundary_adjusted": adjusted,
            "validation": "ok",
        }
        return out, True, "ok"

    return pick, False, "rescue attempts exhausted"


def _de_overlap(picks: list[dict], overlap_pct: float = 0.5) -> list[dict]:
    """Drop picks that overlap >overlap_pct with a higher-scored pick. Preserves order afterwards."""
    sorted_picks = sorted(
        picks,
        key=lambda p: (p.get("quality_score", 0) + p.get("stand_alone_score", 0)),
        reverse=True,
    )
    kept: list[dict] = []
    for p in sorted_picks:
        p_dur = p["end_sec"] - p["start_sec"]
        if p_dur <= 0:
            continue
        ok = True
        for q in kept:
            overlap_start = max(p["start_sec"], q["start_sec"])
            overlap_end = min(p["end_sec"], q["end_sec"])
            overlap = max(0.0, overlap_end - overlap_start)
            if overlap / p_dur > overlap_pct:
                ok = False
                break
        if ok:
            kept.append(p)
    # Return in chronological order for nicer diffs
    return sorted(kept, key=lambda p: p["start_sec"])


# --- Claude call ------------------------------------------------------------

def _call_claude(topic_name: str, transcript_blob: str, n: int) -> list[dict]:
    import anthropic

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=6000,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": USER_TEMPLATE.format(
                    topic_name=topic_name, transcript_blob=transcript_blob, n=n
                ),
            }
        ],
    )
    text = "".join(b.text for b in resp.content if b.type == "text").strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.rsplit("```", 1)[0]
    return json.loads(text)


# --- Orchestrator -----------------------------------------------------------

def pick_clips_from_transcript(
    transcript_path: Path,
    dry_run: bool = False,
    target_count: int = 5,
) -> list[dict]:
    tx = json.loads(transcript_path.read_text())
    segments = tx.get("segments", [])
    topic_name = transcript_path.stem.replace("_1080p", "").replace("-", " ").title()
    transcript_blob = _format_transcript_for_prompt(tx)

    if dry_run:
        print(f"[DRY] {topic_name}: {len(segments)} segments, {len(transcript_blob)} chars for Claude")
        return []

    candidates = _call_claude(topic_name, transcript_blob, PICKS_REQUESTED)

    validated: list[dict] = []
    rejected: list[dict] = []
    for raw in candidates:
        pick, ok, reason = _snap_and_validate(raw, segments)
        if ok:
            validated.append(pick)
        else:
            rejected.append({**raw, "validation": f"rejected: {reason}"})

    # Drop near-duplicates (retain highest-scoring representative of each cluster)
    deduped = _de_overlap(validated)

    # Finalize to target_count — prefer those in the 60-90s sweet spot + higher scores
    def _rank(p: dict) -> float:
        in_sweet_spot = DURATION_TARGET_LO <= p["duration_sec"] <= DURATION_TARGET_HI
        bonus = 0.15 if in_sweet_spot else 0.0
        return p.get("quality_score", 0) + p.get("stand_alone_score", 0) + bonus

    deduped.sort(key=_rank, reverse=True)
    final = deduped[:target_count]
    final.sort(key=lambda p: p["start_sec"])

    stem_key = transcript_path.stem
    for i, p in enumerate(final, 1):
        p["clip_id"] = f"{stem_key}_c{i}"
        p["source_stem"] = stem_key

    print(
        f"  [STATS] {topic_name}: {len(candidates)} candidates → "
        f"{len(validated)} validated → {len(deduped)} unique → {len(final)} final"
    )
    if rejected:
        print(f"  [REJECT] {len(rejected)} dropped:")
        for r in rejected[:5]:
            print(f"    · {r.get('title', '?')}: {r.get('validation', '?')}")

    return final


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("transcript", nargs="?", help="Path to a transcript JSON")
    parser.add_argument("--batch", help="Directory of transcripts to process")
    parser.add_argument("--dry-run", action="store_true", help="Skip Claude call; show stats only")
    parser.add_argument("--target-count", type=int, default=5, help="Final picks per topic (default 5)")
    args = parser.parse_args()

    if not args.transcript and not args.batch:
        parser.error("pass a transcript path or --batch <dir>")

    targets: list[Path] = []
    if args.transcript:
        targets.append(Path(args.transcript).resolve())
    if args.batch:
        targets.extend(sorted(Path(args.batch).resolve().glob("*.json")))

    CLIPS_PLAN_DIR.mkdir(parents=True, exist_ok=True)
    all_picks: list[dict] = []
    for t in targets:
        try:
            picks = pick_clips_from_transcript(
                t, dry_run=args.dry_run, target_count=args.target_count
            )
            out = CLIPS_PLAN_DIR / t.name
            out.write_text(json.dumps(picks, indent=2))
            print(f"[PICKED] {len(picks)} stand-alone clips from {t.name} → {out.name}")
            all_picks.extend(picks)
        except Exception as exc:
            print(f"[ERROR] {t.name}: {exc}", file=sys.stderr)

    combined = CLIPS_PLAN_DIR / "_all.json"
    combined.write_text(json.dumps(all_picks, indent=2))
    print(f"\n[TOTAL] {len(all_picks)} stand-alone clips across {len(targets)} topics → {combined}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
