"""YuNet-based face detection + active-speaker selection for vertical shorts.

Replaces the Haar-cascade approach which had a 33% Gate-3 rejection rate on the
May 5 reprocess because:
  (a) Haar misses profile/angled poses — the off-center podcast member whose
      camera shows them at an angle to the lens was frequently un-detected,
      and the renderer fell back to a dead-center crop, leaving them off-screen.
  (b) When 3 faces are visible, taking the MEDIAN X positions all three speakers
      between cameras instead of cropping on whoever is actively talking.

YuNet (built into OpenCV ≥4.5 as `cv2.FaceDetectorYN`):
  - Better recall on profile/angled poses (~95% vs Haar's ~50%)
  - Returns 5 facial landmarks per face including left+right mouth corners
  - Returns confidence scores per detection
  - 227KB ONNX model, no extra dependencies beyond opencv-python(-headless)

Active-speaker selection (when multiple faces in frame):
  - Sample N frames across the scene window
  - YuNet detects all faces per frame
  - Greedy-match faces across frames into "tracks" (one track per person)
  - Per track, score by:
      * mouth_motion: variance of mouth-opening across the track's frames
        (talking → lips part and rejoin repeatedly → high variance)
      * face_size: average area (camera focused on subject → larger face)
      * stability: detection count (consistently visible = main subject)
  - Return median X of the highest-scoring track's faces

Falls back to Haar cascades if YuNet ONNX is unavailable (graceful degrade —
container without the model still works, just less accurately).
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

import numpy as np

ROOT = Path(__file__).resolve().parent.parent.parent
MODEL_PATH = ROOT / "data" / "podcast" / "_models" / "face_detection_yunet_2023mar.onnx"

# Tunables --------------------------------------------------------------------
YUNET_SCORE_THRESHOLD = 0.45  # min confidence for a face detection
YUNET_NMS_THRESHOLD = 0.3
YUNET_TOP_K = 10              # cap on faces per frame (more than 5 is unusual for a 3-person podcast)
# Min bbox size in source-resolution pixels — filters distant background faces.
# At 1920×1080, a typical podcast face is 140-220 px wide. Set floor to 50
# (covers the "Tristan-in-front-of-arcade" angle which can come down to ~70 px).
MIN_FACE_SIZE = 50

# Track matching: faces in consecutive frames are the same person if their IoU
# (intersection over union) exceeds this threshold OR their center-to-center
# distance is within a face's width.
TRACK_IOU_MATCH = 0.30
TRACK_CENTER_DISTANCE_FRAC = 1.0  # multiple of face width

# Haar fallback (used only if YuNet ONNX can't be loaded)
HAAR_MIN_SIZE = 60
HAAR_SCALE_FACTOR = 1.1
HAAR_MIN_NEIGHBORS = 4


class FaceDetector:
    """Singleton face detector. Loads YuNet ONNX lazily on first use.

    Construction is cheap; first detection downloads the model into memory.
    Reuse across many frames within one pipeline run.
    """
    _instance = None

    @classmethod
    def get(cls) -> "FaceDetector":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        import cv2  # type: ignore

        self.cv2 = cv2
        self.use_yunet = False
        self.yunet = None
        self.haar_frontal = None
        self.haar_profile = None
        self._current_size = (0, 0)

        if MODEL_PATH.exists():
            try:
                self.yunet = cv2.FaceDetectorYN.create(
                    model=str(MODEL_PATH),
                    config="",
                    input_size=(320, 320),
                    score_threshold=YUNET_SCORE_THRESHOLD,
                    nms_threshold=YUNET_NMS_THRESHOLD,
                    top_k=YUNET_TOP_K,
                )
                self.use_yunet = True
            except Exception as exc:  # pragma: no cover — environment-dependent
                print(f"  [face] YuNet load failed ({exc}); falling back to Haar")

        if not self.use_yunet:
            self.haar_frontal = cv2.CascadeClassifier(
                cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            )
            self.haar_profile = cv2.CascadeClassifier(
                cv2.data.haarcascades + "haarcascade_profileface.xml"
            )

    # ------------------------------------------------------------------------

    def detect(self, image: np.ndarray) -> list[dict]:
        """Detect faces in a single BGR image.

        Returns a list of:
            {
              "bbox": (x, y, w, h),         # source-image coordinates
              "conf": float,                 # detection confidence 0-1
              "cx": int,                     # face center X (= x + w/2)
              "cy": int,                     # face center Y
              "area": int,                   # w * h
              "mouth_opening": float | None, # vertical span between mouth corners
              "landmarks": dict | None,      # YuNet keypoints; None for Haar fallback
            }
        Sorted by area DESC (largest face first).
        """
        if self.use_yunet:
            return self._detect_yunet(image)
        return self._detect_haar(image)

    # ------------------------------------------------------------------------

    def _detect_yunet(self, image: np.ndarray) -> list[dict]:
        h, w = image.shape[:2]
        if (w, h) != self._current_size:
            self.yunet.setInputSize((w, h))
            self._current_size = (w, h)
        retval, faces = self.yunet.detect(image)
        if faces is None:
            return []
        results: list[dict] = []
        for f in faces:
            fx, fy, fw, fh = int(f[0]), int(f[1]), int(f[2]), int(f[3])
            if fw < MIN_FACE_SIZE or fh < MIN_FACE_SIZE:
                continue
            # Clamp bbox into image bounds (YuNet sometimes emits slightly negative coords)
            fx = max(0, fx); fy = max(0, fy)
            fw = min(fw, w - fx); fh = min(fh, h - fy)
            if fw <= 0 or fh <= 0:
                continue

            # Landmarks
            mr_x, mr_y = float(f[10]), float(f[11])
            ml_x, ml_y = float(f[12]), float(f[13])
            # Mouth opening proxy: vertical span between left + right mouth corners,
            # normalized by face height (so we can compare across face sizes).
            # When a person talks, mouth corners shift slightly vertically as the
            # mouth opens/closes. Track variance across frames is the signal.
            mouth_dy = abs(ml_y - mr_y)
            mouth_open_norm = mouth_dy / max(1, fh)

            results.append({
                "bbox": (fx, fy, fw, fh),
                "conf": float(f[14]),
                "cx": int(fx + fw / 2),
                "cy": int(fy + fh / 2),
                "area": fw * fh,
                "mouth_opening": mouth_open_norm,
                "landmarks": {
                    "right_eye": (float(f[4]), float(f[5])),
                    "left_eye": (float(f[6]), float(f[7])),
                    "nose": (float(f[8]), float(f[9])),
                    "mouth_right": (mr_x, mr_y),
                    "mouth_left": (ml_x, ml_y),
                },
            })
        results.sort(key=lambda r: r["area"], reverse=True)
        return results

    def _detect_haar(self, image: np.ndarray) -> list[dict]:
        cv2 = self.cv2
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        w_img = gray.shape[1]
        all_faces: list[tuple[int, int, int, int]] = []

        # Frontal pass
        if self.haar_frontal is not None and not self.haar_frontal.empty():
            faces = self.haar_frontal.detectMultiScale(
                gray, scaleFactor=HAAR_SCALE_FACTOR,
                minNeighbors=HAAR_MIN_NEIGHBORS,
                minSize=(HAAR_MIN_SIZE, HAAR_MIN_SIZE),
            )
            for (x, y, fw, fh) in faces:
                all_faces.append((int(x), int(y), int(fw), int(fh)))

        # Profile passes (both directions)
        if self.haar_profile is not None and not self.haar_profile.empty():
            for flipped in (False, True):
                search = cv2.flip(gray, 1) if flipped else gray
                faces = self.haar_profile.detectMultiScale(
                    search, scaleFactor=HAAR_SCALE_FACTOR,
                    minNeighbors=HAAR_MIN_NEIGHBORS,
                    minSize=(HAAR_MIN_SIZE, HAAR_MIN_SIZE),
                )
                for (x, y, fw, fh) in faces:
                    if flipped:
                        x = w_img - x - fw
                    all_faces.append((int(x), int(y), int(fw), int(fh)))

        # Deduplicate overlapping detections (simple: cluster by center proximity)
        dedup: list[tuple[int, int, int, int]] = []
        for box in all_faces:
            x, y, fw, fh = box
            cx, cy = x + fw // 2, y + fh // 2
            is_dup = False
            for ox, oy, ow, oh in dedup:
                ocx, ocy = ox + ow // 2, oy + oh // 2
                if abs(cx - ocx) < fw // 2 and abs(cy - ocy) < fh // 2:
                    is_dup = True
                    break
            if not is_dup:
                dedup.append(box)

        results = [
            {
                "bbox": b,
                "conf": 0.5,  # Haar has no real score; pick a neutral one
                "cx": b[0] + b[2] // 2,
                "cy": b[1] + b[3] // 2,
                "area": b[2] * b[3],
                "mouth_opening": None,
                "landmarks": None,
            }
            for b in dedup
        ]
        results.sort(key=lambda r: r["area"], reverse=True)
        return results


# =============================================================================
# Active-speaker selection: face tracks across multiple frames
# =============================================================================

def _iou(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> float:
    """Standard IoU on (x, y, w, h) boxes."""
    ax1, ay1, aw, ah = a
    bx1, by1, bw, bh = b
    ax2, ay2 = ax1 + aw, ay1 + ah
    bx2, by2 = bx1 + bw, by1 + bh
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0, ix2 - ix1), max(0, iy2 - iy1)
    inter = iw * ih
    if inter == 0:
        return 0.0
    union = aw * ah + bw * bh - inter
    return inter / union


def _build_tracks(frames_faces: list[list[dict]]) -> list[list[dict]]:
    """Greedy temporal matcher: assign each face in each frame to a track.

    Two faces in consecutive frames are the same person if either:
      - IoU(box, prev_box) ≥ TRACK_IOU_MATCH, OR
      - center-distance ≤ TRACK_CENTER_DISTANCE_FRAC × face width

    Returns a list of tracks; each track is a list of face dicts in frame order
    (with at most one face per track per frame).
    """
    tracks: list[list[dict]] = []
    for frame_faces in frames_faces:
        if not tracks:
            for f in frame_faces:
                tracks.append([f])
            continue
        # For each track, find the best-matching face in this frame
        used_face_idxs: set[int] = set()
        for tr in tracks:
            last = tr[-1]
            last_bbox = last["bbox"]
            last_cx, last_cy = last["cx"], last["cy"]
            last_w = last_bbox[2]
            best_idx = None
            best_score = 0.0
            for i, f in enumerate(frame_faces):
                if i in used_face_idxs:
                    continue
                # Primary match: IoU
                iou_val = _iou(last_bbox, f["bbox"])
                if iou_val >= TRACK_IOU_MATCH:
                    score = iou_val
                else:
                    # Secondary: center proximity scaled by face width
                    d = ((f["cx"] - last_cx) ** 2 + (f["cy"] - last_cy) ** 2) ** 0.5
                    if d <= TRACK_CENTER_DISTANCE_FRAC * last_w:
                        score = 1.0 - (d / (TRACK_CENTER_DISTANCE_FRAC * last_w))
                    else:
                        continue
                if score > best_score:
                    best_score = score
                    best_idx = i
            if best_idx is not None:
                tr.append(frame_faces[best_idx])
                used_face_idxs.add(best_idx)
        # Any faces not matched start new tracks
        for i, f in enumerate(frame_faces):
            if i not in used_face_idxs:
                tracks.append([f])
    return tracks


def _score_track(track: list[dict], n_frames_total: int) -> float:
    """Score a track for "likely active speaker" weight.

    Combines:
      mouth_motion: variance of mouth_opening across frames (high → talking)
      face_size:    average area, normalized (high → camera focused on subject)
      stability:    detections / n_frames_total (consistently visible = main)
      confidence:   average detection confidence

    Returns a non-negative composite score; larger = more likely the speaker.
    """
    if not track:
        return 0.0

    # Mouth-motion variance — only valid if landmarks were captured (YuNet)
    mouth_open = [t.get("mouth_opening") for t in track if t.get("mouth_opening") is not None]
    if len(mouth_open) >= 2:
        m = sum(mouth_open) / len(mouth_open)
        var = sum((x - m) ** 2 for x in mouth_open) / len(mouth_open)
        # Scale variance into a 0-1ish range. Empirical: variances ~0.0001 (still
        # face) to ~0.005 (active talking). Multiply by 200 then clip.
        mouth_motion = min(1.0, var * 200.0)
    else:
        mouth_motion = 0.0

    avg_area = sum(t["area"] for t in track) / len(track)
    # 1920×1080 frame ~ 2M pixels. A face spanning 200×250 = 50K = 2.5%. Use a
    # generous normalizer so most podcast-face areas fall in 0-1 range.
    face_size_score = min(1.0, avg_area / 80000.0)

    stability = len(track) / max(1, n_frames_total)
    avg_conf = sum(t["conf"] for t in track) / len(track)

    # Weights tuned to bias toward MOUTH MOTION when available (YuNet path).
    # When mouth landmarks are absent (Haar fallback), face_size + stability +
    # confidence carry the full signal.
    if mouth_open:
        # Mouth motion is the strongest signal when present
        score = (
            0.50 * mouth_motion +
            0.25 * face_size_score +
            0.15 * stability +
            0.10 * avg_conf
        )
    else:
        # No mouth landmarks: rely on size + stability
        score = (
            0.45 * face_size_score +
            0.40 * stability +
            0.15 * avg_conf
        )
    return score


def best_speaker_cx(frames_faces: list[list[dict]]) -> int | None:
    """Given a list of per-frame face-detection results, return the X-center of
    the most likely active speaker.

    Frames are assumed to be sampled from a single scene window where the
    active speaker is the same person throughout.

    Returns None if no faces were detected in any frame.
    """
    if not frames_faces or not any(frames_faces):
        return None

    # Special case: only 1 face ever detected → it's the speaker
    all_xs: list[int] = []
    flat_faces: list[dict] = []
    for frame in frames_faces:
        for f in frame:
            flat_faces.append(f)
            all_xs.append(f["cx"])
    if not flat_faces:
        return None
    # If every detection clusters within ~150px (same person, jitter), return median
    if max(all_xs) - min(all_xs) < 150:
        all_xs.sort()
        return all_xs[len(all_xs) // 2]

    # Build tracks + score
    tracks = _build_tracks(frames_faces)
    if not tracks:
        return None
    scored = [(t, _score_track(t, len(frames_faces))) for t in tracks]
    scored.sort(key=lambda x: x[1], reverse=True)

    # Round 14 (2026-05-14): two-speakers-both-talking tie-breaker.
    # When the top-2 tracks score within 10% AND both show real mouth motion
    # (>0.5 normalized), the winner is decided by floating-point noise in the
    # variance estimator. The user sees the "wrong" person centered for the
    # whole scene, with the choice flipping unpredictably across re-renders.
    # Tie-break by avg face area DESC — the camera-focused subject wins.
    if len(scored) >= 2:
        s1 = scored[0][1]
        s2 = scored[1][1]
        if s1 > 0 and (s1 - s2) / s1 < 0.10:
            mouth1 = [t.get("mouth_opening") for t in scored[0][0]
                      if t.get("mouth_opening") is not None]
            mouth2 = [t.get("mouth_opening") for t in scored[1][0]
                      if t.get("mouth_opening") is not None]
            def _var(xs: list[float]) -> float:
                if len(xs) < 2:
                    return 0.0
                m = sum(xs) / len(xs)
                return sum((x - m) ** 2 for x in xs) / len(xs)
            if _var(mouth1) * 200.0 > 0.5 and _var(mouth2) * 200.0 > 0.5:
                # Both are clearly talking — pick the larger-area subject
                area1 = sum(t["area"] for t in scored[0][0]) / len(scored[0][0])
                area2 = sum(t["area"] for t in scored[1][0]) / len(scored[1][0])
                if area2 > area1:
                    scored[0], scored[1] = scored[1], scored[0]

    best_track, best_score = scored[0]

    # The chosen speaker's X = median of their face centers across frames they appear in
    cxs = [t["cx"] for t in best_track]
    cxs.sort()
    return cxs[len(cxs) // 2]


# =============================================================================
# Public entry point used by render_clip.py
# =============================================================================

def face_center_for_range(cap, t_start: float, t_end: float,
                          samples: int = 8) -> int | None:
    """Sample `samples` frames evenly inside [t_start, t_end] (source-video
    timestamps, seconds) and return the X-center of the most likely active
    speaker (or None if no faces detected in any sample).

    This replaces render_clip.py's `_face_center_for_range` Haar-only implementation.
    Bumped samples 5 → 8 for better active-speaker statistics (variance of
    mouth-opening needs more frames to be reliable).

    `cap` is an open cv2.VideoCapture; this function seeks via CAP_PROP_POS_MSEC.
    """
    import cv2  # type: ignore

    det = FaceDetector.get()
    dur = max(0.1, t_end - t_start)
    frames_faces: list[list[dict]] = []
    for i in range(samples):
        t = t_start + dur * ((i + 0.5) / samples)
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000.0)
        ok, frame = cap.read()
        if not ok or frame is None:
            frames_faces.append([])
            continue
        frames_faces.append(det.detect(frame))
    return best_speaker_cx(frames_faces)


def using_yunet() -> bool:
    """True iff YuNet ONNX is active; False if we're on Haar fallback.
    Used by callers (render_clip.py) for logging."""
    return FaceDetector.get().use_yunet
