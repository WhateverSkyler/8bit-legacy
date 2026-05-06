#!/usr/bin/env python3
"""Generate a Merchant Center supplemental feed that excludes CIB variants from Shopping ads.

Per user direction 2026-04-20, the Google Ads campaign advertises ONLY the Game Only
variant of each product — lower price, more competitive vs DKOldies. CIB variants stay
in the FREE Listings feed (organic discovery is still valuable) but are blocked from
paid Shopping ads via supplemental feed with `excluded_destination=Shopping_ads`.

Shopify's Google & YouTube app emits one Merchant Center offer per variant. Offer IDs
follow the convention: `shopify_ZZ_{product_numeric_id}_{variant_numeric_id}`
(prefix changed from `shopify_US_` to `shopify_ZZ_` after Feed B was reinstalled
2026-04-24 — see reference_mc_feed_offer_ids.md). The script enumerates all
multi-variant games, identifies CIB variants by title, and outputs a CSV.

Output:
  data/merchant-center-cib-exclusion.csv — 2 columns: id, excluded_destination

Usage:
  python3 scripts/generate-cib-exclusion-feed.py              # generate
  python3 scripts/generate-cib-exclusion-feed.py --limit 100  # test with first 100 products
  python3 scripts/generate-cib-exclusion-feed.py --dry-run    # count only, no CSV
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_CSV = ROOT / "data" / "merchant-center-cib-exclusion.csv"

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / "config" / ".env")
except ImportError:
    pass

SHOPIFY_STORE = os.getenv("SHOPIFY_STORE_URL", "")
SHOPIFY_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN", "")
API_VERSION = "2024-10"
PAGE_SIZE = 100

CIB_MARKERS = ("cib", "complete in box", "complete (cib)", "complete")


def _gid_to_numeric(gid: str) -> str:
    """Convert 'gid://shopify/Product/12345' → '12345' or similar for variants."""
    m = re.search(r"/(\d+)$", gid)
    return m.group(1) if m else gid


def _is_cib_variant(title: str) -> bool:
    title_lower = (title or "").lower().strip()
    # "Game Only" = NOT CIB even though it ends with "Only"
    if "game only" in title_lower or "loose" in title_lower:
        return False
    return any(marker in title_lower for marker in CIB_MARKERS)


def _graphql(query: str, variables: dict | None = None) -> dict:
    url = f"https://{SHOPIFY_STORE}/admin/api/{API_VERSION}/graphql.json"
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
    if "errors" in data:
        raise RuntimeError(f"GraphQL errors: {data['errors']}")
    return data.get("data", {})


def _iter_game_products(limit: int | None = None) -> list[dict]:
    """Paginate through all active games with variant data."""
    products: list[dict] = []
    cursor: str | None = None
    query = """
    query($cursor: String) {
      products(
        first: 100,
        after: $cursor,
        query: "tag:'category:game' status:active"
      ) {
        pageInfo { hasNextPage endCursor }
        edges {
          node {
            id
            title
            handle
            variants(first: 10) {
              edges { node { id title sku price } }
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
        time.sleep(0.3)  # Shopify rate-limit courtesy
    return products


def _collect_cib_item_ids(products: list[dict]) -> list[dict]:
    """For each multi-variant product, identify CIB variants and build MC offer ids."""
    out: list[dict] = []
    for p in products:
        variants = [e["node"] for e in p.get("variants", {}).get("edges", [])]
        if len(variants) < 2:
            continue  # Single-variant products don't have a CIB issue
        product_num = _gid_to_numeric(p["id"])
        for v in variants:
            if _is_cib_variant(v.get("title", "")):
                variant_num = _gid_to_numeric(v["id"])
                offer_id = f"shopify_ZZ_{product_num}_{variant_num}"
                out.append({
                    "id": offer_id,
                    "excluded_destination": "Shopping_ads",
                    # Debug fields — NOT exported to CSV, useful for auditing
                    "_handle": p.get("handle"),
                    "_variant_title": v.get("title"),
                    "_price": v.get("price"),
                })
    return out


def _write_csv(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "excluded_destination"])
        writer.writeheader()
        for r in rows:
            writer.writerow({"id": r["id"], "excluded_destination": r["excluded_destination"]})


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, help="Process at most N products (testing)")
    parser.add_argument("--dry-run", action="store_true", help="Count only; don't write CSV")
    parser.add_argument("--output", default=str(OUTPUT_CSV))
    args = parser.parse_args()

    if not SHOPIFY_STORE or not SHOPIFY_TOKEN:
        print("[FATAL] SHOPIFY_STORE_URL / SHOPIFY_ACCESS_TOKEN not set in config/.env", file=sys.stderr)
        return 2

    t0 = time.time()
    print(f"[1/3] Fetching active games from Shopify (tag:'category:game')…")
    products = _iter_game_products(limit=args.limit)
    print(f"      {len(products)} products fetched in {time.time() - t0:.1f}s")

    t1 = time.time()
    print(f"[2/3] Identifying CIB variants…")
    rows = _collect_cib_item_ids(products)
    print(f"      {len(rows)} CIB variants identified in {time.time() - t1:.1f}s")

    # Sanity: print a few samples
    print("\n      Sample entries:")
    for r in rows[:3]:
        print(f"        {r['id']}  (handle={r['_handle']}, variant='{r['_variant_title']}', price=${r['_price']})")
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
    print(f"  1. Verify a few item_ids against Merchant Center:")
    print(f"     Merchant Center → Products → All products → search for a CIB variant → check its 'id' field matches our format")
    print(f"     (Shopify's Google app uses `shopify_US_<productNum>_<variantNum>` for US offers)")
    print(f"  2. If format matches → upload CSV as supplemental feed:")
    print(f"     MC → Products → Feeds → Add Supplemental feed → Name 'CIB Shopping Exclusion' → Upload file")
    print(f"  3. Apply to the primary Shopify feed; set schedule to Daily.")
    print(f"  4. Wait 24-48h for MC to reprocess + verify CIB offers show `Disapproved for Shopping_ads` while staying Active for Free_listings.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
