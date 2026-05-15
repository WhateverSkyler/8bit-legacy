#!/usr/bin/env python3
"""Copy podcast source videos from USB and downscale to 1080p working copies.

For each .mp4 in --source: downscale to 1920×1080 with -crf 23 -preset fast, audio copied.
With --full-video, ALSO downscale the full episode (needed for the auto_segment
stage to stream-copy per-topic cuts). Without --full-video, the full file stays
on USB and uploads to YouTube directly.

Keyframe interval is set to 60 frames (~2s at 30fps) so downstream ffmpeg
stream-copy cuts (in topic_segment.py) snap to within ~2s of requested boundaries.

Usage:
  python3 scripts/podcast/prepare_sources.py --source "/path/to/topic-cuts/"
  python3 scripts/podcast/prepare_sources.py --source "/path/to/topic-cuts/" --full-video "/path/to/full.mp4"
"""

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
OUT_DIR = ROOT / "data" / "podcast" / "source" / "1080p"


def downscale(src: Path, dst: Path) -> None:
    if dst.exists() and dst.stat().st_size > 1_000_000:
        print(f"[SKIP] {dst.name} exists")
        return
    print(f"[DOWNSCALE] {src.name}")
    subprocess.check_call([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(src),
        "-vf", "scale=1920:1080",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-g", "60", "-keyint_min", "60",
        "-c:a", "copy",
        str(dst),
    ])
    print(f"[DONE] {dst.name}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", help="Directory containing source MP4s (topic cuts)")
    parser.add_argument("--full-video", help="Path to the full-episode MP4. Will also be downscaled.")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    if args.source:
        source_dir = Path(args.source).resolve()
        if not source_dir.exists():
            print(f"[FATAL] source dir not found: {source_dir}", file=sys.stderr)
            return 2
        for src in sorted(source_dir.glob("*.mp4")):
            dst = OUT_DIR / f"{src.stem}_1080p.mp4"
            try:
                downscale(src, dst)
            except subprocess.CalledProcessError as exc:
                print(f"[ERROR] {src.name}: ffmpeg exited {exc.returncode}", file=sys.stderr)

    if args.full_video:
        full_src = Path(args.full_video).resolve()
        if not full_src.exists():
            print(f"[ERROR] --full-video not found: {full_src}", file=sys.stderr)
            return 2
        full_dst = OUT_DIR / f"{full_src.stem}_1080p.mp4"
        try:
            downscale(full_src, full_dst)
        except subprocess.CalledProcessError as exc:
            print(f"[ERROR] {full_src.name}: ffmpeg exited {exc.returncode}", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
