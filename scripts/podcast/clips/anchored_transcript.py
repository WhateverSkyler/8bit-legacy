"""Build the anchored transcript fed to Claude.

Walks whisperX words chronologically and inserts breakpoint markers `[Bi:T/D]`
exactly where real audio silences occurred. Strips whisperX punctuation
from word text — we are explicitly ignoring it as a structural signal.

The resulting text reads as continuous prose with rhythm markers showing
where the audio actually pauses. Claude can read it naturally and pick a
start/end breakpoint by index without ever needing to see a separate
timestamp table.

A second helper (`build_breakpoint_table`) emits a clean numbered table
appended at the end of the prompt as a sanity-check lookup.
"""
from __future__ import annotations

import re

from .silence_breakpoints import Breakpoint

# Punctuation we strip from word text (transcript-side noise we ignore)
_PUNCT_RE = re.compile(r"[.,!?;:]+")


def _flatten_words(transcript: dict) -> list[dict]:
    """Pull every word from every segment into one chronological list.

    Each returned word dict: {start, end, word}. Words missing timestamps
    are skipped (rare; whisperX can produce them on overlapping speech).
    """
    out: list[dict] = []
    for seg in transcript.get("segments", []):
        for w in seg.get("words", []) or []:
            if "start" not in w or "end" not in w:
                continue
            out.append(w)
    out.sort(key=lambda w: w["start"])
    return out


def _clean_word(text: str) -> str:
    """Strip transcript punctuation; preserve the leading space whisperX uses
    as inter-word separator."""
    if not text:
        return ""
    leading_space = " " if text.startswith(" ") else ""
    stripped = _PUNCT_RE.sub("", text.strip())
    return leading_space + stripped if stripped else ""


def build_anchored_transcript(transcript: dict, breakpoints: list[Breakpoint]) -> str:
    """Interleave words and `[Bi:T/D]` markers.

    Marker insertion rule: a breakpoint Bi is emitted just BEFORE the first
    word whose `start` is at or after `Bi.end`. This puts the marker exactly
    where the silence finished and speech resumed — the natural reading
    position.

    Format: `[B3:18.50/1.42]` means breakpoint index 3, midpoint 18.50s,
    silence duration 1.42s.
    """
    words = _flatten_words(transcript)
    if not words:
        return ""

    bp_iter = iter(breakpoints)
    next_bp: Breakpoint | None = next(bp_iter, None)

    parts: list[str] = []
    for w in words:
        # Emit any breakpoints that finished before this word starts.
        while next_bp is not None and next_bp.end <= w["start"] + 1e-6:
            parts.append(f" [B{next_bp.idx}:{next_bp.mid_sec:.2f}/{next_bp.duration:.2f}]")
            next_bp = next(bp_iter, None)
        parts.append(_clean_word(w["word"]))

    # Trailing breakpoints (silence at the very end of the topic file).
    while next_bp is not None:
        parts.append(f" [B{next_bp.idx}:{next_bp.mid_sec:.2f}/{next_bp.duration:.2f}]")
        next_bp = next(bp_iter, None)

    text = "".join(parts).strip()
    # Collapse any double spaces introduced by adjacent emissions.
    return re.sub(r"\s+", " ", text)


def build_breakpoint_table(breakpoints: list[Breakpoint]) -> str:
    """Numbered table appended at end of prompt for sanity lookup.

    Format mirrors the inline marker format so the model reads it as a
    direct cross-reference:
        B0   t=0.62   d=0.51
        B1   t=11.84  d=0.78
    """
    if not breakpoints:
        return "(no breakpoints — topic too quiet or too short)"
    lines = [f"B{bp.idx:<3} t={bp.mid_sec:>7.2f}  d={bp.duration:.2f}" for bp in breakpoints]
    return "\n".join(lines)


def estimate_input_tokens(anchored_text: str, table_text: str,
                          system_prompt_tokens: int = 700,
                          context_tokens: int = 250) -> int:
    """Rough token estimate (chars/4 heuristic) for cost forecasting."""
    body_chars = len(anchored_text) + len(table_text)
    return system_prompt_tokens + context_tokens + (body_chars // 4)
