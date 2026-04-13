#!/usr/bin/env python3
"""
Diagnose why the search-price-refresh.py NO_MATCH set fails on PriceCharting.

For a small random sample of NO_MATCH titles, try 5 search variants and
report how many now find a match. If the match rate jumps materially,
rolling the best-performing variants into the main refresh script is
worth the effort. If no variant helps, these titles genuinely aren't on
PriceCharting and the gap has to be accepted.
"""
from __future__ import annotations

import csv
import random
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup

CSV = Path(__file__).parent.parent / "data" / "logs" / "search-refresh-20260413_104335.csv"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "text/html",
}

SAMPLE_SIZE = 25
DELAY = 1.5


def strip_console_suffix(title: str) -> str:
    return re.sub(
        r"\s*[-–]\s*(NES|SNES|N64|Nintendo|Gameboy|Game Boy|Genesis|PS[123P]|"
        r"Gamecube|Dreamcast|Saturn|GBA|Playstation|Xbox|Wii|Sega|Atari|"
        r"TurboGrafx|GBC).*$",
        "", title, flags=re.IGNORECASE
    ).strip()


def roman_swap(text: str) -> str:
    """Swap arabic ↔ roman numerals both ways."""
    arabic_to_roman = {" 2": " II", " 3": " III", " 4": " IV",
                       " 5": " V", " 6": " VI", " 7": " VII", " 8": " VIII"}
    roman_to_arabic = {v: k for k, v in arabic_to_roman.items()}
    for a, r in arabic_to_roman.items():
        if a in text:
            return text.replace(a, r, 1)
    for r, a in roman_to_arabic.items():
        if r in text:
            return text.replace(r, a, 1)
    return text


def query_variants(title: str):
    """Yield labeled query strings to try, in order of best-guess efficacy."""
    core = strip_console_suffix(title)
    yield ("v1_baseline", core)

    # Strip subtitle after colon
    if ":" in core:
        yield ("v2_pre_colon", core.split(":", 1)[0].strip())

    # Strip subtitle after " - " (hyphen separator used in some titles)
    if " - " in core:
        yield ("v3_pre_hyphen", core.split(" - ", 1)[0].strip())

    # Drop "The " prefix
    if core.lower().startswith("the "):
        yield ("v4_drop_the", core[4:])

    # Roman ↔ arabic numeral swap
    swap = roman_swap(core)
    if swap != core:
        yield ("v5_roman_swap", swap)

    # Normalize common abbreviations
    for old, new in [("&", "and"), (" vs ", " vs. "), (" vs. ", " vs ")]:
        if old in core.lower():
            variant = core.replace(old, new, 1)
            yield (f"v6_norm_{old.strip().replace(' ','_')}", variant)
            break

    # First 3 meaningful words
    words = [w for w in core.split() if len(w) > 1 and w.isalnum()]
    if len(words) > 3:
        yield ("v7_first3words", " ".join(words[:3]))


def search(query: str) -> bool:
    """Return True if PriceCharting search returned a games_table result."""
    url = f"https://www.pricecharting.com/search-products?q={quote_plus(query)}&type=videogames"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
    except Exception:
        return False
    soup = BeautifulSoup(r.text, "html.parser")
    t = soup.find("table", {"id": "games_table"})
    if not t:
        return False
    tbody = t.find("tbody")
    if not tbody:
        return False
    rows = tbody.find_all("tr")
    return len(rows) > 0


def main():
    # Load NO_MATCH titles from the 2026-04-13 run
    no_match = []
    with open(CSV) as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            if row and row[-1] == "NO_MATCH":
                no_match.append({"title": row[0], "console": row[1]})

    print(f"Total NO_MATCH in refresh run: {len(no_match)}")
    random.seed(20260413)
    sample = random.sample(no_match, min(SAMPLE_SIZE, len(no_match)))
    print(f"Diagnosing {len(sample)} random samples with 7 query variants each\n")

    stats = {}   # variant_label -> matches, attempts
    new_hits = 0 # products that got ANY match via a variant (baseline was NO_MATCH by definition)

    for i, item in enumerate(sample, 1):
        title = item["title"]
        console = item["console"]
        print(f"[{i}/{len(sample)}] {title[:60]:<60} ({console})")

        hit_any = False
        for label, core_query in query_variants(title):
            q = f"{core_query} {console}"
            ok = search(q)
            stats.setdefault(label, [0, 0])
            stats[label][1] += 1
            if ok:
                stats[label][0] += 1
                print(f"    ✓ {label:<20} → hit  (query: {q!r})")
                if not hit_any:
                    new_hits += 1
                    hit_any = True
                break
            else:
                pass
            time.sleep(DELAY)

        if not hit_any:
            print(f"    ✗ all variants failed")

    print()
    print("=" * 60)
    print(f"Products saved by ANY retry: {new_hits}/{len(sample)}  ({100*new_hits/len(sample):.1f}%)")
    print("By variant (count successes / total tried):")
    for label, (ok, tot) in sorted(stats.items()):
        print(f"  {label:<24} {ok:>3} / {tot:<3} ({100*ok/tot:.0f}%)")


if __name__ == "__main__":
    main()
