"""Shared caption + hashtag config for the podcast shorts pipeline.

Imported by:
- scripts/podcast/schedule_shorts.py (initial post scheduling)
- scripts/watcher/buffer_scheduler.py (evergreen reposts)

Single source of truth for hashtags and the title-truncation threshold so the
two paths can't drift.
"""

from __future__ import annotations

# Algorithm + brand baseline that goes on every short. The LLM-driven per-clip
# hashtags (set by pick_clips._post_pick_enrichment as `_llm_hashtags`) fill
# the rest up to MAX_TOTAL_HASHTAGS=15. YouTube Shorts ignores all hashtags on
# any post with >15 of them, so the cap is a real ceiling.
BASELINE_HASHTAGS: list[str] = [
    # Algorithm/discovery (always include — required by feedback memory)
    "#fyp", "#foryoupage", "#explorepage",
    # Brand + format
    "#8bitlegacy", "#shorts",
]

# Fallback set used ONLY when LLM hashtag generation fails or is unavailable.
# Replicates the prior fixed list. Once the LLM pipeline is reliable in prod,
# the fallback gets exercised much less often.
FALLBACK_HASHTAGS: list[str] = [
    "#retrogaming", "#retrogames", "#videogames", "#gaming",
    "#nintendo", "#playstation", "#podcast",
]

# Kept for back-compat with any caller that imports DEFAULT_HASHTAGS directly.
DEFAULT_HASHTAGS = BASELINE_HASHTAGS + FALLBACK_HASHTAGS

MAX_TOTAL_HASHTAGS = 15
TITLE_HARD_MAX_CHARS = 70  # mirrors pick_clips.TITLE_HARD_MAX_CHARS


def topic_tags(topics: list[str], limit: int = 3) -> list[str]:
    """Convert topic strings to hashtags. Lowercases, strips spaces/dashes, dedupes."""
    out: list[str] = []
    seen: set[str] = set()
    for t in (topics or [])[:limit]:
        cleaned = t.replace(" ", "").replace("-", "").lower()
        if not cleaned:
            continue
        tag = f"#{cleaned}"
        if tag not in seen:
            seen.add(tag)
            out.append(tag)
    return out


def merged_hashtags(topics: list[str], llm_tags: list[str] | None = None) -> str:
    """Return the final space-joined hashtag string for a clip's topics.

    Priority order (caller controls):
      1. BASELINE_HASHTAGS (always present — algorithm + brand)
      2. llm_tags (from pick_clips._post_pick_enrichment, per-clip relevance)
      3. topic_tags(topics) (fallback if llm_tags missing/short)
      4. FALLBACK_HASHTAGS (filler if still short)

    Capped at MAX_TOTAL_HASHTAGS (15). Deduped case-insensitively.

    `llm_tags` defaults to None to preserve the old single-arg call signature.
    Callers pass `spec.get("_llm_hashtags")` to opt into per-clip relevance.
    """
    pool = list(BASELINE_HASHTAGS)
    if llm_tags:
        pool.extend(llm_tags)
    pool.extend(topic_tags(topics))
    pool.extend(FALLBACK_HASHTAGS)
    seen: set[str] = set()
    deduped: list[str] = []
    for tag in pool:
        key = tag.lower()
        if key not in seen:
            seen.add(key)
            deduped.append(tag)
    return " ".join(deduped[:MAX_TOTAL_HASHTAGS])


def truncate_title(title: str) -> tuple[str, bool]:
    """Truncate a title to TITLE_HARD_MAX_CHARS at a word boundary.

    Returns (truncated_title, was_truncated).
    """
    title = (title or "").strip()
    if len(title) <= TITLE_HARD_MAX_CHARS:
        return title, False
    head = title[:TITLE_HARD_MAX_CHARS].rsplit(" ", 1)[0]
    return head + "…", True
