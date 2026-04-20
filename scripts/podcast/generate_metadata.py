#!/usr/bin/env python3
"""Generate YouTube metadata (title, description, tags) for podcast videos via Claude.

Mirrors the observed style of the live 8-Bit Legacy YouTube channel — see
`reference_youtube_style.md` in memory for the full spec.

Enhancements over v1:
- Stronger title prompt — YT-algorithm-aware AND accurate; picks from 4 framing
  archetypes (hot take / question / comparison / reaction) informed by actual
  channel precedent (#2-#5)
- Description has a 1-2 sentence HOOK above the boilerplate (first 125 chars =
  above-fold on YT; old version had no hook and was pure boilerplate)
- Full-episode descriptions include CHAPTER TIMESTAMPS derived from transcript
  segment boundaries. Topic videos get a 2-3 bullet summary instead.
- "Connect with us" boilerplate is baked in Python (not Claude) — always
  consistent brand identity, saves tokens.
- Tags field: 10-18 comma-separated, mix of broad/franchise/specific, capped at 500 chars.

Inputs:
  - transcript JSON (from transcribe.py) — used to ground hook + chapters
  - type: "full" or "topic"
  - episode-number (for full episodes) — next one is #6 as of 2026-04-20

Output:
  data/podcast/metadata/<stem>.json = {title, description, tags, category_id, default_language}

Usage:
  python3 scripts/podcast/generate_metadata.py <transcript.json> --type topic
  python3 scripts/podcast/generate_metadata.py --batch data/podcast/transcripts/ --type topic
  python3 scripts/podcast/generate_metadata.py <full-transcript.json> --type full --episode-number 6
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
METADATA_DIR = ROOT / "data" / "podcast" / "metadata"

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / "config" / ".env")
except ImportError:
    pass


# --- Brand constants (verbatim match to live channel; see reference_youtube_style.md) ---

CONNECT_BOILERPLATE = """Connect with us:
🌐 Shop Retro Games – Lowest prices available! http://8bitlegacy.com
📘 Facebook: https://www.facebook.com/8bitlegacyco
📸 Instagram: https://www.instagram.com/8bitlegacyretro
🎥 TikTok: https://www.tiktok.com/@8bitlegacy.com

Thank you for joining us for this discussion. Be sure to subscribe for future episodes of The 8-Bit Podcast."""

# Base hashtags that appear on every video. Claude adds episode-specific ones.
BASE_HASHTAGS = ["#GamingPodcast", "#RetroGaming", "#The8BitPodcast"]

BRAND_SUFFIX_TOPIC = " | The 8-Bit Podcast"
BRAND_SUFFIX_FULL = " | The 8-Bit Podcast #{n}"


# --- Claude prompts ---------------------------------------------------------

SYSTEM = """You write YouTube metadata for "The 8-Bit Podcast" — biweekly retro gaming show hosted by three people, run by 8-Bit Legacy (retro games + Pokemon card ecommerce store at 8bitlegacy.com).

Channel: @8bitlegacyretro. Voice: casual, knowledgeable, slightly confrontational, never corporate.

YOUR GOAL has two pillars, BOTH of equal weight:
1. **Accuracy** — title must honestly represent what the video is actually about. No bait, no misleading framing. A viewer who clicks should get what the title promised.
2. **YouTube algorithm** — title must be searchable + scroll-stopping. Front-load the hook keyword (first 50 chars carry the most algo weight). Match the channel's existing style so the channel reads as a coherent brand.

## Title style — MIRROR the existing channel

Observed title formulas from past episodes (these are the house style, not my suggestions):
- `Our HONEST Thoughts On The Nintendo Switch 2`
- `Should Xbox Drop Out Of The Console War?`
- `NEW OKAMI SEQUEL?!?!?`
- `Elon CHEATING in Path of Exile 2???`
- `Are GTA Games BAD???`
- `Mario Kart VS. Mario Party, Which is the BETTER PARTY Game?`
- `The Console War Is OVER`
- `Ranking The Most Popular Games of All Time`

Pick ONE framing archetype that fits the content:
- HOT TAKE ("The X Is OVER", "Publishers Want Too Much")
- QUESTION ("Should X Do Y?", "Is X Actually BAD?")
- COMPARISON ("X VS Y", "X or Y, Which Wins?")
- REACTION ("Nintendo Switch 2 Reveal Thoughts", "NEW X ANNOUNCED?!?")
- STRONG CLAIM ("Ranking X", "What We Got Wrong About X")

Rules:
- 45-70 chars for the HEAD (do NOT include the " | The 8-Bit Podcast" suffix — the Python wrapper adds it)
- Title case. Selective ALL CAPS on 1-3 emphasis words.
- Optional trailing `?`, `??`, `???`, `?!?` — up to 3 repeated chars max — for questions or reactions.
- NO emojis, NO "you won't believe", NO generic "episode discussion".
- Front-load the most searchable/interesting word.

## Description structure

Return these FIELDS separately (Python assembles the final description):
- `hook`: 1-2 sentences, ≤200 chars, that directly tells someone clicking what they're about to watch. This is what YT shows above the "show more" fold. MUST accurately summarize the content. Write in the casual/confrontational voice.
- `chapters` (ONLY for full episodes): list of `{time_sec, title}`. Use real segment boundaries from the transcript — take the start time of each topic section. 5-8 chapters total, even spacing.
- `summary_bullets` (ONLY for topic videos): list of 2-3 short bullets (each ≤80 chars) describing what's discussed. Bullet form, no lead-in.
- `episode_hashtags`: 3-5 hashtags specific to this video's topics (e.g. `#Nintendo`, `#SwitchReveal`). Title case, NO spaces. These get appended to the base `#GamingPodcast #RetroGaming #The8BitPodcast`.

## Tags (YouTube's hidden keyword field)

Return a `tags` field — 10-18 items, comma-separated in a single string. Cap the total string length at 500 chars.
- First 3 tags are highest-weight — put the most important broad terms there ("retro gaming", "video game podcast", etc.)
- Middle: franchise/console/game-specific names discussed
- End: long-tail specifics, current year (2026), current month if content is timely
- Lowercase preferred; multi-word tags use spaces

## Output — STRICT JSON only

Return exactly:
```
{
  "title_head": "...",
  "hook": "...",
  "chapters": [{"time_sec": 0, "title": "..."}, ...],    // full only, omit for topic
  "summary_bullets": ["...", "..."],                     // topic only, omit for full
  "episode_hashtags": ["#...", "#..."],
  "tags": "comma,separated,tag,list"
}
```

No prose, no explanation, no markdown fences outside the JSON."""


USER_TOPIC = """TOPIC VIDEO — 2-16 min standalone segment from a full episode.

Topic title hint from filename: {topic_name}

Transcript (first ~6000 words):

{transcript_blob}

Write the metadata. `title_head` is the title BEFORE the " | The 8-Bit Podcast" suffix (which the wrapper appends). Include `summary_bullets` (NOT chapters)."""


USER_FULL = """FULL EPISODE #{ep_number} — long-form conversation stitched from multiple topic segments.

Recorded {ep_date}. The topic segments in order (use the timing/names for chapter timestamps):

{chapter_list}

Full transcript (first ~10000 words):

{transcript_blob}

Write the metadata. `title_head` is the title BEFORE the " | The 8-Bit Podcast #{ep_number}" suffix. Include `chapters` (NOT summary_bullets). Each chapter's `time_sec` MUST be the real segment start in seconds — use the times provided above, NOT rounded approximations."""


# --- Helpers ---------------------------------------------------------------

def _format_hhmmss(sec: float) -> str:
    s = int(sec)
    h = s // 3600
    m = (s % 3600) // 60
    s = s % 60
    if h:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def _transcript_blob(tx: dict, max_chars: int) -> str:
    out: list[str] = []
    total = 0
    for seg in tx.get("segments", []):
        line = f"[{seg['start']:7.2f}s] {seg['text'].strip()}\n"
        if total + len(line) > max_chars:
            break
        out.append(line)
        total += len(line)
    return "".join(out)


def _assemble_description(meta: dict, kind: str) -> str:
    hook = (meta.get("hook") or "").strip()

    parts: list[str] = []
    if hook:
        parts.append(hook)
        parts.append("")  # blank line

    if kind == "full":
        chapters = meta.get("chapters") or []
        if chapters:
            parts.append("Chapters:")
            for ch in chapters:
                ts = _format_hhmmss(ch.get("time_sec", 0))
                parts.append(f"{ts} {ch.get('title', '').strip()}")
            parts.append("")
    else:
        bullets = meta.get("summary_bullets") or []
        for b in bullets:
            b = b.strip()
            if b:
                parts.append(f"• {b}")
        if bullets:
            parts.append("")

    parts.append(CONNECT_BOILERPLATE)
    parts.append("")

    # Hashtags: base + episode-specific, deduped
    ep_tags = meta.get("episode_hashtags") or []
    seen: set[str] = set()
    merged: list[str] = []
    for tag in BASE_HASHTAGS + ep_tags:
        t = tag.strip()
        if not t.startswith("#"):
            t = "#" + t
        k = t.lower()
        if k not in seen:
            seen.add(k)
            merged.append(t)
    parts.append(" ".join(merged))

    full = "\n".join(parts).rstrip()
    # YT description cap is 5000 chars
    return full[:5000]


def _assemble_title(title_head: str, kind: str, episode_number: int | None) -> str:
    head = (title_head or "").strip().rstrip("|- :").strip()
    if kind == "full":
        if episode_number is None:
            episode_number = 6  # fallback — next after #5
        suffix = BRAND_SUFFIX_FULL.format(n=episode_number)
    else:
        suffix = BRAND_SUFFIX_TOPIC
    # YouTube hard limit 100 chars; trim head if necessary
    max_head = 100 - len(suffix)
    if len(head) > max_head:
        head = head[: max_head - 1].rstrip() + "…"
    return head + suffix


def _trim_tags(tags: str, cap: int = 500) -> str:
    tags = (tags or "").strip()
    if len(tags) <= cap:
        return tags
    # Trim whole tag entries until under cap
    parts = [t.strip() for t in tags.split(",") if t.strip()]
    while parts and len(", ".join(parts)) > cap:
        parts.pop()
    return ", ".join(parts)


# --- Main ------------------------------------------------------------------

def generate(
    transcript_path: Path,
    kind: str,
    chapters_hint: list[dict] | None = None,
    episode_number: int | None = None,
    episode_date: str = "2026-04-14",
) -> dict:
    import anthropic

    tx = json.loads(transcript_path.read_text())
    topic_name = transcript_path.stem.replace("_1080p", "").replace("-", " ").title()
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    if kind == "full":
        chapter_list = "\n".join(
            f"- {c.get('stem', '')} (segment start ~{c.get('start_sec', 0):.0f}s)"
            for c in (chapters_hint or [])
        )
        prompt = USER_FULL.format(
            ep_number=episode_number or 6,
            ep_date=episode_date,
            chapter_list=chapter_list or "(no chapter hints provided — derive from transcript topic shifts)",
            transcript_blob=_transcript_blob(tx, 40000),
        )
    else:
        prompt = USER_TOPIC.format(
            topic_name=topic_name,
            transcript_blob=_transcript_blob(tx, 30000),
        )

    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=3000,
        system=SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(b.text for b in resp.content if b.type == "text").strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.rsplit("```", 1)[0]
    raw = json.loads(text)

    title = _assemble_title(raw.get("title_head", ""), kind, episode_number)
    description = _assemble_description(raw, kind)
    tags = _trim_tags(raw.get("tags", ""))

    return {
        "title": title,
        "description": description,
        "tags": tags,
        "category_id": "20",           # Gaming
        "default_language": "en",
        # Preserve Claude's raw fields for debugging / re-assembly
        "_raw": raw,
        "_kind": kind,
        "_episode_number": episode_number,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("transcript", nargs="?", help="Path to transcript JSON")
    parser.add_argument("--type", choices=["full", "topic"], default="topic")
    parser.add_argument("--batch", help="Directory of transcripts to process")
    parser.add_argument("--episode-number", type=int, help="Episode number (full only; next is 6)")
    parser.add_argument("--episode-date", default="2026-04-14", help="Recorded date YYYY-MM-DD")
    args = parser.parse_args()

    METADATA_DIR.mkdir(parents=True, exist_ok=True)
    targets: list[Path] = []
    if args.transcript:
        targets.append(Path(args.transcript).resolve())
    if args.batch:
        targets.extend(sorted(Path(args.batch).resolve().glob("*.json")))

    if not targets:
        parser.error("pass a transcript path or --batch <dir>")

    # For full-episode batch (unusual — typically 1 full ep at a time) pass chapters_hint
    # from other transcripts in the batch. For topic batch, no chapter hint needed.
    chapters_hint: list[dict] = []
    if args.type == "full" and len(targets) > 1:
        # Heuristic: non-full transcripts in batch become chapter hints for the full one
        for t in targets:
            if "full" not in t.stem.lower():
                try:
                    tx = json.loads(t.read_text())
                    chapters_hint.append({
                        "stem": t.stem,
                        "start_sec": tx.get("segments", [{}])[0].get("start", 0),
                    })
                except (OSError, json.JSONDecodeError):
                    pass

    for t in targets:
        try:
            meta = generate(
                t,
                kind=args.type,
                chapters_hint=chapters_hint if args.type == "full" else None,
                episode_number=args.episode_number,
                episode_date=args.episode_date,
            )
            out = METADATA_DIR / t.name
            out.write_text(json.dumps(meta, indent=2))
            print(f"[META] {t.name} → {meta['title']}")
        except Exception as exc:
            print(f"[ERROR] {t.name}: {exc}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
