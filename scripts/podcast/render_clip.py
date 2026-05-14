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
END_CARD = ROOT / "assets" / "brand" / "end-card-9x16.mp4"

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
# --- Scene detection ---------------------------------------------------------
# Round 10 (2026-05-13): replaced homegrown histogram bisect with ffmpeg's
# native `select='gt(scene,X)'` filter. The threshold below maps to
# ffmpeg's scene_score, which is frame-accurate and lives in
# _detect_cuts_via_ffmpeg. 0.30 is the standard public-tooling default;
# Gate-3 rescue lowers it to 0.20 to catch softer cuts that the first
# pass missed.
SCENE_DETECT_THRESHOLD = 0.30
# Scenes shorter than this get merged into the NEXT scene (not previous).
# Lowered 0.6 → 0.25 + flipped merge direction (2026-05-07). Old behavior was
# the second compounding bug behind the visible centering delay: when a brief
# transitional frame (camera switching) sat between two stable scenes, we'd
# absorb it into the PREVIOUS scene, extending the old crop_x into the new
# camera's content for up to MIN_SCENE_DURATION_SEC. Merging into NEXT means
# brief scenes inherit the upcoming camera's face position so the new speaker
# is centered the moment they appear on-screen.
MIN_SCENE_DURATION_SEC = 0.25


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


def _detect_cuts_via_ffmpeg(source_video: Path, start_sec: float,
                            end_sec: float, threshold: float = 0.30) -> list[float]:
    """Run ffmpeg's built-in scene-change detection over the clip window.
    Returns clip-relative PTS values (seconds, 0-based) where new scenes start.

    Why this is frame-accurate where my prior homegrown detection wasn't:
    ffmpeg's `select='gt(scene,X)'` filter operates on decoded frame data in
    the demuxer's PTS space. The metadata filter prints the EXACT pts of each
    frame that triggers a scene change — no seek imprecision, no off-by-one.

    ffmpeg trim semantics: `trim=start=X` includes frames where pts >= X. So
    if this returns pts=12.567, setting scene[i+1].start=12.567 puts the
    frame at 12.567 (first new-camera frame) in scene N+1 with the NEW crop,
    and the frame just before (last old-camera frame) stays in scene N with
    the OLD crop. Zero off-by-one possible.
    """
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error",
        "-ss", f"{start_sec:.3f}", "-to", f"{end_sec:.3f}",
        "-i", str(source_video),
        "-vf", f"select='gt(scene,{threshold:.3f})',metadata=mode=print:file=-",
        "-an", "-f", "null", "-",
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        print("  [SCENES] ffmpeg scene-detect timed out")
        return []
    cuts: list[float] = []
    for line in proc.stdout.splitlines():
        # Output format: "frame:N    pts:XXXX   pts_time:Y.YYY"
        if "pts_time:" in line:
            try:
                # The pts_time is RELATIVE to the trimmed window start because
                # we used -ss before -i (input-relative seek + reset PTS).
                pts = float(line.split("pts_time:")[1].strip().split()[0])
                cuts.append(pts)
            except (ValueError, IndexError):
                continue
    return sorted(cuts)


# Round-14 (2026-05-14): scenes derived from ffmpeg histogram cuts only;
# per-scene crop_x = YuNet active-speaker once per scene. Dense face track,
# EMA smoothing, face-jump cut detection, median filter — all ripped. They
# were per-sample noise accumulators when the actual need is one fixed crop
# per shot. See _face_detect.py for the YuNet wrapper + active-speaker scorer.
MIN_DURATION_FOR_YUNET_SEC = 0.6   # scenes shorter than this inherit prior crop_x

# Intra-scene cut detection: if the 8-sample YuNet output for one scene shows
# two clusters of face X positions separated by >= INTRA_SCENE_CUT_PX with at
# least 3 samples on each side, bisect the scene at the cluster boundary
# midpoint. Recovers similar-lighting cuts ffmpeg missed without re-introducing
# the per-frame face-jump noise (we only consider bisection within an
# already-confirmed scene window).
INTRA_SCENE_CUT_PX = 300


def _crop_x_for_scene(cap, source_video: Path, start_sec: float,
                      end_sec: float, prev_crop_x: int | None,
                      crop_w: int, source_w: int,
                      speaker_profile: list[dict] | None,
                      samples: int = 3,
                      _depth: int = 0) -> tuple[list[tuple[float, float, int]], list[int]]:
    """Identify WHICH speaker is on camera in this scene and return their
    canonical crop_x from the per-episode speaker profile.

    Round 15 (2026-05-14): per-scene face tracking was producing drift and
    delayed transitions per user feedback. Replaced with: take a few quick
    samples to identify WHICH speaker is on screen, then use that speaker's
    FIXED canonical_x from the per-episode profile. The crop_x for the
    whole scene is locked. No per-clip movement.

    Returns (sub_scenes, per_sample_face_xs).
      - sub_scenes: usually 1 element [(start, end, crop_x)]; 2 if
        intra-scene bisection caught a missed cut where two different
        speakers are in the same ffmpeg-undetected window.
      - per_sample_face_xs: raw observations for logging.

    Falls back to prev_crop_x (or CENTER_CROP_X) when YuNet can't detect
    a face anywhere in the scene.

    `cap` is an open cv2.VideoCapture; we seek via CAP_PROP_POS_MSEC.
    """
    import cv2  # type: ignore
    from _face_detect import FaceDetector
    from _speaker_profile import canonical_x_for_scene, speaker_for_face_x

    duration = max(0.1, end_sec - start_sec)

    # Sample a few frames inside the scene to identify which speaker is on
    # screen. 3 samples is plenty when we only need to MATCH against the
    # speaker profile (not compute a precise face position).
    det = FaceDetector.get()
    per_sample_face_x: list[int] = []
    for i in range(samples):
        t = start_sec + duration * ((i + 0.5) / samples)
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000.0)
        ok, frame = cap.read()
        if not ok or frame is None:
            continue
        faces = det.detect(frame)
        if faces:
            per_sample_face_x.append(faces[0]["cx"])  # largest face per frame

    fallback_face_x = (prev_crop_x + crop_w // 2) if prev_crop_x is not None else (CENTER_CROP_X + crop_w // 2)
    if speaker_profile:
        canonical_face_x = canonical_x_for_scene(
            per_sample_face_x, speaker_profile, fallback_x=fallback_face_x,
        )
    elif per_sample_face_x:
        # No profile (very short/short-episode mode) — use median of observations
        per_sample_face_x.sort()
        canonical_face_x = per_sample_face_x[len(per_sample_face_x) // 2]
    else:
        canonical_face_x = fallback_face_x

    crop_x = max(0, min(source_w - crop_w, int(canonical_face_x) - crop_w // 2))

    # Intra-scene bisection: if the samples in this scene match TWO different
    # speakers from the profile, the scene contains a missed cut. Bisect at
    # the boundary between the two speakers' samples.
    # Depth-limited (max 2 levels) and minimum half-duration to prevent
    # runaway recursion on noisy scenes where consecutive samples keep
    # alternating speakers.
    MAX_BISECT_DEPTH = 2
    MIN_BISECT_HALF_SEC = 0.8
    bisect_t: float | None = None
    if (_depth < MAX_BISECT_DEPTH
            and speaker_profile and len(per_sample_face_x) >= 3
            and duration >= 2 * MIN_BISECT_HALF_SEC):
        sample_speakers = [
            speaker_for_face_x(x, speaker_profile) for x in per_sample_face_x
        ]
        sample_speaker_ids = [s["speaker_id"] if s else None for s in sample_speakers]
        # Find the first transition between two different non-None speaker ids
        for k in range(len(sample_speaker_ids) - 1):
            a, b = sample_speaker_ids[k], sample_speaker_ids[k + 1]
            if a is not None and b is not None and a != b:
                t_left = start_sec + duration * ((k + 0.5) / samples)
                t_right = start_sec + duration * ((k + 1.5) / samples)
                candidate_t = (t_left + t_right) / 2
                # Reject bisections that leave a half shorter than the floor.
                if (candidate_t - start_sec >= MIN_BISECT_HALF_SEC
                        and end_sec - candidate_t >= MIN_BISECT_HALF_SEC):
                    bisect_t = candidate_t
                    break

    if bisect_t is None:
        return [(round(start_sec, 3), round(end_sec, 3), crop_x)], per_sample_face_x

    # Bisected — compute crop_x for each half independently.
    left_subs, _ = _crop_x_for_scene(
        cap, source_video, start_sec, bisect_t, prev_crop_x,
        crop_w, source_w, speaker_profile, samples=samples,
        _depth=_depth + 1,
    )
    right_prev = left_subs[-1][2] if left_subs else prev_crop_x
    right_subs, _ = _crop_x_for_scene(
        cap, source_video, bisect_t, end_sec, right_prev,
        crop_w, source_w, speaker_profile, samples=samples,
        _depth=_depth + 1,
    )
    return left_subs + right_subs, per_sample_face_x


def detect_scenes_and_crops(
    source_video: Path,
    start_sec: float,
    end_sec: float,
    crop_w: int = CROP_W,
    source_w: int = SOURCE_W,
    cut_threshold: float = SCENE_DETECT_THRESHOLD,
) -> list[tuple[float, float, int]]:
    """Detect camera cuts inside [start_sec, end_sec] and return one fixed
    crop_x per scene as a list of (start, end, crop_x) tuples.

    Round 15 (2026-05-14): per-clip face tracking still drifted within stable
    shots and lagged at shot transitions because each clip's scenes had to
    re-decide both WHO is on camera AND WHERE their face is. Per user:
    crop should snap to a FIXED canonical X per speaker, detected ONCE per
    episode. Even if a speaker temporarily leans left/right, their crop
    stays at their typical seat position.

    Flow:
      1. Load the per-episode speaker profile (cached at
         <source>.speakers.json; built lazily by _speaker_profile).
      2. ffmpeg histogram cuts → scene windows.
      3. Per scene: 3 quick face-detection samples → match to a profile
         speaker → use that speaker's canonical_x for the WHOLE scene.
      4. Intra-scene bisection: if the 3 samples match TWO different
         profile speakers, the scene contained a missed cut → bisect.

    Shorter scenes (< MIN_DURATION_FOR_YUNET_SEC) inherit prior crop_x.
    """
    duration = max(0.1, end_sec - start_sec)
    fallback = [(0.0, duration, CENTER_CROP_X)]

    try:
        import cv2  # type: ignore
    except ImportError:
        print("  [SCENES] opencv not installed → 1 scene, center crop")
        return fallback

    # Load per-episode speaker profile (Round 15). Failing to build it is
    # non-fatal — _crop_x_for_scene falls back to per-scene face median.
    speaker_profile: list[dict] | None = None
    try:
        from _speaker_profile import build_speaker_profile
        speaker_profile = build_speaker_profile(source_video)
        if speaker_profile and not getattr(detect_scenes_and_crops, "_profile_logged", False):
            speakers_str = ", ".join(
                f"#{s['speaker_id']} x={s['canonical_x']}" for s in speaker_profile
            )
            print(f"  [profile] speakers: {speakers_str}")
            detect_scenes_and_crops._profile_logged = True  # type: ignore[attr-defined]
    except Exception as exc:
        print(f"  [profile] speaker profile unavailable ({exc}) — per-scene fallback")
        speaker_profile = None

    cap = None
    try:
        cap = cv2.VideoCapture(str(source_video))
        if not cap.isOpened():
            print("  [SCENES] cv2 could not open source → 1 scene, center crop")
            return fallback

        # 1. ffmpeg histogram cuts — sole cut signal
        ffmpeg_cuts = _detect_cuts_via_ffmpeg(
            source_video, start_sec, end_sec, threshold=cut_threshold,
        )
        ffmpeg_cuts = [t for t in ffmpeg_cuts if 0.5 <= t < duration - 0.1]

        # Scene windows from cuts + boundaries
        boundaries = sorted([0.0] + ffmpeg_cuts + [duration])
        scene_windows: list[tuple[float, float]] = []
        for i in range(len(boundaries) - 1):
            s, e = boundaries[i], boundaries[i + 1]
            if e - s < MIN_SCENE_DURATION_SEC:
                continue
            scene_windows.append((s, e))

        if not scene_windows:
            return fallback

        # 2-3. Per-scene speaker-profile lookup + intra-scene bisection
        all_scenes: list[tuple[float, float, int]] = []
        prev_crop_x: int | None = None
        n_bisected = 0
        n_inherited = 0
        for (s_rel, e_rel) in scene_windows:
            dur = e_rel - s_rel
            if dur < MIN_DURATION_FOR_YUNET_SEC:
                inherit = prev_crop_x if prev_crop_x is not None else CENTER_CROP_X
                all_scenes.append((round(s_rel, 3), round(e_rel, 3), inherit))
                prev_crop_x = inherit
                n_inherited += 1
                continue
            sub_scenes, _ = _crop_x_for_scene(
                cap, source_video,
                start_sec + s_rel, start_sec + e_rel, prev_crop_x,
                crop_w, source_w, speaker_profile,
            )
            # Convert source-relative timestamps back to clip-relative
            for (abs_s, abs_e, cx) in sub_scenes:
                all_scenes.append((
                    round(abs_s - start_sec, 3),
                    round(abs_e - start_sec, 3),
                    cx,
                ))
                prev_crop_x = cx
            if len(sub_scenes) > 1:
                n_bisected += len(sub_scenes) - 1

        if not all_scenes:
            return fallback

        # Collapse-to-one optimization: if every scene's crop_x is within
        # 50px of the others, the whole clip is effectively one camera —
        # return a single scene to simplify the filter graph.
        if max(cx for _s, _e, cx in all_scenes) - min(cx for _s, _e, cx in all_scenes) < 50:
            avg_cx = sum(cx for _s, _e, cx in all_scenes) // len(all_scenes)
            print(f"  [SCENES] {len(scene_windows)} cuts → 1 collapsed scene (crop_x={avg_cx})")
            return [(0.0, duration, avg_cx)]

        print(
            f"  [SCENES] {len(ffmpeg_cuts)} cuts → {len(all_scenes)} scenes "
            f"(ffmpeg only{f', +{n_bisected} bisected' if n_bisected else ''}"
            f"{f', {n_inherited} short→inherited' if n_inherited else ''})"
        )
        return all_scenes

    except Exception as exc:
        print(f"  [SCENES] detection failed: {exc} → 1 scene, center crop")
        return fallback
    finally:
        if cap is not None:
            cap.release()


# Title overlay tunables (round 9 — banner-based design)
# User hand-designed a banner with a circular brand badge on the left and a
# white title strip extending to the right edge. We overlay the banner for
# the first 5 seconds and place title text inside the strip with auto-fit
# font sizing for any title length.
TITLE_OVERLAY_SECONDS = 5.0          # total time the banner is on screen
# Banner intro animation (motion of the strip extending) lasts 23 frames at 30fps
TITLE_BANNER_INTRO_DURATION = 23.0 / 30.0   # ≈ 0.767s
# After the banner finishes its intro motion, fade the title text in.
TITLE_TEXT_FADE_IN = 0.30
TITLE_TEXT_FADE_OUT = 0.40
# Round 9b (2026-05-13): start fade-out earlier than the visual boundary
# at TITLE_OVERLAY_SECONDS so the title is fully gone before the next
# beat of the clip lands. User wanted 0.5-1s earlier — using 0.75s.
TITLE_TEXT_FADE_OUT_LEAD = 0.75
# Path to the user's banner asset — animated MOV ProRes 1080x1920.
TITLE_BANNER = ROOT / "assets" / "brand" / "title-banner-9x16.mov"

# Title strip bounds (where text goes inside the banner). Measured from the
# PNG via PIL. The banner has a logo badge in the upper-left circle (roughly
# x=21-280) and the WHITE TITLE STRIP extending right from there to the edge.
# We give the text safe area generous padding inside the strip so descenders
# don't clip and the layout has breathing room.
TITLE_STRIP_X = 320      # left edge — clear of the logo badge
TITLE_STRIP_Y = 130      # top edge of strip's text-safe area
TITLE_STRIP_W = 720      # width — extends to ~x=1040 leaving 40px right padding
TITLE_STRIP_H = 195      # vertical text-safe area
TITLE_STRIP_PAD_H = 30   # extra horizontal padding inside the strip for text
TITLE_STRIP_PAD_V = 12   # extra vertical padding
# Round 9b (2026-05-13) fine alignment: user feedback "move down and left,
# a few photoshop arrow-key presses". 6px down, 8px left.
# Round 13.5 (2026-05-14): "slightly too high aligned in the white box" — nudge 2 more px down.
TITLE_STRIP_NUDGE_X = -8
TITLE_STRIP_NUDGE_Y = 8

# Auto-fit font size search bounds (Bebas Neue at the strip's pixel size).
# Round 13.5 (2026-05-14): "kinda small" — bump max + min so short titles
# render larger when they have room.
TITLE_FONT_MAX = 124
TITLE_FONT_MIN_ONE_LINE = 72   # below this, wrap to 2 lines instead of shrinking further
TITLE_FONT_MIN_TWO_LINE = 50

# Brand color (matches active-word ORANGE used for karaoke captions). Hex form
# for ffmpeg's drawtext fontcolor= argument. The 0x prefix is added at use site.
BRAND_ORANGE_HEX = "ff9526"


def _font_path() -> str:
    """Locate the Bebas Neue font. In the deployed container it's installed
    under /usr/local/share/fonts/...; locally (for tests) it's in
    assets/fonts/. Use whichever exists."""
    deployed = Path("/usr/local/share/fonts/bebas-neue/BebasNeue-Regular.ttf")
    if deployed.exists():
        return str(deployed)
    return str(ROOT / "assets" / "fonts" / "BebasNeue-Regular.ttf")


def _fit_title_to_strip(text: str) -> tuple[int, list[str]]:
    """Binary-search the largest font size that fits the title in the strip's
    text-safe area (with padding) on 1 line. If even the minimum 1-line size
    overflows, wrap to 2 lines and find the largest size that fits both.

    Returns (font_size, lines).

    Pure auto-fit: any title length renders cleanly inside the strip without
    manual intervention. A 4-word title fills the box at large size, a 9-word
    title shrinks gracefully or wraps to 2 lines centered vertically.
    """
    try:
        from PIL import ImageFont
    except ImportError:
        # Conservative fallback if PIL isn't available
        words = text.strip().split()
        if len(words) <= 5:
            return (90, [text.strip()])
        midpoint = len(words) // 2
        return (70, [" ".join(words[:midpoint]), " ".join(words[midpoint:])])

    text = text.strip()
    fp = _font_path()
    avail_w = TITLE_STRIP_W - 2 * TITLE_STRIP_PAD_H
    avail_h = TITLE_STRIP_H - 2 * TITLE_STRIP_PAD_V

    def _line_w(s: str, size: int) -> int:
        font = ImageFont.truetype(fp, size)
        bbox = font.getbbox(s)
        return bbox[2] - bbox[0]

    def _line_h(size: int) -> int:
        font = ImageFont.truetype(fp, size)
        # Use a generic uppercase string to estimate display height
        bbox = font.getbbox("AGTHQy")
        return bbox[3] - bbox[1]

    # Try ONE LINE at decreasing font sizes
    for size in range(TITLE_FONT_MAX, TITLE_FONT_MIN_ONE_LINE - 1, -2):
        if _line_w(text, size) <= avail_w and _line_h(size) <= avail_h:
            return (size, [text])

    # Wrap to TWO LINES — pick the most-balanced split (matches the existing
    # _wrap_title heuristic but ignores char limit since strip is wider than
    # 22-char wrap target).
    words = text.split()
    n = len(words)
    if n < 2:
        return (TITLE_FONT_MIN_ONE_LINE, [text])
    best_split = n // 2
    best_imbalance = float("inf")
    for split in range(1, n):
        l1 = " ".join(words[:split])
        l2 = " ".join(words[split:])
        imbalance = abs(len(l1) - len(l2))
        # Penalize splits that leave a function word at end of line 1
        last_w = words[split - 1].lower().rstrip(",.!?;:")
        if last_w in {"a", "an", "the", "to", "of", "in", "on", "and", "or", "but", "is", "as", "for"}:
            imbalance += 6
        if imbalance < best_imbalance:
            best_imbalance = imbalance
            best_split = split
    lines = [" ".join(words[:best_split]), " ".join(words[best_split:])]

    avail_h_per_line = (avail_h - 8) // 2  # 8px line gap
    longer = max(lines, key=len)
    for size in range(TITLE_FONT_MIN_ONE_LINE - 4, TITLE_FONT_MIN_TWO_LINE - 1, -2):
        if _line_w(longer, size) <= avail_w and _line_h(size) <= avail_h_per_line:
            return (size, lines)

    # Floor: emit at minimum size and hope for the best
    return (TITLE_FONT_MIN_TWO_LINE, lines)


def _title_overlay_filter(title: str | None, episode_dir: Path, clip_id: str,
                          banner_input_label: str = "[1:v]") -> str:
    """Build the filter chain segment that overlays the user's hand-designed
    banner + auto-fit drawtext on the dialogue stream.

    Round 9 redesign (2026-05-12): drops every drawbox-backdrop attempt and
    uses the user's hand-designed asset (animated 5s ProRes MOV with a logo
    badge + white title strip). Title text is rendered with auto-fit font
    sizing into the strip's text-safe area. Looks like designed graphic
    instead of programmer-drawn rectangle.

    Returns a CHAIN of filter segments (separated by `;`) that:
      1. takes the dialogue stream label `[v_pre_title]` as input
      2. overlays the banner video (banner_input_label) on top for first 5s
      3. drawtext per line fades in starting at TITLE_BANNER_INTRO_DURATION
      4. emits the result as `[v_with_title]`

    The caller wires `[v_pre_title]` → `[v_with_title]` into the larger graph.
    """
    if not title or not title.strip():
        return ""

    font_size, lines = _fit_title_to_strip(title)
    n_lines = len(lines)
    fp = _font_path()

    # Vertical positioning: center N lines in the strip's text-safe area,
    # then apply the round-9b nudge for fine alignment.
    line_gap = 8 if n_lines > 1 else 0
    line_height = font_size + line_gap
    block_h = line_height * n_lines - line_gap
    block_top_y = (TITLE_STRIP_Y + TITLE_STRIP_PAD_V
                   + (TITLE_STRIP_H - 2 * TITLE_STRIP_PAD_V - block_h) // 2
                   + TITLE_STRIP_NUDGE_Y)

    # Banner overlay: starts at t=0 of the clip, plays for 5s.
    # setpts shifts banner to start at 0; eof_action=pass keeps the underlying
    # dialogue visible after the banner ends.
    parts: list[str] = []
    parts.append(
        f"{banner_input_label}setpts=PTS-STARTPTS,format=rgba[banner_v]"
    )
    parts.append(
        f"[v_pre_title][banner_v]overlay=0:0:enable='lte(t\\,{TITLE_OVERLAY_SECONDS})'"
        f":eof_action=pass[v_with_banner]"
    )

    # Title text fades in AFTER the banner intro animation completes.
    # Fades out FADE_OUT_LEAD seconds before the banner disappears so the
    # text clears the screen before the next beat of the clip lands.
    text_fade_in_start = TITLE_BANNER_INTRO_DURATION
    text_fade_in_end = text_fade_in_start + TITLE_TEXT_FADE_IN
    text_fade_out_end = TITLE_OVERLAY_SECONDS - TITLE_TEXT_FADE_OUT_LEAD
    text_fade_out_start = text_fade_out_end - TITLE_TEXT_FADE_OUT
    text_alpha_expr = (
        f"if(lt(t\\,{text_fade_in_start:.3f})\\,0\\,"
        f"if(lt(t\\,{text_fade_in_end:.3f})\\,"
        f"(t-{text_fade_in_start:.3f})/{TITLE_TEXT_FADE_IN:.3f}\\,"
        f"if(gt(t\\,{text_fade_out_end:.3f})\\,0\\,"
        f"if(gt(t\\,{text_fade_out_start:.3f})\\,"
        f"({text_fade_out_end:.3f}-t)/{TITLE_TEXT_FADE_OUT:.3f}\\,1))))"
    )

    # Build a chain that applies one drawtext per line on top of the banner
    # overlay output. Last drawtext emits [v_with_title].
    text_chain_in = "[v_with_banner]"
    for i, line in enumerate(lines):
        title_txt = episode_dir / f"{clip_id}.title.{i}.txt"
        title_txt.write_text(line)

        y_line = block_top_y + i * line_height
        # Center text horizontally inside the strip (not the whole frame),
        # then apply the round-9b nudge for fine alignment.
        strip_left = TITLE_STRIP_X + TITLE_STRIP_PAD_H + TITLE_STRIP_NUDGE_X
        strip_inner_w = TITLE_STRIP_W - 2 * TITLE_STRIP_PAD_H
        x_expr = f"{strip_left}+({strip_inner_w}-text_w)/2"

        out_label = "[v_with_title]" if i == n_lines - 1 else f"[v_text_{i}]"
        parts.append(
            f"{text_chain_in}drawtext="
            f"fontfile='{fp}'"
            f":textfile='{title_txt}'"
            f":fontsize={font_size}"
            # Pure black text on the white strip — no orange stroke per
            # user feedback ("remove the orange stroke around the text").
            f":fontcolor=black"
            f":x='{x_expr}'"
            f":y={y_line}"
            f":enable='lte(t\\,{TITLE_OVERLAY_SECONDS})'"
            f":alpha='{text_alpha_expr}'"
            f"{out_label}"
        )
        text_chain_in = out_label

    return ";".join(parts)


def _build_video_filter(scenes: list[tuple[float, float, int]], ass_path: Path,
                        crop_w: int = CROP_W) -> list[str]:
    """Build the video-branch filter segments that produce the `[v_pre_title]`
    label — a 1080x1920 stream with crop applied per scene + captions burned
    in. Callers then layer banner overlay + drawtext title on top, and CTA
    appended at the end.

    Round 9 refactor: stripped title overlay from this function. Title is now
    a separate banner-video overlay handled in _build_ffmpeg_cmd.

    Single-scene fast path:
        [0:v]crop=...,scale=1080:1920,setsar=1,subtitles='...'[v_pre_title]

    Multi-scene path: split the video N ways, trim+crop each branch with its
    own offset, concat, then apply subtitles to the rebuilt 0-based timeline.
    """
    n = len(scenes)
    if n <= 1:
        _s, _e, cx = scenes[0]
        return [
            f"[0:v]crop={crop_w}:1080:{cx}:0,scale=1080:1920,setsar=1,"
            f"subtitles='{ass_path}'[v_pre_title]"
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
        f"{concat_inputs}concat=n={n}:v=1:a=0,setsar=1,"
        f"subtitles='{ass_path}'[v_pre_title]"
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

    Round 9 architecture (2026-05-12):

    INPUTS:
      [0] source_video — full podcast episode (we use -ss/-to to extract dialog window)
      [1] music bed (if has_music)
      [2] title banner (animated 5s MOV) — if title is provided
      [3] end-card / closer ad (5s MP4) — if END_CARD exists

    VIDEO CHAIN:
      [0:v] → crop + scale + subtitles → [v_pre_title]
      [v_pre_title] + [banner] → overlay banner first 5s → [v_with_banner]
      [v_with_banner] → drawtext title in strip area → [v_with_title]
      ([v_with_title] = dialogue portion, 1080x1920 with captions + banner + title)
      [closer_ad] → scale + fade-in from black → [v_cta]
      [v_with_title] + [v_cta] → concat → [v_out]

    AUDIO CHAIN:
      [0:a] dialogue
      [1:a] music — single continuous stream from t=0, volume timeline:
            quiet during dialog (music_volume), bumps to 0.20 during CTA
      Mix dialogue + music with sidechain ducking on the dialog portion only.
      apad the dialogue to total_duration so the audio stream extends through
      the CTA portion as silence + bumped music.

    OUTPUT:
      [v_out] + [a_out], total duration = dialog_duration + CTA_DURATION
    """
    music_volume = max(0.05, min(0.20, float(music_volume)))

    has_title = bool(title and title.strip() and episode_dir is not None
                     and clip_id is not None and TITLE_BANNER.exists())
    has_cta = END_CARD.exists()
    CTA_DURATION = 5.0
    CTA_FADE_IN = 0.4
    total_duration = duration + (CTA_DURATION if has_cta else 0.0)

    # Build the VIDEO chain
    filter_parts = _build_video_filter(scenes, ass_path, crop_w=crop_w)

    # Determine input indices dynamically. Order: source(0), music(1?), banner(?), endcard(?)
    next_input_idx = 1
    music_idx = -1
    banner_idx = -1
    cta_idx = -1
    if has_music:
        music_idx = next_input_idx; next_input_idx += 1
    if has_title:
        banner_idx = next_input_idx; next_input_idx += 1
    if has_cta:
        cta_idx = next_input_idx; next_input_idx += 1

    # Title overlay (banner + drawtext) — operates on [v_pre_title] → [v_with_title]
    if has_title:
        title_chain = _title_overlay_filter(title, episode_dir, clip_id,
                                            banner_input_label=f"[{banner_idx}:v]")
        if title_chain:
            filter_parts.append(title_chain)
        last_video_label = "[v_with_title]"
    else:
        last_video_label = "[v_pre_title]"

    # CTA append — concat dialogue portion with CTA portion
    if has_cta:
        filter_parts.append(
            f"[{cta_idx}:v]scale=1080:1920,setsar=1,"
            f"fade=t=in:st=0:d={CTA_FADE_IN:.2f}:color=black[v_cta]"
        )
        filter_parts.append(
            f"{last_video_label}[v_cta]concat=n=2:v=1:a=0[v_out]"
        )
        vout_label = "[v_out]"
    else:
        vout_label = last_video_label

    # AUDIO CHAIN — round 14 (2026-05-14) redesign.
    #
    # Round-13.5 fade was inaudible because afade was applied to [0:a] BEFORE
    # the asplit. The faded stream fed BOTH the playback branch AND the
    # sidechain compressor's key input — when the key faded to silence, the
    # compressor let off the ducking, music ramped UP at exactly the same
    # rate voice ramped DOWN, and the net loudness barely changed.
    #
    # Round-14 fix:
    #   1. apad the un-faded dialogue (keys for sidechain need full signal).
    #   2. asplit AFTER apad — one branch feeds sidechain key (un-faded),
    #      the other feeds the playback fade.
    #   3. afade applied ONLY to the playback branch.
    #   4. Music volume becomes a 4-piece linear ramp (was a step function):
    #        before fade:      ducked level V
    #        during fade:      V → MUSIC_TROUGH (music dips with the voice swell-out)
    #        during CTA fade:  MUSIC_TROUGH → 0.22 (matches visual CTA_FADE_IN)
    #        after CTA fade:   0.22 (bumped level)
    #      This is smooth instead of a step at t=duration.
    # Constants bumped: DIALOG_FADE_OUT 0.30 → 0.60 (user said 0.30 unnoticeable).
    DIALOG_FADE_OUT = 0.60
    MUSIC_TROUGH = 0.05
    fade_start = max(0.0, duration - DIALOG_FADE_OUT)
    if has_music:
        # Step 1: apad un-faded dialogue (keys for sidechain need full signal).
        filter_parts.append(
            f"[0:a]apad=whole_dur={total_duration:.3f}[dialog_padded]"
        )
        # Step 2-3: asplit, then afade only on playback branch.
        filter_parts.append("[dialog_padded]asplit=2[dialog_key][dialog_pre_fade]")
        filter_parts.append(
            f"[dialog_pre_fade]afade=t=out:st={fade_start:.3f}:d={DIALOG_FADE_OUT:.3f}[dialog]"
        )
        # Step 4: piecewise-linear music volume ramp.
        # Sentinels for readability inside the ffmpeg expression: F=fade_start,
        # D=duration, Df=fade duration, C=CTA fade-in, V=music_volume, MT=trough.
        # Inside filter_complex, commas inside the expression MUST be \-escaped.
        F = fade_start
        D = duration
        Df = DIALOG_FADE_OUT
        C = CTA_FADE_IN
        V = music_volume
        MT = MUSIC_TROUGH
        # Linear interpolation form: a + (b-a)*progress, with progress clipped
        # to its segment. Nested if() preserves piecewise behavior.
        music_vol_expr = (
            f"if(lt(t\\,{F:.3f})\\,{V:.3f}\\,"
            f"if(lt(t\\,{D:.3f})\\,{V:.3f}+({MT:.3f}-{V:.3f})*(t-{F:.3f})/{Df:.3f}\\,"
            f"if(lt(t\\,{D + C:.3f})\\,{MT:.3f}+(0.22-{MT:.3f})*(t-{D:.3f})/{C:.3f}\\,"
            f"0.22)))"
        )
        filter_parts.append(
            f"[{music_idx}:a]aloop=loop=-1:size=2e9,"
            f"atrim=0:{total_duration:.3f},"
            f"volume='{music_vol_expr}':eval=frame[music_raw]"
        )
        # Sidechain ducks against the UN-faded key (full signal during the
        # voice fade-out → keeps music ducked through the fade, releasing
        # only when dialog actually stops post-fade). The 400ms release +
        # the music ramp climb both go in the same direction at CTA fade-in,
        # producing a smooth swell.
        filter_parts.append(
            "[music_raw][dialog_key]sidechaincompress="
            "threshold=0.05:ratio=8:attack=5:release=400:makeup=1[music]"
        )
        filter_parts.append(
            f"[dialog][music]amix=duration=first:dropout_transition=3[aout]"
        )
        aout_label = "[aout]"
    else:
        # No music: apad + afade on the single dialogue stream (no asplit
        # needed — there's no sidechain key consumer).
        filter_parts.append(
            f"[0:a]apad=whole_dur={total_duration:.3f},"
            f"afade=t=out:st={fade_start:.3f}:d={DIALOG_FADE_OUT:.3f}[aout]"
        )
        aout_label = "[aout]"

    filter_complex = ";".join(filter_parts)

    # Build the input arg list. Order matters — must match input indices above.
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-ss", f"{start:.3f}", "-to", f"{end:.3f}", "-i", str(source_video),
    ]
    if has_music and music is not None:
        cmd += ["-stream_loop", "-1", "-i", str(music)]
    if has_title:
        cmd += ["-i", str(TITLE_BANNER)]
    if has_cta:
        cmd += ["-i", str(END_CARD)]

    cmd += [
        "-filter_complex", filter_complex,
        "-map", vout_label,
        "-map", aout_label,
        "-c:v", "libx264", "-preset", "medium", "-crf", "22",
        "-pix_fmt", "yuv420p",
        "-r", "30",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        "-t", f"{total_duration:.3f}",
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
        """Gate 3 rescue: re-run scene detection with a more sensitive
        threshold (0.20 vs default 0.30). Lower threshold → ffmpeg flags more
        cuts → each new scene gets fresh face-detection sampling. Returns
        (ok, new_scenes)."""
        nonlocal scenes
        new_scenes = detect_scenes_and_crops(
            source_video, start, end,
            crop_w=crop_w, cut_threshold=0.20,
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
