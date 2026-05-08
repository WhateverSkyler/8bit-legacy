#!/usr/bin/env python3
"""Build the music-bed catalog: data/music-beds/_catalog.json.

For each .wav/.mp3/.flac/.ogg in data/music-beds/, ask Claude (filename only —
we don't process audio) to classify mood + energy + podcast-appropriateness.
Writes a JSON catalog that render_clip.py uses to mood-match music to clips.

Usage:
  python3 scripts/podcast/build_music_catalog.py            # one-pass classify all
  python3 scripts/podcast/build_music_catalog.py --refresh  # re-classify even cached entries
  python3 scripts/podcast/build_music_catalog.py --dry-run  # preview without writing

Idempotent: re-running only classifies NEW beds unless --refresh.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "podcast"))
sys.path.insert(0, str(ROOT / "scripts"))

MUSIC_BEDS = ROOT / "data" / "music-beds"
CATALOG_PATH = MUSIC_BEDS / "_catalog.json"


def _infer_source(filename: str) -> str:
    """Best-effort source detection from filename — helps Claude classify.

    Most beds have descriptive filenames (e.g.,
    'F05 - Gourmet Race - Kirby Super Star (Composer ...)'). The Composer/
    artist parens often leak the genre. Pull the bracketed bit if present.
    """
    if "(" in filename and ")" in filename:
        # Get the parenthetical — usually composer/source attribution
        i = filename.index("(")
        j = filename.rindex(")")
        return filename[i+1:j].strip()
    return ""


async def classify_one(filename: str, source_hint: str) -> dict | None:
    from _qa_helpers import call_claude_text_async
    from qa_prompts import MUSIC_BED_MOOD_CLASSIFY_V1
    prompt = MUSIC_BED_MOOD_CLASSIFY_V1.format(
        filename=filename,
        source=source_hint or "(no metadata)",
    )
    try:
        return await call_claude_text_async(prompt, max_tokens=400)
    except Exception as exc:
        print(f"  [classify] error on {filename[:40]}: {exc}")
        return None


async def main_async(args: argparse.Namespace) -> int:
    if not MUSIC_BEDS.is_dir():
        print(f"FATAL: no music-beds dir at {MUSIC_BEDS}", file=sys.stderr)
        return 2

    # Load existing catalog
    existing: dict[str, dict] = {}
    if CATALOG_PATH.exists():
        try:
            existing = json.loads(CATALOG_PATH.read_text())
        except json.JSONDecodeError:
            print("[warn] existing catalog is malformed — starting fresh")

    # Discover all beds
    all_beds = sorted(
        list(MUSIC_BEDS.glob("*.wav")) + list(MUSIC_BEDS.glob("*.mp3")) +
        list(MUSIC_BEDS.glob("*.flac")) + list(MUSIC_BEDS.glob("*.ogg"))
    )
    if not all_beds:
        print(f"No music beds found in {MUSIC_BEDS}", file=sys.stderr)
        return 2

    # Decide which to (re-)classify
    needs_classify = []
    for bed in all_beds:
        if args.refresh or bed.name not in existing:
            needs_classify.append(bed)
    print(f"Found {len(all_beds)} beds. {len(needs_classify)} need classification.")

    if not needs_classify:
        print("Nothing to do. Pass --refresh to re-classify all.")
        return 0

    if args.dry_run:
        for b in needs_classify[:20]:
            print(f"  would classify: {b.name}")
        if len(needs_classify) > 20:
            print(f"  ... and {len(needs_classify) - 20} more")
        return 0

    # Classify all in parallel (batches of 20 to avoid hitting rate limits)
    BATCH = 20
    new_entries: dict[str, dict] = {}
    for batch_start in range(0, len(needs_classify), BATCH):
        batch = needs_classify[batch_start:batch_start+BATCH]
        print(f"[batch {batch_start//BATCH + 1}] classifying {len(batch)}...")
        t0 = time.time()
        results = await asyncio.gather(
            *(classify_one(b.name, _infer_source(b.name)) for b in batch),
            return_exceptions=True,
        )
        for bed, res in zip(batch, results):
            if isinstance(res, Exception) or not res or not isinstance(res, dict):
                new_entries[bed.name] = {"mood": "unknown", "energy": "unknown",
                                         "podcast_appropriate": True, "reason": "classification failed"}
                continue
            mood = (res.get("mood") or "unknown").lower()
            energy = (res.get("energy") or "unknown").lower()
            new_entries[bed.name] = {
                "mood": mood,
                "energy": energy,
                "podcast_appropriate": bool(res.get("podcast_appropriate", True)),
                "reason": res.get("reason", "")[:200],
            }
        print(f"  done in {time.time()-t0:.1f}s")

    # Merge + write
    merged = {**existing, **new_entries}
    CATALOG_PATH.write_text(json.dumps(merged, indent=2, sort_keys=True))
    print(f"\n[wrote] {CATALOG_PATH} ({len(merged)} entries)")

    # Distribution summary
    from collections import Counter
    moods = Counter(v.get("mood", "?") for v in merged.values())
    energies = Counter(v.get("energy", "?") for v in merged.values())
    podcast_ok = sum(1 for v in merged.values() if v.get("podcast_appropriate", True))
    print(f"\nMood distribution: {dict(moods)}")
    print(f"Energy distribution: {dict(energies)}")
    print(f"Podcast-appropriate: {podcast_ok}/{len(merged)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true",
                        help="Re-classify even already-cataloged beds")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview list of beds that would be classified, no API calls")
    args = parser.parse_args()
    from dotenv import load_dotenv
    load_dotenv(ROOT / "config" / ".env")
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    sys.exit(main())
