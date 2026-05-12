#!/usr/bin/env python3
"""Generate brand end-card PNG for the shorts pipeline. Run once to bake the
asset; render_clip.py picks up assets/brand/end-card-9x16.png as the final-3s
overlay on every clip.

Round 3 (2026-05-12): redesigned end-card focuses on the STORE, not the
socials. Layout: logo top, "THE 8-BIT LEGACY STORE" tagline, tilted collage
of iconic game covers in the middle, brand-orange accent bar, "VISIT THE
STORE" CTA, 8BITLEGACY.COM URL in brand orange. Two variants — dark
(`#000000` background) and light (`#fafafa` off-white).

Cover art is sourced from assets/game-covers/ — populated once by
scripts/podcast/download_game_covers.py (pulls public Libretro thumbnails).

Usage:
  python3 scripts/podcast/build_end_card.py                       # dark variant → end-card-9x16.png
  python3 scripts/podcast/build_end_card.py --variant light       # → end-card-light.png (preview)
  python3 scripts/podcast/build_end_card.py --variant dark        # → end-card-dark.png (preview)
  python3 scripts/podcast/build_end_card.py --all                 # both variants for comparison
  python3 scripts/podcast/build_end_card.py --variant dark --as-live  # promote dark to end-card-9x16.png

`--as-live` writes the chosen variant to end-card-9x16.png (the path
render_clip reads). Without it, variants get a -<name> suffix and the live
asset is untouched.
"""
from __future__ import annotations

import argparse
import random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent.parent
LOGO_SRC = ROOT / "podcast-assets" / "8-Bit-Legacy-Logo-1-e1674598779406-1536x667.webp"
FONT_PATH = ROOT / "assets" / "fonts" / "BebasNeue-Regular.ttf"
COVERS_DIR = ROOT / "assets" / "game-covers"
OUT_DIR = ROOT / "assets" / "brand"

W, H = 1080, 1920
ORANGE = (255, 149, 38, 255)


def _font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_PATH), size)


def _draw_centered(draw: ImageDraw.ImageDraw, text: str, y: int,
                   font: ImageFont.FreeTypeFont, fill: tuple) -> tuple[int, int]:
    """Draw text centered horizontally at y. Returns (text_width, text_height)."""
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((W - tw) // 2, y), text, font=font, fill=fill)
    return tw, th


def _load_logo(target_w: int, *, light_bg: bool) -> Image.Image:
    """Load the brand logo at target width. For light background, we keep
    the orange logo color (it's brand-correct on both backgrounds)."""
    logo = Image.open(LOGO_SRC).convert("RGBA")
    scale = target_w / logo.width
    return logo.resize((target_w, int(logo.height * scale)), Image.LANCZOS)


def _tilted_cover(cover_path: Path, target_h: int, angle: float,
                  shadow_color: tuple) -> Image.Image:
    """Load a cover, scale to target height (preserving aspect), drop-shadow,
    then rotate by `angle` degrees. Returns RGBA Image with transparent
    margins. Shadow color is parameterized so dark/light variants can use
    appropriate contrast (black shadow on light bg, near-black on dark)."""
    cover = Image.open(cover_path).convert("RGBA")
    aspect = cover.width / cover.height
    target_w = int(target_h * aspect)
    cover = cover.resize((target_w, target_h), Image.LANCZOS)

    # Pad for shadow + rotation slack so corners don't get clipped
    pad = 60
    canvas = Image.new("RGBA", (target_w + pad * 2, target_h + pad * 2), (0, 0, 0, 0))

    # Drop shadow — blur a black silhouette of the cover, offset down
    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(shadow)
    sdraw.rectangle((pad + 6, pad + 8, pad + target_w + 6, pad + target_h + 8),
                    fill=shadow_color)
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=14))
    canvas = Image.alpha_composite(canvas, shadow)

    # Cover on top
    canvas.paste(cover, (pad, pad), cover)

    # Rotate around center
    return canvas.rotate(angle, resample=Image.BICUBIC, expand=True)


def _paste_cover_collage(canvas: Image.Image, covers: list[Path], *,
                         center_y: int, light_bg: bool) -> None:
    """Tile 8 covers in 2 rows × 4 cols centered at center_y. Each cover
    tilted ±3° randomly. Slight horizontal overlap so they read as a fanned
    stack rather than a strict grid.

    Picks 8 covers from `covers` (round-robin if fewer than 8 are available,
    though we expect 12+). Order randomized so successive renders feel fresh
    without re-running the downloader."""
    if not covers:
        return

    # Deterministic shuffle so rebuilds produce the same end-card image.
    # If you want fresh variety, change the seed or pass a different one.
    rng = random.Random(202605120)
    picks = list(covers)
    rng.shuffle(picks)
    # Cycle if we somehow have fewer than 8 covers
    while len(picks) < 8:
        picks.extend(picks)
    picks = picks[:8]

    cover_h = 230
    col_step = 230
    row_step = 320
    total_w = col_step * 3
    start_x = (W - total_w) // 2 - 130  # tweak for visual centering with rotation
    start_y_row0 = center_y - row_step // 2 - cover_h // 2

    shadow_color = (0, 0, 0, 130) if light_bg else (0, 0, 0, 200)

    for idx, cover_path in enumerate(picks):
        row = idx // 4
        col = idx % 4
        # Alternate tilt direction so the stack has visual rhythm
        angle = (-1.0 if (row + col) % 2 == 0 else 1.0) * (2.0 + rng.uniform(-0.5, 0.5))
        tilted = _tilted_cover(cover_path, cover_h, angle, shadow_color)
        cx = start_x + col * col_step + tilted.width // 2
        cy = start_y_row0 + row * row_step + tilted.height // 2
        # Paste centered on (cx, cy)
        paste_x = cx - tilted.width // 2
        paste_y = cy - tilted.height // 2
        canvas.alpha_composite(tilted, (paste_x, paste_y))


def _build_variant(*, light_bg: bool) -> Image.Image:
    """Build the store end-card. Light-bg = off-white background w/ black text.
    Dark-bg = black background w/ white text. Brand orange + logo are shared."""
    bg = (250, 250, 250, 255) if light_bg else (0, 0, 0, 255)
    text_color = (15, 15, 15, 255) if light_bg else (255, 255, 255, 255)
    tagline_color = (110, 110, 110, 255) if light_bg else (180, 180, 180, 255)
    url_color = ORANGE  # brand orange on both
    accent_color = ORANGE

    canvas = Image.new("RGBA", (W, H), bg)
    draw = ImageDraw.Draw(canvas)

    # Logo — top of canvas, ~720px wide for presence
    logo = _load_logo(720, light_bg=light_bg)
    logo_y = 130
    canvas.paste(logo, ((W - logo.width) // 2, logo_y), logo)

    # Tagline below logo
    tagline_y = logo_y + logo.height + 30
    _draw_centered(draw, "THE 8-BIT LEGACY STORE", tagline_y, _font(52), tagline_color)

    # Cover collage — center of canvas
    covers = sorted(p for p in COVERS_DIR.glob("*.png") if p.stat().st_size > 5000)
    _paste_cover_collage(canvas, covers, center_y=1080, light_bg=light_bg)
    # Re-acquire draw after alpha_composite operations (PIL caches draw on
    # the original canvas object — fine here since we didn't replace canvas)

    # Accent bar — separates collage from CTA block
    bar_y = 1430
    bar_w = 700
    draw.rectangle(((W - bar_w) // 2, bar_y, (W + bar_w) // 2, bar_y + 6),
                   fill=accent_color)

    # CTA
    _draw_centered(draw, "VISIT THE STORE", bar_y + 50, _font(110), text_color)

    # URL — brand orange, larger for emphasis
    _draw_centered(draw, "8BITLEGACY.COM", bar_y + 220, _font(108), url_color)

    return canvas


VARIANTS = {
    "dark": lambda: _build_variant(light_bg=False),
    "light": lambda: _build_variant(light_bg=True),
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant", choices=list(VARIANTS), default="dark",
                        help="Background variant")
    parser.add_argument("--all", action="store_true",
                        help="Build both variants for comparison")
    parser.add_argument("--as-live", action="store_true",
                        help="Promote chosen variant to end-card-9x16.png "
                             "(the path render_clip.py reads). Without this "
                             "flag, output goes to end-card-<variant>.png.")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    targets = list(VARIANTS) if args.all else [args.variant]
    for name in targets:
        canvas = VARIANTS[name]()
        if args.as_live and not args.all:
            out = OUT_DIR / "end-card-9x16.png"
        else:
            out = OUT_DIR / f"end-card-{name}.png"
        canvas.save(out, "PNG", optimize=True)
        print(f"  wrote {out.relative_to(ROOT)} ({out.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
