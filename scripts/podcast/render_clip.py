#!/usr/bin/env python3
"""Render a single 1080x1920 vertical short from a podcast topic cut.

Pipeline:
  1. Cut segment [start_sec, end_sec] from 1080p source MP4
  2. Detect camera cuts *inside* the clip (HSV-histogram Bhattacharyya jumps).
     For each scene, detect faces and compute a crop-X that keeps the subject
     centered in the 9:16 output. Stitch scenes back together via ffmpeg
     trim+concat so multi-camera clips no longer sacrifice off-center shots
     (e.g., the guy-in-front-of-arcade camera) to a single fixed center crop.
  3. Burn word-karaoke captions (Bebas Neue 96pt, white + #ff9526 active word, thick black stroke)
  4. Mix original dialogue with a random music bed at -18dB
  5. Overlay brand end-card last 4 seconds (if assets/brand/end-card-9x16.png exists)
  6. Export H.264 1080x1920 @30fps AAC 192kbps

Inputs:
  --spec data/podcast/clips_plan/<stem>.json (element index 0 if no --index)
  OR --clip-id <id> which locates the spec in _all.json

Outputs:
  data/podcast/clips/<episode>/<clip_id>.mp4

Usage:
  python3 scripts/podcast/render_clip.py --spec .../clips_plan/01-...json --index 0
  python3 scripts/podcast/render_clip.py --batch data/podcast/clips_plan/_all.json --episode "Episode April 14th 2026"
"""

from __future__ import annotations

import argparse
import json
import random
import subprocess
import sys
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parent.parent.parent
SOURCE_1080P = ROOT / "data" / "podcast" / "source" / "1080p"
TRANSCRIPTS = ROOT / "data" / "podcast" / "transcripts"
MUSIC_BEDS = ROOT / "data" / "music-beds"
CLIPS_DIR = ROOT / "data" / "podcast" / "clips"
END_CARD = ROOT / "assets" / "brand" / "end-card-9x16.png"

FONT_NAME = "Bebas Neue"
FONT_SIZE = 96              # bumped 70 → 96; users reported captions were too small on phones
FONT_OUTLINE = 7            # thicker stroke to keep proportion with the larger font
WHITE = "&H00FFFFFF"   # ASS AABBGGRR
ORANGE = "&H002695FF"  # #ff9526 → R=FF, G=95, B=26 → BBGGRR = 2695FF
BLACK = "&H00000000"

# 9:16 strip from 1920×1080: 607 px wide. Full valid X range is [0, 1313].
CROP_W = 607
SOURCE_W = 1920
CENTER_CROP_X = (SOURCE_W - CROP_W) // 2  # 656

# --- Face detection ----------------------------------------------------------
# Minimum face size (px) — filters out noise / far-background detections.
# At 1080p, typical face on-camera is ~140-220 px wide.
# 2026-04-29: lowered 90 → 60. The "Tristan in front of arcade" angle had him
# at ~70-110 px wide due to camera distance + angled pose; old 90 floor missed
# him completely → fell back to dead-center crop with subject off-frame.
FACE_MIN_SIZE = 60
# Frames sampled per detected scene when computing that scene's face center.
# Bumped 3 → 5 for better recall on scenes with brief angled poses.
FACE_SAMPLES_PER_SCENE = 5

# --- Scene detection ---------------------------------------------------------
# Sampling stride when walking the clip to find hard camera cuts (seconds).
# Lowered 0.4 → 0.15 (2026-05-07): a 0.4s stride could miss the true cut
# boundary by up to 0.4s, so the new camera angle would render with the OLD
# scene's crop_x for up to 0.4s before the next sample triggered a new scene.
# Combined with merge-into-previous, this manifested as ~1s of "cut to Madison
# but he's still off-frame" before the centering snapped. 0.15s → max stride
# latency 0.15s, ~3x compute on detection (still <1s wall on a 60s clip).
SCENE_SAMPLE_STRIDE_SEC = 0.15
# Bhattacharyya distance above which consecutive frames are flagged as a cut.
BHATTA_CUT_THRESHOLD = 0.35
# Scenes shorter than this get merged into the NEXT scene (not previous).
# Lowered 0.6 → 0.25 + flipped merge direction (2026-05-07). Old behavior was
# the second compounding bug behind the visible centering delay: when a brief
# transitional frame (camera switching) sat between two stable scenes, we'd
# absorb it into the PREVIOUS scene, extending the old crop_x into the new
# camera's content for up to MIN_SCENE_DURATION_SEC. Merging into NEXT means
# brief scenes inherit the upcoming camera's face position so the new speaker
# is centered the moment they appear on-screen.
MIN_SCENE_DURATION_SEC = 0.25
# Safety rail: if scene detection returns more scenes than this for a short,
# something is wrong with the content (compressed artifacts, rapid-fire cuts,
# etc.). Fall back to fixed center crop rather than produce a filter graph
# with 50+ trim branches.
MAX_SCENES = 15


def _ass_time(sec: float) -> str:
    sec = max(0.0, sec)
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = sec % 60
    return f"{h:d}:{m:02d}:{s:05.2f}"


def _words_in_range(transcript: dict, start: float, end: float) -> list[dict]:
    words: list[dict] = []
    for seg in transcript.get("segments", []):
        if seg["end"] < start or seg["start"] > end:
            continue
        for w in seg.get("words") or []:
            if w["end"] < start or w["start"] > end:
                continue
            ws = max(w["start"], start) - start
            we = min(w["end"], end) - start
            if we <= ws:
                continue
            words.append({"start": ws, "end": we, "word": (w["word"] or "").strip()})
    return words


def build_ass(words: list[dict], duration: float, width: int = 1080, height: int = 1920,
              words_per_group: int = 3) -> str:
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
ScaledBorderAndShadow: yes
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{FONT_NAME},{FONT_SIZE},{WHITE},{WHITE},{BLACK},&H00000000,-1,0,0,0,100,100,0,0,1,{FONT_OUTLINE},2,2,60,60,260,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events: list[str] = []
    if not words:
        return header

    groups: list[list[dict]] = []
    i = 0
    while i < len(words):
        groups.append(words[i:i + words_per_group])
        i += words_per_group

    for group in groups:
        if not group:
            continue
        for idx, active in enumerate(group):
            parts: list[str] = []
            for j, w in enumerate(group):
                txt = w["word"].upper().replace(",", "").replace(".", "").replace("?", "").replace("!", "")
                if not txt:
                    continue
                if j == idx:
                    parts.append(f"{{\\c{ORANGE}}}{txt}{{\\r}}")
                else:
                    parts.append(txt)
            text = " ".join(parts)
            start_t = active["start"]
            # end at next word's start within the group, or at group end if last word
            if idx + 1 < len(group):
                end_t = group[idx + 1]["start"]
            else:
                end_t = active["end"]
            end_t = min(end_t, duration)
            if end_t <= start_t:
                continue
            events.append(
                f"Dialogue: 0,{_ass_time(start_t)},{_ass_time(end_t)},Default,,0,0,0,,{text}"
            )
    return header + "\n".join(events) + "\n"


def _ffprobe_duration(path: Path) -> float:
    out = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path)
    ]).decode().strip()
    return float(out)


def _pick_music_bed(seed: str | None = None, mood: str | None = None) -> Path | None:
    """Select a music bed for a clip.

    If `data/music-beds/_catalog.json` exists (built by build_music_catalog.py)
    AND `mood` is provided (set by pick_clips' AUDIO_MIX_MOOD_V1 audit), restrict
    candidates to mood-compatible + podcast-appropriate beds, then deterministically
    pick by seed. Otherwise falls back to legacy random selection across all beds.

    Mood compatibility map (clip mood → preferred bed moods):
      intense:      dramatic, intense, epic
      storytelling: reflective, nostalgic, chill, mysterious
      casual:       chill, playful, nostalgic
      upbeat:       upbeat, playful, epic
    """
    candidates = sorted(list(MUSIC_BEDS.glob("*.wav")) + list(MUSIC_BEDS.glob("*.mp3")) +
                        list(MUSIC_BEDS.glob("*.flac")) + list(MUSIC_BEDS.glob("*.ogg")))
    if not candidates:
        return None

    catalog_path = MUSIC_BEDS / "_catalog.json"
    if mood and catalog_path.exists():
        try:
            import json as _json
            catalog = _json.loads(catalog_path.read_text())
        except Exception:
            catalog = {}

        compat = {
            "intense":      {"dramatic", "intense", "epic"},
            "storytelling": {"reflective", "nostalgic", "chill", "mysterious"},
            "casual":       {"chill", "playful", "nostalgic"},
            "upbeat":       {"upbeat", "playful", "epic"},
        }
        wanted = compat.get(mood.lower(), set())
        # First pass: only podcast-appropriate beds with a wanted mood
        filtered = [c for c in candidates
                    if catalog.get(c.name, {}).get("podcast_appropriate", True)
                    and catalog.get(c.name, {}).get("mood") in wanted]
        if filtered:
            rng = random.Random(seed)
            chosen = rng.choice(filtered)
            return chosen
        # Second pass: ANY podcast-appropriate bed (mood didn't match but still safe)
        appropriate = [c for c in candidates
                       if catalog.get(c.name, {}).get("podcast_appropriate", True)]
        if appropriate:
            rng = random.Random(seed)
            return rng.choice(appropriate)

    # Legacy fallback: random across all beds (no catalog OR no mood signal).
    rng = random.Random(seed)
    return rng.choice(candidates)


def _face_center_for_range(cap, cascades: list, t_start: float, t_end: float,
                           samples: int = FACE_SAMPLES_PER_SCENE,
                           min_face: int = FACE_MIN_SIZE) -> int | None:
    """Return the X-center of the most likely active speaker in [t_start, t_end].

    Delegates to scripts/podcast/_face_detect.py which uses YuNet (state-of-the-art
    lightweight face detector built into OpenCV ≥4.5) and active-speaker selection
    via mouth-corner-motion variance across multiple sampled frames.

    YuNet (built-in to opencv-python-headless, 227KB ONNX model):
      - ~95% recall on profile/angled poses (vs Haar's ~50%)
      - Returns landmarks (eye/nose/mouth corners) used for active-speaker scoring
      - Returns confidence scores

    Falls back automatically to Haar cascades if YuNet model is unavailable
    (graceful degrade — see _face_detect.FaceDetector).

    `cascades` arg retained for backward-compat signature; ignored by YuNet path.
    Samples bumped 5 → 8 in the new module (better active-speaker statistics —
    mouth-motion variance needs more samples to be reliable).
    """
    # Lazy import — keep render_clip.py importable on hosts without the new module.
    try:
        from _face_detect import face_center_for_range as _new_impl
    except ImportError:
        # Fall back to the legacy Haar median path if _face_detect isn't deployed.
        return _face_center_for_range_haar_legacy(
            cap, cascades, t_start, t_end, samples=samples, min_face=min_face,
        )
    # Use 8 samples for the new path (better mouth-motion statistics)
    return _new_impl(cap, t_start, t_end, samples=max(samples, 8))


def _face_center_for_range_haar_legacy(cap, cascades: list, t_start: float, t_end: float,
                                       samples: int = FACE_SAMPLES_PER_SCENE,
                                       min_face: int = FACE_MIN_SIZE) -> int | None:
    """Legacy Haar-cascade median fallback. Used only when _face_detect is
    unavailable (e.g., the YuNet ONNX model file is missing on a stripped
    container deploy). Kept verbatim for compatibility — caller signature
    unchanged.
    """
    import cv2  # type: ignore

    dur = max(0.1, t_end - t_start)
    xs: list[int] = []
    for i in range(samples):
        t = t_start + dur * ((i + 0.5) / samples)
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000.0)
        ok, frame = cap.read()
        if not ok or frame is None:
            continue
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        for idx, cascade in enumerate(cascades):
            search_img = gray
            mirror = (idx == 1)
            if mirror:
                search_img = cv2.flip(gray, 1)
            faces = cascade.detectMultiScale(
                search_img, scaleFactor=1.1, minNeighbors=4,
                minSize=(min_face, min_face),
            )
            if len(faces) > 0:
                w_img = search_img.shape[1]
                for (x, _y, w, _h) in faces:
                    cx = int(x + w / 2)
                    if mirror:
                        cx = w_img - cx
                    xs.append(cx)
                break

    if not xs:
        return None
    xs.sort()
    return xs[len(xs) // 2]


def _hsv_hist(frame) -> "any":
    """Normalized 8x8x8 HSV histogram. Used for frame-to-frame similarity."""
    import cv2  # type: ignore
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    hist = cv2.calcHist([hsv], [0, 1, 2], None, [8, 8, 8],
                        [0, 180, 0, 256, 0, 256])
    cv2.normalize(hist, hist, 0, 1, cv2.NORM_MINMAX)
    return hist


def detect_scenes_and_crops(
    source_video: Path,
    start_sec: float,
    end_sec: float,
    crop_w: int = CROP_W,
    source_w: int = SOURCE_W,
    cut_threshold: float = BHATTA_CUT_THRESHOLD,
) -> list[tuple[float, float, int]]:
    """Detect camera cuts inside [start_sec, end_sec] and return per-scene
    crop offsets.

    Returns a list of (scene_start_rel, scene_end_rel, crop_x) tuples, where
    times are CLIP-RELATIVE (0-based). Always returns at least one tuple
    covering the full duration — callers never have to handle an empty list.

    Args:
      cut_threshold: Bhattacharyya distance above which two consecutive
        sampled frames are flagged as a hard cut. Default 0.35 (BHATTA_CUT_THRESHOLD).
        Gate 3 rerender rescue lowers this to 0.25 to catch softer cuts the
        first pass missed (the fix path when a clip's framing is judged
        reject_reframe by Claude — a tighter threshold splits more scenes,
        each gets fresh face detection).

    Safe fallbacks (all return a single-scene center crop):
      - OpenCV not installed / cv2 can't open the source
      - Haar cascade fails to load
      - Detection throws
      - > MAX_SCENES scenes returned (detector gone wild on noisy content)
    """
    duration = max(0.1, end_sec - start_sec)
    fallback = [(0.0, duration, CENTER_CROP_X)]

    try:
        import cv2  # type: ignore
    except ImportError:
        print("  [SCENES] opencv not installed → 1 scene, center crop")
        return fallback

    cap = None
    try:
        cap = cv2.VideoCapture(str(source_video))
        if not cap.isOpened():
            print("  [SCENES] cv2 could not open source → 1 scene, center crop")
            return fallback

        # Multi-cascade chain: frontal first, then profile (twice — once on
        # the original gray, once on horizontally-flipped gray to catch the
        # opposite profile direction since OpenCV's profileface XML only
        # detects right-facing profiles).
        # 2026-04-29: added profile cascades to fix recurring miss on the
        # "Tristan in front of arcade" angle. Frontal-only previously fell
        # back to center-crop on this pose.
        frontal_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        profile_path = cv2.data.haarcascades + "haarcascade_profileface.xml"
        frontal = cv2.CascadeClassifier(frontal_path)
        if frontal.empty():
            print("  [SCENES] frontal haar cascade failed to load → 1 scene, center crop")
            return fallback
        profile = cv2.CascadeClassifier(profile_path)
        # Profile cascade is best-effort; if it fails to load, keep going with
        # frontal-only rather than abandoning detection entirely.
        cascades = [frontal]
        if not profile.empty():
            # Order: frontal, flipped-profile (left-facing), profile (right-facing).
            # The flipped variant is index 1 — _face_center_for_range mirrors
            # the search image at that index to detect left-facing profiles.
            cascades = [frontal, profile, profile]

        # --- Pass 1: walk the clip at fixed stride, diff HSV histograms -----
        # When a cut is detected between samples N-1 and N, bisect the gap to
        # find the EXACT cut frame (down to single-frame precision, 33ms at 30fps).
        # Without this refinement the cut boundary lands at the sample-N timestamp,
        # so the new camera's content can play for up to STRIDE seconds (0.15s)
        # with the OLD crop_x, producing the visible "half-second-off-center"
        # lag the user reported on c1's first cut.
        stride = SCENE_SAMPLE_STRIDE_SEC
        n_samples = max(2, int(duration / stride) + 1)
        prev_hist = None
        prev_t_rel = 0.0
        # cut_points holds clip-relative timestamps where a cut is detected
        cut_points: list[float] = [0.0]

        def _refine_cut(t_lo: float, t_hi: float, hist_lo, hist_hi) -> float:
            """Frame-by-frame walk between t_lo and t_hi (clip-relative seconds)
            to find the exact frame where the histogram jumps. Returns the
            timestamp of the FIRST frame whose histogram is closer to hist_hi
            than to hist_lo — i.e., the post-cut frame.

            2026-05-12 — snap result back by 1 frame (1/30s). The bisect already
            operates at frame-level precision, but a single frame can still slip
            through the boundary: ffmpeg's trim end is exclusive, so a cut
            reported at t=36.45 means the frame at t=36.4333 (1 frame earlier)
            still gets the OLD scene's crop_x. User saw exactly this at 36-37s
            of c2. Pulling back 1 frame is conservative: the previous scene
            loses its very last frame (invisible at 30fps) but the new camera's
            first frame is guaranteed to render with the correct centering.
            """
            # Walk every ~33ms (single frame at 30fps). Cap at 8 frames to avoid
            # unbounded looping; typical gap is 5 frames (0.15s / 30ms).
            n_steps = min(8, max(1, int((t_hi - t_lo) * 30)))
            best_t = t_hi  # default: cut is at t_hi if refinement fails
            for k in range(1, n_steps + 1):
                t = t_lo + (t_hi - t_lo) * (k / (n_steps + 1))
                cap.set(cv2.CAP_PROP_POS_MSEC, (start_sec + t) * 1000.0)
                ok, frame = cap.read()
                if not ok or frame is None:
                    continue
                h = _hsv_hist(frame)
                d_to_lo = cv2.compareHist(hist_lo, h, cv2.HISTCMP_BHATTACHARYYA)
                d_to_hi = cv2.compareHist(hist_hi, h, cv2.HISTCMP_BHATTACHARYYA)
                if d_to_hi < d_to_lo:
                    # This frame is closer to post-cut content — cut happened before this t
                    best_t = t
                    break
            # Conservative snap-back by 1 frame so the new scene's crop_x is
            # already in effect on the very first frame of the new camera.
            return max(t_lo, best_t - (1.0 / 30.0))

        for i in range(n_samples):
            t_rel = min(duration, i * stride)
            t_abs = start_sec + t_rel
            cap.set(cv2.CAP_PROP_POS_MSEC, t_abs * 1000.0)
            ok, frame = cap.read()
            if not ok or frame is None:
                continue
            hist = _hsv_hist(frame)
            if prev_hist is not None:
                d = cv2.compareHist(prev_hist, hist, cv2.HISTCMP_BHATTACHARYYA)
                if d > cut_threshold:
                    # Refine to find the exact post-cut frame within [prev_t_rel, t_rel]
                    refined = _refine_cut(prev_t_rel, t_rel, prev_hist, hist)
                    cut_points.append(refined)
            prev_hist = hist
            prev_t_rel = t_rel
        cut_points.append(duration)

        # Build initial scene list from consecutive cut points
        scenes_rel: list[tuple[float, float]] = []
        for a, b in zip(cut_points, cut_points[1:]):
            if b > a:
                scenes_rel.append((a, b))

        # --- Merge scenes shorter than MIN_SCENE_DURATION_SEC ----------------
        # Merge into the NEXT scene (not previous) so brief transitional frames
        # take on the upcoming camera's crop_x. Fixes "speaker appears off-center
        # for ~1s after a cut" by ensuring the new camera's crop is established
        # immediately at the cut, not delayed by a transitional sliver.
        merged: list[tuple[float, float]] = []
        carry_start: float | None = None
        for s, e in scenes_rel:
            scene_start = carry_start if carry_start is not None else s
            if (e - scene_start) < MIN_SCENE_DURATION_SEC:
                # Defer this scene's content into the NEXT iteration's start.
                if carry_start is None:
                    carry_start = scene_start
                continue
            merged.append((scene_start, e))
            carry_start = None
        # If a trailing brief scene was carried but never absorbed into a next,
        # attach it to the previous scene so we don't drop content.
        if carry_start is not None:
            if merged:
                ps, _pe = merged[-1]
                merged[-1] = (ps, scenes_rel[-1][1] if scenes_rel else carry_start)
            else:
                merged = [(carry_start, scenes_rel[-1][1] if scenes_rel else duration)]
        if not merged:
            merged = [(0.0, duration)]

        if len(merged) > MAX_SCENES:
            print(f"  [SCENES] {len(merged)} scenes > cap {MAX_SCENES} → 1 scene, center crop")
            return fallback

        # --- Pass 2: detect face_x per scene, then assign crop_x with look-ahead --
        # Two-pass design (2026-05-07): pass 1 collects raw face_x for each scene;
        # pass 2 fills None entries by looking AHEAD to the next detected face,
        # not BACK to the previous one. Looking back was the centering bug —
        # after a hard cut to a new speaker, brief detection failure on the
        # incoming scene would inherit the previous speaker's crop, leaving the
        # new speaker visibly off-frame until the next sample succeeded.
        face_xs: list[int | None] = []
        for s, e in merged:
            face_xs.append(_face_center_for_range(
                cap, cascades, start_sec + s, start_sec + e,
            ))
        any_face = any(fx is not None for fx in face_xs)
        if not any_face:
            print(f"  [SCENES] {len(merged)} scenes, 0 faces → 1 scene, center crop")
            return fallback
        # Last-resort fallback: if every later scene also failed, use the most
        # recent successful crop_x. Keeps stable shots stable when face detection
        # is briefly noisy mid-scene rather than crossing a real cut.
        result: list[tuple[float, float, int]] = []
        last_good_crop_x: int | None = None
        for i, ((s, e), fx) in enumerate(zip(merged, face_xs)):
            if fx is not None:
                cx = fx - crop_w // 2
                cx = max(0, min(source_w - crop_w, cx))
                last_good_crop_x = cx
            else:
                # Look ahead for the next detected face_x.
                next_fx = next((face_xs[j] for j in range(i + 1, len(face_xs))
                                if face_xs[j] is not None), None)
                if next_fx is not None:
                    cx = next_fx - crop_w // 2
                    cx = max(0, min(source_w - crop_w, cx))
                elif last_good_crop_x is not None:
                    cx = last_good_crop_x
                else:
                    cx = CENTER_CROP_X
            result.append((s, e, cx))

        # Optimization: if every scene lands on the same crop_x, collapse to
        # the fast single-scene path (identical output, simpler filter graph).
        uniq_x = {x for _s, _e, x in result}
        if len(uniq_x) == 1:
            only_x = result[0][2]
            delta = abs(only_x - CENTER_CROP_X)
            print(f"  [SCENES] {len(result)} scenes, all crop_x={only_x} (Δ{delta} from center) → collapsed to 1")
            return [(0.0, duration, only_x)]

        summary = ", ".join(f"({s:.2f}-{e:.2f}, cx={x})" for s, e, x in result)
        print(f"  [SCENES] {len(result)} scenes → {summary}")
        return result

    except Exception as exc:
        print(f"  [SCENES] detection failed: {exc} → 1 scene, center crop")
        return fallback
    finally:
        if cap is not None:
            cap.release()


# Title overlay tunables (top-of-frame text shown for first N seconds)
TITLE_OVERLAY_SECONDS = 5.0          # total time the title is on screen
TITLE_OVERLAY_FADE_IN = 0.4          # fade-in duration at the start
TITLE_OVERLAY_FADE_OUT = 0.5         # fade-out duration at the end
TITLE_OVERLAY_FONT_SIZE = 84         # bumped 72→84 for stronger presence at thumbnail size
TITLE_OVERLAY_MAX_CHARS_PER_LINE = 22  # 2-3 lines wrap for typical 4-8 word titles
TITLE_OVERLAY_Y_OFFSET = 240         # px from top — clears the iOS clock + lower for breathing room
TITLE_OVERLAY_LINE_SPACING = 18

# Brand color (matches active-word ORANGE used for karaoke captions). Hex form
# for ffmpeg's drawtext fontcolor= argument. The 0x prefix is added at use site.
BRAND_ORANGE_HEX = "ff9526"


def _wrap_title(s: str, max_chars: int = TITLE_OVERLAY_MAX_CHARS_PER_LINE) -> list[str]:
    """Wrap a title into 1-3 lines, optimizing for visual BALANCE (line-length
    parity) rather than greedy fill.

    Why: greedy left-to-right wrap routinely produced orphan-word trailers like
    "GameStop Is Trying to" / "Buy eBay" or "Pokemon Games Are Too" / "Easy
    Now" — the second line is awkwardly short and the first ends on a dangling
    preposition. Balanced split picks the break that minimizes |len(line1) -
    len(line2)|, which both reads better and looks more poster-like.

    Algorithm:
      1. If single line fits within max_chars, no wrap.
      2. Try every 2-line split point; pick the one with smallest length
         imbalance, allowing each line to stretch up to max_chars + slack
         (4 chars) so balance can win over hard-cap.
      3. If no 2-line split fits even with slack, fall back to greedy 3-line
         wrap. Cap at 3 lines, truncating the last with "…" if longer.
    """
    s = s.strip()
    if not s:
        return []
    words = s.split()

    if len(s) <= max_chars:
        return [s]

    n = len(words)
    slack = 4  # let lines stretch slightly past max_chars to win balance
    best_split = None
    best_imbalance = float("inf")

    # Function words we don't want trailing line 1 — they belong with the
    # noun they introduce, so a "to / Buy eBay" break reads worse than
    # "Trying / to Buy eBay" even though it's more balanced in length.
    FUNCTION_WORDS = {
        "a", "an", "the",                          # articles
        "to", "of", "in", "on", "at", "by",        # short prepositions
        "for", "from", "with", "into", "onto",     # longer prepositions
        "and", "or", "but", "as", "if", "than",    # conjunctions
        "is", "are", "was", "be", "been",          # auxiliaries
    }

    for split_idx in range(1, n):
        line1 = " ".join(words[:split_idx])
        line2 = " ".join(words[split_idx:])
        if len(line1) > max_chars + slack or len(line2) > max_chars + slack:
            continue
        score = abs(len(line1) - len(line2))
        # Penalty 1: line 1 ends on a function word that should lead line 2.
        # Strong penalty (+8) because semantic mis-break reads worse than
        # mild length imbalance.
        last_word_line1 = words[split_idx - 1].lower().rstrip(",.!?;:")
        if last_word_line1 in FUNCTION_WORDS:
            score += 8
        # Penalty 2: line 1 ends on any 1-2 char token (catches numbers,
        # symbols, anything else that looks like a leftover).
        if len(last_word_line1) <= 2 and last_word_line1 not in FUNCTION_WORDS:
            score += 3
        if score < best_imbalance:
            best_imbalance = score
            best_split = split_idx

    if best_split is not None:
        return [" ".join(words[:best_split]), " ".join(words[best_split:])]

    # Long title — fall back to greedy 3-line.
    lines: list[str] = []
    cur = ""
    for w in words:
        candidate = (cur + " " + w).strip() if cur else w
        if len(candidate) > max_chars and cur:
            lines.append(cur)
            cur = w
        else:
            cur = candidate
    if cur:
        lines.append(cur)
    if len(lines) > 3:
        lines = lines[:3]
        lines[-1] = lines[-1] + "…"
    return lines


def _title_overlay_filter(title: str | None, episode_dir: Path, clip_id: str) -> str:
    """Return the ffmpeg drawtext filter segment for the title overlay.

    Round 3 redesign (2026-05-12): drop the orange text outline (looked
    dated), drop the heavy text-shadow doubling. Add:
      - Translucent dark backdrop block behind the text (soft, low alpha)
      - Brand-orange accent bar BELOW the title that grows from center
        as the title fades in
      - Cleaner main text: white with a thin black border for legibility

    Per-line rendering retained (one drawtext per line per layer) to keep
    the X-in-box fix from the prior round.

    Filter chain order:
      [backdrop drawbox]  → soft black rectangle, low alpha, behind text
      [drawtext per line] → white text + thin black border, fades in
      [accent drawbox]    → brand-orange bar below, animated width
    """
    if not title or not title.strip():
        return ""

    lines = _wrap_title(title.strip())
    if not lines:
        return ""

    font_path = "/usr/local/share/fonts/bebas-neue/BebasNeue-Regular.ttf"

    # Alpha curve for the TEXT — fade in 0→FADE_IN, hold, fade out.
    # Backslash-comma needed because ',' inside drawtext expressions
    # otherwise terminates the filter argument.
    fade_in_end = TITLE_OVERLAY_FADE_IN
    fade_out_start = TITLE_OVERLAY_SECONDS - TITLE_OVERLAY_FADE_OUT
    text_alpha_expr = (
        f"if(lt(t\\,{fade_in_end:.2f})\\,t/{fade_in_end:.2f}\\,"
        f"if(gt(t\\,{fade_out_start:.2f})\\,"
        f"({TITLE_OVERLAY_SECONDS:.2f}-t)/{TITLE_OVERLAY_FADE_OUT:.2f}\\,"
        f"1))"
    )

    line_height = TITLE_OVERLAY_FONT_SIZE + TITLE_OVERLAY_LINE_SPACING
    n_lines = len(lines)
    # Estimated text block bounds — used to size the backdrop block.
    # Title block: from y_main_line0 to y_main_last + font_size.
    block_top = TITLE_OVERLAY_Y_OFFSET - 24
    block_bottom = TITLE_OVERLAY_Y_OFFSET + (n_lines - 1) * line_height + TITLE_OVERLAY_FONT_SIZE + 36
    # Accent bar sits below the text block
    accent_y = block_bottom + 22
    accent_height = 8

    parts: list[str] = []

    # === Backdrop block ============================================
    # A translucent black rectangle behind the text. Uses drawbox with
    # @alpha. Spans full width so the design feels intentional rather
    # than a tight box that crops the text awkwardly.
    # Backdrop alpha matches the text alpha curve so it fades in/out
    # together — we use the same alpha_expr but scaled to lower max.
    backdrop_alpha_expr = (
        f"if(lt(t\\,{fade_in_end:.2f})\\,(t/{fade_in_end:.2f})*0.35\\,"
        f"if(gt(t\\,{fade_out_start:.2f})\\,"
        f"(({TITLE_OVERLAY_SECONDS:.2f}-t)/{TITLE_OVERLAY_FADE_OUT:.2f})*0.35\\,"
        f"0.35))"
    )
    backdrop_h = block_bottom - block_top
    parts.append(
        f",drawbox=x=0:y={block_top}:w=1080:h={backdrop_h}"
        f":color=black@0.001:t=fill"
        f":enable='lte(t\\,{TITLE_OVERLAY_SECONDS})'"
    )
    # The above drawbox with color=black@0.001 is a no-op (placeholder);
    # ffmpeg's drawbox doesn't support an animated alpha expression directly.
    # Instead we emit a SECOND drawbox with a static alpha that's gated by
    # enable= for the visible window. Trade-off: backdrop pops on/off rather
    # than fading. With short FADE_IN/OUT the pop is mostly hidden behind
    # the text's smoother fade. Accept the trade-off — drawbox doesn't have
    # the alpha= eval that drawtext does.
    parts[-1] = (
        f",drawbox=x=0:y={block_top}:w=1080:h={backdrop_h}"
        f":color=0x000000@0.35:t=fill"
        f":enable='between(t\\,{fade_in_end:.2f}\\,{fade_out_start:.2f})'"
    )

    # === Title text per line =======================================
    for i, line in enumerate(lines):
        title_txt = episode_dir / f"{clip_id}.title.{i}.txt"
        title_txt.write_text(line)

        y_main = TITLE_OVERLAY_Y_OFFSET + i * line_height
        common = (
            f"fontfile='{font_path}'"
            f":textfile='{title_txt}'"
            f":fontsize={TITLE_OVERLAY_FONT_SIZE}"
            f":enable='lte(t\\,{TITLE_OVERLAY_SECONDS})'"
            f":alpha='{text_alpha_expr}'"
        )
        # White text with thin black border. No orange outline this time —
        # the brand pop goes on the accent bar instead.
        parts.append(
            f",drawtext={common}"
            f":fontcolor=white"
            f":borderw=3:bordercolor=black@0.85"
            f":x=(w-text_w)/2"
            f":y={y_main}"
        )

    # === Brand-orange accent bar ===================================
    # Animated width: grows from center 0 → target over FADE_IN seconds,
    # holds, shrinks again on fade-out. Implemented as a drawbox with
    # x/w expressions tied to t.
    accent_target_w = 480
    # ffmpeg drawbox expressions: w can use t. width grows linearly during
    # fade_in window, holds, then shrinks during fade_out.
    accent_w_expr = (
        f"if(lt(t\\,{fade_in_end:.2f})\\,"
        f"(t/{fade_in_end:.2f})*{accent_target_w}\\,"
        f"if(gt(t\\,{fade_out_start:.2f})\\,"
        f"(({TITLE_OVERLAY_SECONDS:.2f}-t)/{TITLE_OVERLAY_FADE_OUT:.2f})*{accent_target_w}\\,"
        f"{accent_target_w}))"
    )
    accent_x_expr = f"(1080-({accent_w_expr}))/2"
    parts.append(
        f",drawbox=x='{accent_x_expr}':y={accent_y}"
        f":w='{accent_w_expr}':h={accent_height}"
        f":color=0x{BRAND_ORANGE_HEX}@1.0:t=fill"
        f":enable='lte(t\\,{TITLE_OVERLAY_SECONDS})'"
    )

    return "".join(parts)


def _build_video_filter(scenes: list[tuple[float, float, int]], ass_path: Path,
                        crop_w: int = CROP_W, title: str | None = None,
                        episode_dir: Path | None = None,
                        clip_id: str | None = None) -> list[str]:
    """Build the video-branch filter segments that produce the `[v0]` label
    (a 1080x1920 stream with captions burned in). Callers then append the
    end-card overlay and audio branches the same way regardless of scene
    count.

    Single-scene fast path (identical to pre-fix behavior):
        [0:v]crop=...,scale=1080:1920,setsar=1,fade=in,drawtext=...,subtitles='...'[v0]

    Multi-scene path: split the video N ways, trim+crop each branch with its
    own offset, concat, then apply subtitles to the rebuilt 0-based timeline.

    Polish (2026-05-11):
      - Title overlay (drawtext) at top of frame for first TITLE_OVERLAY_SECONDS,
        animated alpha (fade in/out), brand-orange outline + drop shadow.
      - Intro fade-in from black over INTRO_FADE_DURATION sec — clip no longer
        cold-pops in.
      The intro fade and title overlay both apply to the FINAL concat'd stream
      so they're continuous regardless of internal scene count.
    """
    title_filter = _title_overlay_filter(title, episode_dir, clip_id) if (
        title and episode_dir is not None and clip_id is not None
    ) else ""
    n = len(scenes)
    if n <= 1:
        _s, _e, cx = scenes[0]
        return [
            f"[0:v]crop={crop_w}:1080:{cx}:0,scale=1080:1920,setsar=1"
            f"{title_filter},"
            f"subtitles='{ass_path}'[v0]"
        ]

    parts: list[str] = []
    split_labels = "".join(f"[v{i}s]" for i in range(n))
    parts.append(f"[0:v]split={n}{split_labels}")
    for i, (s, e, cx) in enumerate(scenes):
        parts.append(
            f"[v{i}s]trim=start={s:.3f}:end={e:.3f},setpts=PTS-STARTPTS,"
            f"crop={crop_w}:1080:{cx}:0,scale=1080:1920[s{i}]"
        )
    concat_inputs = "".join(f"[s{i}]" for i in range(n))
    parts.append(
        f"{concat_inputs}concat=n={n}:v=1:a=0,setsar=1"
        f"{title_filter},"
        f"subtitles='{ass_path}'[v0]"
    )
    return parts


def _build_ffmpeg_cmd(source_video: Path, start: float, end: float, duration: float,
                      scenes: list[tuple[float, float, int]], ass_path: Path,
                      music: Path | None, has_music: bool, crop_w: int,
                      out_path: Path, music_volume: float = 0.12,
                      title: str | None = None,
                      episode_dir: Path | None = None,
                      clip_id: str | None = None) -> list[str]:
    """Build the full ffmpeg command for one render. Pure function — no side effects.

    Factored out of render_clip() so Gate 2 + Gate 3 rescue paths can rebuild
    cmd with shifted captions or restricter scene detection and re-run.

    Args:
      music_volume: dialog-vs-music balance. Default 0.12 (legacy fixed value).
        Pick_clips' AUDIO_MIX_MOOD_V1 audit overrides this per-clip via the
        spec's `_audio_music_volume` field — intense=0.08, storytelling=0.10,
        casual=0.12, upbeat=0.14. Clamped to [0.05, 0.20] for safety.
      episode_dir, clip_id: required for the title overlay's textfile= sidecar.
        If either is None, the title overlay is silently skipped.
    """
    music_volume = max(0.05, min(0.20, float(music_volume)))
    filter_parts = _build_video_filter(scenes, ass_path, crop_w=crop_w, title=title,
                                       episode_dir=episode_dir, clip_id=clip_id)
    vout_label = "[v0]"
    if END_CARD.exists():
        # End-card covers the last END_CARD_DURATION seconds with a quick
        # fade-in. 3s is the YouTube Shorts standard for branded outros —
        # long enough for the viewer to register the handle/CTA, short
        # enough not to eat too much dialogue.
        end_card_duration = 3.0
        end_card_start = max(0.0, duration - end_card_duration)
        filter_parts.append(
            f"[2:v]scale=1080:1920,format=rgba,fade=t=in:st={end_card_start:.2f}:d=0.4:alpha=1[ec]"
        )
        filter_parts.append(
            f"[v0][ec]overlay=0:0:enable='gte(t,{end_card_start:.2f})'[vout]"
        )
        vout_label = "[vout]"

    if has_music:
        # Music bed adaptive per clip mood (intense=0.08 → upbeat=0.14),
        # set by pick_clips._post_pick_enrichment via AUDIO_MIX_MOOD_V1.
        #
        # 2026-05-12: added sidechain ducking. Music dips ~10dB when dialog
        # is loud and returns smoothly between phrases. Much more pro-sounding
        # than the prior flat-mix approach where music either drowned dialog
        # or sat too low to add presence.
        #
        # Filter chain:
        #   [0:a] dialog       -> asplit: one copy to sidechain key, one to mix
        #   [1:a] music bed    -> volume scaled, looped to clip length
        #   music + dialog-key -> sidechaincompress (10dB attenuation, fast
        #                         attack, slow release for natural ducking)
        #   ducked music + dialog -> amix
        filter_parts.append("[0:a]asplit=2[dialog][dialog_key]")
        filter_parts.append(f"[1:a]volume={music_volume:.3f},aloop=loop=-1:size=2e9[music_raw]")
        # sidechaincompress params:
        #   threshold=0.05  ~ -26dB — kicks in when dialog has any speech energy
        #   ratio=8         strong compression on the music when triggered
        #   attack=5        5ms — duck quickly so consonants don't get masked
        #   release=400     400ms — let music come back gently between phrases
        #   makeup=1        no makeup gain (we already set music volume)
        filter_parts.append(
            "[music_raw][dialog_key]sidechaincompress="
            "threshold=0.05:ratio=8:attack=5:release=400:makeup=1[music]"
        )
        filter_parts.append("[dialog][music]amix=duration=shortest:dropout_transition=3[aout]")
        aout_label = "[aout]"
    else:
        aout_label = "0:a"

    filter_complex = ";".join(filter_parts)

    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-ss", f"{start:.3f}", "-to", f"{end:.3f}", "-i", str(source_video),
    ]
    if has_music and music is not None:
        cmd += ["-stream_loop", "-1", "-i", str(music)]
    if END_CARD.exists():
        if not has_music:
            # if no music, end_card becomes input [1], not [2]
            filter_complex = filter_complex.replace("[2:v]", "[1:v]")
        # -loop 1 is CRITICAL: without it, ffmpeg presents the PNG as a
        # single-frame stream that only exists at t≈0. The overlay's
        # `enable='gte(t,duration-3)'` is then never true while the stream
        # is alive, so the overlay silently no-ops and the end-card never
        # appears. (This is the bug that masked the end-card on 2026-05-11.)
        # -t bounds the looped image so it doesn't outlast the output.
        cmd += ["-loop", "1", "-t", f"{duration:.3f}", "-i", str(END_CARD)]

    cmd += [
        "-filter_complex", filter_complex,
        "-map", vout_label,
        "-map", aout_label,
        "-c:v", "libx264", "-preset", "medium", "-crf", "22",
        "-pix_fmt", "yuv420p",
        "-r", "30",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        "-t", f"{duration:.3f}",
        str(out_path),
    ]
    return cmd


def render_clip(spec: dict, episode: str, transcripts_by_stem: dict[str, dict],
                crop_x: int | None = None, crop_w: int = CROP_W, dry_run: bool = False) -> Path | None:
    clip_id = spec["clip_id"]
    source_stem = spec["source_stem"]
    start = float(spec["start_sec"])
    end = float(spec["end_sec"])
    duration = end - start
    if duration < 5 or duration > 120:
        print(f"[SKIP] {clip_id}: duration {duration:.1f}s out of 5–120s range")
        return None

    source_video = SOURCE_1080P / f"{source_stem}.mp4"
    if not source_video.exists():
        print(f"[ERROR] {clip_id}: source video missing: {source_video}")
        return None

    transcript = transcripts_by_stem.get(source_stem)
    if not transcript:
        print(f"[ERROR] {clip_id}: transcript missing for {source_stem}")
        return None

    words = _words_in_range(transcript, start, end)
    if not words:
        print(f"[WARN] {clip_id}: no words found in range; skipping captions")
    ass_content = build_ass(words, duration=duration)

    episode_clips_dir = CLIPS_DIR / _safe(episode)
    episode_clips_dir.mkdir(parents=True, exist_ok=True)
    ass_path = episode_clips_dir / f"{clip_id}.ass"
    ass_path.write_text(ass_content)
    out_path = episode_clips_dir / f"{clip_id}.mp4"

    # Mood-matched music selection: pick_clips' enrichment writes _audio_mood
    # (intense/storytelling/casual/upbeat). _pick_music_bed prefers compatible
    # beds from the catalog; falls back to random when no catalog/no mood.
    music = _pick_music_bed(seed=clip_id, mood=spec.get("_audio_mood"))
    has_music = music is not None

    # Build the scene list that drives the crop graph. Explicit --crop-x from
    # the CLI still wins as a manual escape hatch; otherwise auto-detect.
    if crop_x is not None:
        scenes: list[tuple[float, float, int]] = [(0.0, duration, crop_x)]
    else:
        scenes = detect_scenes_and_crops(source_video, start, end, crop_w=crop_w)

    # Adaptive audio mix: pick_clips' enrichment classifies clip mood and
    # writes _audio_music_volume into the spec (0.08 intense / 0.10 storytelling /
    # 0.12 casual / 0.14 upbeat). Default 0.12 if not set (older specs).
    music_volume = float(spec.get("_audio_music_volume") or 0.12)
    # Title overlay text for the first 5 seconds — pulled from spec.title.
    # Helps cold viewers know the topic at a glance (audio-off scrolling).
    title_text = spec.get("title", "")
    cmd = _build_ffmpeg_cmd(source_video, start, end, duration, scenes,
                            ass_path, music, has_music, crop_w, out_path,
                            music_volume=music_volume, title=title_text,
                            episode_dir=episode_clips_dir, clip_id=clip_id)

    mood_label = spec.get("_audio_mood", "?")
    print(f"[RENDER] {clip_id}  {duration:.1f}s  music={music.name if music else 'none'}  "
          f"mood={mood_label} vol={music_volume:.2f}")
    if dry_run:
        print("  " + " ".join(cmd))
        return out_path

    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        print(f"[ERROR] {clip_id} ffmpeg exited {proc.returncode}")
        print(proc.stderr[-2000:])
        return None
    print(f"[DONE] {out_path.relative_to(ROOT)}")

    # ----- Rerender closures (used by Gate 2 + Gate 3 rescue paths) ------
    # State captured: words, duration, ass_path, source_video, start, end, crop_w,
    # music, has_music, scenes, out_path, cmd. Each closure mutates the
    # appropriate input file (ASS for Gate 2; scenes for Gate 3) then re-runs
    # ffmpeg. Returns True on success.
    def _rerender_with_caption_offset(offset_sec: float) -> bool:
        """Gate 2 rescue: shift every word's start/end by offset_sec, rewrite
        ASS, re-run ffmpeg. Positive offset = captions appear later (audio is
        ahead of captions). Negative = earlier (audio lags captions)."""
        shifted = [{
            "start": max(0.0, w["start"] + offset_sec),
            "end": min(duration, w["end"] + offset_sec),
            "word": w["word"],
        } for w in words]
        # Drop any words pushed entirely outside the clip window after shift
        shifted = [w for w in shifted if w["end"] > w["start"]]
        ass_path.write_text(build_ass(shifted, duration=duration))
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            print(f"  [gate2-rescue] ffmpeg returned {proc.returncode}: {proc.stderr[-500:]}")
            return False
        return True

    def _rerender_with_stricter_scenes() -> tuple[bool, list[tuple[float, float, int]]]:
        """Gate 3 rescue: re-run scene detection with cut_threshold=0.25 (vs
        default 0.35). Tighter threshold → more scene boundaries → each new
        scene gets fresh face-detection sampling. Returns (ok, new_scenes)."""
        nonlocal scenes
        new_scenes = detect_scenes_and_crops(
            source_video, start, end,
            crop_w=crop_w, cut_threshold=0.25,
        )
        if new_scenes == scenes:
            print("  [gate3-rescue] stricter threshold returned identical scenes — no rerender")
            return False, scenes
        new_cmd = _build_ffmpeg_cmd(
            source_video, start, end, duration, new_scenes,
            ass_path, music, has_music, crop_w, out_path,
            music_volume=music_volume, title=title_text,
            episode_dir=episode_clips_dir, clip_id=clip_id,
        )
        proc = subprocess.run(new_cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            print(f"  [gate3-rescue] ffmpeg returned {proc.returncode}: {proc.stderr[-500:]}")
            return False, scenes
        scenes = new_scenes  # update for downstream preview generation
        return True, new_scenes

    # GATE 2 (2026-05-07): caption-audio sync verification via Claude Vision.
    # Extract 2 keyframes (early + late), send with word timings to Claude.
    # On rerender_with_offset, rebuild ASS with shifted timings + re-run ffmpeg
    # + re-call Gate 2 once. Cap retries at 1.
    g2 = _gate2_caption_sync(out_path, words, spec, duration, episode_clips_dir,
                             clip_id, rerender_func=_rerender_with_caption_offset)
    if g2 and g2.get("recommendation") == "reject":
        return None  # _gate2 handles reject routing + Navi

    # QA preview: 2x2 contact sheet at 25/50/75/95% of clip duration.
    try:
        _generate_preview(out_path, clip_id, episode_clips_dir, scenes, duration)
    except Exception as exc:
        print(f"  [PREVIEW] generation failed (non-fatal): {exc}")

    # GATE 3 (2026-05-07): framing/centering verification via Claude Vision.
    # Extract 4 keyframes, send with scene-detection data. On reject_reframe,
    # re-run scene detection with cut_threshold=0.25 + re-render + re-call Gate 3.
    # Cap retries at 1. If still fails OR rec='reject', move to _rejected/.
    g3 = _gate3_framing(out_path, scenes, duration, spec, episode_clips_dir,
                       clip_id, rerender_func=_rerender_with_stricter_scenes)
    if g3 and g3.get("recommendation") in ("reject", "reject_reframe"):
        return None

    return out_path


# ===== Gate 2 + Gate 3 — multimodal QA via Claude Vision =====================
# (2026-05-07 evening) Wraps each rendered clip with two LLM checks:
#   Gate 2: do the burned captions match the audio? (sync verification)
#   Gate 3: is the speaker centered in keyframes? (framing verification)
# Both decide pass / reject; reject moves clip to _rejected/ + emits Navi task.

def _gate2_caption_sync(out_path: Path, words: list[dict], spec: dict,
                        duration: float, episode_dir: Path, clip_id: str,
                        rerender_func=None, _retry: int = 0) -> dict | None:
    """Send 2 keyframes (early + late) + word timings to Claude Vision.
    Returns the verdict dict, or None on infra error (in which case we
    let the clip through — don't drop on infrastructure flakes).

    Rescue path: if Claude returns recommendation='rerender_with_offset' and
    rerender_func is provided, shift caption timings by estimated_offset_sec,
    re-render, and re-call Gate 2 ONCE. _retry caps the recursion at 1 attempt.
    """
    try:
        from _qa_helpers import (
            call_claude_vision, extract_keyframes,
            move_to_rejected, emit_reject_navi, log_gate_decision, SONNET_MODEL,
        )
        from qa_prompts import GATE_2_CAPTION_SYNC_V1
    except ImportError as exc:
        print(f"  [gate2] qa helpers unavailable ({exc}) — skipping caption sync check")
        return None

    if duration < 4:
        # Too short to extract two distinct keyframes; skip
        return {"recommendation": "pass", "reason": "duration < 4s, skipping gate2"}

    kf_dir = episode_dir / "_kf" / clip_id
    timestamps = [2.0, max(2.5, duration - 2.5)]
    # Use a different prefix on retry so we don't overwrite the original keyframes
    # (useful for post-mortem inspection of why Claude rejected the rescue).
    prefix = "g2" if _retry == 0 else f"g2_retry{_retry}"
    keyframes = extract_keyframes(out_path, timestamps, kf_dir, prefix=prefix)
    if len(keyframes) < 2:
        print(f"  [gate2] only {len(keyframes)} keyframes extracted — skipping")
        return None

    # Word timings excerpt — first 30 words, formatted compactly
    word_excerpt = "\n".join(
        f"  [{w.get('start', 0):.2f}s-{w.get('end', 0):.2f}s] {w.get('word', '').strip()}"
        for w in words[:30]
    ) or "(no words in transcript range)"

    prompt = GATE_2_CAPTION_SYNC_V1.format(
        title=spec.get("title", "?"),
        duration_sec=duration,
        word_timings_excerpt=word_excerpt,
    )

    try:
        verdict = call_claude_vision(prompt, keyframes, model=SONNET_MODEL, max_tokens=1500)
    except Exception as exc:
        print(f"  [gate2] claude vision error: {exc} — letting clip through")
        return None

    rec = (verdict.get("recommendation") or "").lower()
    quality = verdict.get("sync_quality", "?")
    label = "gate2-retry" if _retry else "gate2"
    print(f"  [{label}] sync={quality} rec={rec}")

    # Log every Gate 2 decision (PASS / DRIFT / REJECT including rescue retries)
    episode_stem = spec.get("source_stem", "unknown")
    log_gate_decision(episode_stem, label, clip_id, verdict, extra={
        "duration_sec": duration,
        "n_keyframes": len(keyframes),
    })

    if rec == "reject":
        episode = spec.get("source_stem", "?")
        move_to_rejected(out_path, episode_dir, f"Gate 2 (caption sync) — retry={_retry}",
                         verdict, clip_id)
        emit_reject_navi(clip_id, "Gate 2 (caption sync)", verdict, episode)
    elif rec == "rerender_with_offset" and rerender_func is not None and _retry == 0:
        offset = verdict.get("estimated_offset_sec")
        if offset is None or not isinstance(offset, (int, float)):
            print(f"  [gate2] rerender requested but no estimated_offset_sec — skipping rescue")
            return verdict
        # Cap the offset to a sane range; Whisper drift rarely exceeds 1s.
        # Refuse to apply offsets > 2s — that's almost certainly a hallucination.
        if abs(offset) > 2.0:
            print(f"  [gate2] offset {offset}s exceeds 2s sanity cap — rejecting instead")
            episode = spec.get("source_stem", "?")
            verdict["_rescue_skipped"] = f"offset {offset}s out of bounds"
            move_to_rejected(out_path, episode_dir, "Gate 2 (offset out of bounds)",
                             verdict, clip_id)
            emit_reject_navi(clip_id, "Gate 2 (offset out of bounds)", verdict, episode)
            verdict["recommendation"] = "reject"
            return verdict
        print(f"  [gate2] RESCUE: re-rendering with caption offset {offset:+.2f}s")
        if not rerender_func(float(offset)):
            print(f"  [gate2] rescue rerender failed — falling back to reject")
            episode = spec.get("source_stem", "?")
            verdict["_rescue_failed"] = True
            move_to_rejected(out_path, episode_dir, "Gate 2 (rescue rerender failed)",
                             verdict, clip_id)
            emit_reject_navi(clip_id, "Gate 2 (rescue rerender failed)", verdict, episode)
            verdict["recommendation"] = "reject"
            return verdict
        # Recurse once to validate the rescued render
        retry_verdict = _gate2_caption_sync(out_path, words, spec, duration,
                                            episode_dir, clip_id,
                                            rerender_func=None, _retry=1)
        if retry_verdict is None:
            return verdict  # original verdict if retry infra-failed
        if (retry_verdict.get("recommendation") or "").lower() in ("pass",):
            print(f"  [gate2] RESCUE SUCCESS: clip passes after offset retry")
            retry_verdict["_rescued_from_offset"] = float(offset)
            return retry_verdict
        # Retry didn't pass — propagate its decision (likely reject by now)
        return retry_verdict
    elif rec == "rerender_with_offset" and _retry > 0:
        # Caption still misaligned after rescue rerender — give up, reject
        print(f"  [gate2-retry] rescue did not fix sync — rejecting")
        episode = spec.get("source_stem", "?")
        move_to_rejected(out_path, episode_dir, "Gate 2 (rescue still misaligned)",
                         verdict, clip_id)
        emit_reject_navi(clip_id, "Gate 2 (rescue still misaligned)", verdict, episode)
        verdict["recommendation"] = "reject"
    return verdict


def _gate3_framing(out_path: Path, scenes: list[tuple[float, float, int]],
                   duration: float, spec: dict, episode_dir: Path, clip_id: str,
                   rerender_func=None, _retry: int = 0) -> dict | None:
    """Send 4 keyframes (25/50/75/95% of duration) + scene data to Claude Vision.
    Verdict: pass / manual_review / reject_reframe / reject.

    Rescue path: if Claude returns reject_reframe and rerender_func is provided,
    re-run scene detection with stricter Bhattacharyya threshold (0.25 vs 0.35),
    re-render, re-call Gate 3 ONCE. If still fails, REJECT. _retry caps recursion.
    """
    try:
        from _qa_helpers import (
            call_claude_vision, extract_keyframes,
            move_to_rejected, emit_reject_navi, emit_flag_navi,
            log_gate_decision, SONNET_MODEL,
        )
        from qa_prompts import GATE_3_FRAMING_V1
    except ImportError as exc:
        print(f"  [gate3] qa helpers unavailable ({exc}) — skipping framing check")
        return None

    if duration < 8:
        return {"recommendation": "pass", "reason": "duration < 8s, skipping gate3"}

    kf_dir = episode_dir / "_kf" / clip_id
    timestamps = [duration * pct for pct in (0.25, 0.50, 0.75, 0.95)]
    prefix = "g3" if _retry == 0 else f"g3_retry{_retry}"
    keyframes = extract_keyframes(out_path, timestamps, kf_dir, prefix=prefix)
    if len(keyframes) < 3:
        print(f"  [gate3] only {len(keyframes)} keyframes — skipping")
        return None

    scenes_summary = ", ".join(
        f"({s:.1f}-{e:.1f}s, cx={cx})" for s, e, cx in scenes[:8]
    )
    frame_timestamps = ", ".join(f"{t:.1f}s" for t in timestamps[:len(keyframes)])

    prompt = GATE_3_FRAMING_V1.format(
        title=spec.get("title", "?"),
        duration_sec=duration,
        frame_timestamps=frame_timestamps,
        scenes_summary=scenes_summary,
    )

    try:
        verdict = call_claude_vision(prompt, keyframes, model=SONNET_MODEL, max_tokens=2000)
    except Exception as exc:
        print(f"  [gate3] claude vision error: {exc} — letting clip through")
        return None

    rec = (verdict.get("recommendation") or "").lower()
    quality = verdict.get("overall_quality", "?")
    label = "gate3-retry" if _retry else "gate3"
    print(f"  [{label}] quality={quality} rec={rec}")

    # Log every Gate 3 decision (PASS / MANUAL_REVIEW / REJECT_REFRAME / REJECT)
    episode_stem = spec.get("source_stem", "unknown")
    log_gate_decision(episode_stem, label, clip_id, verdict, extra={
        "duration_sec": duration,
        "n_keyframes": len(keyframes),
        "n_scenes": len(scenes),
    })

    episode = spec.get("source_stem", "?")

    if rec == "reject":
        # No rescue path — Claude says framing is fundamentally broken
        move_to_rejected(out_path, episode_dir, f"Gate 3 (framing) — reject", verdict, clip_id)
        emit_reject_navi(clip_id, "Gate 3 (framing)", verdict, episode)
    elif rec == "reject_reframe" and rerender_func is not None and _retry == 0:
        print(f"  [gate3] RESCUE: re-running scene detection with cut_threshold=0.25")
        ok, new_scenes = rerender_func()
        if not ok:
            print(f"  [gate3] rescue rerender failed — falling back to reject")
            verdict["_rescue_failed"] = True
            move_to_rejected(out_path, episode_dir, "Gate 3 (rescue rerender failed)",
                             verdict, clip_id)
            emit_reject_navi(clip_id, "Gate 3 (rescue rerender failed)", verdict, episode)
            verdict["recommendation"] = "reject"
            return verdict
        # Re-call Gate 3 with the new scenes
        retry_verdict = _gate3_framing(out_path, new_scenes, duration, spec,
                                       episode_dir, clip_id,
                                       rerender_func=None, _retry=1)
        if retry_verdict is None:
            return verdict
        retry_rec = (retry_verdict.get("recommendation") or "").lower()
        if retry_rec in ("pass", "manual_review"):
            print(f"  [gate3] RESCUE SUCCESS: clip {retry_rec} after stricter scene detection")
            retry_verdict["_rescued_from"] = "reject_reframe"
            retry_verdict["_new_scene_count"] = len(new_scenes)
            return retry_verdict
        # Retry still wants reject → propagate
        return retry_verdict
    elif rec == "reject_reframe":
        # No rerender_func or already in retry — treat as final reject
        move_to_rejected(out_path, episode_dir, f"Gate 3 (reject_reframe, retry={_retry})",
                         verdict, clip_id)
        emit_reject_navi(clip_id, "Gate 3 (reject_reframe final)", verdict, episode)
        verdict["recommendation"] = "reject"
    elif rec == "manual_review":
        emit_flag_navi(clip_id, "Gate 3 (framing)", verdict.get("frames", []) or [], episode)
    return verdict


def _generate_preview(rendered_mp4: Path, clip_id: str, episode_dir: Path,
                      scenes: list[tuple[float, float, int]], duration: float) -> None:
    """Build a 2x2 contact sheet from the rendered vertical MP4 for QA.

    Tiles 4 still frames sampled at 25/50/75/95% of the clip's duration. Each
    tile shows the 9:16 framing as it will appear to viewers, plus a small
    annotation strip with the source-video crop_x for that timestamp's scene.

    Output: <episode>/preview/<clip_id>.jpg (1080x1920 contact sheet downscaled
    to 540x960 per tile, arranged 2x2).
    """
    preview_dir = episode_dir / "preview"
    preview_dir.mkdir(parents=True, exist_ok=True)
    out = preview_dir / f"{clip_id}.jpg"

    # Find which scene's crop_x covers each preview timestamp
    pcts = [0.25, 0.50, 0.75, 0.95]
    annotations = []
    for pct in pcts:
        t_rel = pct * duration
        cx = next((x for s, e, x in scenes if s <= t_rel < e), scenes[-1][2] if scenes else CENTER_CROP_X)
        annotations.append(f"t={t_rel:.1f}s cx={cx}")

    select = "+".join(f"eq(n\\,{int(p * 1)})" for p in [])  # placeholder; actually use ts
    # Build ffmpeg call: extract 4 frames at the percentages, scale each to
    # 540x960, draw the annotation, tile 2x2 to 1080x1920, save JPG.
    # Use a separate input per frame to keep the filter graph simple.
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"]
    for pct in pcts:
        cmd += ["-ss", f"{pct * duration:.2f}", "-i", str(rendered_mp4)]
    fparts = []
    for i, ann in enumerate(annotations):
        # scale to 540x960, draw annotation in white with black outline
        # escape colons in drawtext for ffmpeg filter syntax
        ann_escaped = ann.replace(":", "\\:")
        fparts.append(
            f"[{i}:v]select=eq(n\\,0),scale=540:960,setsar=1,"
            f"drawtext=text='{ann_escaped}':fontsize=22:fontcolor=white:"
            f"borderw=2:bordercolor=black:x=10:y=10[t{i}]"
        )
    fparts.append("[t0][t1]hstack=inputs=2[top]")
    fparts.append("[t2][t3]hstack=inputs=2[bot]")
    fparts.append("[top][bot]vstack=inputs=2[v]")
    cmd += ["-filter_complex", ";".join(fparts), "-map", "[v]",
            "-frames:v", "1", "-q:v", "3", str(out)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode == 0:
        print(f"  [PREVIEW] {out.relative_to(ROOT)}")
    else:
        print(f"  [PREVIEW] ffmpeg returned {proc.returncode}: {proc.stderr[-500:]}")


def _safe(s: str) -> str:
    return "".join(c if c.isalnum() or c in " -_" else "_" for c in s).strip().replace(" ", "_")


def _load_transcripts() -> dict[str, dict]:
    out: dict[str, dict] = {}
    for p in TRANSCRIPTS.glob("*.json"):
        try:
            out[p.stem] = json.loads(p.read_text())
        except json.JSONDecodeError:
            continue
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", help="Path to a per-topic clips_plan JSON")
    parser.add_argument("--index", type=int, default=0, help="Index within --spec to render")
    parser.add_argument("--clip-id", help="Render a specific clip from clips_plan/_all.json")
    parser.add_argument("--batch", help="Path to clips_plan/_all.json to render everything")
    parser.add_argument("--episode", default="Episode April 14th 2026")
    parser.add_argument("--crop-x", type=int, default=None,
                        help="Horizontal crop offset in px. Omit to auto-detect via face detection.")
    parser.add_argument("--crop-w", type=int, default=CROP_W)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    transcripts = _load_transcripts()
    if not transcripts:
        print(f"[FATAL] no transcripts in {TRANSCRIPTS} — run transcribe.py first", file=sys.stderr)
        return 2

    if args.spec:
        picks = json.loads(Path(args.spec).read_text())
        render_clip(picks[args.index], args.episode, transcripts,
                    crop_x=args.crop_x, crop_w=args.crop_w, dry_run=args.dry_run)
        return 0

    if args.clip_id:
        all_picks = json.loads((ROOT / "data" / "podcast" / "clips_plan" / "_all.json").read_text())
        match = next((p for p in all_picks if p["clip_id"] == args.clip_id), None)
        if not match:
            print(f"[FATAL] clip_id not found: {args.clip_id}", file=sys.stderr)
            return 2
        render_clip(match, args.episode, transcripts,
                    crop_x=args.crop_x, crop_w=args.crop_w, dry_run=args.dry_run)
        return 0

    if args.batch:
        picks = json.loads(Path(args.batch).read_text())
        ok = fail = 0
        for spec in picks:
            r = render_clip(spec, args.episode, transcripts,
                            crop_x=args.crop_x, crop_w=args.crop_w, dry_run=args.dry_run)
            if r:
                ok += 1
            else:
                fail += 1
        print(f"\n[BATCH] rendered {ok}, failed {fail}")
        return 0 if fail == 0 else 1

    parser.error("pass --spec, --clip-id, or --batch")


if __name__ == "__main__":
    sys.exit(main())
