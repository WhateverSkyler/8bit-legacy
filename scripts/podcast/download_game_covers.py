#!/usr/bin/env python3
"""Download a hand-picked set of iconic retro game cover images to
assets/game-covers/ for use in the end-card collage.

Sources from the Libretro thumbnails project on GitHub — high-quality public
boxart for every major retro platform, no API key required. Each platform has
its own thumbnails repo and the file paths follow a consistent pattern.

  https://raw.githubusercontent.com/libretro-thumbnails/{Platform}/master/
    Named_Boxarts/{Game Name}.png

The list is hand-curated for visual impact: high-color covers, iconic IP,
spread across NES/SNES/N64/GameCube/PS1/PS2/Genesis. We pick maybe 16 so the
collage has variety + room to swap if any one looks off.

Idempotent: skips files that already exist. Run from repo root.
"""
from __future__ import annotations

import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
OUT_DIR = ROOT / "assets" / "game-covers"

LIBRETRO_BASE = "https://raw.githubusercontent.com/libretro-thumbnails"

# (platform_repo, file_name_on_libretro, local_slug)
# File names on libretro use the full "(Region)" suffix — usually USA.
COVERS: list[tuple[str, str, str]] = [
    # SNES
    ("Nintendo_-_Super_Nintendo_Entertainment_System",
     "Super Mario World (USA)",
     "super-mario-world"),
    ("Nintendo_-_Super_Nintendo_Entertainment_System",
     "Legend of Zelda, The - A Link to the Past (USA)",
     "zelda-a-link-to-the-past"),
    ("Nintendo_-_Super_Nintendo_Entertainment_System",
     "Donkey Kong Country (USA)",
     "donkey-kong-country"),
    ("Nintendo_-_Super_Nintendo_Entertainment_System",
     "Super Metroid (Japan, USA) (En,Ja)",
     "super-metroid"),
    # N64
    ("Nintendo_-_Nintendo_64",
     "Super Mario 64 (USA)",
     "super-mario-64"),
    ("Nintendo_-_Nintendo_64",
     "Legend of Zelda, The - Ocarina of Time (USA)",
     "ocarina-of-time"),
    ("Nintendo_-_Nintendo_64",
     "GoldenEye 007 (USA)",
     "goldeneye-007"),
    ("Nintendo_-_Nintendo_64",
     "Mario Kart 64 (USA)",
     "mario-kart-64"),
    # GameCube
    ("Nintendo_-_GameCube",
     "Super Smash Bros. Melee (USA)",
     "smash-bros-melee"),
    # NES
    ("Nintendo_-_Nintendo_Entertainment_System",
     "Super Mario Bros. 3 (USA)",
     "super-mario-bros-3"),
    ("Nintendo_-_Nintendo_Entertainment_System",
     "Mega Man 2 (USA)",
     "mega-man-2"),
    # Game Boy / GBA
    ("Nintendo_-_Game_Boy",
     "Pokemon - Red Version (USA, Europe)",
     "pokemon-red"),
    # Genesis
    ("Sega_-_Mega_Drive_-_Genesis",
     "Sonic the Hedgehog 2 (USA, Europe)",
     "sonic-2"),
    ("Sega_-_Mega_Drive_-_Genesis",
     "Streets of Rage 2 (USA, Europe)",
     "streets-of-rage-2"),
    # PS1
    ("Sony_-_PlayStation",
     "Final Fantasy VII (USA) (Disc 1)",
     "ff7"),
    ("Sony_-_PlayStation",
     "Crash Bandicoot (USA)",
     "crash-bandicoot"),
    # PS2
    ("Sony_-_PlayStation_2",
     "Grand Theft Auto - San Andreas (USA) (v3.00)",
     "gta-san-andreas"),
]


def _url(platform: str, name: str) -> str:
    # libretro thumbnails URL-encode the filename path component
    name_encoded = urllib.parse.quote(name, safe="")
    return f"{LIBRETRO_BASE}/{platform}/master/Named_Boxarts/{name_encoded}.png"


def _fetch(url: str, dest: Path) -> bool:
    req = urllib.request.Request(url, headers={"User-Agent": "8bit-legacy-covers/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = resp.read()
        dest.write_bytes(data)
        return True
    except urllib.error.HTTPError as exc:
        print(f"  ✗ {dest.name}: HTTP {exc.code}")
        return False
    except Exception as exc:
        print(f"  ✗ {dest.name}: {exc}")
        return False


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Downloading to {OUT_DIR.relative_to(ROOT)}/")

    ok = skipped = failed = 0
    for platform, name, slug in COVERS:
        dest = OUT_DIR / f"{slug}.png"
        if dest.exists() and dest.stat().st_size > 5000:
            skipped += 1
            continue
        url = _url(platform, name)
        if _fetch(url, dest):
            kb = dest.stat().st_size // 1024
            print(f"  ✓ {dest.name} ({kb} KB)")
            ok += 1
        else:
            failed += 1

    print()
    print(f"=== {ok} fetched, {skipped} skipped, {failed} failed ===")
    if failed:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
