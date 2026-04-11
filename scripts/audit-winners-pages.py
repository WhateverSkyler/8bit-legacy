#!/usr/bin/env python3
"""
Audit the Google Ads Winners list against live Shopify data.

For each product in docs/ads-winners-curation-list.md:
  - Find the Shopify product by title search
  - Check active status
  - Check each variant's price + inventory
  - Check product has an image
  - Check tags include category:game (not accessory/console)
  - Output a markdown report and JSON data file

Usage:
    python3 scripts/audit-winners-pages.py
    python3 scripts/audit-winners-pages.py --save   # write output file
"""

import requests
import json
import time
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / "dashboard" / ".env.local")
load_dotenv(Path(__file__).parent.parent / "config" / ".env")

SHOP_URL = os.getenv("SHOPIFY_STORE_URL", "")
ACCESS_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN", "")
API_VERSION = "2024-10"

if not SHOP_URL or not ACCESS_TOKEN:
    print("ERROR: Set SHOPIFY_STORE_URL and SHOPIFY_ACCESS_TOKEN")
    sys.exit(1)

HEADERS = {
    "X-Shopify-Access-Token": ACCESS_TOKEN,
    "Content-Type": "application/json"
}
BASE_URL = f"https://{SHOP_URL}/admin/api/{API_VERSION}"
GQL_URL = f"https://{SHOP_URL}/admin/api/{API_VERSION}/graphql.json"

WINNERS = [
    # (title search query, console/variant hint, variant hint)
    ("Galerians", "PS1", "Game Only"),
    ("Galerians", "PS1", "Complete"),
    ("Galerians Ash", "PS2", None),
    ("Mystical Ninja Starring Goemon", "N64", None),
    ("Legend of the Mystical Ninja", "SNES", None),
    ("Phantasy Star Online", "GameCube", None),
    ("Phantasy Star Online Plus", "GameCube", None),
    ("Phantasy Star Online III", "GameCube", None),
    ("Aidyn Chronicles", "N64", None),
    ("Space Station Silicon Valley", "N64", None),
    ("Metal Gear Solid", "PS1", None),
    ("Silent Hill", "PS1", None),
    ("Silent Hill 2", "PS2", None),
    ("Silent Hill 3", "PS2", None),
    ("Fatal Frame", "PS2", None),
    ("Fatal Frame 2", "PS2", None),
    ("Rule of Rose", "PS2", None),
    ("Haunting Ground", "PS2", None),
    ("Klonoa Door to Phantomile", "PS1", None),
    ("Skies of Arcadia Legends", "GameCube", None),
    ("Custom Robo", "GameCube", None),
    ("Geist", "GameCube", None),
    ("Baten Kaitos Origins", "GameCube", None),
    ("Eternal Darkness", "GameCube", None),
]


CONSOLE_VARIANTS = {
    "PS1": ["ps1", "playstation"],
    "PS2": ["ps2", "playstation 2"],
    "N64": ["nintendo 64", "n64"],
    "SNES": ["snes", "super nintendo"],
    "GameCube": ["gamecube", "gcn"],
    "NES": ["nes", "nintendo entertainment"],
    "Genesis": ["genesis", "sega genesis"],
    "Dreamcast": ["dreamcast"],
    "Saturn": ["saturn", "sega saturn"],
    "GBA": ["gba", "game boy advance"],
}


def console_matches(hint, title):
    if not hint:
        return True
    title_lo = title.lower()
    for token in CONSOLE_VARIANTS.get(hint, [hint.lower()]):
        if token in title_lo:
            return True
    return False


ROMAN = {"ii": "2", "iii": "3", "iv": "4", "v": "5", "vi": "6", "vii": "7", "viii": "8", "ix": "9", "x": "10"}


def normalize_title(t):
    """Lowercase and convert roman numerals to digits for token comparison."""
    words = t.lower().replace("-", " ").replace(":", " ").split()
    return " ".join(ROMAN.get(w, w) for w in words)


def has_sequel_number(s):
    """Return the sequel digit in a title if present (e.g. 'silent hill 2' → '2').
    Skip numbers that follow 'episode' or 'part' — those are chapter markers, not sequels."""
    import re
    # Remove "episode N" / "part N" patterns first
    cleaned = re.sub(r"\b(episode|part|chapter|disc)\s+\d+\b", "", s)
    # Also skip "& N" (e.g. "Episode I & II" becomes "1 2" normalized; the "& 2" is a combo, not sequel)
    cleaned = re.sub(r"\&\s*\d+", "", cleaned)
    m = re.search(r"\b([2-9]|1[0-9])\b", cleaned)
    return m.group(1) if m else None


def score_match(node, query_title, console_hint, variant_hint):
    """Higher score = better match."""
    score = 0
    node_norm = normalize_title(node["title"])
    query_norm = normalize_title(query_title)

    # Hard gate: base game name must appear (first 2 words of query)
    first_words = query_norm.split()[:2]
    if not all(w in node_norm for w in first_words):
        return -999

    # Sequel number must match exactly
    query_seq = has_sequel_number(query_norm)
    # Look for sequel number in the part of node_norm that's NOT from the console suffix
    node_base = node_norm.split(" ps")[0].split(" nintendo")[0].split(" snes")[0].split(" gamecube")[0].split(" playstation")[0]
    node_seq = has_sequel_number(node_base)
    if query_seq and node_seq != query_seq:
        return -999
    if not query_seq and node_seq:
        return -999  # query is "Silent Hill", node is "Silent Hill 2" → reject

    # Exact phrase bonus
    if query_norm in node_norm:
        score += 100

    # Every query word present
    for w in query_norm.split():
        if w in node_norm:
            score += 5

    # Console match bonus
    if console_hint and console_matches(console_hint, node["title"]):
        score += 100
    elif console_hint:
        score -= 100

    # Shorter title = better (tighter match)
    score -= len(node["title"]) * 0.1

    return score


def gql_search_product(query_title, console_hint):
    """Use GraphQL products query with title filter."""
    # Shopify search syntax: plain words are AND'd, wildcards work without quotes.
    # title:galerians matches "Galerians - PS1 Game".
    words = query_title.strip().split()
    # Roman numerals like "II" don't play nice with wildcards; keep them plain.
    parts = [f"title:{w}*" if len(w) > 2 else f"title:{w}" for w in words]
    q = " ".join(parts)

    gql = """
    query($q: String!) {
      products(first: 25, query: $q) {
        edges {
          node {
            id
            title
            handle
            status
            productType
            tags
            featuredImage { url }
            images(first: 1) { edges { node { url } } }
            variants(first: 10) {
              edges {
                node {
                  id
                  title
                  price
                  sku
                  inventoryQuantity
                  availableForSale
                }
              }
            }
          }
        }
      }
    }
    """
    resp = requests.post(
        GQL_URL,
        headers=HEADERS,
        json={"query": gql, "variables": {"q": q}},
    )
    if resp.status_code != 200:
        return None, f"HTTP {resp.status_code}: {resp.text[:200]}"
    data = resp.json()
    if "errors" in data:
        return None, str(data["errors"])[:300]
    edges = data.get("data", {}).get("products", {}).get("edges", [])
    return [e["node"] for e in edges], None


def search_best_match(query_title, console_hint, variant_hint):
    """Search by title then pick the best-scoring match."""
    nodes, err = gql_search_product(query_title, console_hint)
    if err:
        return None, err
    if not nodes:
        # Fallback: try the first 1-2 words only (for cases like "Fatal Frame II")
        words = query_title.split()
        if len(words) > 1:
            short = " ".join(words[:2])
            nodes, err = gql_search_product(short, console_hint)
            if err or not nodes:
                return None, "no results"
        else:
            return None, "no results"

    # Score and pick the best
    scored = [(score_match(n, query_title, console_hint, variant_hint), n) for n in nodes]
    scored.sort(key=lambda x: -x[0])
    best_score, best = scored[0]
    if best_score < 0:
        # All candidates are garbage
        return None, f"no confident match (best: {best['title']}, score={best_score:.0f})"
    return best, None


def audit_product(product, variant_hint):
    if not product:
        return {"status": "MISSING"}
    title = product["title"]
    status = product["status"]
    has_image = bool(product.get("featuredImage") or product.get("images", {}).get("edges"))
    tags = product.get("tags", [])
    tags_lo = [t.lower() for t in tags]
    # Category tag is the authoritative category signal. `console:ps1` is a console-family label, not a category.
    has_game_tag = "category:game" in tags_lo
    is_accessory = "category:accessory" in tags_lo
    is_console = "category:console" in tags_lo

    variants = [v["node"] for v in product["variants"]["edges"]]
    # Pick variant matching hint
    target_variant = None
    if variant_hint:
        for v in variants:
            if variant_hint.lower() in v["title"].lower():
                target_variant = v
                break
    if not target_variant:
        target_variant = variants[0] if variants else None

    all_variant_data = []
    for v in variants:
        all_variant_data.append({
            "title": v["title"],
            "price": v["price"],
            "sku": v.get("sku") or "",
            "inventory": v.get("inventoryQuantity"),
            "available": v.get("availableForSale"),
        })

    return {
        "status": status,
        "title": title,
        "handle": product["handle"],
        "has_image": has_image,
        "tags": tags[:8],
        "has_game_tag": has_game_tag,
        "is_accessory": is_accessory,
        "is_console": is_console,
        "target_variant": {
            "title": target_variant["title"] if target_variant else None,
            "price": target_variant["price"] if target_variant else None,
            "inventory": target_variant.get("inventoryQuantity") if target_variant else None,
            "available": target_variant.get("availableForSale") if target_variant else None,
        } if target_variant else None,
        "all_variants": all_variant_data,
    }


def main():
    save = "--save" in sys.argv
    results = []
    print(f"Auditing {len(WINNERS)} Winners products against live Shopify...\n")

    for i, (title, console, variant_hint) in enumerate(WINNERS, 1):
        print(f"[{i}/{len(WINNERS)}] {title} ({console}) ...", end=" ", flush=True)
        try:
            product, err = search_best_match(title, console, variant_hint)
            if err:
                print(f"ERROR: {err}")
                results.append({
                    "query": title, "console": console, "variant_hint": variant_hint,
                    "error": err,
                })
                continue
            audit = audit_product(product, variant_hint)
            audit["query"] = title
            audit["console_hint"] = console
            audit["variant_hint"] = variant_hint
            results.append(audit)

            if audit["status"] == "MISSING":
                print("NOT FOUND")
            else:
                tv = audit.get("target_variant") or {}
                flag = "OK" if (audit["status"] == "ACTIVE" and audit["has_image"] and tv.get("available")) else "FLAG"
                print(f"{flag} — {audit['title']} / {tv.get('title')} / ${tv.get('price')} / qty={tv.get('inventory')}")
        except Exception as e:
            print(f"EXC: {e}")
            results.append({"query": title, "console": console, "error": str(e)})
        time.sleep(0.6)

    # Write report
    md_lines = [
        "# Winners List Audit — Live Shopify Verification",
        f"\nRun date: 2026-04-11",
        f"Source list: `docs/ads-winners-curation-list.md`",
        "\n## Results\n",
        "| # | Query | Console | Status | Variant | Price | Inv | Img | Tags OK | Notes |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]

    ok_count = 0
    flag_count = 0
    missing_count = 0

    for i, r in enumerate(results, 1):
        if r.get("error") or r.get("status") == "MISSING":
            md_lines.append(
                f"| {i} | {r['query']} | {r.get('console', r.get('console_hint'))} | MISSING | — | — | — | — | — | {r.get('error', 'not found')} |"
            )
            missing_count += 1
            continue
        tv = r.get("target_variant") or {}
        notes = []
        status_ok = r["status"] == "ACTIVE"
        img_ok = r["has_image"]
        avail_ok = tv.get("available")
        tags_ok = r["has_game_tag"] and not r["is_accessory"] and not r["is_console"]
        if not status_ok: notes.append(f"status={r['status']}")
        if not img_ok: notes.append("no image")
        if not avail_ok: notes.append("unavailable")
        if r["is_accessory"]: notes.append("accessory tag")
        if r["is_console"]: notes.append("console tag")

        flag = "OK" if (status_ok and img_ok and avail_ok and tags_ok) else "FLAG"
        if flag == "OK":
            ok_count += 1
        else:
            flag_count += 1

        md_lines.append(
            f"| {i} | {r['query']} | {r.get('console_hint')} | {flag} | {tv.get('title', '')} | ${tv.get('price', '')} | {tv.get('inventory', '')} | {'Y' if img_ok else 'N'} | {'Y' if tags_ok else 'N'} | {'; '.join(notes) or '—'} |"
        )

    md_lines.insert(3, f"\n**Summary:** {ok_count} OK, {flag_count} flagged, {missing_count} missing (of {len(results)})\n")

    # Append per-product detail
    md_lines.append("\n## Detail\n")
    for i, r in enumerate(results, 1):
        md_lines.append(f"\n### {i}. {r['query']} ({r.get('console_hint')})")
        if r.get("error") or r.get("status") == "MISSING":
            md_lines.append(f"- NOT FOUND ({r.get('error', 'no results')})")
            continue
        md_lines.append(f"- Title: {r['title']}")
        md_lines.append(f"- Handle: `{r['handle']}`")
        md_lines.append(f"- Status: {r['status']}")
        md_lines.append(f"- Image: {'yes' if r['has_image'] else 'NO'}")
        md_lines.append(f"- Tags: {', '.join(r['tags'][:6])}")
        md_lines.append("- Variants:")
        for v in r.get("all_variants", []):
            md_lines.append(f"  - {v['title']}: ${v['price']} (inv={v['inventory']}, avail={v['available']}, sku={v['sku']})")

    report = "\n".join(md_lines)
    print("\n" + "=" * 60)
    print(f"Summary: {ok_count} OK, {flag_count} flagged, {missing_count} missing (of {len(results)})")
    print("=" * 60)

    if save:
        out_md = Path(__file__).parent.parent / "docs" / "ads-winners-audit-2026-04-11.md"
        out_json = Path(__file__).parent.parent / "data" / "ads-winners-audit-2026-04-11.json"
        out_md.write_text(report)
        out_json.parent.mkdir(exist_ok=True)
        out_json.write_text(json.dumps(results, indent=2))
        print(f"Report: {out_md}")
        print(f"Data:   {out_json}")
    else:
        print("\n(run with --save to write reports to disk)")
        print(report[:3000])


if __name__ == "__main__":
    main()
