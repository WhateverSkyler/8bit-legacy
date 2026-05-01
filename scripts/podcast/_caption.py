"""Shared caption + hashtag config for the podcast shorts pipeline.

Imported by:
- scripts/podcast/schedule_shorts.py (initial post scheduling)
- scripts/watcher/buffer_scheduler.py (evergreen reposts)

Single source of truth for hashtags and the title-truncation threshold so the
two paths can't drift.
"""

from __future__ import annotations

# 12 baseline tags + ≤3 topic tags = 15 max. YouTube Shorts ignores all
# hashtags on any post with >15 of them, so the cap below is a real ceiling.
DEFAULT_HASHTAGS: list[str] = [
    # Algorithm/discovery
    "#fyp", "#foryoupage", "#explorepage",
    # Retro gaming niche
    "#retrogaming", "#retrogames", "#videogames", "#gaming",
    "#nintendo", "#playstation",
    # Brand + format
    "#8bitlegacy", "#podcast", "#shorts",
]

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


def merged_hashtags(topics: list[str]) -> str:
    """Return the final space-joined hashtag string for a clip's topics.

    Combines DEFAULT_HASHTAGS + topic_tags(topics), dedupes, caps at 15.
    """
    all_tags = DEFAULT_HASHTAGS + topic_tags(topics)
    seen: set[str] = set()
    deduped: list[str] = []
    for tag in all_tags:
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
