#!/usr/bin/env python3
"""Generate assets/brand/end-card-9x16.png from the 8-Bit Legacy logo + brand
text. Run once to bake the asset; render_clip.py picks it up automatically
via its END_CARD path (overlay on the last 4s of every clip).

Layout (1080x1920):
  - Solid black background
  - Logo centered, top half (max 800px wide, preserved aspect)
  - Tagline below logo
  - Bottom block: handle + subscribe CTA
  - Brand orange accent bar above the bottom block
"""
from __future__ import annotations
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent.parent
LOGO_SRC = ROOT / "podcast-assets" / "8-Bit-Legacy-Logo-1-e1674598779406-1536x667.webp"
FONT_PATH = ROOT / "assets" / "fonts" / "BebasNeue-Regular.ttf"
OUT = ROOT / "assets" / "brand" / "end-card-9x16.png"

W, H = 1080, 1920
BLACK = (0, 0, 0, 255)
WHITE = (255, 255, 255, 255)
ORANGE = (255, 149, 38, 255)  # #ff9526
DIM_WHITE = (200, 200, 200, 255)


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    canvas = Image.new("RGBA", (W, H), BLACK)
    draw = ImageDraw.Draw(canvas)

    # Logo — load WebP, downscale to fit 800px wide, center horizontally,
    # place vertically around the upper third of the canvas.
    logo = Image.open(LOGO_SRC).convert("RGBA")
    target_w = 820
    scale = target_w / logo.width
    logo = logo.resize((target_w, int(logo.height * scale)), Image.LANCZOS)
    logo_x = (W - logo.width) // 2
    logo_y = 480
    canvas.paste(logo, (logo_x, logo_y), logo)

    # Tagline (small, dim white)
    tagline_font = ImageFont.truetype(str(FONT_PATH), 56)
    tagline = "RETRO. RANKED. UNFILTERED."
    bbox = draw.textbbox((0, 0), tagline, font=tagline_font)
    tag_w = bbox[2] - bbox[0]
    tag_y = logo_y + logo.height + 60
    draw.text(((W - tag_w) // 2, tag_y), tagline, font=tagline_font, fill=DIM_WHITE)

    # Brand-orange accent bar above the CTA
    bar_w = 600
    bar_y = 1380
    draw.rectangle(((W - bar_w) // 2, bar_y, (W + bar_w) // 2, bar_y + 8),
                   fill=ORANGE)

    # Subscribe CTA (large, white)
    cta_font = ImageFont.truetype(str(FONT_PATH), 96)
    cta = "FOLLOW FOR MORE"
    bbox = draw.textbbox((0, 0), cta, font=cta_font)
    cta_w = bbox[2] - bbox[0]
    cta_y = bar_y + 60
    draw.text(((W - cta_w) // 2, cta_y), cta, font=cta_font, fill=WHITE)

    # Handle (medium, brand orange) — primary social handle on TT/IG/YT
    handle_font = ImageFont.truetype(str(FONT_PATH), 80)
    handle = "@8BITLEGACYRETRO"
    bbox = draw.textbbox((0, 0), handle, font=handle_font)
    h_w = bbox[2] - bbox[0]
    h_y = cta_y + 130
    draw.text(((W - h_w) // 2, h_y), handle, font=handle_font, fill=ORANGE)

    canvas.save(OUT, "PNG", optimize=True)
    print(f"Wrote {OUT} ({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
