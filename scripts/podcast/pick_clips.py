#!/usr/bin/env python3
"""Pick viral short-form moments from a podcast transcript using Claude.

Input:  data/podcast/transcripts/<stem>.json  (from transcribe.py)
Output: data/podcast/clips_plan/<stem>.json   with 4-5 entries per topic cut:
    [
      {
        "clip_id": "01-welcome-back-aaa-gaming-debate_c1",
        "source_stem": "01-welcome-back-aaa-gaming-debate_1080p",
        "start_sec": 47.3,
        "end_sec": 107.8,
        "title": "AAA Gaming Is Cooked",
        "hook": "Publishers want $80 games but refuse to ship anything worth $80.",
        "topics": ["aaa gaming", "game pricing"]
      }, ...
    ]

Usage:
    python3 scripts/podcast/pick_clips.py <transcript.json>
    python3 scripts/podcast/pick_clips.py --batch data/podcast/transcripts/
"""

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
CLIPS_PLAN_DIR = ROOT / "data" / "podcast" / "clips_plan"

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / "config" / ".env")
except ImportError:
    pass


SYSTEM_PROMPT = """You are an elite TikTok / YouTube Shorts editor who curates moments from a
long-form retro-gaming podcast (\"The 8-Bit Legacy Podcast\"). Your job is to identify 4–5
self-contained 30–75 second moments from each topic segment that would stop a scroll.

What works:
- Strong opinion delivered confidently ("Nintendo is doing X and it's insane because…")
- A surprising fact, a sharp hot take, or a hard numerical claim
- A funny beat or a shared joke that lands and gets a reaction
- A dramatic pause into a punchline
- A "tell me what you think" callout that invites comments

What doesn't work:
- Filler, "umm", tangent intros that don't pay off
- Mid-thought cuts; a clip must start clean and end on a conclusion or beat
- Generic commentary with no stakes or edge

For each pick return strict JSON: {start_sec, end_sec, title, hook, topics}.
- start_sec/end_sec match the transcript's word-level timestamps; aim for the nearest clean sentence boundary.
- title: 4-7 words, title case, no clickbait punctuation.
- hook: one sentence, first person or direct address, no hashtags.
- topics: 2-4 lowercase short tags (e.g. "nintendo", "elden ring", "game prices").
"""

USER_TEMPLATE = """Topic segment: {topic_name}
Full transcript (word-level timestamps available; segment times shown):

{transcript_blob}

Return a JSON ARRAY (no prose) of 4 to 5 clip picks in the format described."""


def _format_transcript_for_prompt(tx: dict, max_chars: int = 60000) -> str:
    lines = []
    total = 0
    for seg in tx.get("segments", []):
        start = seg["start"]
        text = seg["text"]
        line = f"[{start:7.2f}s] {text}\n"
        if total + len(line) > max_chars:
            break
        lines.append(line)
        total += len(line)
    return "".join(lines)


def pick_clips_from_transcript(transcript_path: Path, dry_run: bool = False) -> list[dict]:
    import anthropic

    tx = json.loads(transcript_path.read_text())
    topic_name = transcript_path.stem.replace("_1080p", "").replace("-", " ").title()
    transcript_blob = _format_transcript_for_prompt(tx)

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    if dry_run:
        print(f"[DRY] would send {len(transcript_blob)} chars to Claude for {topic_name}")
        return []

    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": USER_TEMPLATE.format(topic_name=topic_name, transcript_blob=transcript_blob)}],
    )
    text = "".join(b.text for b in resp.content if b.type == "text").strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.rsplit("```", 1)[0]
    picks = json.loads(text)
    stem_key = transcript_path.stem  # e.g. "01-welcome-back-aaa-gaming-debate_1080p"
    for i, p in enumerate(picks, 1):
        p["clip_id"] = f"{stem_key}_c{i}"
        p["source_stem"] = stem_key
    return picks


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("transcript", nargs="?", help="Path to a transcript JSON")
    parser.add_argument("--batch", help="Directory of transcripts to process")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not args.transcript and not args.batch:
        parser.error("pass a transcript path or --batch <dir>")

    targets: list[Path] = []
    if args.transcript:
        targets.append(Path(args.transcript).resolve())
    if args.batch:
        targets.extend(sorted(Path(args.batch).resolve().glob("*.json")))

    CLIPS_PLAN_DIR.mkdir(parents=True, exist_ok=True)
    all_picks = []
    for t in targets:
        try:
            picks = pick_clips_from_transcript(t, dry_run=args.dry_run)
            out = CLIPS_PLAN_DIR / t.name
            out.write_text(json.dumps(picks, indent=2))
            print(f"[PICKED] {len(picks)} clips from {t.name} → {out.name}")
            all_picks.extend(picks)
        except Exception as exc:
            print(f"[ERROR] {t.name}: {exc}", file=sys.stderr)

    combined = CLIPS_PLAN_DIR / "_all.json"
    combined.write_text(json.dumps(all_picks, indent=2))
    print(f"\n[TOTAL] {len(all_picks)} clips across {len(targets)} topics → {combined}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
