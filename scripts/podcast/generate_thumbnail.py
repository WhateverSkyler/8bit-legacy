#!/usr/bin/env python3
"""Generate a YouTube thumbnail (1280x720 JPG) for a podcast video.

Style:
  - Frame grab at 35% through the video, saturation +20%, brightness +10%
  - Bold Bebas Neue title text in top-third (2-3 lines, ~110pt),
    white fill with a 6px orange #ff9526 stroke + black drop shadow
  - Brand orange accent bar bottom-right
  - 8-Bit Legacy logo bottom-right corner (if assets/brand/logo-white.png exists)

Usage:
  python3 scripts/podcast/generate_thumbnail.py <video.mp4> --title "AAA Gaming Is Cooked"
  python3 scripts/podcast/generate_thumbnail.py --batch data/podcast/source/1080p/ --metadata data/podcast/metadata/
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFont

ROOT = Path(__file__).resolve().parent.parent.parent
THUMB_DIR = ROOT / "data" / "podcast" / "thumbnails"


def _find_bebas_font() -> Path:
    """Locate Bebas Neue TTF. Checks system font dirs and known install paths
    so the script works inside the Docker container (where Path.home() is /app)
    and on dev workstations (where fonts live under ~/.local/share/fonts)."""
    candidates = [
        Path("/usr/local/share/fonts/bebas-neue/BebasNeue-Regular.ttf"),
        Path("/usr/share/fonts/truetype/bebas-neue/BebasNeue-Regular.ttf"),
        Path("/usr/share/fonts/bebas-neue/BebasNeue-Regular.ttf"),
        Path.home() / ".local/share/fonts/bebas-neue/BebasNeue-Regular.ttf",
        Path("/app/.local/share/fonts/bebas-neue/BebasNeue-Regular.ttf"),
    ]
    for c in candidates:
        if c.exists():
            return c
    raise FileNotFoundError(
        "BebasNeue-Regular.ttf not found in any of: " + ", ".join(str(c) for c in candidates)
    )


def _canonical_stem(video: Path) -> str:
    """Strip the _1080p working-copy suffix so the thumbnail filename matches the
    original video stem. That way a single thumbnail file works for both the 1080p
    clip-rendering pipeline and the 4K YouTube upload."""
    s = video.stem
    return s[:-6] if s.endswith("_1080p") else s
BEBAS_FONT: Path | None = None


def _bebas() -> Path:
    global BEBAS_FONT
    if BEBAS_FONT is None:
        BEBAS_FONT = _find_bebas_font()
    return BEBAS_FONT
LOGO = ROOT / "assets" / "brand" / "logo-white.png"
W, H = 1280, 720
ORANGE = (0xff, 0x95, 0x26)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)


def _grab_frame(video: Path, t: float) -> Image.Image:
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        subprocess.check_call([
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-ss", f"{t:.2f}", "-i", str(video),
            "-vframes", "1", "-vf", f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}",
            tmp.name,
        ])
        return Image.open(tmp.name).convert("RGB")


def _ffprobe_duration(video: Path) -> float:
    out = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(video)
    ]).decode().strip()
    return float(out)


def _draw_stroked_text(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str,
                       font: ImageFont.ImageFont, fill=WHITE, stroke_fill=ORANGE, stroke_width=6,
                       shadow=True):
    if shadow:
        sx, sy = xy[0] + 4, xy[1] + 4
        draw.text((sx, sy), text, font=font, fill=(0, 0, 0))
    draw.text(xy, text, font=font, fill=fill, stroke_width=stroke_width, stroke_fill=stroke_fill)


def _wrap(text: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current: list[str] = []
    for w in words:
        trial = " ".join(current + [w])
        bbox = font.getbbox(trial)
        if bbox[2] - bbox[0] > max_width and current:
            lines.append(" ".join(current))
            current = [w]
        else:
            current.append(w)
    if current:
        lines.append(" ".join(current))
    return lines[:3]


def make_thumbnail(video: Path, title: str, out_path: Path) -> Path:
    duration = _ffprobe_duration(video)
    frame = _grab_frame(video, t=duration * 0.35)
    frame = ImageEnhance.Color(frame).enhance(1.20)
    frame = ImageEnhance.Brightness(frame).enhance(1.05)
    frame = ImageEnhance.Contrast(frame).enhance(1.10)

    # darken top-third so the title pops
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.rectangle([(0, 0), (W, int(H * 0.55))], fill=(0, 0, 0, 110))
    frame = Image.alpha_composite(frame.convert("RGBA"), overlay).convert("RGB")

    draw = ImageDraw.Draw(frame)
    font_big = ImageFont.truetype(str(_bebas()), 120)
    lines = _wrap(title.upper(), font_big, max_width=W - 120)
    y = 60
    for line in lines:
        bbox = font_big.getbbox(line)
        tx = (W - (bbox[2] - bbox[0])) // 2
        _draw_stroked_text(draw, (tx, y), line, font=font_big)
        y += (bbox[3] - bbox[1]) + 10

    # orange accent bar bottom-left
    bar_h = 14
    draw.rectangle([(0, H - bar_h), (int(W * 0.55), H)], fill=ORANGE)

    # "THE 8-BIT LEGACY PODCAST" caption bottom-left
    font_sub = ImageFont.truetype(str(_bebas()), 42)
    _draw_stroked_text(draw, (32, H - 90), "THE 8-BIT LEGACY PODCAST",
                       font=font_sub, fill=WHITE, stroke_fill=BLACK, stroke_width=3, shadow=False)

    # logo bottom-right if available
    if LOGO.exists():
        logo = Image.open(LOGO).convert("RGBA")
        lh = 120
        ratio = lh / logo.height
        lw = int(logo.width * ratio)
        logo = logo.resize((lw, lh), Image.LANCZOS)
        frame.paste(logo, (W - lw - 24, H - lh - 24), logo)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    frame.save(out_path, "JPEG", quality=92)
    print(f"[THUMB] {video.name} → {out_path.relative_to(ROOT)}")
    return out_path


def _title_for(video: Path, metadata_dir: Path | None) -> str:
    if metadata_dir:
        meta_json = metadata_dir / f"{video.stem}.json"
        if meta_json.exists():
            try:
                return json.loads(meta_json.read_text())["title"]
            except Exception:
                pass
    # fallback: derive from filename
    stem = video.stem.replace("_1080p", "")
    parts = stem.split("-", 1)
    rest = parts[1] if len(parts) > 1 else stem
    return rest.replace("-", " ").title()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("video", nargs="?")
    parser.add_argument("--title", help="Override title")
    parser.add_argument("--batch", help="Dir of videos to batch-thumbnail")
    parser.add_argument("--metadata", help="Dir of metadata JSONs (to pull titles)")
    args = parser.parse_args()

    THUMB_DIR.mkdir(parents=True, exist_ok=True)
    if args.video:
        video = Path(args.video).resolve()
        title = args.title or _title_for(video, Path(args.metadata) if args.metadata else None)
        make_thumbnail(video, title, THUMB_DIR / f"{_canonical_stem(video)}.jpg")
        return 0

    if args.batch:
        metadata_dir = Path(args.metadata) if args.metadata else None
        for v in sorted(Path(args.batch).resolve().glob("*.mp4")):
            title = args.title or _title_for(v, metadata_dir)
            make_thumbnail(v, title, THUMB_DIR / f"{_canonical_stem(v)}.jpg")
        return 0

    parser.error("pass a video path or --batch <dir>")


if __name__ == "__main__":
    sys.exit(main())
