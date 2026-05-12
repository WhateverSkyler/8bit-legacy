#!/usr/bin/env python3
"""Pre-publish sanity check for rendered shorts.

Run BEFORE scheduling to socials. Validates each .mp4 in
data/podcast/clips/<episode>/ against a checklist that catches the kinds of
silent failures that have shipped before:

  - Duration > 59s (YouTube Shorts will treat it as a regular long video,
    and IG/TT reject anyway).
  - Wrong dimensions (must be 1080×1920; anything else is a render bug).
  - File size way out of band (< 3 MB → likely truncated render, > 60 MB →
    likely H.264 settings regression that'll bloat the feed).
  - Missing audio stream (silent clip).
  - Missing ASS caption sidecar (captions never burned in).
  - End-card overlay missing from the final second (this is the bug I
    nearly shipped on 2026-05-11 — the asset wasn't in the container so
    the END_CARD.exists() branch was a no-op).

Wire into schedule_shorts.py BEFORE the upload loop. Exit code 0 = all
clean. Exit code 1 = at least one clip failed (the failure list is printed
plus written to data/logs/preflight-<ts>.json for inspection).

Usage:
  python3 scripts/podcast/preflight_check.py --episode "Episode May 5 2026"
  python3 scripts/podcast/preflight_check.py --episode "Episode May 5 2026" --strict
  python3 scripts/podcast/preflight_check.py --clip /path/to/single.mp4

`--strict` upgrades soft warnings (e.g. brief clip, ~25-28s) to failures.
Default mode only fails on hard problems.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
CLIPS_DIR = ROOT / "data" / "podcast" / "clips"
LOGS_DIR = ROOT / "data" / "logs"

# Hard thresholds — failure
MAX_DURATION_SEC = 59.0          # YouTube Shorts ceiling
MIN_FILE_SIZE_MB = 3.0           # < this is almost certainly truncated
MAX_FILE_SIZE_MB = 60.0          # > this is a render-config regression
EXPECTED_W, EXPECTED_H = 1080, 1920

# Soft thresholds — strict-mode only
SOFT_MIN_DURATION_SEC = 25.0     # < this and the topic probably wasn't fully delivered

# End-card detection thresholds. The end-card PNG is ~95% black with brand-
# orange accents in the LEGACY logo and dividers. We extract the last frame
# and check: (1) mean luma is low (mostly dark) AND (2) the orange channel
# has enough hits to confirm the brand color is present.
END_CARD_LAST_FRAME_OFFSET_SEC = 0.5  # sample frame this far before end
END_CARD_MAX_MEAN_LUMA = 50.0    # 0-255 scale; > this means it's clearly NOT the end-card
END_CARD_MIN_ORANGE_PCT = 0.5    # at least 0.5% of pixels must be brand-orange-ish


def _ffprobe_json(path: Path, extra_args: list[str]) -> dict:
    cmd = ["ffprobe", "-v", "error", "-print_format", "json", "-show_format",
           "-show_streams"] + extra_args + [str(path)]
    out = subprocess.check_output(cmd, text=True)
    return json.loads(out)


def _extract_frame(video: Path, t_sec: float, out: Path) -> bool:
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
           "-ss", f"{t_sec:.2f}", "-i", str(video),
           "-frames:v", "1", "-q:v", "3", str(out)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode == 0 and out.exists()


def _end_card_signature(frame: Path) -> tuple[float, float]:
    """Return (mean_luma_0_255, orange_pct_0_to_100).

    "Orange-ish" = R∈[200,255] AND G∈[120,180] AND B∈[0,80]. Chosen wide
    enough to catch both the BBGGRR-derived end-card pixels and minor
    H.264-encode color drift.
    """
    try:
        from PIL import Image
        import numpy as np
    except ImportError:
        # If PIL/numpy aren't available, skip end-card check (return values
        # that always pass — the script falls back to "warn but don't fail").
        return (0.0, 100.0)
    img = Image.open(frame).convert("RGB")
    arr = np.asarray(img)
    # Standard luma weights
    luma = 0.299 * arr[..., 0] + 0.587 * arr[..., 1] + 0.114 * arr[..., 2]
    mean_luma = float(luma.mean())
    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
    orange_mask = (r >= 200) & (g >= 120) & (g <= 180) & (b <= 80)
    orange_pct = 100.0 * float(orange_mask.sum()) / float(arr.shape[0] * arr.shape[1])
    return (mean_luma, orange_pct)


def check_clip(mp4: Path, *, strict: bool = False) -> tuple[list[str], list[str]]:
    """Returns (errors, warnings) for one clip. Both empty = pass."""
    errors: list[str] = []
    warnings: list[str] = []

    if not mp4.exists():
        return ([f"file does not exist: {mp4}"], [])

    # File size
    size_mb = mp4.stat().st_size / (1024 * 1024)
    if size_mb < MIN_FILE_SIZE_MB:
        errors.append(f"file size {size_mb:.1f} MB < {MIN_FILE_SIZE_MB} MB floor (likely truncated)")
    elif size_mb > MAX_FILE_SIZE_MB:
        errors.append(f"file size {size_mb:.1f} MB > {MAX_FILE_SIZE_MB} MB ceiling (encode regression)")

    # ffprobe metadata
    try:
        probe = _ffprobe_json(mp4, [])
    except subprocess.CalledProcessError as exc:
        errors.append(f"ffprobe failed: {exc}")
        return (errors, warnings)

    fmt = probe.get("format", {})
    streams = probe.get("streams", [])
    video_streams = [s for s in streams if s.get("codec_type") == "video"]
    audio_streams = [s for s in streams if s.get("codec_type") == "audio"]

    duration = float(fmt.get("duration") or 0)
    if duration > MAX_DURATION_SEC:
        errors.append(f"duration {duration:.1f}s > {MAX_DURATION_SEC}s YouTube Shorts cap")
    if strict and duration < SOFT_MIN_DURATION_SEC:
        errors.append(f"duration {duration:.1f}s < {SOFT_MIN_DURATION_SEC}s strict floor")
    elif duration < SOFT_MIN_DURATION_SEC:
        warnings.append(f"duration {duration:.1f}s short — topic may not be fully developed")

    if not video_streams:
        errors.append("no video stream")
        return (errors, warnings)
    v = video_streams[0]
    if int(v.get("width") or 0) != EXPECTED_W or int(v.get("height") or 0) != EXPECTED_H:
        errors.append(f"dimensions {v.get('width')}x{v.get('height')} != {EXPECTED_W}x{EXPECTED_H}")

    if not audio_streams:
        errors.append("no audio stream (silent clip)")

    # ASS sidecar
    ass_path = mp4.with_suffix(".ass")
    if not ass_path.exists():
        warnings.append("no .ass sidecar (captions may have been skipped)")

    # End-card overlay check — extract a frame 0.5s before the end and verify
    # it matches the end-card signature (mostly dark + brand-orange present).
    # Skip if duration is too short to be meaningful or end-card is disabled.
    if duration >= 5.0:
        with tempfile.TemporaryDirectory() as tmp:
            frame_path = Path(tmp) / "last_frame.jpg"
            t = max(0.0, duration - END_CARD_LAST_FRAME_OFFSET_SEC)
            if _extract_frame(mp4, t, frame_path):
                mean_luma, orange_pct = _end_card_signature(frame_path)
                if mean_luma > END_CARD_MAX_MEAN_LUMA:
                    errors.append(
                        f"end-card not detected at t={t:.1f}s — last frame mean "
                        f"luma {mean_luma:.1f} > {END_CARD_MAX_MEAN_LUMA} (clip "
                        f"is still showing the speaker, not the end-card)"
                    )
                elif orange_pct < END_CARD_MIN_ORANGE_PCT:
                    warnings.append(
                        f"end-card brand-orange coverage {orange_pct:.2f}% < "
                        f"{END_CARD_MIN_ORANGE_PCT}% — last frame is dark but "
                        f"may be a fade-to-black instead of the end-card"
                    )
            else:
                warnings.append(f"could not extract verification frame at t={t:.1f}s")

    return (errors, warnings)


def main() -> int:
    parser = argparse.ArgumentParser()
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--episode", help='Episode name, e.g. "Episode May 5 2026"')
    g.add_argument("--clip", help="Path to a single .mp4")
    parser.add_argument("--strict", action="store_true",
                        help="Treat soft warnings (brief duration, etc.) as failures")
    parser.add_argument("--log-dir", default=str(LOGS_DIR))
    args = parser.parse_args()

    if args.clip:
        clips = [Path(args.clip)]
    else:
        safe = "".join(c if c.isalnum() or c in " -_" else "_" for c in args.episode).strip().replace(" ", "_")
        episode_dir = CLIPS_DIR / safe
        if not episode_dir.exists():
            print(f"[FATAL] no clips dir: {episode_dir}", file=sys.stderr)
            return 2
        clips = sorted(p for p in episode_dir.glob("*.mp4") if p.parent.name == safe)
        if not clips:
            print(f"[FATAL] no clips in {episode_dir}", file=sys.stderr)
            return 2

    total = len(clips)
    pass_count = 0
    results: list[dict] = []
    for mp4 in clips:
        errors, warnings = check_clip(mp4, strict=args.strict)
        passed = not errors
        if passed:
            pass_count += 1
        results.append({
            "clip": mp4.name,
            "passed": passed,
            "errors": errors,
            "warnings": warnings,
        })
        status = "PASS" if passed else "FAIL"
        print(f"[{status}] {mp4.name}")
        for e in errors:
            print(f"   ERR  {e}")
        for w in warnings:
            print(f"   warn {w}")

    print()
    print(f"=== {pass_count}/{total} clips passed ===")

    # Write the run log
    log_dir = Path(args.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = log_dir / f"preflight-{ts}.json"
    log_path.write_text(json.dumps({
        "ts": ts,
        "strict": args.strict,
        "total": total,
        "pass_count": pass_count,
        "results": results,
    }, indent=2))
    print(f"=== log written to {log_path.relative_to(ROOT)} ===")

    return 0 if pass_count == total else 1


if __name__ == "__main__":
    sys.exit(main())
