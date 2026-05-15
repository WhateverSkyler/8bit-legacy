"""Audio silence breakpoint detection for short-form clip extraction.

ffmpeg's silencedetect is a measurement tool, not a heuristic — it reports the
audio periods that ARE silent. We use it as ground truth for where a clip can
start or end. The transcript is consulted only for word timing (which is
reliable); transcript punctuation is ignored entirely.

Design choices (see plan: wild-brewing-pearl.md §3 and §pre-processing):
- Detect at -35 dB / 0.30s minimum, then filter to >= 0.45s for breakpoints.
- 0.45s is the floor where pauses are communicatively meaningful in
  fast-paced multi-speaker banter (Heldner & Edlund 2010 conversational pause
  research). Below that, you pick up breath catches and consonant gaps.
- Density retry: if breakpoints/minute falls outside [2, 30], try -30 dB and
  -40 dB once each and pick whichever lands inside that band. Catches
  recordings that are noticeably quieter or louder than the May 5 baseline.
"""
from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass, asdict
from pathlib import Path

# Detector settings (we cast a wide net here)
_DETECT_NOISE_DB_DEFAULT = -35
_DETECT_MIN_SILENCE_SEC = 0.30  # fed to ffmpeg silencedetect d= parameter

# Breakpoint qualification (the meaningful threshold).
#
# We started at 0.45s based on conversation-research priors, but real episode
# testing on April 19 produced sparse breakpoint maps (1-2 per minute) on
# fast-talking topics. With sparse breakpoints, the model has very few
# clip-width options and routinely overshoots the 90s cap.
#
# 0.35s gives the model meaningfully more endpoint choice while staying
# clearly above breath/consonant gaps. The prompt explicitly nudges toward
# longer silences (≥1.0s) for clip endings, so weak breakpoints get used
# mostly for starts (where they're fine — start is just "after a pause").
# Indices-not-floats means Claude can simply ignore breakpoints it judges
# too weak for the position it needs.
BREAKPOINT_MIN_DURATION_SEC = 0.35

# Density sanity bounds (breakpoints per minute of audio)
_DENSITY_MIN_PER_MIN = 2.0
_DENSITY_MAX_PER_MIN = 30.0
_DENSITY_RETRY_FLOORS_DB = (-30, -40)

# ffmpeg silencedetect emits two log lines per silence period
_RE_SILENCE_START = re.compile(r"silence_start:\s*([0-9.]+)")
_RE_SILENCE_END = re.compile(r"silence_end:\s*([0-9.]+)\s+\|\s+silence_duration:\s*([0-9.]+)")


@dataclass(frozen=True)
class Breakpoint:
    """One real audio silence that's a candidate clip start/end position."""
    idx: int          # 0-based, assigned in chronological order after filtering
    start: float      # seconds from start of topic file
    end: float        # seconds from start of topic file
    duration: float   # seconds (= end - start)

    @property
    def mid_sec(self) -> float:
        return (self.start + self.end) / 2.0


def _run_silencedetect(audio_path: Path, noise_db: int, min_silence_sec: float) -> list[dict]:
    """Run ffmpeg silencedetect once and parse stderr.

    Returns raw silence periods (NOT yet filtered to >= 0.45s).
    Each dict: {start, end, duration} as floats, in audio-time seconds.
    """
    cmd = [
        "ffmpeg", "-hide_banner", "-nostats", "-i", str(audio_path),
        "-af", f"silencedetect=noise={noise_db}dB:d={min_silence_sec}",
        "-f", "null", "-",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        # silencedetect itself can return 0 even with a junk file; if ffmpeg
        # truly failed (bad path, codec issue) we want to know.
        raise RuntimeError(f"ffmpeg silencedetect failed for {audio_path}: {proc.stderr[:500]}")

    silences: list[dict] = []
    pending_start: float | None = None
    for line in proc.stderr.splitlines():
        if (m := _RE_SILENCE_START.search(line)):
            pending_start = float(m.group(1))
            continue
        if (m := _RE_SILENCE_END.search(line)):
            end_sec = float(m.group(1))
            dur = float(m.group(2))
            start_sec = pending_start if pending_start is not None else max(0.0, end_sec - dur)
            silences.append({"start": start_sec, "end": end_sec, "duration": dur})
            pending_start = None
    return silences


def _filter_to_breakpoints(silences: list[dict]) -> list[Breakpoint]:
    """Apply the 0.45s qualification threshold and assign chronological indices."""
    qualified = [s for s in silences if s["duration"] >= BREAKPOINT_MIN_DURATION_SEC]
    qualified.sort(key=lambda s: s["start"])
    return [
        Breakpoint(idx=i, start=s["start"], end=s["end"], duration=s["duration"])
        for i, s in enumerate(qualified)
    ]


def _density_per_minute(breakpoints: list[Breakpoint], topic_duration_sec: float) -> float:
    if topic_duration_sec <= 0:
        return 0.0
    return len(breakpoints) / (topic_duration_sec / 60.0)


def _cache_path_for(audio_path: Path) -> Path:
    """Cache sits next to the audio file as `<stem>.silence.json`.

    Keeps a 1:1 mapping between audio and silence map (re-encoded audio
    invalidates cleanly via mtime check) and avoids assuming any sibling
    directory layout exists.
    """
    return audio_path.parent / f"{audio_path.stem}.silence.json"


def _load_cache(cache_path: Path, audio_path: Path) -> list[Breakpoint] | None:
    if not cache_path.exists():
        return None
    try:
        data = json.loads(cache_path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    # Invalidate if the audio file was modified after the cache.
    try:
        if audio_path.stat().st_mtime > cache_path.stat().st_mtime:
            return None
    except OSError:
        return None
    if data.get("min_silence_for_breakpoint") != BREAKPOINT_MIN_DURATION_SEC:
        return None
    return [Breakpoint(**bp) for bp in data.get("breakpoints", [])]


def _save_cache(cache_path: Path, audio_path: Path, breakpoints: list[Breakpoint],
                noise_db: int, topic_duration_sec: float) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "source_audio": str(audio_path),
        "noise_floor_db": noise_db,
        "min_silence_for_detect": _DETECT_MIN_SILENCE_SEC,
        "min_silence_for_breakpoint": BREAKPOINT_MIN_DURATION_SEC,
        "topic_duration_sec": topic_duration_sec,
        "density_per_minute": round(_density_per_minute(breakpoints, topic_duration_sec), 2),
        "breakpoints": [asdict(bp) for bp in breakpoints],
    }
    cache_path.write_text(json.dumps(payload, indent=2))


def compute_breakpoints(audio_path: Path, topic_duration_sec: float,
                        use_cache: bool = True) -> list[Breakpoint]:
    """Main entry point: return the qualified breakpoint list for one topic file.

    Tries the default -35 dB floor first. If breakpoint density per minute is
    outside [2, 30], retries with -30 and -40 dB and picks the floor whose
    density falls in band (or whichever is closest if neither does).

    Caches by `<stem>.silence.json` next to the transcript.
    """
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio source missing: {audio_path}")

    cache_path = _cache_path_for(audio_path)
    if use_cache:
        cached = _load_cache(cache_path, audio_path)
        if cached is not None:
            return cached

    # Default floor first.
    silences = _run_silencedetect(audio_path, _DETECT_NOISE_DB_DEFAULT, _DETECT_MIN_SILENCE_SEC)
    breakpoints = _filter_to_breakpoints(silences)
    chosen_floor = _DETECT_NOISE_DB_DEFAULT
    density = _density_per_minute(breakpoints, topic_duration_sec)

    if not (_DENSITY_MIN_PER_MIN <= density <= _DENSITY_MAX_PER_MIN):
        # Try alternate floors.
        candidates: list[tuple[int, list[Breakpoint], float]] = [
            (_DETECT_NOISE_DB_DEFAULT, breakpoints, density),
        ]
        for alt_db in _DENSITY_RETRY_FLOORS_DB:
            alt_silences = _run_silencedetect(audio_path, alt_db, _DETECT_MIN_SILENCE_SEC)
            alt_bps = _filter_to_breakpoints(alt_silences)
            candidates.append((alt_db, alt_bps, _density_per_minute(alt_bps, topic_duration_sec)))

        # Prefer any candidate whose density is in band; otherwise pick the
        # closest to the band's midpoint.
        in_band = [c for c in candidates
                   if _DENSITY_MIN_PER_MIN <= c[2] <= _DENSITY_MAX_PER_MIN]
        if in_band:
            chosen = in_band[0]
        else:
            mid = (_DENSITY_MIN_PER_MIN + _DENSITY_MAX_PER_MIN) / 2.0
            chosen = min(candidates, key=lambda c: abs(c[2] - mid))
        chosen_floor, breakpoints, density = chosen
        print(f"  [silence] density {candidates[0][2]:.1f}/min outside [2,30] at -35dB; "
              f"chose {chosen_floor}dB → {density:.1f}/min")

    if use_cache:
        _save_cache(cache_path, audio_path, breakpoints, chosen_floor, topic_duration_sec)
    return breakpoints


def find_breakpoint_for_audio(transcript_path: Path) -> Path:
    """Resolve a transcript .json path to its source audio file.

    Pipeline convention: transcripts at data/podcast/transcripts/<stem>.json
    correspond to source video at data/podcast/source/1080p/<stem>.mp4.
    """
    repo_root = transcript_path.resolve().parent.parent.parent.parent
    candidate = repo_root / "data" / "podcast" / "source" / "1080p" / f"{transcript_path.stem}.mp4"
    if candidate.exists():
        return candidate
    # Fallback: read the "source" field embedded in the transcript JSON
    try:
        data = json.loads(transcript_path.read_text())
        embedded = data.get("source")
        if embedded and Path(embedded).exists():
            return Path(embedded)
    except (OSError, json.JSONDecodeError):
        pass
    raise FileNotFoundError(
        f"Cannot locate source audio for transcript {transcript_path}. "
        f"Looked at {candidate} and the transcript's 'source' field."
    )
