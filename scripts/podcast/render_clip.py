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
FACE_MIN_SIZE = 90
# Frames sampled per detected scene when computing that scene's face center.
FACE_SAMPLES_PER_SCENE = 3

# --- Scene detection ---------------------------------------------------------
# Sampling stride when walking the clip to find hard camera cuts (seconds).
# 0.4s is the sweet spot: dense enough to place a cut within a single frame of
# the true boundary, sparse enough to keep detection under ~1s wall-time.
SCENE_SAMPLE_STRIDE_SEC = 0.4
# Bhattacharyya distance above which consecutive frames are flagged as a cut.
# Range [0,1]; 0 = identical, 1 = disjoint histograms. For hard cuts between
# different cameras in a podcast, observed values are typically > 0.40;
# within-scene frame-to-frame values are typically < 0.20. 0.35 splits the
# difference with margin.
BHATTA_CUT_THRESHOLD = 0.35
# Scenes shorter than this are merged into the previous scene (drops
# transition frames + avoids 1-sample "scenes" that would spawn tiny trim
# segments in the filter graph).
MIN_SCENE_DURATION_SEC = 0.6
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


def _pick_music_bed(seed: str | None = None) -> Path | None:
    candidates = sorted(list(MUSIC_BEDS.glob("*.wav")) + list(MUSIC_BEDS.glob("*.mp3")) +
                        list(MUSIC_BEDS.glob("*.flac")) + list(MUSIC_BEDS.glob("*.ogg")))
    if not candidates:
        return None
    rng = random.Random(seed)
    return rng.choice(candidates)


def _face_center_for_range(cap, cascade, t_start: float, t_end: float,
                           samples: int = FACE_SAMPLES_PER_SCENE,
                           min_face: int = FACE_MIN_SIZE) -> int | None:
    """Sample `samples` frames evenly inside [t_start, t_end] (source-video
    timestamps, seconds) and return the median face X-center, or None if no
    face was detected in any sample.
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
        faces = cascade.detectMultiScale(
            gray, scaleFactor=1.2, minNeighbors=5, minSize=(min_face, min_face),
        )
        for (x, _y, w, _h) in faces:
            xs.append(int(x + w / 2))

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
) -> list[tuple[float, float, int]]:
    """Detect camera cuts inside [start_sec, end_sec] and return per-scene
    crop offsets.

    Returns a list of (scene_start_rel, scene_end_rel, crop_x) tuples, where
    times are CLIP-RELATIVE (0-based). Always returns at least one tuple
    covering the full duration — callers never have to handle an empty list.

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

        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        cascade = cv2.CascadeClassifier(cascade_path)
        if cascade.empty():
            print("  [SCENES] haar cascade failed to load → 1 scene, center crop")
            return fallback

        # --- Pass 1: walk the clip at fixed stride, diff HSV histograms -----
        stride = SCENE_SAMPLE_STRIDE_SEC
        n_samples = max(2, int(duration / stride) + 1)
        prev_hist = None
        # cut_points holds clip-relative timestamps where a cut is detected
        cut_points: list[float] = [0.0]
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
                if d > BHATTA_CUT_THRESHOLD:
                    cut_points.append(t_rel)
            prev_hist = hist
        cut_points.append(duration)

        # Build initial scene list from consecutive cut points
        scenes_rel: list[tuple[float, float]] = []
        for a, b in zip(cut_points, cut_points[1:]):
            if b > a:
                scenes_rel.append((a, b))

        # --- Merge scenes shorter than MIN_SCENE_DURATION_SEC ----------------
        merged: list[tuple[float, float]] = []
        for s, e in scenes_rel:
            if merged and (e - s) < MIN_SCENE_DURATION_SEC:
                ps, _pe = merged[-1]
                merged[-1] = (ps, e)
            else:
                merged.append((s, e))
        if not merged:
            merged = [(0.0, duration)]

        if len(merged) > MAX_SCENES:
            print(f"  [SCENES] {len(merged)} scenes > cap {MAX_SCENES} → 1 scene, center crop")
            return fallback

        # --- Pass 2: for each scene, detect face → crop_x --------------------
        result: list[tuple[float, float, int]] = []
        any_face = False
        for s, e in merged:
            face_x = _face_center_for_range(
                cap, cascade, start_sec + s, start_sec + e,
            )
            if face_x is None:
                crop_x = CENTER_CROP_X
            else:
                any_face = True
                crop_x = face_x - crop_w // 2
                crop_x = max(0, min(source_w - crop_w, crop_x))
            result.append((s, e, crop_x))

        if not any_face:
            print(f"  [SCENES] {len(result)} scenes, 0 faces → 1 scene, center crop")
            return fallback

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


def _build_video_filter(scenes: list[tuple[float, float, int]], ass_path: Path,
                        crop_w: int = CROP_W) -> list[str]:
    """Build the video-branch filter segments that produce the `[v0]` label
    (a 1080x1920 stream with captions burned in). Callers then append the
    end-card overlay and audio branches the same way regardless of scene
    count.

    Single-scene fast path (identical to pre-fix behavior):
        [0:v]crop=...,scale=1080:1920,setsar=1,subtitles='...'[v0]

    Multi-scene path: split the video N ways, trim+crop each branch with its
    own offset, concat, then apply subtitles to the rebuilt 0-based timeline.
    """
    n = len(scenes)
    if n <= 1:
        _s, _e, cx = scenes[0]
        return [
            f"[0:v]crop={crop_w}:1080:{cx}:0,scale=1080:1920,setsar=1,"
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
        f"{concat_inputs}concat=n={n}:v=1:a=0,setsar=1,"
        f"subtitles='{ass_path}'[v0]"
    )
    return parts


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

    music = _pick_music_bed(seed=clip_id)
    has_music = music is not None

    # Build the scene list that drives the crop graph. Explicit --crop-x from
    # the CLI still wins as a manual escape hatch; otherwise auto-detect.
    if crop_x is not None:
        scenes: list[tuple[float, float, int]] = [(0.0, duration, crop_x)]
    else:
        scenes = detect_scenes_and_crops(source_video, start, end, crop_w=crop_w)

    filter_parts = _build_video_filter(scenes, ass_path, crop_w=crop_w)
    vout_label = "[v0]"
    if END_CARD.exists():
        filter_parts.append(
            f"[2:v]scale=1080:1920,format=rgba,fade=t=in:st={max(0, duration-4):.2f}:d=0.5:alpha=1[ec]"
        )
        filter_parts.append(
            f"[v0][ec]overlay=0:0:enable='gte(t,{max(0, duration-4):.2f})'[vout]"
        )
        vout_label = "[vout]"

    if has_music:
        # Music bed mixed quieter (2026-04-23: bumped from 0.15 → 0.12 per user ask
        # for "5% quieter"; interpreted as a perceptible ~2dB cut).
        filter_parts.append("[0:a]volume=1.0[dialog]")
        filter_parts.append("[1:a]volume=0.12,aloop=loop=-1:size=2e9[music]")
        filter_parts.append("[dialog][music]amix=duration=shortest:dropout_transition=3[aout]")
        aout_label = "[aout]"
    else:
        aout_label = "0:a"

    filter_complex = ";".join(filter_parts)

    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-ss", f"{start:.3f}", "-to", f"{end:.3f}", "-i", str(source_video),
    ]
    if has_music:
        cmd += ["-stream_loop", "-1", "-i", str(music)]
    else:
        # keep input indexes predictable even without music
        pass
    if END_CARD.exists():
        if not has_music:
            # if no music, end_card becomes input [1], not [2]
            filter_complex = filter_complex.replace("[2:v]", "[1:v]")
        cmd += ["-i", str(END_CARD)]

    cmd += [
        "-filter_complex", filter_complex,
        "-map", vout_label,
    ]
    if aout_label.startswith("["):
        cmd += ["-map", aout_label]
    else:
        cmd += ["-map", aout_label]

    cmd += [
        "-c:v", "libx264", "-preset", "medium", "-crf", "22",
        "-pix_fmt", "yuv420p",
        "-r", "30",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        "-t", f"{duration:.3f}",
        str(out_path),
    ]

    print(f"[RENDER] {clip_id}  {duration:.1f}s  music={music.name if music else 'none'}")
    if dry_run:
        print("  " + " ".join(cmd))
        return out_path

    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        print(f"[ERROR] {clip_id} ffmpeg exited {proc.returncode}")
        print(proc.stderr[-2000:])
        return None
    print(f"[DONE] {out_path.relative_to(ROOT)}")
    return out_path


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
