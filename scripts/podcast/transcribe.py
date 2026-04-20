#!/usr/bin/env python3
"""Transcribe podcast videos with faster-whisper, word-level timestamps.

Outputs one JSON per input video:
    data/podcast/transcripts/<stem>.json
    {
      "source": "<abs path>",
      "duration_sec": 580.4,
      "language": "en",
      "segments": [
        {"start": 0.0, "end": 2.4, "text": "...",
         "words": [{"start": 0.0, "end": 0.2, "word": "Welcome"}]}
      ]
    }

Usage:
    python3 scripts/podcast/transcribe.py <video.mp4>
    python3 scripts/podcast/transcribe.py --batch data/podcast/source/1080p/
    python3 scripts/podcast/transcribe.py --batch data/podcast/source/1080p/ --model large-v3
"""

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
TRANSCRIPT_DIR = ROOT / "data" / "podcast" / "transcripts"


def transcribe_file(video_path: Path, model_name: str = "large-v3", device: str = "cpu", compute_type: str = "int8") -> Path:
    from faster_whisper import WhisperModel  # lazy import so --help is fast

    TRANSCRIPT_DIR.mkdir(parents=True, exist_ok=True)
    out = TRANSCRIPT_DIR / f"{video_path.stem}.json"
    if out.exists():
        print(f"[SKIP] {video_path.name} → {out.name} already exists")
        return out

    print(f"[TRANSCRIBE] {video_path.name} (model={model_name}, device={device}, compute={compute_type})")
    t0 = time.time()
    model = WhisperModel(model_name, device=device, compute_type=compute_type)
    segments_iter, info = model.transcribe(
        str(video_path),
        language="en",
        word_timestamps=True,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 400},
    )

    segments = []
    for seg in segments_iter:
        segments.append({
            "id": seg.id,
            "start": seg.start,
            "end": seg.end,
            "text": seg.text.strip(),
            "words": [
                {"start": w.start, "end": w.end, "word": w.word}
                for w in (seg.words or [])
            ],
        })

    payload = {
        "source": str(video_path),
        "duration_sec": info.duration,
        "language": info.language,
        "language_probability": info.language_probability,
        "model": model_name,
        "segments": segments,
    }
    out.write_text(json.dumps(payload, indent=2))
    dt = time.time() - t0
    rt_ratio = info.duration / dt if dt > 0 else 0
    print(f"[DONE] {video_path.name} in {dt:.1f}s  (audio={info.duration:.1f}s, realtime={rt_ratio:.1f}x) → {out.name}")
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("video", nargs="?", help="Single video path to transcribe")
    parser.add_argument("--batch", help="Directory of videos to transcribe (all .mp4)")
    parser.add_argument("--model", default="large-v3", help="Whisper model (tiny/base/small/medium/large-v3)")
    parser.add_argument("--device", default="cpu", help="cpu or cuda")
    parser.add_argument("--compute-type", default="int8", help="int8 / float16 / float32")
    args = parser.parse_args()

    if not args.video and not args.batch:
        parser.error("pass a video path or --batch <dir>")

    targets: list[Path] = []
    if args.video:
        targets.append(Path(args.video).resolve())
    if args.batch:
        batch_dir = Path(args.batch).resolve()
        if not batch_dir.exists():
            parser.error(f"batch directory does not exist: {batch_dir}")
        targets.extend(sorted(batch_dir.glob("*.mp4")))

    if not targets:
        print("(no videos to transcribe)")
        return 0

    for v in targets:
        try:
            transcribe_file(v, model_name=args.model, device=args.device, compute_type=args.compute_type)
        except Exception as exc:
            print(f"[ERROR] {v.name}: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
