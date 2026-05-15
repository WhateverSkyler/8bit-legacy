"""Audio-waveform silence detection for clip end-boundary placement.

Round 14 (2026-05-14): rebuilt end-boundary placement to use REAL audio silence
instead of text-derived sentence boundaries. The previous text-based approach
(round 13: HIGH/MED/LOW sentence boundary_confidence + safe_breath_pad +
0.10s safety margin) kept producing clips that cut mid-word in the audio,
because whisperX word timing isn't audio-aligned to actual silence and
"sentences" with 0.5-1.0s text-gaps can have continuous speech audio between
them (the speaker's breath/room tone is louder than -30dB).

This module's job: identify the REAL pause points in an episode's audio via
ffmpeg silencedetect, cache them per-episode, and provide a lookup that
returns clip-end timestamps guaranteed to land in actual silence.

Threshold tuning (May 5 2026 episode sweep):
- -30dB catches breath/HVAC noise → 1139 events for 67min episode (too many).
- -35dB:d=0.20 → 654 events (≈10/min, ~one per 6s, matches natural pause density).
- -40dB:d=0.25 → 261 events (some real conversational pauses get missed).

Picked -35dB:d=0.20 for the wide net. Strict end-boundary picking then
filters to silence_duration ≥ MIN_END_SILENCE_SEC (0.30s) — REAL pauses, not
mid-word stops.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

# ----------------------------------------------------------------------------
# Tunables
# ----------------------------------------------------------------------------
SILENCE_DB = -35              # ffmpeg silencedetect noise floor
SILENCE_MIN_DUR = 0.20        # min silence duration the detector reports (seconds)

# For clip-end placement we require LONGER silences than the detector's floor.
# A 0.20s "silence" is often a mid-word stop on a hard consonant; we want a
# real pause where the speaker has finished a thought.
MIN_END_SILENCE_SEC = 0.30

# Round 17 (2026-05-14): the end-completion GATE (Claude judgment over
# multiple candidates) can consider slightly tighter pauses than the
# first-pass _snap_and_validate placement. Reason: when the gate is
# EXTENDing to capture a payoff (e.g., "guess which franchise → Mario"),
# the answer-landing silence is sometimes shorter than the setup-landing
# silence. Strict 0.30s threshold for _snap_and_validate keeps initial
# placement clean; relaxed 0.22s for gate candidates gives Claude more
# options without lowering the bar for clips with no over-extension.
GATE_END_MIN_SILENCE_SEC = 0.22

# Offset into the silence period at which the clip ends. 100ms gives the audio
# a clean tail of post-word silence before the visual/audio fade kicks in.
END_OFFSET_INTO_SILENCE = 0.10

# Format string for the disk-cache params field. If this changes, caches
# invalidate automatically.
PARAMS_FINGERPRINT = f"{SILENCE_DB}dB:d={SILENCE_MIN_DUR}"

_SILENCE_START_RE = re.compile(r"silence_start:\s*([0-9.]+)")
_SILENCE_END_RE = re.compile(
    r"silence_end:\s*([0-9.]+)\s*\|\s*silence_duration:\s*([0-9.]+)"
)


# ----------------------------------------------------------------------------
# Cache infrastructure
# ----------------------------------------------------------------------------
def _cache_path_for(audio_path: Path) -> Path:
    """Cache lives next to the audio file as <stem>.silence.json. Keeps the
    1:1 mapping between audio and silence map (re-encoded audio invalidates
    cleanly), and avoids assuming a transcripts/ sibling directory exists."""
    return audio_path.parent / f"{audio_path.stem}.silence.json"


def _cache_key(audio_path: Path) -> dict:
    """Composite key: file mtime + size + ffmpeg params fingerprint.

    Re-encoded source (different bytes), threshold tuning (different
    fingerprint), or moved/touched file (different mtime) all invalidate.
    """
    st = audio_path.stat()
    return {
        "audio_mtime": st.st_mtime,
        "audio_size": st.st_size,
        "params": PARAMS_FINGERPRINT,
    }


def _load_cache(cache_file: Path, expected_key: dict) -> list[dict] | None:
    if not cache_file.exists():
        return None
    try:
        blob = json.loads(cache_file.read_text())
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(blob, dict):
        return None
    if blob.get("audio_mtime") != expected_key["audio_mtime"]:
        return None
    if blob.get("audio_size") != expected_key["audio_size"]:
        return None
    if blob.get("params") != expected_key["params"]:
        return None
    periods = blob.get("periods")
    if not isinstance(periods, list):
        return None
    return periods


def _save_cache(cache_file: Path, key: dict, periods: list[dict]) -> None:
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    payload = {**key, "periods": periods}
    cache_file.write_text(json.dumps(payload, indent=2))


# ----------------------------------------------------------------------------
# silencedetect runner
# ----------------------------------------------------------------------------
def _run_silencedetect(audio_path: Path) -> list[dict]:
    """Run ffmpeg silencedetect on the file, parse stderr, return periods.

    ffmpeg's silencedetect emits one start line + one end line per silence
    period. Output goes to stderr. We pair them by order — the format is
    deterministic.
    """
    cmd = [
        "ffmpeg", "-hide_banner", "-nostats",
        "-i", str(audio_path),
        "-af", f"silencedetect=n={SILENCE_DB}dB:d={SILENCE_MIN_DUR}",
        "-f", "null", "-",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    starts: list[float] = []
    ends: list[tuple[float, float]] = []  # (end_t, duration)
    for line in proc.stderr.splitlines():
        m = _SILENCE_START_RE.search(line)
        if m:
            starts.append(float(m.group(1)))
            continue
        m = _SILENCE_END_RE.search(line)
        if m:
            ends.append((float(m.group(1)), float(m.group(2))))
    # Pair by order; if mismatched (shouldn't happen), truncate to min length.
    n = min(len(starts), len(ends))
    return [
        {"start": starts[i], "end": ends[i][0], "duration": ends[i][1]}
        for i in range(n)
    ]


def compute_silence_map(audio_path: Path) -> list[dict]:
    """Return list of silence periods (start, end, duration) for the given
    audio file. Cached on disk by mtime+size+params.

    `audio_path` should be the 1080p source mp4 (dialogue-only — no music
    is mixed in until render time, so silencedetect sees real audio pauses).
    """
    cache_file = _cache_path_for(audio_path)
    key = _cache_key(audio_path)
    cached = _load_cache(cache_file, key)
    if cached is not None:
        return cached
    periods = _run_silencedetect(audio_path)
    _save_cache(cache_file, key, periods)
    return periods


# ----------------------------------------------------------------------------
# Boundary lookup
# ----------------------------------------------------------------------------
def best_end_in_window(silence_map: list[dict], target_end: float,
                       search_lo: float, search_hi: float,
                       min_silence: float = MIN_END_SILENCE_SEC) -> float | None:
    """Return the clip-end timestamp closest to `target_end` that lands in
    real audio silence within [search_lo, search_hi].

    Filters silence_map to periods with `duration >= min_silence` (real
    pauses, not consonant stops) whose `start` is inside the window.
    Picks the one whose start is closest to target_end; on ties, prefers
    the LONGER silence period (more emphatic landing).

    Returns silence["start"] + END_OFFSET_INTO_SILENCE (100ms into silence
    so the clip end has a clean post-word tail before fade).

    Returns None if no qualifying silence exists. Caller should widen the
    window or REJECT the pick — do NOT fall back to text-based snapping
    (the broken path this module exists to replace).
    """
    qualifying = [
        s for s in silence_map
        if search_lo <= s["start"] <= search_hi and s["duration"] >= min_silence
    ]
    if not qualifying:
        return None
    qualifying.sort(key=lambda s: (abs(s["start"] - target_end), -s["duration"]))
    chosen = qualifying[0]
    return chosen["start"] + END_OFFSET_INTO_SILENCE


def nearest_silence_at_or_after(silence_map: list[dict], target_t: float,
                                forward_window: float = 5.0,
                                back_window: float = 5.0,
                                min_duration: float = GATE_END_MIN_SILENCE_SEC,
                                ) -> float | None:
    """Round 19 (2026-05-14): given an LLM-identified semantic conclusion
    timestamp, return the clip-end timestamp at the nearest REAL audio
    silence period at-or-after that point. Preserves the round-14 guarantee
    that clip ends always land in real silence (no mid-word cuts).

    Search order:
      1. Forward: first silence whose `start >= target_t` AND
         `start <= target_t + forward_window` AND `duration >= min_duration`.
      2. If nothing forward: backward to the latest silence whose `start <=
         target_t` AND `start >= target_t - back_window` AND duration ok.

    Returns `silence_start + END_OFFSET_INTO_SILENCE` (= 100ms into the
    silence). Returns None if no qualifying silence within ±forward/back.

    Used by `_end_completion_gate` (round 19) to snap an LLM-returned
    semantic conclusion timestamp to the closest real audio pause.
    """
    forward: dict | None = None
    backward: dict | None = None
    for s in silence_map:
        if s["duration"] < min_duration:
            continue
        if target_t <= s["start"] <= target_t + forward_window:
            forward = s
            break  # silence_map is sorted; first hit is closest forward
        if target_t - back_window <= s["start"] < target_t:
            backward = s  # keep updating to find LATEST in back window
    chosen = forward if forward is not None else backward
    if chosen is None:
        return None
    return chosen["start"] + END_OFFSET_INTO_SILENCE


def silence_candidates_for_gate(silence_map: list[dict],
                                lo: float, hi: float,
                                min_silence: float = MIN_END_SILENCE_SEC,
                                max_n: int = 6) -> list[dict]:
    """Return the silence periods within [lo, hi] that qualify as candidate
    clip-ends, sorted by START time ascending. Used by `_end_completion_gate`
    to show Claude a set of silence-aligned ending options to choose from.

    Each returned dict has:
      start:     silence_start (seconds)
      end:       silence_end (seconds)
      duration:  silence duration (seconds)
      clip_end:  start + END_OFFSET_INTO_SILENCE (where the clip would end)
    """
    qualifying = [
        {**s, "clip_end": s["start"] + END_OFFSET_INTO_SILENCE}
        for s in silence_map
        if lo <= s["start"] <= hi and s["duration"] >= min_silence
    ]
    qualifying.sort(key=lambda s: s["start"])
    return qualifying[:max_n]
