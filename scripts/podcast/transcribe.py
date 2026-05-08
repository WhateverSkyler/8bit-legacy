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


def _try_whisperx_align(video_path: Path, segments: list[dict], language: str,
                       device: str) -> tuple[list[dict], bool]:
    """Best-effort: refine word timestamps via whisperX forced alignment.

    Returns (segments, did_align). If whisperX isn't installed or alignment fails,
    returns the original segments unchanged + did_align=False (caller logs).

    whisperX uses wav2vec2 to align Whisper's word output to the actual audio,
    eliminating the drift that lets Gate 2 reject clips. With alignment, captions
    are accurate to ±50ms instead of Whisper's ±300ms typical.

    Cost: adds ~20% to transcribe wall time on CPU. ~500MB wav2vec2 model is
    downloaded once and cached in /app/.cache.
    """
    try:
        import whisperx  # type: ignore
    except ImportError:
        return segments, False

    try:
        # whisperX expects {start, end, text} segments and word-level alignment
        # is added in-place. Load alignment model (cached after first run).
        align_model, metadata = whisperx.load_align_model(language_code=language, device=device)
        audio = whisperx.load_audio(str(video_path))
        aligned = whisperx.align(
            segments,
            align_model,
            metadata,
            audio,
            device,
            return_char_alignments=False,
        )
        # whisperX's aligned result has segments with refined word timestamps
        out_segments = []
        for i, seg in enumerate(aligned.get("segments", segments)):
            words = []
            for w in (seg.get("words") or []):
                # whisperX keys: start, end, word, score (optional)
                if "start" not in w or "end" not in w:
                    continue
                words.append({
                    "start": float(w["start"]),
                    "end": float(w["end"]),
                    "word": w.get("word", "").strip() or w.get("text", ""),
                })
            out_segments.append({
                "id": seg.get("id", i),
                "start": float(seg.get("start", 0)),
                "end": float(seg.get("end", 0)),
                "text": (seg.get("text") or "").strip(),
                "words": words,
            })
        # Free the wav2vec2 model
        del align_model
        return out_segments, True
    except Exception as exc:
        print(f"  [whisperx] alignment failed: {exc} — keeping original timestamps")
        return segments, False


def transcribe_file(video_path: Path, model_name: str = "large-v3",
                   device: str = "cpu", compute_type: str = "int8",
                   align: bool = True) -> Path:
    """Transcribe a video to a per-source JSON with word-level timestamps.

    Args:
      align: if True (default), runs whisperX forced alignment after Whisper to
        refine word timestamps to ±50ms accuracy. Falls back to plain Whisper
        timing if whisperX isn't installed. Pass --no-align to opt out.
    """
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

    # Forced alignment via whisperX (refines word timestamps). Best-effort —
    # falls back to plain Whisper output if whisperx isn't available.
    aligned = False
    if align:
        t_align = time.time()
        segments, aligned = _try_whisperx_align(video_path, segments, info.language, device)
        if aligned:
            print(f"  [whisperx] forced alignment in {time.time()-t_align:.1f}s")

    payload = {
        "source": str(video_path),
        "duration_sec": info.duration,
        "language": info.language,
        "language_probability": info.language_probability,
        "model": model_name,
        "aligned_with_whisperx": aligned,
        "segments": segments,
    }
    out.write_text(json.dumps(payload, indent=2))
    dt = time.time() - t0
    rt_ratio = info.duration / dt if dt > 0 else 0
    align_tag = " (forced-aligned)" if aligned else ""
    print(f"[DONE] {video_path.name} in {dt:.1f}s  (audio={info.duration:.1f}s, realtime={rt_ratio:.1f}x){align_tag} → {out.name}")
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("video", nargs="?", help="Single video path to transcribe")
    parser.add_argument("--batch", help="Directory of videos to transcribe (all .mp4)")
    parser.add_argument("--model", default="large-v3", help="Whisper model (tiny/base/small/medium/large-v3)")
    parser.add_argument("--device", default="cpu", help="cpu or cuda")
    parser.add_argument("--compute-type", default="int8", help="int8 / float16 / float32")
    parser.add_argument("--no-align", action="store_true",
                        help="Skip whisperX forced alignment (default: aligned, falls back if whisperx unavailable)")
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
            transcribe_file(v, model_name=args.model, device=args.device,
                          compute_type=args.compute_type,
                          align=(not args.no_align))
        except Exception as exc:
            print(f"[ERROR] {v.name}: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
