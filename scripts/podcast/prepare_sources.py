#!/usr/bin/env python3
"""Copy podcast source videos from USB and downscale to 1080p working copies.

For each .mp4 in --source: downscale to 1920×1080 with -crf 23 -preset fast, audio copied.
Full-episode file stays on USB — we don't pull 24GB down; upload reads directly from USB.

Usage:
  python3 scripts/podcast/prepare_sources.py --source "/run/media/tristan/TRISTAN/.../Topic Cuts"
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
        "-c:a", "copy",
        str(dst),
    ])
    print(f"[DONE] {dst.name}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, help="Directory containing source MP4s")
    args = parser.parse_args()

    source_dir = Path(args.source).resolve()
    if not source_dir.exists():
        print(f"[FATAL] source dir not found: {source_dir}", file=sys.stderr)
        return 2

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for src in sorted(source_dir.glob("*.mp4")):
        dst = OUT_DIR / f"{src.stem}_1080p.mp4"
        try:
            downscale(src, dst)
        except subprocess.CalledProcessError as exc:
            print(f"[ERROR] {src.name}: ffmpeg exited {exc.returncode}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
