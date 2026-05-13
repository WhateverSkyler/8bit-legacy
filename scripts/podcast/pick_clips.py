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


# --- Duration policy ---
# 2026-05-12: hard ceiling lowered 59→54s to leave room for the 5s appended
# closer-ad CTA. Total output = dialog + 5s CTA, must stay under 60s YT
# Shorts cap. Sweet-spot target also adjusted accordingly.
DURATION_FLOOR_SEC = 25.0      # below this the clip feels like a fragment
DURATION_TARGET_LO = 30.0      # sweet-spot lower bound
DURATION_TARGET_HI = 50.0      # sweet-spot upper bound (4s margin under hard cap)
DURATION_CEILING_SEC = 54.0    # HARD CAP — dialog + 5s CTA = 59s ≤ 60s YT cap

# --- Stand-alone validators ---
BAD_OPENING_WORDS = {
    # Continuation conjunctions — imply prior context
    "so", "and", "but", "then", "because", "anyway", "also", "plus",
    "or", "nor", "yet",
    # Prepositions — cannot start a sentence on their own (round 9c:
    # user saw clip starting "of like kind of pre scalping" which is
    # clearly mid-thought continuation)
    "of", "for", "with", "by", "from", "in", "on", "at",
    "into", "onto", "through", "across", "between",
    "to",  # "to be honest" rare but mostly mid-clause continuation
    # Articles — can technically start a sentence but in this transcript
    # context "the way they..." is almost always mid-thought reference
    "the", "a", "an",
    # Quantifier/qualifier fillers that imply continuation
    "kind", "sort",
    # Filler agreement — implies responding to something
    "yeah", "yep", "right", "exactly", "totally", "absolutely",
    # Mid-thought markers
    "like", "you", "i",  # "like I was saying", "you know what", "I mean"
    "oh",
    # Contractions of the above (2026-05-08 fix: "I'm just impressed..." was
    # passing because i'm wasn't matching "i" — it's stripped to "i'm" not "i")
    "i'm", "i've", "i'll", "i'd",
    "you're", "you've", "you'll", "you'd",
    "we're", "we've", "we'll", "we'd",
    "they're", "they've", "they'll", "they'd",
    "he's", "she's", "it's",
    "that's", "what's", "there's", "here's",
    "don't", "doesn't", "didn't", "won't", "wouldn't", "couldn't", "shouldn't",
    "isn't", "aren't", "wasn't", "weren't", "hasn't", "haven't", "hadn't",
}
UNRESOLVED_PRONOUNS = {
    "he", "she", "they", "it", "that", "this", "those", "these", "him", "her", "them",
    # Contractions still imply unresolved subject
    "he's", "she's", "it's", "they're", "they've", "they'll", "they'd",
    "that's", "those're", "these're",
}
# Pronouns that, if appearing within the FIRST 10 WORDS of a clip, suggest
# the clip starts mid-conversation (the antecedent is in earlier audio the
# viewer never heard). Used by _has_orphan_pronoun_in_opener.
EARLY_OPENER_PRONOUNS = {
    "he", "she", "they", "it", "that", "this", "those", "these", "them", "him", "her",
}
# Sentinel words that, if appearing BEFORE a pronoun, indicate the pronoun
# IS resolvable from clip-internal text (a noun was just introduced).
ANTECEDENT_PROXY_TAGS = {"NN", "NNS", "NNP", "NNPS"}  # nouns from POS tag prefixes
SENTENCE_END_PUNCT = {".", "!", "?"}

PICKS_REQUESTED = 25  # bumped 14→25 (2026-05-08 PM): user goal is dozens of
# shippable shorts per episode. With Gate 0/1/enrichment/2/3/4 attrition (~50%
# per stage cumulative), starting from 25 candidates per source × ~7 sources
# = ~175 raw candidates → ~30-50 surviving clips per episode. Hits the
# "3 per day for 2 weeks" cadence with margin.

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

DURATION TARGET (hard constraint, optimized for cross-platform Shorts qualification):
- Sweet spot: 30–50 seconds
- Floor: 25 seconds (below this feels like a fragment, no payoff)
- HARD CEILING: 54 seconds (NEVER exceed — we APPEND a 5-second branded
  closer ad after every clip, so dialog + ad must total <60s to qualify as
  a Short on YouTube + Reel on IG/FB + short-form on TikTok.)
Err shorter if the arc lands cleanly. Cutting at the punchline beats overstaying
the welcome — completion rate matters more than length.

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
- **TITLE MUST CAPTURE THE CLIP'S MAIN POINT / THESIS** — what the
  speakers are actually arguing or making a case about — NOT just any
  concrete fact mentioned in passing. Ask yourself: "If I asked the
  speakers what this clip is about in one sentence, what would they
  say?" The title should match THAT, not a side detail.
  - GOOD: clip where speakers complain that scalpers ruin the trading
    card hobby for kids → "Scalpers Are Ruining Kids' Hobby"
  - BAD: same clip → "GameStop Pro Doubles The Card Limit" (this fact
    is mentioned in passing as evidence; it's NOT what the clip is
    about)
  - GOOD: clip where they argue Switch 2 physical copies cost more than
    digital → "Physical Switch 2 Games Cost More"
  - BAD: same clip → "1,000 People At The Demo" (a passing detail)
  Concrete-but-incidental titles look like the AI just grabbed the most
  searchable noun. Topical titles tell the viewer the actual
  conversation in 5 words.
- **MUST contain at least one CONCRETE noun from the clip's transcript**
  related to the main point — a specific game title, console name,
  company, person, hobby, or year that is literally said in the clip.
  "Adult Gaming Reality Check" fails (too generic). The concrete noun
  must be one that anchors the MAIN POINT, not a tangent.
- **MUST be GROUNDED in what's actually said.** Every content verb and
  noun in the title must appear in the transcript verbatim or as a clear
  paraphrase. If the speakers said "this game isn't engaging," titles
  like "Tears of the Kingdom Feels Empty" or "Tears of the Kingdom Isn't
  Engaging" pass. "Tears of the Kingdom Is Too Easy to Break" FAILS
  because nobody used the word "break" or talked about breaking the
  game — it embellishes a hot-take frame the speakers didn't voice.
- **PREFER honest specificity** over either extreme of vagueness or
  embellishment. The viewer should learn the actual topic AND the actual
  take from the title, not just one or the other.
- NO time-decay words: "today", "this week", "next month", "just announced", "just dropped", "just released", "leaked", "breaking", "yesterday", "now", "recently". These work for one day and look stale forever after.
- NO numerical specifics that aren't directly quoted in the clip ("3 reasons", "10x bigger", "first ever") — only use a number if the speakers literally state it.
- NO names of people or companies in the title unless the clip is centrally about them — a tangent mention isn't enough.
- NO metaphorical extensions ("ruins / breaks / kills / destroys / saves")
  unless the speakers actually used that exact framing in the clip.
- The title should preview the *take* AND name *what it's about*. "AAA
  Gaming Is Cooked" is OK but "GameStop Wants To Buy eBay" is better
  because it names the specific subject.

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


def _has_orphan_pronoun_in_opener(opener_text: str, max_words: int = 10) -> tuple[bool, str]:
    """Detect mid-conversation starts: pronoun in first N words with no antecedent
    earlier in the clip's own opening text.

    Example BAD: "I'm just impressed that they were able to keep that level..."
        → "they" is in first 10 words but no noun has been introduced yet — viewer
          has no idea who "they" are.

    Example OK: "Donkey Kong's animation is incredible. They nailed every level."
        → "Donkey Kong" introduced before "they" → resolvable from clip-internal text.

    Returns (is_orphan, reason).
    """
    import re as _re
    words = _re.findall(r"[A-Za-z']+", opener_text.lower())[:max_words]
    if not words:
        return False, ""
    # Track whether ANY noun-ish word has appeared before the pronoun.
    # Cheap heuristic: capitalized proper nouns (we lowercased so check raw text)
    # OR common-noun-ish words that aren't function words.
    raw_words = _re.findall(r"[A-Za-z']+", opener_text)[:max_words]
    function_words = {
        "i", "i'm", "i've", "i'll", "i'd", "you", "we", "we're", "they", "they're",
        "the", "a", "an", "of", "to", "in", "on", "at", "for", "with", "by", "from",
        "and", "but", "or", "if", "when", "where", "why", "how", "is", "was", "are",
        "were", "be", "been", "have", "has", "had", "do", "does", "did", "will",
        "would", "could", "should", "may", "might", "can", "just", "really", "very",
        "so", "as", "all", "any", "some", "more", "most", "less", "few", "also",
        "this", "that", "these", "those", "it", "its", "their", "his", "her", "our",
    }

    seen_noun = False
    for raw, w in zip(raw_words, words):
        # Strip apostrophe trail for matching
        w_clean = w.rstrip("'s").rstrip("'")
        # Treat capitalized words (not at sentence start) as proper nouns
        if raw[0].isupper() and not seen_noun:
            seen_noun = True
            continue
        if w in EARLY_OPENER_PRONOUNS or w_clean in EARLY_OPENER_PRONOUNS:
            if not seen_noun:
                return True, f"orphan pronoun '{w}' in opener ({' '.join(words[:10])})"
        # Generic noun-like: > 3 chars, not a function word, mostly letters
        if len(w_clean) > 3 and w_clean not in function_words:
            seen_noun = True
    return False, ""


def _opener_mentions_topic(opener_text: str, title: str, topics: list[str],
                          max_seconds: float = 10.0) -> tuple[bool, str]:
    """Mechanical check: clip's first ~10 seconds of text must mention at least
    one keyword from the title or topics list. Otherwise the viewer doesn't
    know what the clip is about within 5-10 sec — fails the scroll-stop test.

    Args:
      opener_text: text of the clip's first ~max_seconds (caller-extracted).
      title: clip's title (e.g., "Donkey Kong Tropical Freeze Might Be the Best 2D Platformer Ever")
      topics: clip's topics list (e.g., ["donkey kong", "platformers", "nintendo"])

    Returns (mentions_topic, reason).
    """
    import re as _re
    opener_lower = (opener_text or "").lower()
    if not opener_lower:
        return False, "empty opener"

    # Extract content words from title (drop stopwords/short words)
    title_words = set(_re.findall(r"[a-z]+", (title or "").lower()))
    stopwords = {"the", "a", "an", "of", "to", "in", "on", "at", "for", "with", "by",
                 "and", "but", "or", "is", "are", "be", "been", "have", "has", "had",
                 "do", "does", "did", "will", "would", "could", "should", "may", "might",
                 "this", "that", "these", "those", "it", "its", "their", "his", "her",
                 "be", "best", "ever", "very", "much", "more", "most", "many", "some",
                 "any", "all", "what", "why", "how", "when", "where", "than"}
    title_keywords = {w for w in title_words if w not in stopwords and len(w) >= 3}

    # Topics → flatten to words
    topic_keywords = set()
    for t in (topics or []):
        for w in _re.findall(r"[a-z]+", str(t).lower()):
            if len(w) >= 3 and w not in stopwords:
                topic_keywords.add(w)

    keywords = title_keywords | topic_keywords
    if not keywords:
        return True, "no keywords to check (title+topics empty)"

    # Find any keyword in opener
    opener_words = set(_re.findall(r"[a-z]+", opener_lower))
    matches = keywords & opener_words
    if matches:
        return True, f"opener mentions: {sorted(matches)[:3]}"
    return False, f"opener mentions NONE of {sorted(keywords)[:5]} (first words: {opener_lower[:120]})"


def _opener_text_in_seconds(segments: list[dict], start_sec: float, n_seconds: float = 10.0) -> str:
    """Concatenate segment text within [start_sec, start_sec + n_seconds]."""
    parts = []
    end_sec = start_sec + n_seconds
    for seg in segments:
        if seg.get("end", 0) < start_sec: continue
        if seg.get("start", 0) > end_sec: break
        parts.append(seg.get("text", "").strip())
    return " ".join(parts).strip()


def _starts_mid_phrase(start_seg: dict, prev_seg: dict | None) -> bool:
    """Detect when a clip's first segment starts mid-phrase — i.e., the
    previous segment ends without sentence-terminal punctuation AND ends with
    a phrase that continues into the current one.

    Catches the "Ocarina of Time" → "Time" cut: prev segment was "...I think the
    best Zelda game is Ocarina of " ending mid-phrase, and the chosen start
    segment begins with "Time," which loses the "Ocarina of" context.

    Returns True if we should pull in the previous segment.
    """
    if not prev_seg:
        return False
    prev_text = (prev_seg.get("text") or "").strip()
    if not prev_text:
        return False
    # If prev segment ends with sentence-terminal punctuation, clip start is fine.
    if prev_text[-1] in SENTENCE_END_PUNCT:
        return False
    # If prev segment ends with comma/no-punct AND its last word looks like an
    # incomplete phrase (preposition, article, "of"/"the"/"a"/"an"), the current
    # segment likely continues that phrase.
    last_word = re.findall(r"[A-Za-z']+", prev_text)
    if not last_word:
        return False
    last_lower = last_word[-1].lower()
    PHRASE_LEADERS = {
        "of", "the", "a", "an", "to", "for", "in", "on", "at", "with", "and",
        "or", "but", "is", "are", "was", "were", "be", "been", "have", "has",
        "had", "do", "does", "did", "will", "would", "could", "should", "can",
        "this", "that", "these", "those",
    }
    return last_lower in PHRASE_LEADERS


def _find_setup_question_backward(segments: list[dict], current_start_idx: int,
                                  title: str, topics: list[str],
                                  max_lookback_sec: float = 30.0) -> int | None:
    """Search backward up to max_lookback_sec for a segment that DOES mention
    the topic — typically a question that sets up the discussion.

    User feedback 2026-05-11: the "Yoshi and Kirby got too easy" clip starts
    with the response but the question "do you think Nintendo will ever go
    back to making harder games?" was 5-15 sec earlier and is the perfect
    hook. We want to pull start back to include it.

    Returns the new start_idx if found, else None.
    """
    if current_start_idx <= 0:
        return None

    # Extract topic keywords (same logic as _opener_mentions_topic)
    title_words = set(re.findall(r"[a-z]+", (title or "").lower()))
    stopwords = {"the", "a", "an", "of", "to", "in", "on", "at", "for", "with", "by",
                 "and", "but", "or", "is", "are", "be", "been", "have", "has", "had",
                 "do", "does", "did", "will", "would", "could", "should", "may", "might",
                 "this", "that", "these", "those", "it", "its", "their", "his", "her",
                 "be", "best", "ever", "very", "much", "more", "most", "many", "some",
                 "any", "all", "what", "why", "how", "when", "where", "than"}
    title_keywords = {w for w in title_words if w not in stopwords and len(w) >= 3}
    topic_keywords = set()
    for t in (topics or []):
        for w in re.findall(r"[a-z]+", str(t).lower()):
            if len(w) >= 3 and w not in stopwords:
                topic_keywords.add(w)
    keywords = title_keywords | topic_keywords
    if not keywords:
        return None

    current_start_time = segments[current_start_idx].get("start", 0)
    earliest_ok_time = current_start_time - max_lookback_sec

    # Walk backward looking for segments that mention the topic AND start a
    # sentence (ending the prior with punctuation, or being a question).
    best_idx: int | None = None
    for i in range(current_start_idx - 1, -1, -1):
        seg = segments[i]
        if seg.get("start", 0) < earliest_ok_time:
            break
        text = (seg.get("text") or "").strip()
        if not text:
            continue
        seg_words = set(re.findall(r"[a-z]+", text.lower()))
        matches = keywords & seg_words
        if not matches:
            continue
        # Found a topic-mentioning segment. Make sure it's a clean sentence start —
        # the segment BEFORE it must end with terminal punctuation (or i==0).
        if i == 0:
            return i
        prev_text = (segments[i - 1].get("text") or "").strip()
        if prev_text and prev_text[-1] in SENTENCE_END_PUNCT:
            # Clean sentence boundary — this is a great place to start
            return i
        # Otherwise keep this as a backup but keep searching for a cleaner one
        if best_idx is None:
            best_idx = i

    return best_idx


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

    # ---- Pre-validation fix 1: pull in previous segment if the chosen start
    # segment starts mid-phrase (2026-05-11 user feedback: "Ocarina of Time" →
    # "Time" cut). When the prior segment ends without terminal punctuation AND
    # ends on a phrase leader (of/the/a/in/on/etc.), extend back one segment.
    if start_idx > 0:
        if _starts_mid_phrase(segments[start_idx], segments[start_idx - 1]):
            start_idx -= 1

    # ---- Pre-validation fix 2: look back for the topic-introducing question
    # (2026-05-11 user feedback: "Yoshi and Kirby got too easy" should start
    # with "do you think Nintendo will ever go back to making harder games?").
    # If the opener doesn't mention the topic, search up to 30s before for a
    # cleaner-starting sentence that does.
    initial_opener_text = _opener_text_in_seconds(
        segments[start_idx:], segments[start_idx]["start"], n_seconds=10.0,
    )
    initial_topic_ok, _ = _opener_mentions_topic(
        initial_opener_text, pick.get("title", ""), pick.get("topics") or [],
    )
    if not initial_topic_ok:
        new_idx = _find_setup_question_backward(
            segments, start_idx,
            pick.get("title", ""), pick.get("topics") or [],
            max_lookback_sec=30.0,
        )
        if new_idx is not None and new_idx < start_idx:
            start_idx = new_idx

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

        # ---- DEEP OPENER CHECKS (2026-05-08) ----
        # The first-word check is necessary but not sufficient. "I'm just impressed
        # that they were able to keep..." passes the first-word check (i'm) but is
        # actually mid-conversation. So also check:
        #   (a) Orphan pronouns within first 10 words ("they" with no antecedent)
        #   (b) Topic keyword present in first 10 seconds (else viewer doesn't know
        #       what we're talking about within the scroll-stop window)
        opener_text = _opener_text_in_seconds(segments[start_idx:], new_start, n_seconds=10.0)
        opener_orphan, orphan_reason = _has_orphan_pronoun_in_opener(opener_text, max_words=10)
        topic_ok, topic_reason = _opener_mentions_topic(
            opener_text, pick.get("title", ""), pick.get("topics") or [],
        )

        # Combine all opener-quality issues into a single "opens_bad" decision
        opener_issues = []
        if opens_bad:
            opener_issues.append(f"first word '{first_word}'")
        if opener_orphan:
            opener_issues.append(orphan_reason)
        if not topic_ok:
            opener_issues.append(topic_reason)
        opener_failed = bool(opener_issues)

        if opener_failed and attempt < max_extensions:
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
        if opener_failed:
            return pick, False, f"opener fails: {' | '.join(opener_issues)}"
        if not ends_clean:
            return pick, False, f"end not sentence-terminal after rescue attempts"

        # Word-boundary snap (2026-05-12): even after segment-level snapping,
        # the LAST word of end_seg might extend slightly past new_end if
        # whisperX picked a phrase pause that's slightly inside the final
        # word. To eliminate ANY mid-word audio chop, walk end_seg's words
        # and snap new_end to the END of the LAST complete word + a 0.10s
        # trailing pad for a clean breath. Same for new_start: snap to the
        # START of the first word so we don't begin mid-syllable.
        if end_seg.get("words"):
            last_word_end = end_seg["start"]
            for w in end_seg["words"]:
                w_end = w.get("end", 0)
                if w_end <= new_end + 0.05:
                    last_word_end = w_end
                else:
                    break
            # Round 9c: bump breath pad 0.10 → 0.40s. User feedback: last
            # word still felt chopped before the CTA — no clean pause.
            # 0.40s gives a noticeable breath without dead air.
            new_end = last_word_end + 0.40
        if start_seg.get("words"):
            first_word_start = start_seg["start"]
            for w in start_seg["words"]:
                w_start = w.get("start", 0)
                if w_start >= new_start - 0.05:
                    first_word_start = w_start
                    break
            new_start = max(0.0, first_word_start - 0.05)  # small lead-in

        # Recompute duration after word-boundary snap (the 0.10s pad
        # may push us slightly over what segment-level snapping picked,
        # but always at a clean word boundary so audio never chops).
        duration = new_end - new_start

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

        # Cold-viewer eval: do NOT pass title/hook to Gate 1. Claude was
        # confabulating context from the hook to "explain" mid-conversation
        # starts. By withholding title/hook, Claude must judge the clip's
        # standalone-ness from clip text alone — same as a real viewer.
        # (Title/hook are still passed to Gate 4 which validates title-content match.)
        prompt = GATE_1_NARRATIVE_COHERENCE_V1.format(
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


# ============================================================================
# COLD-VIEWER OPENER GATE (post-snap, concurrent)
# ============================================================================
# Sends ONLY the first 5 seconds of opener text to Claude with strict cold-
# viewer framing. Catches "starts mid-sentence" failures that Gate 1 misses
# because Gate 1 sees the full clip text and can rationalize bad openings
# from downstream context.
#
# Runs CONCURRENTLY across all picks (asyncio.gather) so wall time is ~3s
# regardless of pick count. Uses Sonnet (cheap, fast — judgment is binary
# yes/no, doesn't need Opus reasoning).

def _cold_opener_gate(picks: list[dict], segments: list[dict]) -> list[dict]:
    """Filter picks by the cold-viewer opener test. Returns the surviving
    picks. Each pick's first 5 seconds get sent to Claude in isolation —
    no title, no hook, no surrounding context. If Claude says the opener
    doesn't make sense as a stand-alone start, reject the pick.

    Concurrent batch — runs all picks in parallel via asyncio.gather to
    keep wall-clock cost minimal. ~50 picks finishes in ~3-5s.

    On infrastructure errors (Anthropic outage, JSON parse failure), the
    pick is PASSED through (don't drop work on infra flakes).
    """
    if not picks:
        return picks
    try:
        from _qa_helpers import call_claude_text_async, log_gate_decision, SONNET_MODEL
        from qa_prompts import COLD_OPENER_TEST_V1
    except ImportError as exc:
        print(f"  [cold-opener] qa helpers unavailable ({exc}) — skipping gate")
        return picks

    import asyncio

    episode_stem = picks[0].get("source_stem", "unknown")

    def _context_window(start_sec: float, window_pre: float = 12.0,
                        window_post: float = 12.0) -> str:
        """Build a context window of transcript text around the current
        clip start, with absolute-timestamped segment lines so Claude
        can suggest a better start time grounded in real transcript pts.
        """
        lo = max(0.0, start_sec - window_pre)
        hi = start_sec + window_post
        lines: list[str] = []
        for seg in segments:
            s_start = seg.get("start", 0.0)
            s_end = seg.get("end", 0.0)
            if s_end < lo:
                continue
            if s_start > hi:
                break
            marker = " ← CURRENT START" if abs(s_start - start_sec) < 0.5 else ""
            lines.append(f"[{s_start:.2f}s]{marker} {seg.get('text','').strip()}")
        return "\n".join(lines)

    # Build per-pick prompts. Each prompt includes the current 5s opener
    # AND a ±12s context window so Claude can suggest a better start_sec
    # when the current one is bad.
    work: list[tuple[dict, str | None, str]] = []
    for pick in picks:
        try:
            start = float(pick.get("start_sec", 0))
        except (TypeError, ValueError):
            work.append((pick, None, "?"))
            continue
        start_idx = _find_segment_containing(start, segments)
        if start_idx is None:
            work.append((pick, None, "?"))
            continue
        opener_text = _opener_text_in_seconds(segments[start_idx:], start, n_seconds=5.0)
        if not opener_text or len(opener_text.strip()) < 8:
            work.append((pick, None, "?"))
            continue
        context_window = _context_window(start, window_pre=12.0, window_post=12.0)
        prompt = COLD_OPENER_TEST_V1.format(
            opener_text=opener_text.strip()[:1500],
            current_start_sec=start,
            context_window=context_window[:3000],
        )
        clip_id = pick.get("clip_id") or pick.get("title", "?")[:60]
        work.append((pick, prompt, clip_id))

    async def _gather_all() -> list:
        tasks = []
        for _p, prompt, _c in work:
            if prompt is None:
                tasks.append(asyncio.sleep(0, result=None))
            else:
                # max_tokens=300 — output is a small JSON, no need for more.
                # Sonnet model (default) — judgment is simple, Opus overkill.
                tasks.append(call_claude_text_async(prompt, model=SONNET_MODEL, max_tokens=300))
        return await asyncio.gather(*tasks, return_exceptions=True)

    n_with_prompt = sum(1 for _, p, _ in work if p)
    if n_with_prompt == 0:
        return picks
    print(f"  [cold-opener] running {n_with_prompt} picks concurrently...")
    import time as _time
    t0 = _time.time()
    verdicts = asyncio.run(_gather_all())
    elapsed = _time.time() - t0
    print(f"  [cold-opener] {n_with_prompt} concurrent calls completed in {elapsed:.1f}s")

    surviving: list[dict] = []
    n_adjusted = 0
    for (pick, prompt, clip_id), verdict in zip(work, verdicts):
        if prompt is None:
            surviving.append(pick)
            continue
        if isinstance(verdict, Exception):
            print(f"  [cold-opener] claude error on {pick.get('title','?')[:40]}: {verdict} — keeping pick")
            surviving.append(pick)
            continue
        if not verdict or not isinstance(verdict, dict):
            surviving.append(pick)
            continue
        rec = (verdict.get("recommendation") or "").upper()
        reason = verdict.get("reason", "?")

        log_gate_decision(episode_stem, "cold_opener", clip_id, verdict, extra={
            "title": pick.get("title", "?"),
            "start_sec": pick.get("start_sec", 0),
        })

        if rec == "PASS":
            surviving.append(pick)
            continue

        if rec == "ADJUST":
            # Snap to the suggested start. Then snap to nearest WORD boundary
            # so we don't begin mid-syllable.
            try:
                suggested = float(verdict.get("suggested_start_sec"))
            except (TypeError, ValueError):
                suggested = None
            if suggested is None or suggested < 0:
                print(f"  [cold-opener] REJECT (ADJUST without valid suggestion): {pick.get('title','?')[:50]}")
                continue
            old_start = float(pick.get("start_sec", 0))
            old_end = float(pick.get("end_sec", 0))
            old_duration = old_end - old_start
            # Find the segment containing the suggested start
            seg_idx = _find_segment_containing(suggested, segments)
            if seg_idx is None:
                print(f"  [cold-opener] REJECT (suggested {suggested:.2f}s not in any segment): {pick.get('title','?')[:50]}")
                continue
            target_seg = segments[seg_idx]
            # Snap to the START of the first word at or after suggested
            new_start = target_seg.get("start", suggested)
            words = target_seg.get("words") or []
            for w in words:
                if w.get("start", 0) >= suggested - 0.1:
                    new_start = w.get("start", new_start)
                    break
            # Recompute end_sec to preserve original duration (capped at duration ceiling)
            new_duration = min(old_duration, DURATION_CEILING_SEC)
            new_end = new_start + new_duration
            # Snap new_end to the end of the last whole word that fits
            end_idx = _find_segment_containing(new_end, segments)
            if end_idx is not None:
                end_seg = segments[end_idx]
                last_word_end = end_seg.get("start", new_end)
                for w in (end_seg.get("words") or []):
                    if w.get("end", 0) <= new_end + 0.05:
                        last_word_end = w.get("end", last_word_end)
                    else:
                        break
                new_end = last_word_end + 0.40  # breath pad
            # Validate the adjusted duration
            if new_end - new_start < DURATION_FLOOR_SEC:
                print(f"  [cold-opener] REJECT (adjusted clip too short): {pick.get('title','?')[:50]}")
                continue
            print(f"  [cold-opener] ADJUST: {pick.get('title','?')[:50]} "
                  f"{old_start:.1f}s → {new_start:.2f}s ({reason})")
            pick = {**pick,
                    "start_sec": round(new_start, 2),
                    "end_sec": round(new_end, 2),
                    "duration_sec": round(new_end - new_start, 2),
                    "_cold_opener_adjusted": True}
            n_adjusted += 1
            surviving.append(pick)
            continue

        # REJECT
        print(f"  [cold-opener] REJECT: {pick.get('title','?')[:50]} — {reason}")

    n_rej = len(picks) - len(surviving)
    print(f"  [cold-opener] {len(picks)} picks → {len(surviving)} kept "
          f"({n_adjusted} adjusted, {n_rej} rejected)")
    return surviving


# --- Title quality + hashtag + audio mix audits (post-Gate 1, pre-render) ----
# Run concurrently across surviving candidates. Each candidate gets its title
# audited (+ optionally rewritten), per-clip hashtags generated, and a mood
# tag for adaptive audio mixing in render_clip.py.

def _post_pick_enrichment(picks: list[dict], transcript: dict) -> list[dict]:
    """For each accepted pick: validate title, generate hashtags, classify mood.

    All three calls per-clip run concurrently per-clip via asyncio.gather.
    Surviving picks gain:
      - Possibly rewritten title (if TITLE_QUALITY decided REWRITE)
      - `_llm_hashtags` list (used by _caption.py if present)
      - `_audio_mood` + `_audio_music_volume` (used by render_clip.py)

    Failures (network/JSON) skip enrichment for that clip — never drop the clip.
    """
    if not picks:
        return picks
    try:
        from _qa_helpers import call_claude_text_async, log_gate_decision
        from qa_prompts import (
            TITLE_QUALITY_AUDIT_V1, HASHTAG_SELECTION_V1, AUDIO_MIX_MOOD_V1,
        )
    except ImportError as exc:
        print(f"  [enrich] qa helpers unavailable ({exc}) — skipping post-pick enrichment")
        return picks

    import asyncio
    import time

    episode_stem = picks[0].get("source_stem", "unknown") if picks else "unknown"

    # Build all 3 prompts × N clips upfront
    work: list[tuple[dict, dict]] = []  # (pick, {kind: prompt})
    for p in picks:
        try:
            start = float(p.get("start_sec", 0))
            end = float(p.get("end_sec", 0))
        except (TypeError, ValueError):
            work.append((p, {}))
            continue
        text = _extract_text_in_range(transcript, start, end)[:1500]
        if not text:
            work.append((p, {}))
            continue
        prompts = {
            "title": TITLE_QUALITY_AUDIT_V1.format(
                title=p.get("title", "?"),
                hook=p.get("hook", "?"),
                topics=", ".join(p.get("topics", [])) or "?",
                extracted_text=text,
            ),
            "hashtags": HASHTAG_SELECTION_V1.format(
                title=p.get("title", "?"),
                hook=p.get("hook", "?"),
                topics=", ".join(p.get("topics", [])) or "?",
                extracted_text=text,
            ),
            "mood": AUDIO_MIX_MOOD_V1.format(
                title=p.get("title", "?"),
                extracted_text=text,
            ),
        }
        work.append((p, prompts))

    # Build flat task list, preserving (clip_idx, kind) labels
    flat: list[tuple[int, str]] = []
    coros = []
    for i, (p, prompts) in enumerate(work):
        for kind, prompt in prompts.items():
            flat.append((i, kind))
            coros.append(call_claude_text_async(prompt, max_tokens=800))

    if not coros:
        return picks

    print(f"  [enrich] running {len(coros)} concurrent calls ({len(picks)} clips × 3 audits)...")

    async def _run():
        return await asyncio.gather(*coros, return_exceptions=True)

    t0 = time.time()
    results = asyncio.run(_run())
    print(f"  [enrich] {len(coros)} calls completed in {time.time()-t0:.1f}s")

    # Process results back per-clip
    by_clip: dict[int, dict] = {i: {} for i in range(len(work))}
    for (clip_i, kind), res in zip(flat, results):
        by_clip[clip_i][kind] = res

    enriched = []
    for i, (p, _prompts) in enumerate(work):
        verdicts = by_clip.get(i, {})
        clip_id = p.get("clip_id") or p.get("title", "?")[:60]

        # ---- Title audit ----
        tv = verdicts.get("title")
        if tv and not isinstance(tv, Exception) and isinstance(tv, dict):
            log_gate_decision(episode_stem, "title_audit", clip_id, tv,
                              extra={"original_title": p.get("title", "?")})
            decision = (tv.get("decision") or "").upper()
            if decision == "REWRITE":
                new_title = tv.get("rewritten_title")
                if new_title and isinstance(new_title, str) and 5 <= len(new_title) <= 90:
                    print(f"  [title] REWRITE: '{p.get('title','?')[:40]}' → '{new_title[:40]}'")
                    p["_original_title"] = p.get("title")
                    p["title"] = new_title
                    p["_title_rewritten"] = True
            elif decision == "REJECT":
                # Title gate REJECT means we couldn't even rewrite into something honest.
                # Drop the clip entirely.
                print(f"  [title] REJECT: '{p.get('title','?')[:40]}' — {tv.get('reason','?')}")
                continue  # skip — not added to enriched
            elif decision == "APPROVE_WITH_NOTE":
                p["_title_warnings"] = tv.get("issues", [])

        # ---- Hashtag generation ----
        hv = verdicts.get("hashtags")
        if hv and not isinstance(hv, Exception) and isinstance(hv, dict):
            tags = hv.get("hashtags") or []
            if isinstance(tags, list) and tags:
                # Sanitize: lowercase, strip non-alphanumeric, ensure leading #
                cleaned = []
                seen = set()
                for tag in tags:
                    if not isinstance(tag, str): continue
                    t = tag.strip().lstrip("#").lower()
                    t = "".join(c for c in t if c.isalnum())
                    if not t or t in seen: continue
                    seen.add(t)
                    cleaned.append(f"#{t}")
                if cleaned:
                    p["_llm_hashtags"] = cleaned[:10]
                    log_gate_decision(episode_stem, "hashtag_gen", clip_id, hv,
                                     extra={"n_tags_kept": len(p["_llm_hashtags"])})

        # ---- Audio mix mood ----
        mv = verdicts.get("mood")
        if mv and not isinstance(mv, Exception) and isinstance(mv, dict):
            mood = (mv.get("mood") or "").lower()
            vol = mv.get("music_volume")
            if mood in ("intense", "storytelling", "casual", "upbeat") and \
               isinstance(vol, (int, float)) and 0.05 <= vol <= 0.20:
                p["_audio_mood"] = mood
                p["_audio_music_volume"] = float(vol)
                log_gate_decision(episode_stem, "audio_mood", clip_id, mv)

        enriched.append(p)

    n_dropped = len(picks) - len(enriched)
    if n_dropped:
        print(f"  [enrich] dropped {n_dropped} clip(s) for irreparable title issues")
    return enriched


# --- Orchestrator -----------------------------------------------------------

def pick_clips_from_transcript(
    transcript_path: Path,
    dry_run: bool = False,
    target_count: int = 5,
    chunk_minutes: int = 0,
) -> list[dict]:
    """Pick clips from a transcript.

    chunk_minutes (default 0 = disabled): if >0 AND the transcript is longer than
    chunk_minutes*60*1.5 seconds, splits the transcript into N windows and runs
    Claude once per window, then combines all candidates and runs them through
    Gate 1 + snap + dedup + enrichment as one batch. Necessary for full-episode
    transcripts (2hr+) where a single 25-pick Claude call misses content in the
    middle/end. Recommended: --chunk-minutes 30 for full episodes → 4 chunks ×
    25 candidates each = 100 candidates, capturing content from the FULL episode
    that may not have been included in any auto-segmented topic video.
    """
    tx = json.loads(transcript_path.read_text())
    segments = tx.get("segments", [])
    if not segments:
        return []
    topic_name = transcript_path.stem.replace("_1080p", "").replace("-", " ").title()
    stem_key = transcript_path.stem

    duration = max((s.get("end", 0) for s in segments), default=0)
    use_chunks = chunk_minutes > 0 and duration > (chunk_minutes * 60 * 1.5)

    if use_chunks:
        n_chunks = max(2, round(duration / (chunk_minutes * 60)))
        chunk_dur = duration / n_chunks
        print(f"  [chunked] {topic_name}: {duration:.0f}s ÷ {n_chunks} chunks "
              f"({chunk_dur/60:.0f} min each), {PICKS_REQUESTED} picks per chunk")

        if dry_run:
            for i in range(n_chunks):
                start = i * chunk_dur
                end = (i + 1) * chunk_dur
                chunk_segs = [s for s in segments if s["end"] >= start and s["start"] <= end]
                print(f"  [DRY chunk {i+1}/{n_chunks}] {start/60:.1f}-{end/60:.1f} min: {len(chunk_segs)} segs")
            return []

        candidates: list[dict] = []
        for i in range(n_chunks):
            start = i * chunk_dur
            end = (i + 1) * chunk_dur
            chunk_segs = [s for s in segments if s["end"] >= start and s["start"] <= end]
            if not chunk_segs:
                continue
            chunk_tx = {**tx, "segments": chunk_segs}
            chunk_blob = _format_transcript_for_prompt(chunk_tx, max_chars=120_000)
            chunk_label = f"{topic_name} (window {i+1}/{n_chunks}, {start/60:.0f}-{end/60:.0f} min)"
            try:
                cands = _call_claude(chunk_label, chunk_blob, PICKS_REQUESTED)
                print(f"  [chunk {i+1}/{n_chunks}] Claude returned {len(cands)} candidates")
                candidates.extend(cands)
            except Exception as exc:
                print(f"  [chunk {i+1}/{n_chunks}] FAILED: {exc}")
        print(f"  [chunked] {len(candidates)} total candidates from {n_chunks} chunks → Gate 1...")
    else:
        # Single-source path (used for short transcripts and topic videos)
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

    # COLD-VIEWER OPENER GATE (round 10b — 2026-05-13)
    # Sends only the first 5s of each pick to Claude WITH a ±12s context
    # window. Claude returns PASS / ADJUST (suggesting a better start_sec)
    # / REJECT. The ADJUST path FIXES bad openers instead of dropping them,
    # which is what the user asked for ("if a video starts in the middle
    # of a sentence why not just back it up to start at the right time").
    validated = _cold_opener_gate(validated, segments)

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

    for i, p in enumerate(final, 1):
        p["clip_id"] = f"{stem_key}_c{i}"
        p["source_stem"] = stem_key

    # Post-pick enrichment: title quality audit, per-clip hashtag generation,
    # adaptive audio mix mood. Runs all 3 audits per clip CONCURRENTLY.
    final = _post_pick_enrichment(final, tx)

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
    parser.add_argument("--mtime-within-days", type=int, default=0,
                        help="Only consider --batch transcripts modified within N days. "
                             "0=disabled (default). Use 7 to scope to current episode and avoid "
                             "re-picking already-published episodes.")
    parser.add_argument("--chunk-minutes", type=int, default=0,
                        help="Split long transcripts (>chunk-minutes*1.5) into N-minute windows "
                             "and pick separately from each. 0=disabled. Use 30 for 2hr+ full "
                             "episodes — produces 4x more candidates than a single 25-pick call. "
                             "Necessary when picking from FULL transcript so good moments not "
                             "captured in any auto-segmented topic still get found.")
    args = parser.parse_args()

    if not args.transcript and not args.batch:
        parser.error("pass a transcript path or --batch <dir>")

    targets: list[Path] = []
    if args.transcript:
        targets.append(Path(args.transcript).resolve())
    if args.batch:
        all_in_batch = sorted(Path(args.batch).resolve().glob("*.json"))
        if args.mtime_within_days > 0:
            import time as _time
            cutoff = _time.time() - (args.mtime_within_days * 86400)
            filtered = [p for p in all_in_batch if p.stat().st_mtime >= cutoff]
            n_skipped = len(all_in_batch) - len(filtered)
            if n_skipped:
                print(f"[scope] skipped {n_skipped} transcript(s) older than {args.mtime_within_days}d "
                      f"(prevent re-picking already-published episodes)")
            targets.extend(filtered)
        else:
            targets.extend(all_in_batch)

    CLIPS_PLAN_DIR.mkdir(parents=True, exist_ok=True)
    all_picks: list[dict] = []
    for t in targets:
        try:
            # When chunking is enabled (long full-episode transcripts), bump
            # target_count proportionally so we keep more of the additional
            # candidates the chunked path generates. 4 chunks worth of content
            # means up to ~4x as many final picks should survive.
            tc = args.target_count
            if args.chunk_minutes > 0:
                tc = max(args.target_count, args.target_count * 3)  # cap to 3x to avoid explosion
            picks = pick_clips_from_transcript(
                t, dry_run=args.dry_run, target_count=tc,
                chunk_minutes=args.chunk_minutes,
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
