"""Per-episode speaker profile — fixed crop_x per speaker, detected ONCE.

Round 15 (2026-05-14) — user feedback:

  "can we not just hardcode a specific X value for the crop based on each
   person speaking like if its Ryan it will always be a specific x value
   and if tristan than a specific x value and that is just detected once on
   the podcast video and used throughout all the shorts… i dont need this
   super fancy dynamic tracking if i temporarily move far left/right for a
   few seconds than where i normally am then its fine as long as its just
   default centered where i typically am most of the video bc we dont
   really move that much"

The podcast has 2-3 speakers in FIXED seat positions; each speaker's
camera shows them at roughly the same face_x across the entire episode.
Round 14's per-scene YuNet active-speaker call still drifted with head
movements and lagged at shot transitions because each scene had to
re-decide WHO is on camera AND WHERE their face is. That round chose the
right speaker but the X value still wobbled.

This module computes a per-episode profile ONCE: which speakers exist,
where each speaker's face typically sits in source-X coordinates. The
render path then just identifies WHICH speaker is on screen per scene
(1-3 sample frames is enough) and uses the speaker's CANONICAL X — no
per-clip face-position drift, no slow lag at shot transitions.

Output: list of speaker dicts, each {speaker_id, canonical_x, x_min,
x_max, sample_count}. Sorted by x ascending (speaker 0 = leftmost on
camera).
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Optional


# -------- tunables -----------------------------------------------------------

SAMPLE_FPS = 1.0            # 1 frame per second of source — fast + plenty of stats
HISTOGRAM_BIN_PX = 60       # histogram bin width for face_x distribution
MIN_PEAK_SAMPLES_FRAC = 0.02  # peak bin must have >= 2% of total samples to be a speaker
MERGE_DISTANCE_PX = 200     # peaks within this many pixels get merged (one speaker
                            # might span 2 adjacent bins; this folds them in)
MAX_SPEAKERS = 4            # 3-person podcast + maybe a wide shot → cap at 4 peaks


def _cache_path_for(audio_path: Path) -> Path:
    """Cache lives next to the source mp4 as <stem>.speakers.json."""
    return audio_path.parent / f"{audio_path.stem}.speakers.json"


def _cache_key(audio_path: Path) -> dict:
    """Composite key — mtime + size. Source re-encode or replace invalidates."""
    st = audio_path.stat()
    return {"audio_mtime": st.st_mtime, "audio_size": st.st_size,
            "merge_distance_px": MERGE_DISTANCE_PX}


def _load_cache(path: Path, expected: dict) -> Optional[list[dict]]:
    if not path.exists():
        return None
    try:
        blob = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(blob, dict):
        return None
    for k in ("audio_mtime", "audio_size", "merge_distance_px"):
        if blob.get(k) != expected.get(k):
            return None
    speakers = blob.get("speakers")
    if not isinstance(speakers, list):
        return None
    return speakers


def _save_cache(path: Path, key: dict, speakers: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({**key, "speakers": speakers}, indent=2))


# -------- 1-fps face-x sampling ----------------------------------------------

def _sample_face_xs(video_path: Path) -> list[int]:
    """Walk the video at SAMPLE_FPS, run YuNet on each frame, collect the
    X-center of the LARGEST detected face per frame. Frames with no face
    are skipped.
    """
    import cv2  # type: ignore
    from _face_detect import FaceDetector

    det = FaceDetector.get()
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"cv2 could not open {video_path}")
    try:
        fps_src = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        if total <= 0:
            duration = 0.0
        else:
            duration = total / fps_src
        if duration < 1.0:
            return []
        n_samples = int(duration * SAMPLE_FPS)
        xs: list[int] = []
        for i in range(n_samples):
            t = i / SAMPLE_FPS
            cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000.0)
            ok, frame = cap.read()
            if not ok or frame is None:
                continue
            faces = det.detect(frame)
            # Take the LARGEST face on the frame — we want the active speaker's
            # CAMERA framing, and the largest face is the one the camera is
            # focused on. If multiple speakers are visible at similar sizes
            # (wide shot), we'll catch their positions across many samples and
            # cluster them in the next step.
            if faces:
                xs.append(faces[0]["cx"])
        return xs
    finally:
        cap.release()


# -------- clustering ---------------------------------------------------------

def _cluster_xs(xs: list[int]) -> list[dict]:
    """Find speaker clusters via histogram peak detection.

    Algorithm:
      1. Bin face_x samples into HISTOGRAM_BIN_PX-wide buckets.
      2. Find LOCAL MAXIMA whose count >= MIN_PEAK_SAMPLES_FRAC of total samples.
      3. Merge peaks within MERGE_DISTANCE_PX (treat as same speaker).
      4. For each peak, derive canonical_x = median of samples in the peak's
         neighborhood (peak bin ± 2 bins), and the [min, max] range.

    Why histogram peaks instead of sequential gap clustering: in a multi-
    camera edited podcast, face_x is a continuous distribution across
    speakers — the gaps between peaks are small (~150 px between Tristan
    and Madison's seat positions, etc.). Gap-based clustering merges them.
    Peak detection identifies each speaker's MODE position, which is
    exactly what the user wants ("default centered where i typically am").
    """
    if not xs:
        return []
    n_total = len(xs)
    min_peak_count = max(3, int(n_total * MIN_PEAK_SAMPLES_FRAC))

    n_bins = (1920 // HISTOGRAM_BIN_PX) + 1
    hist = [0] * n_bins
    for x in xs:
        idx = min(n_bins - 1, max(0, x // HISTOGRAM_BIN_PX))
        hist[idx] += 1

    # Smooth with a 3-bin window so a single speaker's cluster — which can
    # spread across 2-3 adjacent bins as their face naturally shifts within
    # their seat — registers as one strong peak instead of three weak ones.
    smoothed = [0] * n_bins
    for i in range(n_bins):
        left = hist[i - 1] if i > 0 else 0
        right = hist[i + 1] if i < n_bins - 1 else 0
        smoothed[i] = left + hist[i] + right

    # Find local maxima on the SMOOTHED histogram: a bin is a peak if its
    # smoothed count is >= both smoothed neighbors AND the bin's own raw
    # count meets the threshold (avoids picking up smoothing-induced fake
    # peaks in low-count regions).
    raw_peaks: list[tuple[int, int]] = []  # (bin_idx, raw_count)
    for i in range(n_bins):
        if hist[i] < min_peak_count and smoothed[i] < min_peak_count * 2:
            continue
        s = smoothed[i]
        left = smoothed[i - 1] if i > 0 else 0
        right = smoothed[i + 1] if i < n_bins - 1 else 0
        if s >= left and s >= right and s > 0:
            raw_peaks.append((i, hist[i]))

    if not raw_peaks:
        # No clear peaks → fall back: single cluster at the median of all xs.
        sorted_xs = sorted(xs)
        median_x = sorted_xs[len(sorted_xs) // 2]
        return [{
            "speaker_id": 0,
            "canonical_x": median_x,
            "x_min": sorted_xs[0],
            "x_max": sorted_xs[-1],
            "sample_count": n_total,
        }]

    # Merge peaks within MERGE_DISTANCE_PX (sequential walk, keep the
    # higher-count peak when merging).
    raw_peaks.sort(key=lambda p: p[0])  # by bin_idx ascending
    merged: list[tuple[int, int]] = [raw_peaks[0]]
    for bin_idx, count in raw_peaks[1:]:
        prev_bin, prev_count = merged[-1]
        bin_distance_px = (bin_idx - prev_bin) * HISTOGRAM_BIN_PX
        if bin_distance_px < MERGE_DISTANCE_PX:
            # Same speaker — keep the higher-count peak
            if count > prev_count:
                merged[-1] = (bin_idx, count)
        else:
            merged.append((bin_idx, count))

    # Keep top MAX_SPEAKERS by sample count (still sorted by x position
    # after).
    merged.sort(key=lambda p: p[1], reverse=True)
    merged = merged[:MAX_SPEAKERS]
    merged.sort(key=lambda p: p[0])

    # For each peak, the "speaker neighborhood" is bins within ±2 of the
    # peak (covering ±120 px around the peak center). Samples inside this
    # window form the speaker's range; the median is canonical_x.
    speakers: list[dict] = []
    for sid, (bin_idx, count) in enumerate(merged):
        lo_bin = max(0, bin_idx - 2)
        hi_bin = min(n_bins - 1, bin_idx + 2)
        lo_x = lo_bin * HISTOGRAM_BIN_PX
        hi_x = (hi_bin + 1) * HISTOGRAM_BIN_PX
        in_range = sorted(x for x in xs if lo_x <= x < hi_x)
        if not in_range:
            continue
        median_x = in_range[len(in_range) // 2]
        speakers.append({
            "speaker_id": sid,
            "canonical_x": median_x,
            "x_min": in_range[0],
            "x_max": in_range[-1],
            "sample_count": len(in_range),
        })
    return speakers


# -------- public API ---------------------------------------------------------

def build_speaker_profile(source_video: Path) -> list[dict]:
    """Return a sorted-by-X list of speaker dicts for the episode. Cached
    on disk by mtime+size. Recomputes from scratch on cache miss.
    """
    cache = _cache_path_for(source_video)
    expected = _cache_key(source_video)
    cached = _load_cache(cache, expected)
    if cached is not None:
        return cached
    xs = _sample_face_xs(source_video)
    speakers = _cluster_xs(xs)
    _save_cache(cache, expected, speakers)
    return speakers


def speaker_for_face_x(face_x: int, profile: list[dict],
                       tolerance_px: int = 200) -> Optional[dict]:
    """Given an observed face_x and the episode's speaker profile, return
    the matching speaker dict (with canonical_x), or None if face_x is too
    far from any speaker's typical position.

    Tolerance is wide (200 px) because a speaker can lean forward/back/
    side-to-side WITHIN their normal seat without us wanting to call them
    "a different speaker". The whole point of the profile is that the
    CANONICAL X stays put even when the speaker temporarily moves.
    """
    if not profile:
        return None
    best = min(profile, key=lambda s: abs(s["canonical_x"] - face_x))
    if abs(best["canonical_x"] - face_x) <= tolerance_px:
        return best
    return None


def canonical_x_for_scene(scene_face_xs: list[int], profile: list[dict],
                          fallback_x: int) -> int:
    """Given the face_x observations from a scene (typically 1-3 samples)
    and the speaker profile, return the FIXED canonical X to use for the
    whole scene.

    Logic:
      - Collect speaker matches for each observation.
      - Pick the speaker that matches the MOST observations.
      - Return that speaker's canonical_x.
      - If no observation matches any profile speaker → fallback_x.
    """
    if not profile or not scene_face_xs:
        return fallback_x
    from collections import Counter
    matches = []
    for x in scene_face_xs:
        sp = speaker_for_face_x(x, profile)
        if sp is not None:
            matches.append(sp["speaker_id"])
    if not matches:
        return fallback_x
    most_common_id = Counter(matches).most_common(1)[0][0]
    sp = next(s for s in profile if s["speaker_id"] == most_common_id)
    return int(sp["canonical_x"])
