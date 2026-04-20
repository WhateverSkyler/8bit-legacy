#!/usr/bin/env python3
"""Normalize a folder of music tracks to -18 LUFS for use as background beds.

Converts to 48kHz stereo WAV, writes to data/music-beds/, and emits an index.json.

Usage:
  python3 scripts/podcast/prepare_music.py --source ~/Music/retro-game-osts
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
OUT_DIR = ROOT / "data" / "music-beds"
INDEX = OUT_DIR / "index.json"

SUPPORTED = {".wav", ".mp3", ".flac", ".ogg", ".m4a", ".aac"}


def _ffprobe_duration(path: Path) -> float:
    out = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path)
    ]).decode().strip()
    return float(out)


def normalize(src: Path, dst: Path) -> None:
    if dst.exists() and dst.stat().st_size > 10_000:
        print(f"[SKIP] {dst.name}")
        return
    print(f"[NORMALIZE] {src.name}")
    subprocess.check_call([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(src),
        "-af", "loudnorm=I=-18:TP=-1.5:LRA=11",
        "-ar", "48000", "-ac", "2",
        "-c:a", "pcm_s16le",
        str(dst),
    ])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, help="Directory of source music files")
    args = parser.parse_args()

    src_dir = Path(args.source).expanduser().resolve()
    if not src_dir.exists():
        print(f"[FATAL] source dir missing: {src_dir}", file=sys.stderr)
        return 2

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    index: list[dict] = []
    for src in sorted(src_dir.rglob("*")):
        if not src.is_file() or src.suffix.lower() not in SUPPORTED:
            continue
        dst = OUT_DIR / f"{src.stem}.wav"
        try:
            normalize(src, dst)
            index.append({
                "file": dst.name,
                "title": src.stem,
                "duration_sec": _ffprobe_duration(dst),
                "source": str(src),
            })
        except subprocess.CalledProcessError as exc:
            print(f"[ERROR] {src.name}: {exc}", file=sys.stderr)

    INDEX.write_text(json.dumps(index, indent=2))
    total_min = sum(t["duration_sec"] for t in index) / 60
    print(f"\n[INDEX] {len(index)} tracks, {total_min:.1f} min → {INDEX.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
