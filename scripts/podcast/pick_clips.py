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

PICKS_REQUESTED = 14  # bumped 7→14 (2026-05-07): now picking shorts from the full
# transcript instead of per-topic, so we need more candidates per source to fill
# the cross-platform short pipeline. Validation will prune to target_count.

# --- Title QA (2026-05-01: user feedback that some titles were inaccurate or too long) ---
# Bias: "a little vague over too specific and inaccurate."
TITLE_MIN_WORDS = 3            # below this is too vague (just a topic, no angle)
TITLE_MAX_WORDS = 8            # above this drifts into specifics that can be wrong
TITLE_HARD_MAX_CHARS = 70      # matches schedule_shorts.py truncation threshold
TITLE_SOFT_MAX_CHARS = 60      # safe — fits without ellipsis on most platforms

# Reject titles that age poorly, sound like clickbait, or claim specifics
# that decay/mismatch over time. Pure topic phrases pass; dated phrases fail.
# Each entry is (pattern, flags) — flags can include re.IGNORECASE selectively.
TITLE_BLOCKLIST_PATTERNS: list[tuple[str, int]] = [
    # Time-decay phrases — what was "this week" becomes wrong on repost
    (r"\b(today|tomorrow|tonight|yesterday|currently|recently)\b", re.IGNORECASE),
    (r"\bthis (week|month|year|morning|evening)\b", re.IGNORECASE),
    (r"\bnext (week|month|year)\b", re.IGNORECASE),
    (r"\blast (week|month|year|night)\b", re.IGNORECASE),
    # News-flash framings — almost always become stale
    (r"\b(just )?(announced|released|dropped|launched|leaked)\b", re.IGNORECASE),
    (r"\b(breaking|exclusive)\b", re.IGNORECASE),
    # Clickbait / mixed punctuation
    (r"!{2,}|\?!|\!\?|\.\.\.{2,}", 0),
    # All-caps shouting (case-SENSITIVE — must NOT have IGNORECASE)
    (r"\b[A-Z]{5,}\b", 0),
]


def _validate_title(title: str) -> tuple[bool, str]:
    """Validate a clip title. Returns (is_valid, reason_if_invalid)."""
    if not title or not title.strip():
        return False, "empty title"
    title = title.strip()
    if len(title) > TITLE_HARD_MAX_CHARS:
        return False, f"title too long ({len(title)} chars > {TITLE_HARD_MAX_CHARS})"
    words = re.findall(r"\b[\w'-]+\b", title)
    if len(words) < TITLE_MIN_WORDS:
        return False, f"title too short ({len(words)} words < {TITLE_MIN_WORDS})"
    if len(words) > TITLE_MAX_WORDS:
        return False, f"title too specific ({len(words)} words > {TITLE_MAX_WORDS})"
    for pat, flags in TITLE_BLOCKLIST_PATTERNS:
        m = re.search(pat, title, flags)
        if m:
            return False, f"title contains time-decay/clickbait pattern: {m.group(0)!r}"
    return True, "ok"


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

TITLE RULES (strict — bad titles get rejected post-generation):
- 3 to 8 words, title case, no clickbait punctuation, no all-caps words.
- **Prefer vague over specific-and-inaccurate.** "Adult Gaming Reality Check" beats "Why Tristan Hates Modern AAA Games" if the second one isn't precisely what's said. A title that works generally is better than one that misrepresents the clip.
- NO time-decay words: "today", "this week", "next month", "just announced", "just dropped", "just released", "leaked", "breaking", "yesterday", "now", "recently". These work for one day and look stale forever after.
- NO numerical specifics that aren't directly quoted in the clip ("3 reasons", "10x bigger", "first ever") — only use a number if the speakers literally state it.
- NO names of people or companies in the title unless the clip is centrally about them — a tangent mention isn't enough.
- The title should preview the *take*, not the *topic alone*. "AAA Gaming Is Cooked" > "AAA Gaming". But "AAA Gaming Pricing Debate" > "Why Tristan Thinks $80 Games Are Theft" if Tristan didn't quite say that.

Return strict JSON ONLY — a JSON ARRAY of picks, no prose, no markdown fences. Each pick:
{
  "start_sec": <float>,
  "end_sec": <float>,
  "title": "3-8 word title case, no clickbait punctuation, no time-decay words",
  "hook": "one sentence, first-person or direct address, no hashtags",
  "topics": ["2-4 lowercase tags"],
  "evergreen": <bool, see below>,
  "stand_alone_score": <float 0-1, 1 = passes the primary test perfectly>,
  "quality_score": <float 0-1, 1 = strong scroll-stopper>,
  "reasoning": "one sentence explaining why this clip stands alone"
}

EVERGREEN CLASSIFICATION (critical for repost-safety):
- evergreen = TRUE  when the clip will still feel fresh 6+ months later. Examples:
  * "Ranking the Zelda games" / retrospectives
  * Opinions on long-running franchises ("Why Final Fantasy peaked at 7")
  * Gameplay observations on classic games
  * Hot takes that aren't tied to a current event
  * Genre / industry musings ("Why indies save gaming")
- evergreen = FALSE when the clip's relevance decays with time. Examples:
  * "Nintendo just announced..." / news reactions
  * "Today's Direct showed..." / leak commentary
  * "Coming out next month" / launch hype
  * Anything containing "this week", "yesterday", "just released"
  * Specific predictions tied to a date ("by Christmas", "before the next Switch")
- When in doubt, mark FALSE. Time-sensitive content reposted months later looks weirdly stale; evergreen content held back is just unused budget.

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
    # Title QA — fail fast before doing snapping work
    title_ok, title_reason = _validate_title(pick.get("title", ""))
    if not title_ok:
        return pick, False, title_reason

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


# --- Gate 1: narrative coherence re-validation ------------------------------

def _extract_text_in_range(transcript: dict, start_sec: float, end_sec: float) -> str:
    """Concatenate segment text within [start_sec, end_sec]. Used by Gate 1
    so Claude sees exactly what the viewer would hear."""
    parts: list[str] = []
    for seg in transcript.get("segments", []):
        if seg["end"] < start_sec:
            continue
        if seg["start"] > end_sec:
            break
        parts.append(seg["text"].strip())
    return " ".join(parts).strip()


def _surrounding_context(transcript: dict, start_sec: float, end_sec: float,
                         context_sec: float = 30.0) -> str:
    """Pull 30s of text on either side of the clip — Claude needs this to judge
    whether the clip's opening relies on prior context (e.g., 'he was saying...')."""
    return _extract_text_in_range(
        transcript,
        max(0, start_sec - context_sec),
        end_sec + context_sec,
    )


def _gate1_narrative_coherence(candidates: list[dict], transcript: dict,
                              segments: list[dict]) -> list[dict]:
    """For each candidate, send extracted-text + surrounding context to Claude
    with the narrative coherence prompt. Drop REJECTs, apply ADJUST boundaries,
    keep PASS as-is.

    Runs all candidate validations CONCURRENTLY via asyncio.gather (one Claude
    call per candidate). For ~14 candidates × ~3s each, this drops wall time
    from ~42s sequential to ~3-5s concurrent. The Anthropic SDK's HTTP pool
    handles parallel requests fine (default pool size ~100).

    Failures during validation (network/JSON errors) → keep the candidate (don't
    drop on infrastructure issues). Failures are logged.
    """
    try:
        # Lazy import — only needed when Gate 1 runs
        from _qa_helpers import call_claude_text_async, log_gate_decision
        from qa_prompts import GATE_1_NARRATIVE_COHERENCE_V1
    except ImportError as exc:
        print(f"  [gate1] qa helpers unavailable ({exc}) — skipping narrative re-validation")
        return candidates

    import asyncio

    # Episode stem for the per-episode JSONL log (all candidates share a source_stem)
    episode_stem = candidates[0].get("source_stem", "unknown") if candidates else "unknown"

    # Build per-candidate prompts (synchronous — pure transcript text manipulation)
    work: list[tuple[dict, str | None, str]] = []  # (cand, prompt_or_None, clip_id)
    for cand in candidates:
        try:
            start = float(cand.get("start_sec", 0))
            end = float(cand.get("end_sec", 0))
        except (TypeError, ValueError):
            work.append((cand, None, "?"))  # malformed — pass through
            continue

        extracted = _extract_text_in_range(transcript, start, end)
        if not extracted or len(extracted) < 50:
            work.append((cand, None, "?"))  # too short to evaluate
            continue

        prompt = GATE_1_NARRATIVE_COHERENCE_V1.format(
            title=cand.get("title", "?"),
            hook=cand.get("hook", "?"),
            topics=", ".join(cand.get("topics", [])) or "?",
            duration_sec=end - start,
            start_sec=start,
            end_sec=end,
            extracted_text=extracted[:4000],
            surrounding_context=_surrounding_context(transcript, start, end)[:6000],
        )
        clip_id = cand.get("clip_id") or cand.get("title", "?")[:60]
        work.append((cand, prompt, clip_id))

    # Concurrent fire of all Claude calls, preserving order
    async def _gather_all() -> list:
        tasks = []
        for _cand, prompt, _cid in work:
            if prompt is None:
                tasks.append(asyncio.sleep(0, result=None))  # no-op placeholder
            else:
                tasks.append(call_claude_text_async(prompt, max_tokens=1500))
        return await asyncio.gather(*tasks, return_exceptions=True)

    print(f"  [gate1] running {sum(1 for _, p, _ in work if p)} candidates concurrently...")
    t0 = __import__("time").time()
    verdicts = asyncio.run(_gather_all())
    elapsed = __import__("time").time() - t0
    print(f"  [gate1] {sum(1 for _, p, _ in work if p)} concurrent calls completed in {elapsed:.1f}s")

    # Process verdicts in original order — apply REJECT / ADJUST / PASS logic
    accepted: list[dict] = []
    rejected_reasons: list[dict] = []
    for (cand, prompt, clip_id), verdict in zip(work, verdicts):
        # Pass-through for cases that didn't produce a prompt
        if prompt is None:
            accepted.append(cand)
            continue
        # Network/exception → keep candidate, log error
        if isinstance(verdict, Exception):
            print(f"  [gate1] claude error on {cand.get('title','?')[:40]}: {verdict} — keeping candidate")
            accepted.append(cand)
            continue
        # Empty / malformed verdict → keep candidate
        if not verdict or not isinstance(verdict, dict):
            accepted.append(cand)
            continue

        decision = (verdict.get("decision") or "").upper()
        reason = verdict.get("reason", "?")

        try:
            start = float(cand.get("start_sec", 0))
            end = float(cand.get("end_sec", 0))
        except (TypeError, ValueError):
            start = end = 0.0

        # Log every Gate 1 decision for retrospective analysis
        log_gate_decision(episode_stem, "gate1", clip_id, verdict, extra={
            "title": cand.get("title", "?"),
            "duration_sec": end - start,
            "start_sec": start, "end_sec": end,
        })

        if decision == "REJECT":
            print(f"  [gate1] REJECT: {cand.get('title','?')[:50]} — {reason}")
            rejected_reasons.append({
                "title": cand.get("title", "?"),
                "reason": reason,
                "issues": verdict.get("issues", []),
            })
            continue

        if decision == "ADJUST":
            adj = verdict.get("adjusted_boundaries") or {}
            try:
                new_start = float(adj.get("start_sec", start))
                new_end = float(adj.get("end_sec", end))
                if new_end - new_start >= 20 and new_start >= 0 and new_end > new_start:
                    print(f"  [gate1] ADJUST: {cand.get('title','?')[:50]} "
                          f"{start:.1f}–{end:.1f}s → {new_start:.1f}–{new_end:.1f}s")
                    cand = {**cand, "start_sec": new_start, "end_sec": new_end,
                            "_gate1_adjusted": True}
            except (TypeError, ValueError):
                pass

        cand["_gate1_hook_in_first_5_sec"] = bool(verdict.get("hook_in_first_5_sec"))
        cand["_gate1_engagement_risk"] = verdict.get("engagement_risk", "unknown")
        accepted.append(cand)

    n_rej = len(candidates) - len(accepted)
    print(f"  [gate1] {len(candidates)} candidates → {len(accepted)} accepted, {n_rej} rejected")
    return accepted


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

    # GATE 1 (2026-05-07): re-validate narrative coherence on each raw candidate
    # using a fresh Claude call with the EXTRACTED segment text. This catches
    # clips Claude initially scored well but that fail the stand-alone test
    # when actually checked against the chosen boundaries.
    candidates = _gate1_narrative_coherence(candidates, tx, segments)

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
    parser.add_argument("--target-count", type=int, default=10, help="Final picks per source (default 10)")
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
