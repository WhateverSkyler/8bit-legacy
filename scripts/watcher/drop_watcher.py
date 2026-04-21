#!/usr/bin/env python3
"""Drop-folder watcher for 8-Bit Legacy content pipelines.

Polls NAS-mounted drop folders every POLL_INTERVAL_SEC, detects new content,
routes it through the appropriate pipeline, then moves the drop to archive.

Layout (inside the pipeline container with the NAS dataset mounted at /media):

    /media/
    ├── podcast/
    │   ├── incoming/          <- you drop `EP-YYYYMMDD/` here (full.mp4 + topic-*.mp4)
    │   ├── processing/        <- watcher moves drops here during a run
    │   ├── archive/           <- succeeded drops end up here
    │   ├── clips-archive/     <- rendered shorts copied here for buffer re-use
    │   └── music-beds/        <- drop raw OSTs (wav/mp3/flac/ogg/m4a/aac); watcher auto-normalizes to -18 LUFS
    ├── photos/
    │   ├── incoming/          <- loose PNGs
    │   ├── processing/        <- grouped by drop date during a run
    │   └── archive/
    ├── state/
    │   └── drop_watcher.json  <- "seen" tracking
    └── logs/
        └── drop_watcher-YYYYMMDD.log

Config via env vars:
    MEDIA_ROOT             default /media
    POLL_INTERVAL_SEC      default 300 (5 min)
    SCRIPTS_ROOT           default /app/scripts (container path to the repo's scripts/ dir)
    NAVI_URL               passed through to navi_alerts (see navi_alerts.py)

Failure policy: any pipeline error emits a Navi task (source='8bit') and moves
the drop to <area>/incoming/_failed/<name>/ for manual inspection. The folder
stays there until you delete it — watcher won't retry automatically.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

# Bring navi_alerts into the import path without assuming container layout
_SCRIPTS_ROOT = Path(os.getenv("SCRIPTS_ROOT", Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(_SCRIPTS_ROOT))
from navi_alerts import emit_navi_task  # noqa: E402

MEDIA_ROOT = Path(os.getenv("MEDIA_ROOT", "/media"))
POLL_INTERVAL_SEC = int(os.getenv("POLL_INTERVAL_SEC", "300"))
BUFFER_EVERY_N_POLLS = int(os.getenv("BUFFER_EVERY_N_POLLS", "12"))  # default: every 60 min
ET = ZoneInfo("America/New_York")

# Sub-paths
PODCAST = MEDIA_ROOT / "podcast"
PHOTOS = MEDIA_ROOT / "photos"
STATE_DIR = MEDIA_ROOT / "state"
LOGS_DIR = MEDIA_ROOT / "logs"
STATE_FILE = STATE_DIR / "drop_watcher.json"

# Pipeline entrypoints
PODCAST_PIPELINE = _SCRIPTS_ROOT / "podcast" / "pipeline.py"
PHOTO_PIPELINE = _SCRIPTS_ROOT / "social" / "schedule_photos.py"
BUFFER_SCHEDULER = _SCRIPTS_ROOT / "watcher" / "buffer_scheduler.py"
PREPARE_MUSIC = _SCRIPTS_ROOT / "podcast" / "prepare_music.py"

# pipeline.py writes rendered clips to <repo>/data/podcast/clips/<safe-episode>/ inside the container.
# Compute the path from SCRIPTS_ROOT so the watcher can copy them to clips-archive after a run.
_REPO_ROOT = _SCRIPTS_ROOT.parent
PODCAST_RENDERED_CLIPS_ROOT = _REPO_ROOT / "data" / "podcast" / "clips"

# Music-bed auto-detect: user drops raw OSTs into the NAS folder (visible over SMB),
# watcher normalizes them to the container-local data dir where render_clip.py reads from.
MUSIC_SOURCE = PODCAST / "music-beds"
MUSIC_NORMALIZED = _REPO_ROOT / "data" / "music-beds"
MUSIC_EXTENSIONS = {".wav", ".mp3", ".flac", ".ogg", ".m4a", ".aac"}


def _safe_episode_name(name: str) -> str:
    """Mirror pipeline.py's _safe() so we can find the rendered-clips folder."""
    cleaned = "".join(c if c.isalnum() or c in " -_" else "_" for c in name).strip()
    return cleaned.replace(" ", "_")


# --- Logging ---------------------------------------------------------------

def _setup_logging() -> logging.Logger:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOGS_DIR / f"drop_watcher-{datetime.now(ET).strftime('%Y%m%d')}.log"
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    try:
        handlers.append(logging.FileHandler(log_file))
    except OSError:
        pass  # NAS mount transiently missing — stdout still works
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=handlers,
        force=True,
    )
    return logging.getLogger("drop_watcher")


log = _setup_logging()


# --- Seen-state tracking ---------------------------------------------------

def _load_state() -> dict:
    if not STATE_FILE.exists():
        return {"podcast_seen": [], "photos_seen": [], "last_scan": None}
    try:
        return json.loads(STATE_FILE.read_text())
    except (OSError, json.JSONDecodeError):
        return {"podcast_seen": [], "photos_seen": [], "last_scan": None}


def _save_state(state: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


# --- Helpers ---------------------------------------------------------------

def _safe_move(src: Path, dst_parent: Path, label: str) -> Path:
    """Move src into dst_parent/src.name with a counter suffix if a collision occurs."""
    dst_parent.mkdir(parents=True, exist_ok=True)
    target = dst_parent / src.name
    i = 1
    while target.exists():
        target = dst_parent / f"{src.name}__{i}"
        i += 1
    shutil.move(str(src), str(target))
    log.info(f"[{label}] moved {src.name} → {target}")
    return target


def _run_subprocess(
    cmd: list[str],
    cwd: Path | None = None,
    timeout_sec: int = 7200,
    env: dict[str, str] | None = None,
) -> tuple[bool, str]:
    log.info(f"[RUN] {' '.join(str(c) for c in cmd)}")
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        if proc.returncode == 0:
            log.info(f"[OK] exit 0 — {out.strip()[-400:]}")
            return True, out
        log.error(f"[FAIL] exit {proc.returncode}\n{out.strip()[-2000:]}")
        return False, out
    except subprocess.TimeoutExpired as exc:
        return False, f"TimeoutExpired after {timeout_sec}s: {exc}"
    except OSError as exc:
        return False, f"OSError: {exc}"


def _file_is_stable(p: Path, window_sec: int = 60) -> bool:
    """Return True if the file hasn't been modified in the last window_sec.

    Prevents processing a drop that's still being uploaded over the network.
    """
    try:
        mtime = p.stat().st_mtime
        return (time.time() - mtime) >= window_sec
    except OSError:
        return False


def _drop_is_stable(folder: Path, window_sec: int = 60) -> bool:
    """All files inside folder must be older than window_sec."""
    for p in folder.rglob("*"):
        if p.is_file() and not _file_is_stable(p, window_sec):
            return False
    return True


# --- Podcast pipeline ------------------------------------------------------

def _process_podcast_drop(drop_dir: Path, state: dict) -> None:
    name = drop_dir.name
    log.info(f"[PODCAST] new drop: {name}")

    # Find the full episode and topic cuts
    videos = sorted(drop_dir.glob("*.mp4"))
    full_candidates = [v for v in videos if "full" in v.name.lower()]
    topic_candidates = [v for v in videos if v not in full_candidates]

    if not full_candidates:
        emit_navi_task(
            title=f"Podcast drop {name} missing full episode",
            description=(
                f"Drop folder {drop_dir} has no file named 'full.mp4' (or 'full' in the name). "
                f"Pipeline skipped. Files in drop: {[v.name for v in videos]}"
            ),
            priority="high",
        )
        _safe_move(drop_dir, PODCAST / "incoming" / "_failed", "PODCAST")
        return

    if not topic_candidates:
        emit_navi_task(
            title=f"Podcast drop {name} has no topic cuts",
            description=(
                f"Drop folder {drop_dir} only contains the full episode — no topic-*.mp4 files. "
                f"Shorts won't be generated. Add topic cuts and re-drop."
            ),
            priority="high",
        )
        _safe_move(drop_dir, PODCAST / "incoming" / "_failed", "PODCAST")
        return

    # Move incoming → processing
    work_dir = _safe_move(drop_dir, PODCAST / "processing", "PODCAST")
    full_video = next((v for v in work_dir.glob("*.mp4") if "full" in v.name.lower()), None)

    # Schedule: full episode goes up the day after the drop is processed; shorts same day
    today = datetime.now(ET)
    yt_start = today.strftime("%Y-%m-%d")
    shorts_start = today.strftime("%Y-%m-%d")

    cmd = [
        sys.executable,
        str(PODCAST_PIPELINE),
        "--episode", name,
        "--source", str(work_dir),
        "--full-video", str(full_video),
        "--yt-start-date", yt_start,
        "--shorts-start-date", shorts_start,
    ]
    ok, out = _run_subprocess(cmd, timeout_sec=4 * 3600)

    if not ok:
        emit_navi_task(
            title=f"Podcast pipeline failed — {name}",
            description=(
                f"scripts/podcast/pipeline.py exited non-zero for drop {name}. "
                f"Drop is in {work_dir}. Last 500 chars of output:\n\n{out.strip()[-500:]}"
            ),
            priority="high",
        )
        _safe_move(work_dir, PODCAST / "incoming" / "_failed", "PODCAST")
        return

    # Success: copy rendered clips to the buffer archive, also copy the clips_plan metadata,
    # then move the raw drop to archive/.
    rendered_clips_dir = PODCAST_RENDERED_CLIPS_ROOT / _safe_episode_name(name)
    if rendered_clips_dir.exists():
        archive_target = PODCAST / "clips-archive" / name
        archive_target.mkdir(parents=True, exist_ok=True)
        n_copied = 0
        for mp4 in rendered_clips_dir.glob("*.mp4"):
            shutil.copy2(mp4, archive_target / mp4.name)
            n_copied += 1
        # Preserve the clips_plan metadata so the buffer scheduler can still recover titles/hooks
        clips_plan_all = _REPO_ROOT / "data" / "podcast" / "clips_plan" / "_all.json"
        if clips_plan_all.exists():
            shutil.copy2(clips_plan_all, archive_target / "_all.json")
        log.info(f"[PODCAST] archived {n_copied} rendered clips → {archive_target}")
    else:
        log.warning(f"[PODCAST] expected rendered clips at {rendered_clips_dir} but didn't find any")

    _safe_move(work_dir, PODCAST / "archive", "PODCAST")
    state["podcast_seen"].append(name)
    log.info(f"[PODCAST] archived {name}")


# --- Photo pipeline --------------------------------------------------------

def _process_photo_drop(state: dict) -> None:
    incoming = PHOTOS / "incoming"
    pngs = [p for p in incoming.glob("*.png") if _file_is_stable(p)]
    if not pngs:
        return

    drop_id = f"{datetime.now(ET).strftime('%Y-%m-%d')}-{len(state['photos_seen']) + 1:03d}"
    processing_dir = PHOTOS / "processing" / drop_id
    processing_dir.mkdir(parents=True, exist_ok=True)
    for p in pngs:
        shutil.move(str(p), str(processing_dir / p.name))
    log.info(f"[PHOTOS] grouped {len(pngs)} PNGs into processing drop {drop_id}")

    start_date = datetime.now(ET).strftime("%Y-%m-%d")
    cmd = [
        sys.executable,
        str(PHOTO_PIPELINE),
        "--start-date", start_date,
        "--execute",
    ]
    env = os.environ.copy()
    env["PHOTOS_DIR"] = str(processing_dir)  # schedule_photos.py reads this env var
    ok, out = _run_subprocess(cmd, timeout_sec=1800, env=env)

    if not ok:
        emit_navi_task(
            title=f"Photo pipeline failed — drop {drop_id}",
            description=(
                f"scripts/social/schedule_photos.py failed for drop {drop_id} "
                f"({len(pngs)} PNGs). Files are in {processing_dir}. "
                f"Last 500 chars:\n\n{out.strip()[-500:]}"
            ),
            priority="high",
        )
        _safe_move(processing_dir, PHOTOS / "incoming" / "_failed", "PHOTOS")
        return

    _safe_move(processing_dir, PHOTOS / "archive", "PHOTOS")
    state["photos_seen"].append(drop_id)
    log.info(f"[PHOTOS] archived drop {drop_id}")


# --- Music bed auto-normalize ----------------------------------------------

def _process_music_beds() -> None:
    """Normalize any new music-bed source files dropped into the NAS folder.

    User drops raw OSTs into /media/podcast/music-beds/ (visible over SMB);
    prepare_music.py normalizes to -18 LUFS and writes to /app/data/music-beds/,
    which is what render_clip.py reads from.

    Idempotent — fast-paths when every source already has a normalized twin, so
    it's cheap to call on every poll cycle.
    """
    if not MUSIC_SOURCE.exists():
        return
    sources = [
        p for p in MUSIC_SOURCE.rglob("*")
        if p.is_file()
        and p.suffix.lower() in MUSIC_EXTENSIONS
        and _file_is_stable(p)
    ]
    if not sources:
        return
    needs_work = [s for s in sources if not (MUSIC_NORMALIZED / f"{s.stem}.wav").exists()]
    if not needs_work:
        return
    log.info(f"[MUSIC] {len(needs_work)} new OST file(s) detected — normalizing")
    MUSIC_NORMALIZED.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, str(PREPARE_MUSIC), "--source", str(MUSIC_SOURCE)]
    ok, out = _run_subprocess(cmd, timeout_sec=1800)
    if not ok:
        emit_navi_task(
            title="Music bed normalization failed",
            description=(
                f"scripts/podcast/prepare_music.py failed while processing new OSTs in "
                f"{MUSIC_SOURCE}. Last 500 chars:\n\n{out.strip()[-500:]}"
            ),
            priority="medium",
        )
        return
    log.info("[MUSIC] normalization complete")


# --- Scan loop -------------------------------------------------------------

def _scan(state: dict) -> None:
    # Podcast: look for fresh EP-* drops
    podcast_in = PODCAST / "incoming"
    if podcast_in.exists():
        for drop in sorted(podcast_in.iterdir()):
            if not drop.is_dir():
                continue
            if drop.name.startswith("_"):  # e.g. _failed
                continue
            if drop.name in state["podcast_seen"]:
                continue
            if not _drop_is_stable(drop):
                log.info(f"[PODCAST] {drop.name} still being written — waiting")
                continue
            try:
                _process_podcast_drop(drop, state)
            except Exception as exc:
                log.exception(f"[PODCAST] unexpected failure on {drop.name}")
                emit_navi_task(
                    title=f"Watcher crashed processing {drop.name}",
                    description=f"Unhandled exception in drop_watcher: {exc}",
                    priority="high",
                )

    # Photos: scan once per cycle (all pending PNGs grouped into one drop)
    if (PHOTOS / "incoming").exists():
        try:
            _process_photo_drop(state)
        except Exception as exc:
            log.exception("[PHOTOS] unexpected failure")
            emit_navi_task(
                title="Watcher crashed processing photo drop",
                description=f"Unhandled exception in drop_watcher photo scan: {exc}",
                priority="high",
            )

    # Music beds: auto-normalize any new OST files in the NAS folder
    try:
        _process_music_beds()
    except Exception as exc:
        log.exception("[MUSIC] unexpected failure")
        emit_navi_task(
            title="Watcher crashed processing music beds",
            description=f"Unhandled exception in drop_watcher music scan: {exc}",
            priority="medium",
        )

    state["last_scan"] = datetime.now(ET).isoformat()
    _save_state(state)


def _run_buffer_scheduler() -> None:
    if not BUFFER_SCHEDULER.exists():
        log.warning(f"buffer_scheduler not at {BUFFER_SCHEDULER}, skipping")
        return
    log.info("[BUFFER] invoking buffer scheduler")
    ok, out = _run_subprocess([sys.executable, str(BUFFER_SCHEDULER)], timeout_sec=600)
    if not ok:
        emit_navi_task(
            title="Buffer scheduler failed",
            description=f"buffer_scheduler.py exited non-zero. Last output:\n\n{out.strip()[-800:]}",
            priority="medium",
        )


def _run_forever() -> int:
    log.info(
        f"drop_watcher starting — MEDIA_ROOT={MEDIA_ROOT}, "
        f"poll={POLL_INTERVAL_SEC}s, scripts={_SCRIPTS_ROOT}, "
        f"buffer every {BUFFER_EVERY_N_POLLS} polls"
    )

    stop = False

    def _shutdown(signum: int, _frame: object) -> None:
        nonlocal stop
        log.info(f"got signal {signum}, shutting down")
        stop = True

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    poll_count = 0
    while not stop:
        try:
            state = _load_state()
            _scan(state)
            if poll_count > 0 and poll_count % BUFFER_EVERY_N_POLLS == 0:
                _run_buffer_scheduler()
        except Exception as exc:
            log.exception(f"scan cycle crashed: {exc}")
            emit_navi_task(
                title="drop_watcher scan cycle crashed",
                description=f"{exc!r} — watcher will retry in {POLL_INTERVAL_SEC}s",
                priority="high",
            )
        poll_count += 1
        # Sleep in short chunks so SIGTERM is responsive
        for _ in range(POLL_INTERVAL_SEC):
            if stop:
                break
            time.sleep(1)
    log.info("drop_watcher stopped")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="8-Bit Legacy drop-folder watcher.")
    parser.add_argument("--once", action="store_true", help="Run one scan then exit")
    args = parser.parse_args()
    if args.once:
        state = _load_state()
        _scan(state)
        return 0
    return _run_forever()


if __name__ == "__main__":
    sys.exit(main())
