#!/usr/bin/env python3
"""Generate YouTube metadata (title, description, tags) for podcast videos via Claude.

Inputs:
  - transcript JSON (from transcribe.py) — used to ground the description
  - type: "full" or "topic" (different description templates)

Output:
  data/podcast/metadata/<stem>.json = {title, description, tags, category_id, default_language}

Usage:
  python3 scripts/podcast/generate_metadata.py <transcript.json> --type full
  python3 scripts/podcast/generate_metadata.py --batch data/podcast/transcripts/ --type topic
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
EPISODE_DATE = "2026-04-14"
STORE_URL = "https://8bitlegacy.com"

SYSTEM = """You write YouTube metadata for \"The 8-Bit Legacy Podcast\", a biweekly retro-gaming
podcast run by 8-Bit Legacy (a retro + Pokemon ecommerce store at 8bitlegacy.com).

Voice: casual, knowledgeable, slightly snarky, never corporate. Hosts are three people talking
about retro games, industry news, collecting, hot takes.

Return ONLY strict JSON: {title, description, tags, category_id, default_language}.
- title: ≤100 chars, hook-first, NO clickbait "YOU WON'T BELIEVE" garbage. Think "The State Of AAA Gaming Is A Joke". For full episodes include the episode number & date.
- description: ≤5000 chars plaintext. Open with 1-2 sentence hook, then a line break, then chapter timestamps (only for full episodes — use [hh:mm:ss]), then store + socials links block (8bitlegacy.com, TikTok/IG/X = @8bitlegacy, podcast = The 8-Bit Legacy Podcast), then hashtags last line.
- tags: 10-18 lowercase tags, mix of broad ("retro gaming", "nintendo") + specific (episode topics). Comma-separated array.
- category_id: "20" (Gaming).
- default_language: "en"."""

USER_TOPIC = """Topic video — 10-15 min standalone segment.
Topic filename: {topic_name}
Transcript (first ~3000 words):

{transcript_blob}

Write the metadata."""

USER_FULL = """Full episode — 74 minutes, 7 topic segments stitched together. Recorded {ep_date}.
Topic segments in order (use for chapter timestamps):

{chapter_list}

Full transcript (first ~5000 words):

{transcript_blob}

Write the metadata. Chapter timestamps use real seconds from the transcript not filler approximations."""


def _transcript_blob(tx: dict, max_chars: int) -> str:
    out = []
    total = 0
    for seg in tx.get("segments", []):
        line = seg["text"].strip() + "\n"
        if total + len(line) > max_chars:
            break
        out.append(line)
        total += len(line)
    return "".join(out)


def generate(transcript_path: Path, kind: str, chapters: list[dict] | None = None) -> dict:
    import anthropic

    tx = json.loads(transcript_path.read_text())
    topic_name = transcript_path.stem.replace("_1080p", "").replace("-", " ").title()
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    if kind == "full":
        chapter_list = "\n".join(f"- {c['stem']}" for c in (chapters or []))
        prompt = USER_FULL.format(ep_date=EPISODE_DATE, chapter_list=chapter_list,
                                  transcript_blob=_transcript_blob(tx, 25000))
    else:
        prompt = USER_TOPIC.format(topic_name=topic_name,
                                   transcript_blob=_transcript_blob(tx, 15000))

    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        system=SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(b.text for b in resp.content if b.type == "text").strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.rsplit("```", 1)[0]
    meta = json.loads(text)
    meta.setdefault("category_id", "20")
    meta.setdefault("default_language", "en")
    return meta


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("transcript", nargs="?")
    parser.add_argument("--type", choices=["full", "topic"], default="topic")
    parser.add_argument("--batch", help="Directory of transcripts")
    args = parser.parse_args()

    METADATA_DIR.mkdir(parents=True, exist_ok=True)
    targets: list[Path] = []
    if args.transcript:
        targets.append(Path(args.transcript).resolve())
    if args.batch:
        targets.extend(sorted(Path(args.batch).resolve().glob("*.json")))

    if not targets:
        parser.error("pass a transcript path or --batch <dir>")

    for t in targets:
        try:
            meta = generate(t, args.type)
            out = METADATA_DIR / t.name
            out.write_text(json.dumps(meta, indent=2))
            print(f"[META] {t.name} → {meta['title']}")
        except Exception as exc:
            print(f"[ERROR] {t.name}: {exc}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
