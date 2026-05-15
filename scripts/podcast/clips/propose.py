"""Lightweight clip-proposal generator.

Per topic transcript, ONE Sonnet call asking for 15-30 candidate moments —
NO filter gauntlet, NO aggressive rejection. The user is the final filter
in the review UI; this stage's job is just to surface every plausibly
interesting moment so the user has good starting material.

Output JSON shape (data/podcast/proposals/<stem>.json):
{
  "source_stem": "...",
  "topic_slug": "...",
  "title_hint": "...",
  "duration_sec": 612.4,
  "model": "claude-sonnet-4-6",
  "generated_at": "...",
  "proposals": [
    {
      "id": "p1",
      "start_sec": 12.5,
      "end_sec": 47.3,
      "duration_sec": 34.8,
      "suggested_title": "...",
      "why": "...",
      "vibe": "hype" | "chill" | "reflective" | "funny" | "heated" | "hopeful"
    },
    ...
  ]
}
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import anthropic

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
TRANSCRIPTS_DIR = REPO_ROOT / "data" / "podcast" / "transcripts"
PROPOSALS_DIR = REPO_ROOT / "data" / "podcast" / "proposals"

SONNET_MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """You are scouting interesting moments in a podcast for a human editor to review.

Your job: read this topic transcript and mark every moment that COULD make a good
short-form video clip (TikTok/Reels/Shorts). Be generous — the user will review
your suggestions in an editor and adjust the boundaries. Your suggestions are a
starting point, not a final decision.

WHAT TO MARK
- Hot takes, strong opinions, confident claims
- Specific numbers, names, dates the audience will recognize
- Stories with a setup and payoff, even rough ones
- Surprising facts, controversial statements
- Moments that make a point about something topical (gaming industry, prices, drama)
- Funny exchanges, callouts, or quotable lines
- Anywhere the energy spikes — speakers getting heated, excited, animated

DO NOT FILTER too aggressively. If you're unsure, INCLUDE it. The user will decide.

LENGTH GUIDANCE (soft, not hard)
- Most picks should land roughly 30-90 seconds
- Slightly longer is OK if the moment genuinely needs it (the user can trim it)
- Slightly shorter is OK for one-line bangers (the user can extend it)
- Don't worry about exact boundaries — pick approximate start/end and the user
  will drag handles to fine-tune

QUANTITY
Aim for 15-30 proposals per topic. If the topic genuinely has fewer good moments,
return fewer. If it has 40, return 40. Don't pad and don't cap.

OUTPUT
Call the submit_proposals tool. For each proposal:
- start_sec, end_sec: approximate timestamps in this topic file
- suggested_title: punchy, 3-8 words, what the user might burn into the video
- why: one sentence — what makes this moment work
- vibe: hype | chill | reflective | funny | heated | hopeful (drives music)
"""

SUBMIT_PROPOSALS_TOOL = {
    "name": "submit_proposals",
    "description": "Submit your clip proposals. Aim for 15-30 candidates per topic.",
    "input_schema": {
        "type": "object",
        "required": ["proposals"],
        "properties": {
            "proposals": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["start_sec", "end_sec", "suggested_title", "why", "vibe"],
                    "properties": {
                        "start_sec": {"type": "number", "minimum": 0},
                        "end_sec": {"type": "number", "minimum": 0},
                        "suggested_title": {"type": "string", "maxLength": 80},
                        "why": {"type": "string"},
                        "vibe": {
                            "type": "string",
                            "enum": ["hype", "chill", "reflective", "funny", "heated", "hopeful"],
                        },
                    },
                },
            }
        },
    },
}


def _format_transcript(transcript: dict, max_chars: int = 80_000) -> str:
    """Render the transcript as one line per word run, with timestamps every ~5s.

    Format: ``[12.34s] welcome back to the show this week we...``
    Compact, easy for the model to scan timestamps.
    """
    lines: list[str] = []
    buf: list[str] = []
    last_emit = -10.0
    last_word_end = 0.0
    char_count = 0
    for seg in transcript.get("segments", []):
        for w in seg.get("words", []) or []:
            if "start" not in w or "end" not in w:
                continue
            t = w["start"]
            text = w["word"].strip()
            if not text:
                continue
            if t - last_emit >= 5.0 and buf:
                line = f"[{last_emit:7.2f}s] " + " ".join(buf)
                lines.append(line)
                char_count += len(line) + 1
                if char_count > max_chars:
                    break
                buf = []
                last_emit = t
            elif last_emit < 0:
                last_emit = t
            buf.append(text)
            last_word_end = w["end"]
        if char_count > max_chars:
            break
    if buf:
        lines.append(f"[{last_emit:7.2f}s] " + " ".join(buf))
    return "\n".join(lines)


def _load_topic_meta(transcript_path: Path) -> dict:
    """Try to find topic title_hint + slug from any auto_segment_plan.json."""
    stem = transcript_path.stem
    name = stem
    if len(name) >= 3 and name[0:2].isdigit() and name[2] == "-":
        name = name[3:]
    for suffix in ("_auto_1080p", "_1080p"):
        if name.endswith(suffix):
            name = name[: -len(suffix)]
            break
    slug = name

    meta = {"slug": slug, "title_hint": "", "thesis": "", "subtopics": []}
    podcast_dir = REPO_ROOT / "data" / "podcast"
    for plan in sorted(podcast_dir.glob("Episode_*/auto_segment_plan.json")):
        try:
            data = json.loads(plan.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        for entry in data.get("accepted", []) + data.get("dropped_sub_floor", []):
            if entry.get("slug") == slug:
                meta["title_hint"] = entry.get("title_hint", "")
                meta["thesis"] = entry.get("thesis", "")
                meta["subtopics"] = list(entry.get("subtopics", []))
                return meta
    return meta


def _client() -> anthropic.Anthropic:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")
    return anthropic.Anthropic(api_key=api_key)


def _propose_sync(transcript_path: Path) -> dict:
    transcript = json.loads(transcript_path.read_text())
    duration = float(transcript.get("duration_sec") or
                     max((s.get("end", 0) for s in transcript.get("segments", [])), default=0.0))
    meta = _load_topic_meta(transcript_path)

    transcript_blob = _format_transcript(transcript)
    user_message = (
        f"TOPIC: {meta['slug']}\n"
        f"TITLE_HINT: {meta['title_hint']}\n"
        f"THESIS: {meta['thesis']}\n"
        f"DURATION: {duration:.0f}s\n\n"
        f"TRANSCRIPT (timestamps in seconds from start of this topic file):\n\n"
        f"{transcript_blob}\n\n"
        f"Return 15-30 proposals via submit_proposals."
    )

    client = _client()
    t0 = time.time()
    response = client.messages.create(
        model=SONNET_MODEL,
        max_tokens=8000,
        system=SYSTEM_PROMPT,
        tools=[SUBMIT_PROPOSALS_TOOL],
        tool_choice={"type": "tool", "name": "submit_proposals"},
        messages=[{"role": "user", "content": user_message}],
    )
    latency = time.time() - t0

    proposals_raw = []
    for block in response.content:
        if getattr(block, "type", None) == "tool_use" and block.name == "submit_proposals":
            proposals_raw = (block.input or {}).get("proposals", [])
            break

    proposals = []
    for i, p in enumerate(proposals_raw):
        try:
            s = float(p["start_sec"])
            e = float(p["end_sec"])
        except (KeyError, TypeError, ValueError):
            continue
        if e <= s:
            continue
        proposals.append({
            "id": f"p{i+1}",
            "start_sec": round(s, 2),
            "end_sec": round(e, 2),
            "duration_sec": round(e - s, 2),
            "suggested_title": str(p.get("suggested_title", ""))[:80],
            "why": str(p.get("why", "")),
            "vibe": str(p.get("vibe", "reflective")),
        })

    return {
        "source_stem": transcript_path.stem,
        "topic_slug": meta["slug"],
        "title_hint": meta["title_hint"],
        "thesis": meta["thesis"],
        "subtopics": meta["subtopics"],
        "duration_sec": round(duration, 2),
        "model": SONNET_MODEL,
        "tokens_in": response.usage.input_tokens,
        "tokens_out": response.usage.output_tokens,
        "latency_sec": round(latency, 2),
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "proposals": proposals,
    }


async def _propose_async(transcript_path: Path) -> dict:
    return await asyncio.to_thread(_propose_sync, transcript_path)


def write_proposals(transcript_path: Path) -> Path:
    PROPOSALS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = PROPOSALS_DIR / f"{transcript_path.stem}.json"
    data = _propose_sync(transcript_path)
    out_path.write_text(json.dumps(data, indent=2))
    print(f"  [propose] {transcript_path.stem}: {len(data['proposals'])} proposals → {out_path.name}")
    return out_path


async def write_all_proposals(transcript_paths: list[Path]) -> list[Path]:
    PROPOSALS_DIR.mkdir(parents=True, exist_ok=True)
    tasks = [_propose_async(t) for t in transcript_paths]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    written: list[Path] = []
    for path, res in zip(transcript_paths, results):
        if isinstance(res, Exception):
            print(f"  [propose] {path.stem}: FAILED — {res}")
            continue
        out_path = PROPOSALS_DIR / f"{path.stem}.json"
        out_path.write_text(json.dumps(res, indent=2))
        written.append(out_path)
        print(f"  [propose] {path.stem}: {len(res['proposals'])} proposals "
              f"(${res['tokens_in']*3/1e6 + res['tokens_out']*15/1e6:.3f})")
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate clip proposals for human review.")
    parser.add_argument("transcripts", nargs="+", type=str)
    args = parser.parse_args()
    paths = [Path(p) for p in args.transcripts]
    asyncio.run(write_all_proposals(paths))
    return 0


if __name__ == "__main__":
    sys.exit(main())
