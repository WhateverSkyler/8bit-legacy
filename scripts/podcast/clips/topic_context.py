"""Load topic context for the editorial pass.

The upstream topic-segmentation step writes `data/podcast/<EpisodeDir>/auto_segment_plan.json`
containing each topic's slug, title_hint, thesis, and subtopics. We feed
that into Claude's prompt so it has the same understanding of the topic
that the segmenter had — the model should not have to re-derive it from
the transcript when better context is sitting on disk.

If the plan is missing or doesn't contain this slug, we return an empty
context. The system prompt instructs the model to fall back to inferring
the topic from the transcript itself, so quality degrades gracefully.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TopicContext:
    slug: str                           # e.g. "adult-gaming-and-handhelds"
    title_hint: str                     # human-readable label
    thesis: str                         # one-paragraph topic summary
    subtopics: tuple[str, ...]          # bulleted conversational beats
    duration_sec: float                 # length of the topic file in seconds

    @property
    def is_empty(self) -> bool:
        return not (self.thesis or self.title_hint or self.subtopics)

    def render_for_prompt(self) -> str:
        """Format the context block as it appears at the top of the user message."""
        if self.is_empty:
            return (
                f"slug: {self.slug}\n"
                f"title_hint: (no upstream plan available — infer from transcript)\n"
                f"thesis: (none)\n"
                f"subtopics: (none)\n"
                f"duration: {self.duration_sec:.1f} seconds"
            )
        bullets = "\n".join(f"  - {s}" for s in self.subtopics) if self.subtopics else "  (none)"
        return (
            f"slug: {self.slug}\n"
            f"title_hint: {self.title_hint}\n"
            f"thesis: {self.thesis}\n"
            f"subtopics:\n{bullets}\n"
            f"duration: {self.duration_sec:.1f} seconds"
        )


def slug_from_transcript_stem(stem: str) -> str:
    """Pipeline convention: stems look like '02-adult-gaming-and-handhelds_1080p'.

    Strip the leading 'NN-' index and the trailing '_1080p' / '_auto_1080p'
    quality suffix to recover the slug used in auto_segment_plan.json.
    """
    name = stem
    # Strip leading "NN-" if present
    if len(name) >= 3 and name[0:2].isdigit() and name[2] == "-":
        name = name[3:]
    # Strip trailing quality suffix
    for suffix in ("_auto_1080p", "_1080p"):
        if name.endswith(suffix):
            name = name[: -len(suffix)]
            break
    return name


def _find_episode_plan(transcript_path: Path, episode_dir: Path | None) -> Path | None:
    """Locate the auto_segment_plan.json for the episode this transcript belongs to.

    Lookup order:
      1. Explicit --episode-dir argument
      2. Any data/podcast/<dir>/auto_segment_plan.json that lists this slug
    """
    if episode_dir:
        candidate = episode_dir / "auto_segment_plan.json"
        if candidate.exists():
            return candidate

    repo_root = transcript_path.resolve().parent.parent.parent.parent
    podcast_dir = repo_root / "data" / "podcast"
    if not podcast_dir.exists():
        return None

    target_slug = slug_from_transcript_stem(transcript_path.stem)
    for plan in sorted(podcast_dir.glob("Episode_*/auto_segment_plan.json")):
        try:
            data = json.loads(plan.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        for entry in data.get("accepted", []) + data.get("dropped_sub_floor", []):
            if entry.get("slug") == target_slug:
                return plan
    return None


def load_topic_context(transcript_path: Path,
                       transcript: dict,
                       episode_dir: Path | None = None) -> TopicContext:
    """Build a TopicContext for one transcript file.

    Always returns a TopicContext — never raises on missing plan. Use
    `.is_empty` to check whether the upstream plan provided meaningful
    context.
    """
    slug = slug_from_transcript_stem(transcript_path.stem)
    duration = float(transcript.get("duration_sec") or
                     max((s.get("end", 0) for s in transcript.get("segments", [])), default=0.0))

    plan_path = _find_episode_plan(transcript_path, episode_dir)
    if not plan_path:
        return TopicContext(slug=slug, title_hint="", thesis="", subtopics=(), duration_sec=duration)

    try:
        plan = json.loads(plan_path.read_text())
    except (OSError, json.JSONDecodeError):
        return TopicContext(slug=slug, title_hint="", thesis="", subtopics=(), duration_sec=duration)

    for entry in plan.get("accepted", []) + plan.get("dropped_sub_floor", []):
        if entry.get("slug") != slug:
            continue
        return TopicContext(
            slug=slug,
            title_hint=entry.get("title_hint") or "",
            thesis=entry.get("thesis") or "",
            subtopics=tuple(entry.get("subtopics") or ()),
            duration_sec=duration,
        )

    return TopicContext(slug=slug, title_hint="", thesis="", subtopics=(), duration_sec=duration)
