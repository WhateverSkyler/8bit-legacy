#!/usr/bin/env python3
"""Generate a Merchant Center supplemental feed that sets custom_label_0 + custom_label_2.

Per cowork session 2026-04-29 (`docs/cowork-session-2026-04-29-mc-fix-and-flip.md`),
the Shopify Google & YouTube app exposes NO UI for mapping Shopify tag prefixes
(price_tier:over_50, category:game, etc.) to Merchant Center custom_label_X fields.
The supplemental-feed CSV approach is the only path forward.

Reads each active product's Shopify tags:
  price_tier:{under_20, 20_to_50, over_50} → custom_label_0
  category:{game, pokemon_card, console, accessory, sealed} → custom_label_2

Produces one CSV row per variant of every active product. Both variants of a
product share the same labels (price_tier is computed from min variant price by
optimize-product-feed.py — Game Only, the cheaper variant, drives both rows).

Offer ID format: `shopify_ZZ_{product_num}_{variant_num}` — Feed B
(USD_88038604834, the canonical post-4/24-reinstall feed) uses ZZ country prefix
per visual confirmation in MC during the 2026-04-29 cowork session.

Output:
  data/merchant-center-custom-labels.csv — 3 columns: id, custom_label_0, custom_label_2

Usage:
  python3 scripts/generate-custom-labels-feed.py              # generate
  python3 scripts/generate-custom-labels-feed.py --limit 100  # test with first 100 products
  python3 scripts/generate-custom-labels-feed.py --dry-run    # count only, no CSV
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import sys
import time
from collections import Counter
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_CSV = ROOT / "data" / "merchant-center-custom-labels.csv"

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / "config" / ".env")
    load_dotenv(ROOT / "dashboard" / ".env.local")
except ImportError:
    pass

SHOPIFY_STORE = os.getenv("SHOPIFY_STORE_URL", "")
SHOPIFY_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN", "")
API_VERSION = "2024-10"

DEFAULT_OFFER_PREFIX = "shopify_ZZ_"  # Feed B (USD_88038604834) — confirmed 2026-04-29 cowork

VALID_PRICE_TIERS = {"under_20", "20_to_50", "over_50"}
VALID_CATEGORIES = {"game", "pokemon_card", "console", "accessory", "sealed"}


def _gid_to_numeric(gid: str) -> str:
    m = re.search(r"/(\d+)$", gid)
    return m.group(1) if m else gid


def _graphql(query: str, variables: dict | None = None, retries: int = 6) -> dict:
    url = f"https://{SHOPIFY_STORE}/admin/api/{API_VERSION}/graphql.json"
    last_exc = None
    for attempt in range(retries):
        try:
            resp = requests.post(
                url,
                headers={
                    "X-Shopify-Access-Token": SHOPIFY_TOKEN,
                    "Content-Type": "application/json",
                },
                json={"query": query, "variables": variables or {}},
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.RequestException as e:
            last_exc = e
            wait = min(2 ** attempt, 30)
            print(f"  Network error ({e.__class__.__name__}), retrying in {wait}s...", flush=True)
            time.sleep(wait)
            continue

        errors = data.get("errors", [])
        if any(err.get("extensions", {}).get("code") == "THROTTLED" for err in errors):
            wait = 2 ** attempt
            print(f"  Throttled, waiting {wait}s...", flush=True)
            time.sleep(wait)
            continue

        if errors:
            raise RuntimeError(f"GraphQL errors: {errors}")
        return data.get("data", {})

    raise RuntimeError(f"Max retries exceeded: {last_exc}")


def _iter_active_products(limit: int | None = None) -> list[dict]:
    products: list[dict] = []
    cursor: str | None = None
    query = """
    query($cursor: String) {
      products(first: 100, after: $cursor, query: "status:active") {
        pageInfo { hasNextPage endCursor }
        edges {
          node {
            id
            tags
            variants(first: 10) {
              edges { node { id title } }
            }
          }
        }
      }
    }
    """
    while True:
        data = _graphql(query, {"cursor": cursor})
        conn = data.get("products", {})
        for edge in conn.get("edges", []):
            products.append(edge["node"])
            if limit and len(products) >= limit:
                return products
        page_info = conn.get("pageInfo", {})
        if not page_info.get("hasNextPage"):
            break
        cursor = page_info.get("endCursor")
        if len(products) % 1000 == 0:
            print(f"  Fetched {len(products)} products...", flush=True)
        time.sleep(0.3)
    return products


def _extract_label(tags: list[str], prefix: str, valid: set[str]) -> str | None:
    for t in tags:
        if t.startswith(prefix):
            value = t[len(prefix):]
            if value in valid:
                return value
    return None


def _build_rows(products: list[dict], offer_prefix: str) -> tuple[list[dict], dict]:
    rows: list[dict] = []
    skipped_no_tier = 0
    skipped_no_cat = 0
    label_counts = Counter()
    cat_counts = Counter()

    for p in products:
        tags = p.get("tags", [])
        price_tier = _extract_label(tags, "price_tier:", VALID_PRICE_TIERS)
        category = _extract_label(tags, "category:", VALID_CATEGORIES)

        if not price_tier:
            skipped_no_tier += 1
            continue
        if not category:
            skipped_no_cat += 1
            continue

        product_num = _gid_to_numeric(p["id"])
        for v in p.get("variants", {}).get("edges", []):
            variant_num = _gid_to_numeric(v["node"]["id"])
            offer_id = f"{offer_prefix}{product_num}_{variant_num}"
            rows.append({
                "id": offer_id,
                "custom_label_0": price_tier,
                "custom_label_2": category,
            })
            label_counts[price_tier] += 1
            cat_counts[category] += 1

    stats = {
        "skipped_no_tier": skipped_no_tier,
        "skipped_no_cat": skipped_no_cat,
        "label_counts": label_counts,
        "cat_counts": cat_counts,
    }
    return rows, stats


def _write_csv(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "custom_label_0", "custom_label_2"])
        writer.writeheader()
        for r in rows:
            writer.writerow(r)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, help="Process at most N products (testing)")
    parser.add_argument("--dry-run", action="store_true", help="Count only; don't write CSV")
    parser.add_argument("--output", default=str(OUTPUT_CSV))
    parser.add_argument("--prefix", default=DEFAULT_OFFER_PREFIX, help="Offer ID prefix (default: shopify_ZZ_)")
    args = parser.parse_args()

    offer_prefix = args.prefix

    if not SHOPIFY_STORE or not SHOPIFY_TOKEN:
        print("[FATAL] SHOPIFY_STORE_URL / SHOPIFY_ACCESS_TOKEN not set", file=sys.stderr)
        return 2

    t0 = time.time()
    print(f"[1/3] Fetching active products from Shopify…")
    products = _iter_active_products(limit=args.limit)
    print(f"      {len(products)} products fetched in {time.time() - t0:.1f}s")

    t1 = time.time()
    print(f"[2/3] Building supplemental feed rows (prefix='{offer_prefix}')…")
    rows, stats = _build_rows(products, offer_prefix)
    print(f"      {len(rows)} variant rows built in {time.time() - t1:.1f}s")
    print(f"      Skipped — missing price_tier tag: {stats['skipped_no_tier']}")
    print(f"      Skipped — missing category tag:   {stats['skipped_no_cat']}")
    print(f"\n      custom_label_0 distribution:")
    for k, v in stats["label_counts"].most_common():
        print(f"        {k:12} {v}")
    print(f"      custom_label_2 distribution:")
    for k, v in stats["cat_counts"].most_common():
        print(f"        {k:12} {v}")

    print("\n      Sample rows:")
    for r in rows[:3]:
        print(f"        {r['id']}  →  cl0={r['custom_label_0']}, cl2={r['custom_label_2']}")
    if len(rows) > 3:
        print(f"        ... and {len(rows) - 3} more")

    if args.dry_run:
        print(f"\n[3/3] --dry-run → skipping CSV write")
        return 0

    out_path = Path(args.output)
    _write_csv(rows, out_path)
    print(f"\n[3/3] Wrote {len(rows)} rows → {out_path.relative_to(ROOT) if out_path.is_relative_to(ROOT) else out_path}")
    print(f"\nTotal elapsed: {time.time() - t0:.1f}s")
    print(f"\nNEXT STEPS:")
    print(f"  1. Spot-check 2-3 offer IDs in MC: search for a known $50+ game, compare the offer ID")
    print(f"     in MC against the CSV row. Prefix MUST match (currently: '{offer_prefix}').")
    print(f"  2. MC → Data sources → Add supplemental data source → Upload file")
    print(f"     → Name 'Custom Labels Supplemental' → link to Feed B (USD_88038604834)")
    print(f"     → Schedule: Daily")
    print(f"  3. Wait 4-24h for MC to reprocess. Verify by clicking a $50+ game in MC and")
    print(f"     confirming custom_label_0='over_50' and custom_label_2='game' appear.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
