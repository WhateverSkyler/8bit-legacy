#!/usr/bin/env python3
"""Generate brand end-card PNG(s) for the shorts pipeline. Run once to bake
the asset(s); render_clip.py picks up assets/brand/end-card-9x16.png as the
final-3s overlay on every clip.

Usage:
  python3 scripts/podcast/build_end_card.py                  # default variant → end-card-9x16.png
  python3 scripts/podcast/build_end_card.py --variant tight  # → end-card-tight.png (preview only)
  python3 scripts/podcast/build_end_card.py --variant grid   # → end-card-grid.png
  python3 scripts/podcast/build_end_card.py --variant vignette # → end-card-vignette.png
  python3 scripts/podcast/build_end_card.py --all            # builds all variants for side-by-side review

The default variant writes end-card-9x16.png (the live asset). All other
variants write end-card-<name>.png for review — copy the chosen one over
end-card-9x16.png to swap.
"""
from __future__ import annotations
import argparse
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent.parent
LOGO_SRC = ROOT / "podcast-assets" / "8-Bit-Legacy-Logo-1-e1674598779406-1536x667.webp"
FONT_PATH = ROOT / "assets" / "fonts" / "BebasNeue-Regular.ttf"
OUT_DIR = ROOT / "assets" / "brand"

W, H = 1080, 1920
BLACK = (0, 0, 0, 255)
WHITE = (255, 255, 255, 255)
ORANGE = (255, 149, 38, 255)
DIM_WHITE = (200, 200, 200, 255)
SOFT_GRAY = (160, 160, 160, 255)


def _load_logo(target_w: int) -> Image.Image:
    logo = Image.open(LOGO_SRC).convert("RGBA")
    scale = target_w / logo.width
    return logo.resize((target_w, int(logo.height * scale)), Image.LANCZOS)


def _font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_PATH), size)


def _draw_centered(draw: ImageDraw.ImageDraw, text: str, y: int,
                   font: ImageFont.FreeTypeFont, fill: tuple) -> int:
    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    draw.text(((W - w) // 2, y), text, font=font, fill=fill)
    return bbox[3] - bbox[1]  # text height


# ── default variant ────────────────────────────────────────────────────────
def build_default() -> Image.Image:
    """Logo top-half, tagline, brand-orange divider, CTA, handle. Original
    design from the first pass. Balanced, generic, safe."""
    canvas = Image.new("RGBA", (W, H), BLACK)
    draw = ImageDraw.Draw(canvas)

    logo = _load_logo(820)
    logo_y = 480
    canvas.paste(logo, ((W - logo.width) // 2, logo_y), logo)

    _draw_centered(draw, "RETRO. RANKED. UNFILTERED.",
                   logo_y + logo.height + 60, _font(56), DIM_WHITE)

    bar_y = 1380
    bar_w = 600
    draw.rectangle(((W - bar_w) // 2, bar_y, (W + bar_w) // 2, bar_y + 8),
                   fill=ORANGE)

    _draw_centered(draw, "FOLLOW FOR MORE", bar_y + 60, _font(96), WHITE)
    _draw_centered(draw, "@8BITLEGACYRETRO", bar_y + 190, _font(80), ORANGE)
    return canvas


# ── poster variant ─────────────────────────────────────────────────────────
def build_poster() -> Image.Image:
    """Tighter, more poster-like. Bigger logo, bigger handle, less negative
    space. Reads bigger on a phone scroll."""
    canvas = Image.new("RGBA", (W, H), BLACK)
    draw = ImageDraw.Draw(canvas)

    logo = _load_logo(960)
    logo_y = 380
    canvas.paste(logo, ((W - logo.width) // 2, logo_y), logo)

    _draw_centered(draw, "RETRO GAMING. UNFILTERED OPINIONS.",
                   logo_y + logo.height + 50, _font(48), SOFT_GRAY)

    # Big brand-orange CTA section
    cta_block_y = 1240
    block_h = 360
    # Subtle orange tint behind the CTA
    overlay = Image.new("RGBA", (W, block_h), (255, 149, 38, 18))
    canvas.alpha_composite(overlay, (0, cta_block_y))

    # Bar above + below for the band feel
    draw.rectangle((0, cta_block_y, W, cta_block_y + 4), fill=ORANGE)
    draw.rectangle((0, cta_block_y + block_h - 4, W, cta_block_y + block_h),
                   fill=ORANGE)

    _draw_centered(draw, "FOLLOW", cta_block_y + 40, _font(140), WHITE)
    _draw_centered(draw, "@8BITLEGACYRETRO", cta_block_y + 220, _font(88), ORANGE)
    return canvas


# ── grid variant ───────────────────────────────────────────────────────────
def build_grid() -> Image.Image:
    """Lists multiple platform handles + the audio podcast pitch. Useful
    once Spotify/Apple audio is live so we can drive both audiences."""
    canvas = Image.new("RGBA", (W, H), BLACK)
    draw = ImageDraw.Draw(canvas)

    logo = _load_logo(780)
    logo_y = 280
    canvas.paste(logo, ((W - logo.width) // 2, logo_y), logo)

    _draw_centered(draw, "THE 8-BIT LEGACY PODCAST",
                   logo_y + logo.height + 40, _font(60), DIM_WHITE)

    # Brand-orange divider
    bar_y = 1060
    draw.rectangle((140, bar_y, W - 140, bar_y + 6), fill=ORANGE)

    # Platform list, 3 rows
    follow_label_font = _font(56)
    handle_font = _font(72)
    rows = [
        ("TIKTOK / IG / FB", "@8BITLEGACYRETRO"),
        ("YOUTUBE", "@8BITLEGACYRETRO"),
        ("SPOTIFY / APPLE", "THE 8-BIT LEGACY PODCAST"),
    ]
    row_y = bar_y + 80
    for label, handle in rows:
        _draw_centered(draw, label, row_y, follow_label_font, SOFT_GRAY)
        _draw_centered(draw, handle, row_y + 60, handle_font, ORANGE)
        row_y += 180

    return canvas


# ── vignette variant ───────────────────────────────────────────────────────
def build_vignette() -> Image.Image:
    """Deep-black background with a subtle vignette and an extra-large logo.
    More cinematic, less utilitarian. Best when the underlying clip is busy
    and you want a hard reset before the CTA."""
    canvas = Image.new("RGBA", (W, H), (8, 8, 12, 255))

    # Vignette: very subtle radial darkening at the edges
    vignette = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    vd = ImageDraw.Draw(vignette)
    cx, cy = W // 2, H // 2
    max_r = max(W, H)
    for r in range(max_r, max_r // 2, -8):
        alpha = int(60 * (r - max_r // 2) / (max_r // 2))
        vd.ellipse((cx - r, cy - r, cx + r, cy + r), outline=(0, 0, 0, alpha))
    canvas = Image.alpha_composite(canvas, vignette.filter(ImageFilter.GaussianBlur(radius=80)))
    draw = ImageDraw.Draw(canvas)

    logo = _load_logo(980)
    logo_y = 440
    canvas.paste(logo, ((W - logo.width) // 2, logo_y), logo)

    _draw_centered(draw, "@8BITLEGACYRETRO",
                   1400, _font(96), ORANGE)
    _draw_centered(draw, "FOLLOW FOR MORE",
                   1530, _font(72), WHITE)
    return canvas


VARIANTS = {
    "default": build_default,
    "poster": build_poster,
    "grid": build_grid,
    "vignette": build_vignette,
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant", choices=list(VARIANTS), default="default",
                        help="Which design to build")
    parser.add_argument("--all", action="store_true",
                        help="Build all variants (for side-by-side review)")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    targets = list(VARIANTS) if args.all else [args.variant]

    for name in targets:
        canvas = VARIANTS[name]()
        # The "default" variant is the live asset path render_clip reads.
        # All other variants get a -<name> suffix so they don't clobber it.
        if name == "default":
            out = OUT_DIR / "end-card-9x16.png"
        else:
            out = OUT_DIR / f"end-card-{name}.png"
        canvas.save(out, "PNG", optimize=True)
        print(f"  wrote {out.relative_to(ROOT)} ({out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
