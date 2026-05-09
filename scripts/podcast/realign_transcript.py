#!/usr/bin/env python3
"""Force-align existing whisper-only transcripts via whisperX wav2vec2.

Use case: transcript JSONs were generated BEFORE whisperX was integrated
(`aligned_with_whisperx` key missing or False). Re-running transcribe.py
would skip them (idempotency). This tool runs ONLY the alignment step on
existing transcripts — much faster than full re-transcribe.

Per-source cost: ~30-90s wall on CPU (vs 30-60 min for full re-transcribe).

Usage:
  python3 scripts/podcast/realign_transcript.py <transcript.json> <source.mp4>
  python3 scripts/podcast/realign_transcript.py --batch                # all in transcripts/
  python3 scripts/podcast/realign_transcript.py --batch --force        # re-align even if already aligned
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
TRANSCRIPT_DIR = ROOT / "data" / "podcast" / "transcripts"
SOURCE_DIR = ROOT / "data" / "podcast" / "source" / "1080p"


def realign_one(transcript_path: Path, source_path: Path,
               device: str = "cpu", force: bool = False) -> bool:
    """Load existing transcript, run whisperX align, write back. Returns True on success."""
    try:
        import whisperx  # type: ignore
    except ImportError:
        print(f"FATAL: whisperx not installed. pip install whisperx>=3.1", file=sys.stderr)
        return False

    if not transcript_path.exists():
        print(f"  [skip] {transcript_path.name} not found")
        return False
    if not source_path.exists():
        print(f"  [skip] {source_path.name} not found at {source_path}")
        return False

    data = json.loads(transcript_path.read_text())
    if data.get("aligned_with_whisperx") and not force:
        print(f"  [skip] {transcript_path.name} already aligned (pass --force to re-do)")
        return True

    segments = data.get("segments") or []
    if not segments:
        print(f"  [skip] {transcript_path.name} has no segments")
        return False

    language = data.get("language", "en")
    print(f"[ALIGN] {transcript_path.name} ({len(segments)} segs, lang={language})")
    t0 = time.time()

    try:
        align_model, metadata = whisperx.load_align_model(language_code=language, device=device)
    except Exception as exc:
        print(f"  [error] load_align_model failed: {exc}")
        return False

    try:
        audio = whisperx.load_audio(str(source_path))
    except Exception as exc:
        print(f"  [error] load_audio failed: {exc}")
        return False

    try:
        aligned = whisperx.align(
            segments, align_model, metadata, audio, device,
            return_char_alignments=False,
        )
    except Exception as exc:
        print(f"  [error] alignment failed: {exc}")
        return False

    out_segments = []
    for i, seg in enumerate(aligned.get("segments", segments)):
        words = []
        for w in (seg.get("words") or []):
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

    data["segments"] = out_segments
    data["aligned_with_whisperx"] = True
    data["realigned_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")

    # Backup existing then write
    backup = transcript_path.with_suffix(".json.pre-realign.bak")
    if not backup.exists():
        backup.write_text(transcript_path.read_text())
    transcript_path.write_text(json.dumps(data, indent=2))
    print(f"[DONE] {transcript_path.name} aligned in {time.time()-t0:.1f}s "
          f"({len(out_segments)} segs, {sum(len(s['words']) for s in out_segments)} words)")
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("transcript", nargs="?", help="Path to transcript JSON")
    parser.add_argument("source", nargs="?", help="Path to source MP4")
    parser.add_argument("--batch", action="store_true",
                        help="Process all transcripts in transcripts/ (matches source by stem)")
    parser.add_argument("--force", action="store_true",
                        help="Re-align even if aligned_with_whisperx=True already")
    parser.add_argument("--device", default="cpu", help="cpu or cuda")
    args = parser.parse_args()

    targets: list[tuple[Path, Path]] = []
    if args.transcript and args.source:
        targets.append((Path(args.transcript), Path(args.source)))
    elif args.batch:
        for tx in sorted(TRANSCRIPT_DIR.glob("*.json")):
            src = SOURCE_DIR / f"{tx.stem}.mp4"
            if src.exists():
                targets.append((tx, src))
            else:
                print(f"  [skip] {tx.name} — no matching source MP4 at {src}")
    else:
        parser.error("pass <transcript> <source> OR --batch")

    print(f"Realigning {len(targets)} transcript(s)...")
    ok = 0
    for tx, src in targets:
        if realign_one(tx, src, device=args.device, force=args.force):
            ok += 1
    print(f"\n[BATCH] aligned {ok} of {len(targets)}")
    return 0 if ok == len(targets) else 1


if __name__ == "__main__":
    sys.exit(main())
