"""Structural verification of the model's picks. NO editorial judgment.

Resolves breakpoint indices to seconds, enforces the duration band,
checks EOF safety, dedupes overlapping picks, normalizes the title, and
assembles the final ClipSpec dict that matches render_clip.py's contract.

Anything dropped here is logged with a structured reason. We never reroll
and we never substitute editorial decisions — if a pick is structurally
broken, the right answer is to drop it and let the next episode have more.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Iterable

from .editorial_call import ClipPick
from .silence_breakpoints import Breakpoint
from .topic_context import TopicContext

# Length policy — locked from plan §Hard Requirements
DURATION_FLOOR_SEC = 15.0
DURATION_CEILING_SEC = 90.0

# Mood → music volume mapping (must stay inside renderer's 0.08-0.14 band)
_MOOD_TO_VOLUME = {
    "chill":      0.10,
    "reflective": 0.10,
    "funny":      0.12,
    "hopeful":    0.12,
    "hype":       0.14,
    "heated":     0.14,
}

# IoU dedup threshold
_DEDUP_IOU = 0.50

# All four platforms accept clips ≤90s — see plan §Hard Requirements #7
_ALL_PLATFORMS = ["youtube_shorts", "instagram_reels", "tiktok", "facebook_reels"]


@dataclass
class DroppedPick:
    pick: ClipPick
    reason: str


@dataclass
class VerifyOutput:
    specs: list[dict]
    dropped: list[DroppedPick] = field(default_factory=list)


def _truncate_on_word_boundary(text: str, max_chars: int) -> str:
    """Trim title to <= max_chars without breaking a word in the middle."""
    text = text.strip()
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars]
    if " " in truncated:
        truncated = truncated.rsplit(" ", 1)[0]
    return truncated.rstrip(",.;:- ")


def _iou(a_start: float, a_end: float, b_start: float, b_end: float) -> float:
    inter = max(0.0, min(a_end, b_end) - max(a_start, b_start))
    union = max(a_end, b_end) - min(a_start, b_start)
    return inter / union if union > 0 else 0.0


def _dedup_overlapping(specs: list[dict], iou_threshold: float) -> list[dict]:
    """Greedy: sort by confidence desc, keep, drop later picks that overlap."""
    by_conf = sorted(specs, key=lambda s: s.get("model_confidence", 0.0), reverse=True)
    kept: list[dict] = []
    for s in by_conf:
        overlaps = False
        for k in kept:
            if _iou(s["start_sec"], s["end_sec"], k["start_sec"], k["end_sec"]) >= iou_threshold:
                overlaps = True
                break
        if not overlaps:
            kept.append(s)
    # Restore chronological order for downstream renderer / dashboard
    return sorted(kept, key=lambda s: s["start_sec"])


def verify(picks: Iterable[ClipPick],
           breakpoints: list[Breakpoint],
           topic_context: TopicContext,
           source_stem: str,
           *,
           model: str,
           prompt_version: str) -> VerifyOutput:
    """Build ClipSpec dicts from raw picks. Drop anything structurally broken."""
    output = VerifyOutput(specs=[])
    n_breakpoints = len(breakpoints)
    topic_duration = topic_context.duration_sec
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    for pick in picks:
        # Index validity
        if not (0 <= pick.start_b < pick.end_b < n_breakpoints):
            output.dropped.append(DroppedPick(pick, f"invalid_index:{pick.start_b},{pick.end_b}"))
            continue

        bp_start = breakpoints[pick.start_b]
        bp_end = breakpoints[pick.end_b]

        # Resolve to seconds: clip starts AFTER the start silence (-50ms safety to
        # not bite the first phoneme) and ends BEFORE the end silence (+50ms safety).
        start_sec = max(0.0, bp_start.end - 0.05)
        end_sec = bp_end.start + 0.05
        duration = end_sec - start_sec

        # Duration band
        if not (DURATION_FLOOR_SEC <= duration <= DURATION_CEILING_SEC):
            output.dropped.append(DroppedPick(pick, f"duration_out_of_band:{duration:.1f}s"))
            continue

        # EOF safety
        if topic_duration > 0 and end_sec > topic_duration + 0.5:
            output.dropped.append(DroppedPick(pick, f"past_eof:end={end_sec:.1f}>topic={topic_duration:.1f}"))
            continue

        # Title normalize
        title = _truncate_on_word_boundary(pick.title, max_chars=60)

        # Music volume from mood
        music_volume = _MOOD_TO_VOLUME.get(pick.mood, 0.12)

        spec = {
            # Renderer-required (hard-indexed)
            "clip_id":     f"{source_stem}_c0",   # placeholder; real id assigned post-dedup
            "source_stem": source_stem,
            "start_sec":   round(start_sec, 2),
            "end_sec":     round(end_sec, 2),

            # Renderer-optional (.get-read)
            "title":               title,
            "_audio_mood":         pick.mood,
            "_audio_music_volume": music_volume,

            # Spec metadata (analysis / dashboard / A/B)
            "duration_sec":         round(duration, 2),
            "platform_eligibility": list(_ALL_PLATFORMS),
            "hook_line":            pick.hook_line,
            "payoff_summary":       pick.payoff_summary,
            "single_topic_arc":     pick.single_topic_confirmation,
            "model_confidence":     pick.confidence,
            "breakpoint_pair":      [pick.start_b, pick.end_b],
            "silence_at_start": {
                "start": round(bp_start.start, 2),
                "end":   round(bp_start.end, 2),
                "duration": round(bp_start.duration, 2),
            },
            "silence_at_end": {
                "start": round(bp_end.start, 2),
                "end":   round(bp_end.end, 2),
                "duration": round(bp_end.duration, 2),
            },
            "topic_slug":     topic_context.slug,
            "model":          model,
            "prompt_version": prompt_version,
            "generated_at":   now_iso,
        }
        output.specs.append(spec)

    # Dedup overlapping picks (greedy by confidence, then re-sort chronologically)
    output.specs = _dedup_overlapping(output.specs, _DEDUP_IOU)

    # Final clip_id assignment now that order is locked
    for i, s in enumerate(output.specs, start=1):
        s["clip_id"] = f"{source_stem}_c{i}"

    return output
