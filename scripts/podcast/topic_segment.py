#!/usr/bin/env python3
"""Auto-detect coherent topic boundaries in a full podcast transcript and cut
the source MP4 into per-topic videos.

Slots into pipeline.py between `transcribe` and `thumbnails` as the
`auto_segment` stage. Outputs are placed into the existing source/transcripts
directories with an `_auto_` naming tag, so all downstream stages
(thumbnails, metadata, yt_upload, pick_clips, render_clips, schedule) pick
them up via existing globs without further code changes.

Two modes:
  --mode plan     emit Navi task with proposed topic plan; do NOT cut video
  --mode execute  validate + ffmpeg-cut + write transcripts to disk

Quality bar (per user direction "PLEASE DONT HALF ASS THIS"):
  - Plan mode is the SAFE default. Never auto-cut without proven boundaries.
  - Every topic must have a single-sentence thesis (asserts a position;
    "discusses X" is rejected as lazy).
  - Every topic must contain ≥3 distinct subtopics.
  - Topic boundaries must snap to sentence ends; no mid-thought cuts.
  - Topics must cover the entire episode contiguously (no gaps, no overlaps).
  - Sibling topics must not share ≥2 nouns ≥4 chars in their thesis.
  - Hard duration window: 8–22 min (480–1320 sec) per topic.
  - <3 valid topics → bail entire stage; do not ship junk.

Usage:
  python3 scripts/podcast/topic_segment.py \
      --transcript data/podcast/transcripts/<full_stem>.json \
      --full-video-1080p data/podcast/source/1080p/<full_stem>.mp4 \
      --episode "Episode May 5 2026" \
      --mode plan
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent

# Bring navi_alerts into path
sys.path.insert(0, str(ROOT / "scripts"))
from navi_alerts import emit_navi_task  # noqa: E402

# Local helpers (shared with pick_clips.py)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _transcript_utils import (  # noqa: E402
    carve_transcript,
    find_segment_containing,
    first_content_word,
    format_transcript_for_prompt,
    segment_ends_cleanly,
)

SOURCE_1080P = ROOT / "data" / "podcast" / "source" / "1080p"
TRANSCRIPTS = ROOT / "data" / "podcast" / "transcripts"
STATE_DIR = ROOT / "data" / "podcast"

DURATION_FLOOR_SEC = 240.0    # 4 min — minimum viable long-form video.
DURATION_CEILING_SEC = 1500.0 # 25 min — over this is multiple topics fused, reject.
DURATION_TARGET_LO = 360.0    # 6 min — short but valid if thesis is sharp.
DURATION_TARGET_HI = 900.0    # 15 min — over this, 2nd-pass critic checks for fused theses.

MIN_TOPICS = 3
MAX_TOPICS = 10  # 67-min ep / 8 topics ≈ 8 min each — granular enough for distinct theses.

# Reused from pick_clips.py - opening filters that signal continuation
BAD_OPENING_WORDS = {
    "so", "and", "but", "then", "because", "anyway", "also", "plus",
    "yeah", "yep", "right", "exactly", "totally", "absolutely",
    "like", "you", "i", "oh",
}
UNRESOLVED_PRONOUNS = {
    "he", "she", "they", "it", "that", "this", "those", "these",
    "him", "her", "them",
}

# Phrases Claude reaches for instead of stating an actual thesis
LAZY_THESIS_VERBS = (
    r"\b("
    r"discusses?|talks? about|covers?|mentions?|goes? over|"
    r"gets? into|chats? about|breaks? down|explores?|takes? on|"
    r"dives? into|reviews?"
    r")\b"
)
_LAZY_THESIS_RE = re.compile(LAZY_THESIS_VERBS, re.IGNORECASE)

# Stop words for thesis-noun overlap detection
_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "for", "from",
    "had", "has", "have", "he", "her", "him", "his", "i", "if", "in", "into",
    "is", "it", "its", "more", "no", "not", "of", "on", "or", "our", "out",
    "she", "so", "some", "such", "than", "that", "the", "their", "them",
    "then", "there", "these", "they", "this", "those", "to", "up", "us",
    "was", "we", "were", "what", "when", "where", "which", "while", "who",
    "why", "will", "with", "would", "you", "your",
    # Frequent podcast-context words that aren't distinguishing
    "game", "games", "gaming", "podcast", "episode", "show", "guys",
    "thing", "things", "way", "talk", "argue", "debate", "discussion",
    "people", "make", "makes", "made", "really", "actually", "going",
    "host", "hosts", "consumer", "consumers", "company", "companies",
    "industry", "video", "videos", "today", "year", "years", "time",
    "modern", "current", "recent", "argument", "argue", "argues",
    "examine", "examines", "explore", "explores",
}

SLUG_RE = re.compile(r"^[a-z][a-z0-9-]{2,40}$")
SLUG_CHAR_RE = re.compile(r"^[a-z][a-z0-9-]+$")
SLUG_DOUBLE_HYPHEN = re.compile(r"--")


def die(msg: str, rc: int = 2) -> None:
    print(f"FATAL: {msg}", file=sys.stderr)
    sys.exit(rc)


# ===== System prompt ========================================================

SYSTEM_PROMPT = """You are a podcast structural editor for The 8-Bit Podcast (retro gaming + industry commentary).

YOUR JOB: read a 60–150 minute conversation transcript and identify the DISTINCT THEMATIC BEATS (5–8 typical) where each becomes a coherent stand-alone YouTube long-form video.

DUAL PRINCIPLE — neither lumpy nor fragmenty:

LUMPY FAILURE: fusing distinct conversations into one survey-style topic. If the hosts have a clear 5-min "Top 3 Zelda Games" beat with its own thesis ("Wind Waker > Ocarina"), that beat does NOT belong inside a 14-min "remakes and Nintendo" mega-topic. Two distinct theses = two topics.

FRAGMENT FAILURE: splitting one continuous argument into 2-min slivers. If the hosts spend 2 min on "Black Flag remake pricing" and IMMEDIATELY pivot into "Ocarina of Time remake rumors" as the same conversational beat (not a hard pivot), that's ONE topic about remake pricing — NOT two 2-min fragments.

Test: would a viewer interested in subtopic A also be interested in subtopic B in this same flow? Yes → same topic. No → split. A 5-min topic with one sharp thesis BEATS both a 2-min fragment AND a 14-min survey.

Math reality: a 67 min episode typically has 5–8 substantial beats. Some beats are 4 min, some are 18 min — let the conversation's natural pivots dictate, NOT a duration target.

A valid topic segment MUST:
1. **Have ONE single-sentence thesis** asserting a position. NOT "they discuss A and B" (that's two topics). NOT "they cover X" (that's lazy phrasing). Required form: "they argue X / they push back against Y / they unpack why Z / they rank A > B because C / they predict D". Lead with the position.
2. **Be 4–25 minutes long.** Target 6–15 min for the sweet spot. A 5-min topic with a sharp thesis (e.g. "Top 3 Zelda Games Ranked") is FINE. A 4-min topic that's actually just a fragment of a bigger discussion is NOT.
3. **Open on context** — no "so", "and", "yeah", bare pronouns, filler agreement.
4. **Close on a beat** — conclusion, hand-off, turn of the page. NOT mid-sentence.
5. **Contain ≥3 distinct sub-beats** within ONE thesis. (Three angles on Zelda Top 3 = valid. Black Flag pricing + Zelda Top 3 + OoT remake = THREE topics, not one with three subtopics.)
6. **Be substantively distinct from siblings** — no shared key nouns in different theses. If two theses overlap on key nouns, they're one topic OR you mis-framed them.

CONTIGUITY (non-negotiable): topics MUST tile the entire episode without gaps or overlaps. First topic starts at SEG-0 (fold welcome chatter into topic 1's opening). Last topic ends at the final segment (fold outro into the last topic's close). If topic 2 ends at SEG-N, topic 3 starts at SEG-N+1 exactly.

Title rules: 3–10 words, title case, no time-decay ("today", "this week"), no clickbait punctuation, no all-caps. Slug rules: 2–5 lowercase hyphenated words.

WORKED EXAMPLE (GOOD — granular):
Episode segment covers a stretch on remakes/Nintendo. The hosts:
- Debate whether the $60 Black Flag remake is worth it (~5 min)
- React to leaked Ocarina of Time remake rumors (~4 min)
- Rank their Top 3 Zelda games and roast each other's picks (~5 min)
That's THREE topics, not one:
  T_X [5 min]: "Black Flag Remake Is Not Worth $60" — they argue 1.30x AC4 with new combat doesn't justify the price hike
  T_Y [4 min]: "Why Nintendo Won't Greenlight an OoT Remake" — they unpack why the rumors are likely fan wishful thinking
  T_Z [5 min]: "Our Top 3 Zelda Games Ranked" — they each defend a different Top 3 and argue Wind Waker > Twilight Princess

BAD split (LUMPY — REJECT):
  T_BAD [14 min]: "Nostalgia Bait and Remakes" ← three separate theses fused into one survey video. Each segment deserves its own video.

Return STRICT JSON only — no prose, no markdown fences:
{
  "topics": [
    {
      "slug": "black-flag-remake-pricing",
      "title_hint": "Black Flag Remake Is Not Worth $60",
      "thesis": "...",
      "subtopics": ["...", "...", "..."],
      "start_seg": <int>,
      "end_seg": <int>,
      "boundary_confidence": <0-1>,
      "stand_alone_score": <0-1>
    }, ...
  ]
}
"""

# Second-pass critic: for every topic >12 min, ask Claude whether it should split.
SPLIT_CRITIC_PROMPT = """You are reviewing a SINGLE proposed topic from a podcast auto-segmentation pass. Decide whether this topic has ONE coherent thesis or fuses MULTIPLE distinct theses that should be split into separate videos.

A topic should be SPLIT when:
- The thesis sentence contains "and" connecting two distinct claims (e.g. "they argue X and they unpack Y")
- The subtopics list mixes unrelated arguments (e.g. one about pricing + one about narrative + one about rankings)
- A viewer interested in subtopic A would NOT be the same viewer interested in subtopic C
- It's longer than 15 min and has 4+ subtopics that don't share a unifying argument

A topic should STAY MERGED when:
- All subtopics serve a single overarching argument
- Splitting would produce sub-3-min fragments
- The subtopics are layered evidence for one claim

Topic to review:
{topic_json}

Transcript excerpt for this topic:
{transcript_excerpt}

Return STRICT JSON only:
{{
  "decision": "keep" | "split",
  "reason": "<one sentence>",
  "splits": [  // ONLY include if decision=="split"; must tile the original range exactly
    {{
      "slug": "...",
      "title_hint": "...",
      "thesis": "...",
      "subtopics": ["...", "...", "..."],
      "start_seg": <int>,
      "end_seg": <int>
    }}, ...
  ]
}}
"""


def _build_user_prompt(episode: str, total_dur_sec: float, transcript_blob: str,
                      min_topics: int, max_topics: int) -> str:
    dur_min = total_dur_sec / 60.0
    return f"""Episode: {episode}, total duration {dur_min:.1f} min.

Word-level transcript with [SEG-N start=<s> end=<s>] markers below. Identify {min_topics}–{max_topics} stand-alone topic segments. Topics MUST be contiguous (segment N+1 of one topic = next topic's first segment). Topics MUST cover the whole episode (first topic starts at SEG-0; last topic ends at the final segment).

{transcript_blob}

Return strict JSON only — the schema in the system prompt."""


# ===== Claude call ==========================================================

def call_claude(episode: str, total_dur_sec: float, transcript_blob: str,
                min_topics: int, max_topics: int, retry_hint: str = "") -> dict:
    import anthropic

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    user_prompt = _build_user_prompt(episode, total_dur_sec, transcript_blob,
                                      min_topics, max_topics)
    if retry_hint:
        user_prompt = retry_hint + "\n\n" + user_prompt
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )
    text = "".join(b.text for b in resp.content if b.type == "text").strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.rsplit("```", 1)[0]
    return json.loads(text)


# Topics longer than this trigger the split-critic second pass.
SPLIT_CRITIC_DURATION_SEC = 600.0  # 10 min — catches topics with 2 fused theses


def split_critic_review(topic: dict, segments: list[dict]) -> list[dict] | None:
    """Ask Claude whether this topic should be split into multiple. Returns
    None if Claude says keep, OR a list of split-topic dicts (untyped — will
    be re-validated by validate_topics)."""
    import anthropic

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    s_idx = topic["start_seg"]
    e_idx = topic["end_seg"]
    excerpt_segs = segments[s_idx : e_idx + 1]
    excerpt = "".join(
        f"\n[SEG-{s_idx + i} start={s['start']:.2f} end={s['end']:.2f}]\n{s['text'].strip()}\n"
        for i, s in enumerate(excerpt_segs)
    )
    # Cap excerpt at ~120K chars (well within Sonnet 4.6 context for a single topic)
    if len(excerpt) > 120_000:
        excerpt = excerpt[:120_000] + "\n[…truncated…]\n"

    topic_json = json.dumps({
        k: topic[k] for k in ("slug", "title_hint", "thesis", "subtopics",
                              "start_seg", "end_seg", "duration_sec")
        if k in topic
    }, indent=2)

    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=3000,
        messages=[{"role": "user", "content": SPLIT_CRITIC_PROMPT.format(
            topic_json=topic_json, transcript_excerpt=excerpt
        )}],
    )
    text = "".join(b.text for b in resp.content if b.type == "text").strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.rsplit("```", 1)[0]
    try:
        verdict = json.loads(text)
    except json.JSONDecodeError:
        # Critic returned garbage — fail closed, keep the topic
        print(f"  [critic] non-JSON response for {topic.get('slug', '?')}; keeping merged")
        return None

    if verdict.get("decision") != "split":
        return None
    splits = verdict.get("splits", []) or []
    if len(splits) < 2:
        return None
    # Sanity-check: splits must tile the original range. If not, abort the split.
    splits_sorted = sorted(splits, key=lambda s: s.get("start_seg", -1))
    if splits_sorted[0].get("start_seg") != s_idx:
        print(f"  [critic] split rejected — first split doesn't start at {s_idx}")
        return None
    if splits_sorted[-1].get("end_seg") != e_idx:
        print(f"  [critic] split rejected — last split doesn't end at {e_idx}")
        return None
    for i in range(len(splits_sorted) - 1):
        a, b = splits_sorted[i], splits_sorted[i + 1]
        if b.get("start_seg") != a.get("end_seg", -2) + 1:
            print(f"  [critic] split rejected — gap between split {i} and {i+1}")
            return None
    print(f"  [critic] '{topic.get('title_hint', '?')}' → split into {len(splits)}: "
          f"{verdict.get('reason', '?')}")
    return splits_sorted


# ===== Validation ===========================================================

def _thesis_lazy(thesis: str) -> bool:
    if not thesis or len(thesis.split()) < 8:
        return True
    return bool(_LAZY_THESIS_RE.search(thesis))


def _validate_title(title: str) -> tuple[bool, str]:
    if not title or not title.strip():
        return False, "empty title"
    title = title.strip()
    # Long-form YT topic titles get more SEO room than 60s clips: 90 chars / 12 words.
    if len(title) > 90:
        return False, f"title too long ({len(title)} chars > 90)"
    words = re.findall(r"\b[\w'-]+\b", title)
    if len(words) < 3:
        return False, f"title too short ({len(words)} words < 3)"
    if len(words) > 12:
        return False, f"title too specific ({len(words)} words > 12)"
    blocklist = [
        (r"\b(today|tomorrow|tonight|yesterday|currently|recently)\b", re.I),
        (r"\bthis (week|month|year|morning|evening)\b", re.I),
        (r"\bnext (week|month|year)\b", re.I),
        (r"\blast (week|month|year|night)\b", re.I),
        (r"\b(just )?(announced|released|dropped|launched|leaked)\b", re.I),
        (r"\b(breaking|exclusive)\b", re.I),
        (r"!{2,}|\?!|\!\?|\.\.\.{2,}", 0),
        (r"\b[A-Z]{5,}\b", 0),
    ]
    for pat, flags in blocklist:
        m = re.search(pat, title, flags)
        if m:
            return False, f"title contains blocklisted pattern: {m.group(0)!r}"
    return True, "ok"


def _thesis_nouns(thesis: str) -> set[str]:
    """Extract distinguishing nouns (≥4 chars, not in stopwords) from a thesis sentence."""
    raw = re.sub(r"[^a-z0-9 ]", " ", thesis.lower()).split()
    return {w for w in raw if len(w) >= 4 and w not in _STOPWORDS}


def _opening_clean(seg: dict) -> bool:
    fw = first_content_word(seg)
    return bool(fw) and fw not in BAD_OPENING_WORDS and fw not in UNRESOLVED_PRONOUNS


def _try_extend_start(segments: list[dict], idx: int, max_hops: int = 6,
                      floor_idx: int = 0) -> int:
    """If segment[idx] opens badly, extend backwards up to max_hops to find a clean
    start. `floor_idx` is the lowest index we're allowed to land on (typically the
    previous topic's end_seg + 1). Prevents rescue from creating overlaps with
    adjacent topics."""
    cur = idx
    hops = 0
    while not _opening_clean(segments[cur]) and hops < max_hops and cur > floor_idx:
        cur -= 1
        hops += 1
    return cur


def _try_extend_end(segments: list[dict], idx: int, max_hops: int = 6,
                    ceiling_idx: int | None = None) -> int:
    """Extend forward to a sentence-terminal segment. `ceiling_idx` is the
    highest index allowed (typically the next topic's start_seg - 1).
    Whisper transcripts sometimes drop punctuation in fast-speech regions;
    up to 6 hops covers ~30s of speech, enough to reach a natural break."""
    cur = idx
    hops = 0
    cap = ceiling_idx if ceiling_idx is not None else (len(segments) - 1)
    while not segment_ends_cleanly(segments[cur]) and hops < max_hops and cur < cap:
        cur += 1
        hops += 1
    return cur


def validate_topics(topics: list[dict], segments: list[dict]) -> tuple[list[dict], list[dict]]:
    """Run all per-topic gates. Returns (accepted, rejected) lists.

    Each accepted topic gets `start_sec`, `end_sec`, `duration_sec`, and
    boundary-snap adjustments applied. Each rejected topic gets a `reject_reason`.

    Topics are processed in start_seg order so boundary rescue is neighbor-aware
    (extending one topic's start can't overlap into an already-accepted previous
    topic's end).
    """
    n_segs = len(segments)
    accepted: list[dict] = []
    rejected: list[dict] = []

    # Sort by start_seg for neighbor-aware rescue
    raw_sorted = sorted(
        [t for t in topics if isinstance(t.get("start_seg"), int)],
        key=lambda t: t["start_seg"],
    )

    # Per-topic gates first; coverage check after.
    seen_nouns: list[set[str]] = []
    for ti, raw in enumerate(raw_sorted):
        topic = dict(raw)  # shallow copy

        # Slug — truncate over-long ones (Claude sometimes smashes multiple topic
        # words into one slug, signalling a fused topic — the critic catches that
        # downstream). Reject only on character-class violations.
        slug = topic.get("slug", "")
        if not isinstance(slug, str) or not slug:
            topic["reject_reason"] = "empty/non-string slug"
            rejected.append(topic)
            continue
        if not SLUG_CHAR_RE.match(slug) or SLUG_DOUBLE_HYPHEN.search(slug):
            topic["reject_reason"] = f"bad slug chars: {slug!r}"
            rejected.append(topic)
            continue
        if len(slug) > 40:
            # Truncate at last hyphen before 40-char mark
            truncated = slug[:40].rsplit("-", 1)[0] if "-" in slug[:40] else slug[:40]
            topic["slug_warning"] = f"truncated from {slug!r}"
            topic["slug"] = truncated
            slug = truncated

        # Thesis
        thesis = topic.get("thesis", "")
        if _thesis_lazy(thesis):
            topic["reject_reason"] = f"lazy/empty thesis: {thesis!r}"
            rejected.append(topic)
            continue

        # Title — auto-truncate if too long, reject only on time-decay/clickbait/empty.
        title = (topic.get("title_hint") or "").strip()
        if not title:
            topic["reject_reason"] = "empty title"
            rejected.append(topic)
            continue
        # Reject blocklist patterns + all-caps (these are content red flags)
        for pat, flags in (
            (r"\b(today|tomorrow|tonight|yesterday|currently|recently)\b", re.I),
            (r"\bthis (week|month|year|morning|evening)\b", re.I),
            (r"\bnext (week|month|year)\b", re.I),
            (r"\blast (week|month|year|night)\b", re.I),
            (r"\b(just )?(announced|released|dropped|launched|leaked)\b", re.I),
            (r"\b(breaking|exclusive)\b", re.I),
            (r"!{2,}|\?!|\!\?|\.\.\.{2,}", 0),
            (r"\b[A-Z]{5,}\b", 0),
        ):
            m = re.search(pat, title, flags)
            if m:
                topic["reject_reason"] = f"title contains blocklisted pattern: {m.group(0)!r}"
                break
        if topic.get("reject_reason"):
            rejected.append(topic)
            continue
        # Truncate over-long titles at word boundary
        title_words = re.findall(r"\b[\w'-]+\b", title)
        if len(title_words) < 3:
            topic["reject_reason"] = f"title too short ({len(title_words)} words)"
            rejected.append(topic)
            continue
        if len(title) > 90 or len(title_words) > 12:
            # Truncate to first 10 words, drop trailing "and ..."
            truncated_words = title_words[:10]
            # Trim trailing connectors
            while truncated_words and truncated_words[-1].lower() in ("and", "or", "but", "for", "with", "the", "a", "an"):
                truncated_words.pop()
            new_title = " ".join(truncated_words)
            topic["title_warning"] = f"truncated from {title!r}"
            topic["title_hint"] = new_title
            title = new_title

        # Subtopics
        subs = topic.get("subtopics", [])
        if not isinstance(subs, list) or len(subs) < 3:
            topic["reject_reason"] = f"too few subtopics ({len(subs) if isinstance(subs, list) else '?'})"
            rejected.append(topic)
            continue

        # Boundaries are valid indices. Claude occasionally hallucinates
        # indices slightly past the end (e.g. 1756 for a 1737-seg transcript)
        # — clamp to valid range rather than reject, since this is usually
        # an off-by-N counting error not a content error.
        s_idx = topic.get("start_seg")
        e_idx = topic.get("end_seg")
        if not isinstance(s_idx, int) or not isinstance(e_idx, int):
            topic["reject_reason"] = "non-integer boundaries"
            rejected.append(topic)
            continue
        if s_idx < 0:
            topic["index_warning_start"] = f"clamped from {s_idx} to 0"
            s_idx = 0
        if e_idx >= n_segs:
            topic["index_warning_end"] = f"clamped from {e_idx} to {n_segs - 1}"
            e_idx = n_segs - 1
        if s_idx > e_idx:
            topic["reject_reason"] = f"start > end after clamping: [{s_idx}, {e_idx}]"
            rejected.append(topic)
            continue

        # Boundary cleanliness — try rescue-by-extension WITHIN bounds set by
        # neighbors. Floor for start: previous accepted topic's end + 1.
        # Ceiling for end: next raw topic's start - 1 (if any). If even after
        # rescue the boundary isn't perfectly clean, ACCEPT but warn — Whisper
        # sometimes drops punctuation in fast-speech regions; the post-cut
        # audit catches truly broken openings.
        floor_idx = (accepted[-1]["end_seg"] + 1) if accepted else 0
        ceiling_idx = None
        if ti + 1 < len(raw_sorted):
            nxt_start = raw_sorted[ti + 1].get("start_seg")
            if isinstance(nxt_start, int):
                ceiling_idx = nxt_start - 1
        s_idx = _try_extend_start(segments, s_idx, floor_idx=floor_idx)
        e_idx = _try_extend_end(segments, e_idx, ceiling_idx=ceiling_idx)
        if not _opening_clean(segments[s_idx]):
            topic["boundary_warning_open"] = (
                f"opens with {first_content_word(segments[s_idx])!r} "
                f"at SEG-{s_idx} (rescue exhausted)"
            )
        if not segment_ends_cleanly(segments[e_idx]):
            topic["boundary_warning_end"] = (
                f"ends mid-sentence at SEG-{e_idx} (rescue exhausted; "
                f"likely Whisper punctuation gap, not topic boundary issue)"
            )

        # Duration
        start_sec = float(segments[s_idx]["start"])
        end_sec = float(segments[e_idx]["end"])
        dur = end_sec - start_sec
        # Below-floor and over-ceiling durations both = WARN, not reject. Rejecting
        # broke coverage; the split-critic second pass will catch over-ceiling
        # topics and split them properly with thesis-level reasoning.
        if dur < DURATION_FLOOR_SEC:
            topic["duration_warning"] = (
                f"sub-floor ({dur:.0f}s < {DURATION_FLOOR_SEC:.0f}s) — "
                f"consider merging with adjacent topic during review"
            )
        elif dur < DURATION_TARGET_LO:
            topic["duration_warning"] = f"clip-shaped ({dur:.0f}s; target {DURATION_TARGET_LO:.0f}s+)"
        elif dur > DURATION_TARGET_HI:
            topic["duration_warning"] = f"long ({dur:.0f}s; target ≤{DURATION_TARGET_HI:.0f}s)"
        if dur > DURATION_CEILING_SEC:
            topic["duration_warning"] = (
                f"over-ceiling ({dur:.0f}s > {DURATION_CEILING_SEC:.0f}s) — "
                f"second-pass critic will attempt to split"
            )

        # Word-overlap check vs already-accepted siblings
        nouns = _thesis_nouns(thesis)
        overlap_with = None
        for i, prev in enumerate(seen_nouns):
            shared = nouns & prev
            if len(shared) >= 2:
                overlap_with = (i, shared)
                break
        if overlap_with is not None:
            i, shared = overlap_with
            topic["reject_reason"] = f"thesis overlaps topic {i} on nouns: {sorted(shared)}"
            rejected.append(topic)
            continue

        topic["start_seg"] = s_idx
        topic["end_seg"] = e_idx
        topic["start_sec"] = round(start_sec, 2)
        topic["end_sec"] = round(end_sec, 2)
        topic["duration_sec"] = round(dur, 2)
        accepted.append(topic)
        seen_nouns.append(nouns)

    return accepted, rejected


def _gate0_topic_coherence(topics: list[dict], segments: list[dict],
                          episode: str) -> list[dict]:
    """Gate 0 — per-topic coherence audit (concurrent Claude calls).

    For each topic: build the transcript text within its boundaries, send to
    Claude with the GATE_0_TOPIC_COHERENCE_V1 prompt. Decisions:

      PASS       — keep topic as-is.
      SPLIT      — log a Navi task + drop topic from publish set (split point
                   in verdict so a human can manually re-do segmentation).
      INCOHERENT — drop topic from publish set (it doesn't lead to good clips).

    Failures (network/JSON) → keep topic (don't lose work on infra issues).

    The `episode` name is used for logging; pass-through if helpers can't load.
    """
    try:
        from _qa_helpers import call_claude_text_async, log_gate_decision
        from qa_prompts import GATE_0_TOPIC_COHERENCE_V1
    except ImportError as exc:
        print(f"  [gate0] qa helpers unavailable ({exc}) — skipping pre-pick coherence check")
        return topics

    if not topics:
        return topics

    import asyncio
    import time

    # Build per-topic prompt + transcript text
    work: list[tuple[dict, str | None]] = []
    for t in topics:
        try:
            start_sec = float(t.get("start_sec", 0))
            end_sec = float(t.get("end_sec", 0))
        except (TypeError, ValueError):
            work.append((t, None))
            continue
        # Pull transcript text within topic bounds
        parts = []
        for seg in segments:
            if seg.get("end", 0) < start_sec:
                continue
            if seg.get("start", 0) > end_sec:
                break
            parts.append(seg.get("text", "").strip())
        text = " ".join(parts).strip()
        if len(text) < 200:  # skip extremely short topics — Gate 0 needs material
            work.append((t, None))
            continue
        prompt = GATE_0_TOPIC_COHERENCE_V1.format(
            title=t.get("title_hint", "?"),
            thesis=t.get("thesis", "?"),
            duration_sec=end_sec - start_sec,
            duration_min=(end_sec - start_sec) / 60.0,
            start_sec=start_sec,
            end_sec=end_sec,
            transcript_text=text[:8000],  # cap for prompt size
        )
        work.append((t, prompt))

    # Concurrent Claude calls
    async def _run_all():
        tasks = []
        for _t, prompt in work:
            if prompt is None:
                tasks.append(asyncio.sleep(0, result=None))
            else:
                tasks.append(call_claude_text_async(prompt, max_tokens=1500))
        return await asyncio.gather(*tasks, return_exceptions=True)

    n_actual = sum(1 for _, p in work if p is not None)
    if n_actual == 0:
        return topics
    print(f"  [gate0] running {n_actual} topic-coherence checks concurrently...")
    t0 = time.time()
    verdicts = asyncio.run(_run_all())
    print(f"  [gate0] {n_actual} checks completed in {time.time()-t0:.1f}s")

    kept: list[dict] = []
    for (t, prompt), verdict in zip(work, verdicts):
        if prompt is None or isinstance(verdict, Exception) or not verdict:
            kept.append(t)
            continue
        decision = (verdict.get("decision") or "PASS").upper()
        title = t.get("title_hint", "?")[:50]
        reason = verdict.get("reason", "?")

        # Log every Gate 0 decision
        log_gate_decision(episode or "unknown", "gate0",
                         t.get("slug", "?")[:50], verdict, extra={
                             "title": t.get("title_hint", "?"),
                             "duration_sec": t.get("duration_sec", 0),
                         })

        if decision == "PASS":
            print(f"  [gate0] PASS: {title}")
            kept.append(t)
        elif decision == "SPLIT":
            split_at = verdict.get("split_timestamp_sec")
            print(f"  [gate0] SPLIT: {title} — split @ {split_at}s. Dropping from publish set.")
            try:
                emit_failure_navi_task(
                    episode,
                    f"Gate 0 SPLIT: {title}",
                    f"Topic spans multiple subjects.\n"
                    f"Primary: {verdict.get('primary_subject', '?')}\n"
                    f"Secondary: {verdict.get('secondary_subjects', [])}\n"
                    f"Suggested split @ {split_at}s.\n\n"
                    f"Manual action: re-run topic_segment with --force after editing "
                    f"the source, or edit the resulting clips_plan manually.",
                )
            except Exception as exc:
                print(f"  [gate0] navi emit failed: {exc}")
            # Don't keep — SPLIT topics produce bad clips
        elif decision == "INCOHERENT":
            print(f"  [gate0] INCOHERENT: {title} — dropping. Reason: {reason[:80]}")
            try:
                emit_failure_navi_task(
                    episode,
                    f"Gate 0 INCOHERENT: {title}",
                    f"Topic auto-segmentation produced an incoherent topic.\n"
                    f"Reason: {reason}\nDropped from publish set.",
                )
            except Exception:
                pass
        else:
            print(f"  [gate0] unknown decision '{decision}': {title} — keeping defensively")
            kept.append(t)

    n_dropped = len(topics) - len(kept)
    if n_dropped:
        print(f"  [gate0] dropped {n_dropped} topic(s) for coherence; {len(kept)} remain")
    return kept


def coverage_ok(topics: list[dict], n_segs: int) -> tuple[bool, str]:
    if not topics:
        return False, "empty"
    topics_sorted = sorted(topics, key=lambda t: t["start_seg"])
    if topics_sorted[0]["start_seg"] != 0:
        return False, f"first topic starts at SEG-{topics_sorted[0]['start_seg']}, expected 0"
    if topics_sorted[-1]["end_seg"] != n_segs - 1:
        return False, f"last topic ends at SEG-{topics_sorted[-1]['end_seg']}, expected {n_segs - 1}"
    for i in range(len(topics_sorted) - 1):
        a, b = topics_sorted[i], topics_sorted[i + 1]
        if b["start_seg"] != a["end_seg"] + 1:
            return False, f"gap/overlap: topic {i} ends SEG-{a['end_seg']}, topic {i+1} starts SEG-{b['start_seg']}"
    return True, "ok"


# ===== ffmpeg cutting =======================================================

def ffmpeg_cut(full_video: Path, start_sec: float, end_sec: float,
               out_path: Path) -> bool:
    """Stream-copy cut. Returns True on success.

    Uses `-ss` before `-i` for fast seek; `-c copy` for lossless; the cut
    snaps to the nearest preceding keyframe, so up to ~8 sec of leading
    drift is possible if the source MP4 has a default x264 GOP.
    `prepare_sources.py` should pass `-g 60` going forward to bound drift.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
        "-ss", f"{start_sec:.3f}",
        "-to", f"{end_sec:.3f}",
        "-i", str(full_video),
        "-c", "copy",
        "-avoid_negative_ts", "make_zero",
        "-movflags", "+faststart",
        str(out_path),
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        print(f"  [ffmpeg] timeout cutting {out_path.name}")
        return False
    if r.returncode != 0:
        print(f"  [ffmpeg] rc={r.returncode} on {out_path.name}")
        print(f"  stderr (last 500 chars): {r.stderr[-500:]}")
        return False
    return out_path.exists() and out_path.stat().st_size > 0


# ===== Plan / execute =======================================================

def emit_plan_navi_task(episode: str, accepted: list[dict], rejected: list[dict],
                       total_dur_sec: float) -> None:
    lines = [
        f"Auto-segment plan for {episode}",
        "",
        f"Episode duration: {total_dur_sec/60:.1f} min",
        f"Topics proposed: {len(accepted)} accepted, {len(rejected)} rejected",
        "",
        "ACCEPTED — review before approving execute mode:",
    ]
    for i, t in enumerate(accepted):
        m_s, s_s = divmod(int(t["start_sec"]), 60)
        m_e, s_e = divmod(int(t["end_sec"]), 60)
        lines.append("")
        lines.append(f"  {i+1}. {t['title_hint']}  ({t['duration_sec']/60:.1f} min)")
        lines.append(f"     Range: {m_s:02d}:{s_s:02d} – {m_e:02d}:{s_e:02d}")
        lines.append(f"     Thesis: {t['thesis']}")
        lines.append(f"     Subtopics: {', '.join(t.get('subtopics', []))}")
    if rejected:
        lines.append("")
        lines.append("REJECTED:")
        for r in rejected:
            lines.append(f"  • {r.get('title_hint', r.get('slug', '?'))}: {r.get('reject_reason', '?')}")
    lines.append("")
    lines.append("To accept and cut: re-run with --mode execute")
    body = "\n".join(lines)

    try:
        emit_navi_task(
            title=f"Auto-segment plan: {episode} ({len(accepted)} topics)",
            description=body,
            priority="medium",
        )
        print(f"  [navi] emitted plan for {len(accepted)} topic(s)")
    except Exception as exc:
        print(f"  [navi] emit failed: {exc}")


def emit_failure_navi_task(episode: str, reason: str, details: str = "") -> None:
    body = f"Auto-segment failed for {episode}.\n\n{reason}"
    if details:
        body += f"\n\nDetails:\n{details}"
    body += "\n\nManual segmentation required. Drop topic-cut MP4s in NAS incoming/."
    try:
        emit_navi_task(
            title=f"Auto-segment FAILED: {episode}",
            description=body,
            priority="high",
        )
        print(f"  [navi] emitted failure task")
    except Exception as exc:
        print(f"  [navi] emit failed: {exc}")


def write_plan_json(episode_safe: str, accepted: list[dict], rejected: list[dict]) -> Path:
    out_dir = STATE_DIR / episode_safe
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "auto_segment_plan.json"
    out_path.write_text(json.dumps({
        "accepted": accepted,
        "rejected": rejected,
    }, indent=2))
    return out_path


def safe_episode(name: str) -> str:
    return "".join(c if c.isalnum() or c in " -_" else "_" for c in name).strip().replace(" ", "_")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--transcript", required=True)
    ap.add_argument("--full-video-1080p", required=True)
    ap.add_argument("--episode", required=True)
    ap.add_argument("--mode", choices=["plan", "execute"], default="plan")
    ap.add_argument("--min-topics", type=int, default=4)
    ap.add_argument("--max-topics", type=int, default=MAX_TOPICS)
    ap.add_argument("--force", action="store_true",
                    help="Override skip-if-exists checks in execute mode")
    args = ap.parse_args()

    transcript_path = Path(args.transcript)
    full_video = Path(args.full_video_1080p)
    if not transcript_path.exists():
        die(f"transcript not found: {transcript_path}")
    if args.mode == "execute" and not full_video.exists():
        die(f"full video not found: {full_video}")

    tx = json.loads(transcript_path.read_text())
    segments = tx.get("segments", [])
    if not segments:
        die("transcript has no segments")
    total_dur_sec = float(segments[-1]["end"])
    print(f"[load] {transcript_path.name}: {len(segments)} segs, {total_dur_sec/60:.1f} min")

    # Topic segmentation needs the FULL transcript. Default 80K limit is fine
    # for clip-picking (per-topic), but topic-detection requires global context.
    # Claude Sonnet 4.6 has a 200K-token window; 250K chars ≈ 60K tokens.
    transcript_blob = format_transcript_for_prompt(tx, max_chars=250_000)

    print(f"[claude] requesting {args.min_topics}–{args.max_topics} topics…")
    try:
        plan = call_claude(args.episode, total_dur_sec, transcript_blob,
                           args.min_topics, args.max_topics)
    except json.JSONDecodeError as exc:
        # Single retry with reinforcement
        print(f"  [retry] JSON decode error: {exc} — retrying with reinforcement")
        try:
            plan = call_claude(args.episode, total_dur_sec, transcript_blob,
                               args.min_topics, args.max_topics,
                               retry_hint="STRICT REQUIREMENT: Return raw JSON only. No prose. No markdown fences. Start with { end with }. ")
        except Exception as exc2:
            emit_failure_navi_task(args.episode, "Claude returned non-JSON twice", str(exc2))
            die(f"non-JSON response (retry): {exc2}")

    raw_topics = plan.get("topics", [])
    if not isinstance(raw_topics, list):
        emit_failure_navi_task(args.episode, "Claude returned non-list 'topics' field")
        die("plan.topics is not a list")
    print(f"[validate] {len(raw_topics)} proposed topics")

    accepted, rejected = validate_topics(raw_topics, segments)
    print(f"  {len(accepted)} accepted, {len(rejected)} rejected")
    for r in rejected:
        print(f"    REJECT: {r.get('title_hint', r.get('slug', '?'))} — {r.get('reject_reason', '?')}")

    # Coverage check (whole-stage gate). Retry with VERY specific feedback
    # about what failed in the prior attempt — not just "fix coverage" but
    # which topics need merging or expanding and why.
    cov_ok, cov_why = coverage_ok(accepted, len(segments))
    if not cov_ok:
        rej_summary = "; ".join(
            f"'{r.get('title_hint', r.get('slug', '?'))}' ({r.get('reject_reason', '?')})"
            for r in rejected
        ) or "(none)"
        retry_hint = (
            f"Your previous response had problems:\n"
            f"  - Coverage: {cov_why}\n"
            f"  - Rejected topics: {rej_summary}\n"
            f"\n"
            f"FIX INSTRUCTIONS:\n"
            f"  1. Topics must tile the ENTIRE transcript starting at SEG-0 and ending at SEG-{len(segments)-1}.\n"
            f"  2. Any topic shorter than 480 seconds (8 min) MUST be merged into an adjacent topic. "
            f"A 5-min slot about Resident Evil belongs as the OPENING SUBTOPIC of the larger 'film/horror' topic, "
            f"or rolled into the next 'industry critique' topic. Do not return short standalone topics.\n"
            f"  3. Aim for 4–6 topics total, each 10–20 minutes long. For a {total_dur_sec/60:.0f}-min episode, "
            f"that's roughly {(total_dur_sec/60)/15:.1f} topics at ~15 min each.\n"
            f"  4. Title cap is 10 words. Theses should be one declarative sentence asserting a position.\n"
        )
        print(f"  [coverage] {cov_why} — retrying with detailed feedback")
        try:
            plan2 = call_claude(args.episode, total_dur_sec, transcript_blob,
                                args.min_topics, args.max_topics,
                                retry_hint=retry_hint)
            raw_topics = plan2.get("topics", []) or []
            print(f"  [retry] {len(raw_topics)} proposed topics")
            accepted, rejected = validate_topics(raw_topics, segments)
            print(f"    {len(accepted)} accepted, {len(rejected)} rejected")
            for r in rejected:
                print(f"      REJECT: {r.get('title_hint', r.get('slug', '?'))} — {r.get('reject_reason', '?')}")
            cov_ok, cov_why = coverage_ok(accepted, len(segments))
        except Exception as exc:
            print(f"  [coverage retry] failed: {exc}")
        if not cov_ok:
            emit_failure_navi_task(args.episode, "Coverage check failed twice", cov_why)
            die(f"coverage broken: {cov_why}")

    # Min-topics gate
    if len(accepted) < MIN_TOPICS:
        emit_failure_navi_task(args.episode, f"Only {len(accepted)} valid topics (min {MIN_TOPICS})",
                               f"Rejected:\n" + "\n".join(
                                   f"  • {r.get('title_hint', r.get('slug', '?'))}: {r.get('reject_reason', '?')}"
                                   for r in rejected))
        die(f"insufficient valid topics: {len(accepted)} < {MIN_TOPICS}")

    # Second-pass critic: for every topic >12 min, ask Claude whether it should split.
    # Catches the "lumpy survey topic" failure mode where Claude fused 2-3 distinct
    # theses into one big topic. Each split is re-validated.
    critic_changes = 0
    refined: list[dict] = []
    for t in accepted:
        if t.get("duration_sec", 0) <= SPLIT_CRITIC_DURATION_SEC:
            refined.append(t)
            continue
        print(f"  [critic] reviewing '{t.get('title_hint', '?')}' ({t['duration_sec']/60:.1f} min)…")
        try:
            splits = split_critic_review(t, segments)
        except Exception as exc:
            print(f"  [critic] error reviewing '{t.get('title_hint', '?')}': {exc}; keeping merged")
            refined.append(t)
            continue
        if not splits:
            refined.append(t)
            continue
        # Re-validate the splits as fresh topics (they need slug/thesis/subtopics
        # discipline like any other topic)
        re_accepted, re_rejected = validate_topics(splits, segments)
        if not re_accepted:
            print(f"  [critic] all splits failed validation; keeping merged")
            refined.append(t)
            continue
        if re_rejected:
            print(f"  [critic] {len(re_rejected)} of {len(splits)} splits rejected; keeping merged")
            refined.append(t)
            continue
        refined.extend(re_accepted)
        critic_changes += 1
    accepted = refined
    if critic_changes:
        print(f"  [critic] split {critic_changes} fused topic(s); now {len(accepted)} total")
    # Re-validate coverage after splits
    cov_ok, cov_why = coverage_ok(accepted, len(segments))
    if not cov_ok:
        print(f"  [critic] coverage broken after splits: {cov_why} — reverting to pre-split set is not implemented; bailing")
        emit_failure_navi_task(args.episode, "Critic split broke coverage", cov_why)
        die(f"coverage broken post-critic: {cov_why}")

    # ----- Gate 0: per-topic coherence check (concurrent Claude calls) -----
    # Each surviving topic gets a fresh "is this actually a single coherent
    # discussion?" check. SPLIT verdicts log a Navi task with the proposed
    # split point but DON'T auto-split (that's a manual review). INCOHERENT
    # topics are dropped from the publish set.
    accepted = _gate0_topic_coherence(accepted, segments, args.episode)
    if len(accepted) < MIN_TOPICS:
        emit_failure_navi_task(args.episode,
                              f"Gate 0 dropped accepted to {len(accepted)} (< MIN_TOPICS={MIN_TOPICS})",
                              "All topics were INCOHERENT or SPLIT-flagged. Human review required before publish.")
        die(f"Gate 0 reduced topics to {len(accepted)} (< {MIN_TOPICS})")

    # Cap to MAX_TOPICS, scoring by boundary_confidence + stand_alone_score
    if len(accepted) > args.max_topics:
        scored = sorted(accepted, key=lambda t: (
            float(t.get("boundary_confidence", 0)) + float(t.get("stand_alone_score", 0))
        ), reverse=True)
        kept = sorted(scored[:args.max_topics], key=lambda t: t["start_seg"])
        cov_ok2, _ = coverage_ok(kept, len(segments))
        if not cov_ok2:
            print(f"  [cap] cannot cap to {args.max_topics} without breaking coverage; keeping all {len(accepted)}")
        else:
            print(f"  [cap] reduced {len(accepted)} → {args.max_topics} by score; coverage maintained")
            accepted = kept

    # Persist plan + emit Navi
    episode_safe = safe_episode(args.episode)
    plan_path = write_plan_json(episode_safe, accepted, rejected)
    print(f"[plan] wrote {plan_path}")

    if args.mode == "plan":
        emit_plan_navi_task(args.episode, accepted, rejected, total_dur_sec)
        print("[done] plan-mode — no video cut. Re-run with --mode execute to commit.")
        return 0

    # In execute mode, drop sub-floor topics (under DURATION_FLOOR_SEC).
    # User policy: "no topic videos under 4-5 min — they feel pointless."
    # Their content stays in the full episode; we just don't cut a separate video.
    pre_drop_count = len(accepted)
    accepted = [t for t in accepted
                if not (t.get("duration_warning") or "").startswith("sub-floor")]
    if pre_drop_count != len(accepted):
        print(f"  [execute] dropped {pre_drop_count - len(accepted)} sub-floor topic(s) "
              f"(< {DURATION_FLOOR_SEC:.0f}s); they remain in the full episode")

    # Execute mode: cut MP4s + write per-topic transcripts
    print(f"[execute] cutting {len(accepted)} topics from {full_video.name}")
    cut_failures = 0
    for i, t in enumerate(accepted, start=1):
        slug = t["slug"]
        stem = f"{i:02d}-{slug}_auto_1080p"
        out_mp4 = SOURCE_1080P / f"{stem}.mp4"
        out_tx = TRANSCRIPTS / f"{stem}.json"

        if out_mp4.exists() and not args.force:
            print(f"  [{i}] skip — {out_mp4.name} already exists (--force to overwrite)")
            continue

        if not ffmpeg_cut(full_video, t["start_sec"], t["end_sec"], out_mp4):
            cut_failures += 1
            t["cut_failed"] = True
            if cut_failures >= 2:
                emit_failure_navi_task(args.episode, "≥2 ffmpeg cuts failed — bailing")
                die("ffmpeg cut failures exceed threshold")
            continue

        # Carve transcript
        carved = carve_transcript(tx, t["start_seg"], t["end_seg"])
        carved["source"] = str(out_mp4)
        out_tx.write_text(json.dumps(carved, indent=2))

        # Post-cut audit: re-check first-segment opening
        if carved["segments"]:
            fw = first_content_word(carved["segments"][0])
            if fw in BAD_OPENING_WORDS or fw in UNRESOLVED_PRONOUNS:
                t["audit_warning"] = f"post-cut first word is '{fw}' (likely keyframe drift)"
                print(f"  [{i}] AUDIT WARNING: {t['audit_warning']}")

        m_s, s_s = divmod(int(t["start_sec"]), 60)
        m_e, s_e = divmod(int(t["end_sec"]), 60)
        print(f"  [{i}] {stem}.mp4  ({t['duration_sec']/60:.1f} min, {m_s:02d}:{s_s:02d}–{m_e:02d}:{s_e:02d})")

    # Update plan JSON with execute results
    write_plan_json(episode_safe, accepted, rejected)

    # Final summary Navi
    audit_warnings = [t for t in accepted if t.get("audit_warning")]
    summary = (
        f"Auto-segment executed for {args.episode}.\n\n"
        f"{len(accepted) - cut_failures}/{len(accepted)} topics cut successfully.\n"
        f"Cut failures: {cut_failures}\n"
        f"Audit warnings: {len(audit_warnings)}\n"
    )
    if audit_warnings:
        summary += "\nWarnings:\n" + "\n".join(f"  • {t['title_hint']}: {t['audit_warning']}" for t in audit_warnings)
    try:
        emit_navi_task(
            title=f"Auto-segment EXECUTED: {args.episode}",
            description=summary,
            priority="medium",
        )
    except Exception as exc:
        print(f"  [navi] emit failed: {exc}")

    print(f"[done] cut {len(accepted) - cut_failures} topic(s); {cut_failures} failure(s)")
    return 0 if cut_failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
