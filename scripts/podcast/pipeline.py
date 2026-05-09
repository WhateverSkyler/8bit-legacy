#!/usr/bin/env python3
"""Resumable podcast release orchestrator.

Stages (all idempotent):
  1. sources     — downscale topic cuts from USB → data/podcast/source/1080p/
  2. transcribe  — faster-whisper word-level JSONs
  3. thumbnails  — 1280×720 YouTube thumbnails
  4. metadata    — titles/descriptions/tags for YT
  5. yt_upload   — schedule YT uploads with publishAt
  6. pick_clips  — Claude picks viral moments per topic
  7. render_clips— ffmpeg renders 1080×1920 shorts with captions + music
  8. schedule    — schedule shorts to TikTok/Shorts/Reels via Zernio

Checkpoint at data/podcast/<episode>/pipeline_state.json.

Usage:
  python3 scripts/podcast/pipeline.py --episode "Episode April 14th 2026" \
      --source "/run/media/tristan/TRISTAN/8-bit podcast/Episode April 14th 2026/Topic Cuts" \
      --full-video "/run/media/.../Episode April 14th 2026/8-Bit Podcast April 14 2026 FULL FINAL.mp4" \
      --yt-start-date 2026-04-20 --shorts-start-date 2026-04-20
  python3 scripts/podcast/pipeline.py --episode "..." --resume
  python3 scripts/podcast/pipeline.py --episode "..." --stage transcribe
  python3 scripts/podcast/pipeline.py --episode "..." --dry-run
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent.parent
SOURCE_1080P = ROOT / "data" / "podcast" / "source" / "1080p"
TRANSCRIPTS = ROOT / "data" / "podcast" / "transcripts"
THUMBS = ROOT / "data" / "podcast" / "thumbnails"
METADATA = ROOT / "data" / "podcast" / "metadata"
CLIPS_PLAN_DIR = ROOT / "data" / "podcast" / "clips_plan"
CLIPS_DIR = ROOT / "data" / "podcast" / "clips"
STATE_DIR = ROOT / "data" / "podcast"

sys.path.insert(0, str(ROOT / "scripts"))
try:
    from navi_alerts import emit_navi_task  # noqa: E402
except ImportError:
    emit_navi_task = None  # graceful degrade if requests is missing

STAGES = ["sources", "transcribe", "auto_segment", "thumbnails", "metadata",
          "yt_upload", "pick_clips", "render_clips", "schedule"]

ET = ZoneInfo("America/New_York")


def _safe(s: str) -> str:
    return "".join(c if c.isalnum() or c in " -_" else "_" for c in s).strip().replace(" ", "_")


def _state_path(episode: str) -> Path:
    d = STATE_DIR / _safe(episode)
    d.mkdir(parents=True, exist_ok=True)
    return d / "pipeline_state.json"


def _load_state(episode: str) -> dict:
    p = _state_path(episode)
    if p.exists():
        try:
            return json.loads(p.read_text())
        except json.JSONDecodeError:
            pass
    return {"stages": {}}


def _save_state(episode: str, state: dict) -> None:
    _state_path(episode).write_text(json.dumps(state, indent=2))


def _run(cmd: list[str], dry_run: bool) -> int:
    print(f"    $ {' '.join(cmd)}")
    if dry_run:
        return 0
    t0 = time.time()
    proc = subprocess.run(cmd)
    print(f"    ({time.time() - t0:.1f}s, exit={proc.returncode})")
    return proc.returncode


def _yt_schedule_map(start_date: str, stems: list[str], full_stem: str | None) -> dict[str, str]:
    """Full episode: day 1 18:00 ET. Topics: day 2..N at 12:00 ET."""
    start = datetime.fromisoformat(start_date).replace(tzinfo=ET)
    schedule: dict[str, str] = {}
    if full_stem:
        schedule[full_stem] = start.replace(hour=18, minute=0, second=0).astimezone(
            ZoneInfo("UTC")).isoformat().replace("+00:00", "Z")
    for i, stem in enumerate(stems):
        when = (start + timedelta(days=i + 1)).replace(hour=12, minute=0, second=0)
        schedule[stem] = when.astimezone(ZoneInfo("UTC")).isoformat().replace("+00:00", "Z")
    return schedule


def stage_sources(args, state) -> int:
    if not args.source and not args.full_video:
        print("  [skip] no --source or --full-video provided")
        return 0
    cmd = ["python3", str(ROOT / "scripts" / "podcast" / "prepare_sources.py")]
    if args.source:
        cmd.extend(["--source", args.source])
    if args.full_video:
        cmd.extend(["--full-video", args.full_video])
    return _run(cmd, args.dry_run)


def stage_transcribe(args, state) -> int:
    return _run(["python3", str(ROOT / "scripts" / "podcast" / "transcribe.py"),
                 "--batch", str(SOURCE_1080P)], args.dry_run)


def stage_auto_segment(args, state) -> int:
    """Auto-detect topic boundaries in the full-episode transcript and cut the
    full MP4 into per-topic videos. Skipped when:
      - No --full-video provided
      - Manual topic cuts already exist (non-full *.mp4 in source/1080p/)
      - The auto_segment stage has already run for this episode and produced
        _auto_*.mp4 files (idempotency)

    Plan vs execute is controlled by --auto-segment-mode (default: execute).
    """
    if not args.full_video:
        print("  [skip] no --full-video provided — auto-segment requires the full episode")
        return 0

    full_path = Path(args.full_video)
    if not full_path.exists():
        print(f"  [skip] full video missing: {full_path}")
        return 0

    full_stem = full_path.stem
    full_1080p = SOURCE_1080P / f"{full_stem}_1080p.mp4"
    if not full_1080p.exists():
        # prepare_sources.py should have produced this when --full-video was passed.
        print(f"  [skip] full 1080p not found: {full_1080p} — prepare_sources must run first")
        return 0

    full_transcript = TRANSCRIPTS / f"{full_stem}_1080p.json"
    if not full_transcript.exists():
        print(f"  [skip] full transcript not found: {full_transcript}")
        return 0

    # Skip if manual topic cuts exist (someone pre-segmented; don't double-process)
    if not args.force_auto_segment:
        manual_topics = [
            v for v in SOURCE_1080P.glob("*.mp4")
            if "full" not in v.stem.lower()
            and "_auto_" not in v.stem
            and v.stem != full_1080p.stem
        ]
        if manual_topics:
            print(f"  [skip] {len(manual_topics)} manual topic(s) found — auto-segment disabled")
            print("         (pass --force-auto-segment to override)")
            return 0

    # Skip if auto-segment already produced files (idempotent re-run)
    existing_auto = list(SOURCE_1080P.glob("*_auto_1080p.mp4"))
    if existing_auto and not args.force_auto_segment:
        print(f"  [skip] {len(existing_auto)} auto-segment file(s) already exist; --force-auto-segment to redo")
        return 0

    return _run([
        "python3", str(ROOT / "scripts" / "podcast" / "topic_segment.py"),
        "--transcript", str(full_transcript),
        "--full-video-1080p", str(full_1080p),
        "--episode", args.episode,
        "--mode", args.auto_segment_mode,
    ], args.dry_run)


def stage_thumbnails(args, state) -> int:
    rc = _run(["python3", str(ROOT / "scripts" / "podcast" / "generate_thumbnail.py"),
               "--batch", str(SOURCE_1080P), "--metadata", str(METADATA)], args.dry_run)
    if args.full_video and not args.dry_run:
        fv = Path(args.full_video)
        if fv.exists():
            _run(["python3", str(ROOT / "scripts" / "podcast" / "generate_thumbnail.py"),
                  str(fv), "--metadata", str(METADATA)], args.dry_run)
    return rc


def stage_metadata(args, state) -> int:
    rc = _run(["python3", str(ROOT / "scripts" / "podcast" / "generate_metadata.py"),
               "--batch", str(TRANSCRIPTS), "--type", "topic"], args.dry_run)
    if rc == 0 and not args.dry_run:
        _emit_thumbnail_navi_task(args.episode)
    return rc


def _emit_thumbnail_navi_task(episode: str) -> None:
    """After metadata generation, emit a Navi task listing each video that needs
    a custom thumbnail. The user drops matching PNGs in /media/podcast/custom-thumbnails/
    (fuzzy filename match in youtube_upload.py's _find_thumbnail). YouTube videos
    upload as scheduled-private until publishAt, so there's a window to swap thumbs
    in YouTube Studio if the user doesn't get them dropped before yt_upload runs.
    """
    if emit_navi_task is None:
        print("  [thumbnail-task] navi_alerts unavailable — skipping Navi task")
        return
    if not METADATA.exists():
        print(f"  [thumbnail-task] no metadata dir at {METADATA} — skipping")
        return
    entries = []
    for meta_file in sorted(METADATA.glob("*.json")):
        try:
            data = json.loads(meta_file.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        title = data.get("title", "(no title)")
        entries.append((meta_file.stem, title))
    if not entries:
        print(f"  [thumbnail-task] no metadata files in {METADATA} — skipping")
        return
    lines = [f"Make YouTube thumbnails for {episode}.",
             "",
             "Drop matching PNGs in /mnt/pool/NAS/Media/8-Bit Legacy/podcast/custom-thumbnails/",
             "(fuzzy filename match — name them similar to the source filename).",
             "",
             "Videos:"]
    for stem, title in entries:
        lines.append(f"  • {title}")
        lines.append(f"    source: {stem}")
    body = "\n".join(lines)
    try:
        emit_navi_task(
            title=f"Make {len(entries)} podcast thumbnail(s) — {episode}",
            description=body,
            priority="medium",
        )
        print(f"  [thumbnail-task] emitted Navi task for {len(entries)} video(s)")
    except Exception as exc:  # noqa: BLE001
        print(f"  [thumbnail-task] Navi emit failed: {exc}")


def stage_yt_upload(args, state) -> int:
    """Upload to YouTube using the ORIGINAL-quality source files (e.g. 4K),
    not the 1080p working copies. 1080p copies remain for clip rendering only.

    Picks up topic originals from --source dir and the full-episode original
    from --full-video. Only files that still exist are uploaded (the user may
    have deleted topics from the processing/ folder to skip them).
    """
    if not args.yt_start_date:
        print("  [skip] no --yt-start-date — skipping YT schedule")
        return 0

    source_dir = Path(args.source).resolve()
    full_file = Path(args.full_video).resolve() if args.full_video else None

    # Topic originals = all .mp4 in the source dir, minus the full-episode file.
    all_mp4s = sorted(source_dir.glob("*.mp4"))
    topic_mp4s = [v for v in all_mp4s if (not full_file) or v.resolve() != full_file]

    stems = [v.stem for v in topic_mp4s]
    full_stem = full_file.stem if full_file and full_file.exists() else None
    sched = _yt_schedule_map(args.yt_start_date, stems, full_stem)
    sched_path = STATE_DIR / _safe(args.episode) / "yt_schedule.json"
    sched_path.write_text(json.dumps(sched, indent=2))
    print(f"  schedule → {sched_path.relative_to(ROOT)}")
    print(f"  uploading: full={full_file.name if full_stem else '(none)'}, "
          f"{len(topic_mp4s)} topic(s)")

    # Upload each topic individually (passing explicit paths avoids re-globbing the full
    # episode from the source dir, which --batch would do).
    rc = 0
    for topic in topic_mp4s:
        if topic.stem not in sched:
            continue
        rc = _run(["python3", str(ROOT / "scripts" / "podcast" / "youtube_upload.py"),
                   str(topic), "--publish-at", sched[topic.stem]], args.dry_run)
        if rc != 0:
            return rc
    # Upload full episode
    if full_stem and full_file.exists() and full_stem in sched:
        rc = _run(["python3", str(ROOT / "scripts" / "podcast" / "youtube_upload.py"),
                   str(full_file), "--publish-at", sched[full_stem]], args.dry_run)
    return rc


def stage_pick_clips(args, state) -> int:
    """Pick short-form clips from the CURRENT-EPISODE transcripts only.

    Episode-scoped (2026-05-08 fix): user complaint was that re-running
    pick_clips on a fresh episode was ALSO picking from old episodes'
    transcripts still on disk. April 14 was getting "milked again" alongside
    May 5 because pick_clips iterated all *.json in transcripts/.

    Resolution order:
      1. If --full-video given → use that transcript (single-source pick from
         the full episode, no auto-segment topic-cuts considered)
      2. Else → episode-scoped batch: include only transcripts modified in
         the last 7 days (captures the current episode's freshly-generated
         transcripts + any auto_segment topic-cuts from THIS run)
      3. Else error out — no longer silently globs whole transcripts dir.

    Rationale for #1 (single-full path): when both full and auto-segmented
    topic transcripts exist, picking from each leads to content overlap.
    """
    import time as _time
    if args.full_video:
        full_stem = Path(args.full_video).stem
        full_transcript = TRANSCRIPTS / f"{full_stem}_1080p.json"
        if full_transcript.exists():
            print(f"  picking from full transcript only: {full_transcript.name}")
            return _run(["python3", str(ROOT / "scripts" / "podcast" / "pick_clips.py"),
                         str(full_transcript)], args.dry_run)

    # Episode-scoped batch: pick_clips.py --mtime-within-days 7 filters out
    # transcripts older than 7 days. This captures the current episode's
    # freshly-generated transcripts (just touched by transcribe/auto_segment)
    # and excludes already-published prior episodes' leftovers.
    return _run(["python3", str(ROOT / "scripts" / "podcast" / "pick_clips.py"),
                 "--batch", str(TRANSCRIPTS),
                 "--mtime-within-days", "7"], args.dry_run)


def stage_render_clips(args, state) -> int:
    all_path = CLIPS_PLAN_DIR / "_all.json"
    if not all_path.exists():
        if args.dry_run:
            print(f"  [dry-run] would read {all_path} (not yet generated)")
            return 0
        print(f"  [fatal] {all_path} missing — pick_clips stage must run first")
        return 2
    return _run(["python3", str(ROOT / "scripts" / "podcast" / "render_clip.py"),
                 "--batch", str(all_path), "--episode", args.episode], args.dry_run)


def stage_schedule(args, state) -> int:
    if not args.shorts_start_date:
        print("  [skip] no --shorts-start-date")
        return 0
    episode_clips_dir = CLIPS_DIR / _safe(args.episode)
    if not episode_clips_dir.exists() or not any(episode_clips_dir.glob("*.mp4")):
        if args.dry_run:
            print(f"  [dry-run] would schedule clips in {episode_clips_dir} (not yet rendered)")
            return 0
        print(f"  [fatal] no clips in {episode_clips_dir}", file=sys.stderr)
        return 2
    mode = "--dry-run" if args.dry_run else "--execute"
    return _run(["python3", str(ROOT / "scripts" / "podcast" / "schedule_shorts.py"),
                 "--episode", args.episode, "--start-date", args.shorts_start_date, mode], False)


STAGE_FNS = {
    "sources": stage_sources,
    "transcribe": stage_transcribe,
    "auto_segment": stage_auto_segment,
    "thumbnails": stage_thumbnails,
    "metadata": stage_metadata,
    "yt_upload": stage_yt_upload,
    "pick_clips": stage_pick_clips,
    "render_clips": stage_render_clips,
    "schedule": stage_schedule,
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--episode", required=True)
    parser.add_argument("--source", help="Dir of raw topic-cut MP4s on USB")
    parser.add_argument("--full-video", help="Path to the full episode MP4 on USB")
    parser.add_argument("--yt-start-date", help="YYYY-MM-DD, first YT publish day (ET)")
    parser.add_argument("--shorts-start-date", help="YYYY-MM-DD, first shorts publish day (ET)")
    parser.add_argument("--resume", action="store_true", help="Skip stages marked completed")
    parser.add_argument("--stage", choices=STAGES, help="Run a single stage")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--auto-segment-mode", choices=["plan", "execute"], default="execute",
                        help="auto_segment stage: 'execute' (default) cuts video if quality gates "
                             "pass; 'plan' emits Navi task only without cutting. The stage's internal "
                             "validation (≥3 valid topics, coherent theses, coverage check) protects "
                             "against bad output — failures auto-bail with a Navi alert for review.")
    parser.add_argument("--force-auto-segment", action="store_true",
                        help="Run auto_segment even if manual topic cuts or prior _auto_ files exist")
    args = parser.parse_args()

    state = _load_state(args.episode)
    stages = [args.stage] if args.stage else STAGES

    print(f"[PIPELINE] episode={args.episode}  stages={stages}  dry_run={args.dry_run}")

    for name in stages:
        info = state["stages"].get(name, {})
        if args.resume and info.get("completed"):
            print(f"\n[{name}] already completed at {info.get('completed_at')} — skipping")
            continue
        print(f"\n[{name}] running")
        try:
            rc = STAGE_FNS[name](args, state)
        except Exception as exc:
            print(f"[{name}] EXCEPTION: {exc}", file=sys.stderr)
            rc = 1
        state["stages"][name] = {
            "completed": rc == 0 and not args.dry_run,
            "last_rc": rc,
            "completed_at": datetime.now(ET).isoformat() if rc == 0 else None,
        }
        _save_state(args.episode, state)
        if rc != 0:
            print(f"[{name}] FAILED rc={rc}", file=sys.stderr)
            return rc

    print("\n[PIPELINE] done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
