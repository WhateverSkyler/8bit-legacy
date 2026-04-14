#!/usr/bin/env python3
"""
Audit every product whose current CIB price came from the synthetic
`uplift_1.8x` fallback in fix-cib-equals-loose.py rather than real
PriceCharting market data.

Walks all apply-mode fix-cib CSV logs, builds the per-product history,
and outputs:

  data/synthetic-cib-products.json   — structured list for tooling
  data/synthetic-cib-products.csv    — spreadsheet-friendly list
  data/synthetic-cib-audit.md        — human-readable breakdown

Importantly: if a product was treated multiple times (e.g. 1.8x in April
and then PC-matched in a later run), the LATEST treatment wins and the
product is excluded from the synthetic list. The goal is "what's live on
the site right now, and how did it get there?"
"""
from __future__ import annotations

import csv
import glob
import json
import os
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

PROJECT = Path(__file__).parent.parent
load_dotenv(PROJECT / "dashboard" / ".env.local")
load_dotenv(PROJECT / "config" / ".env")

SHOP = os.getenv("SHOPIFY_STORE_URL", "")
TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN", "")
GQL_URL = f"https://{SHOP}/admin/api/2024-10/graphql.json"
HEADERS = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}


def parse_timestamp(csv_path: Path):
    """Extract apply timestamp from fix-cib-equals-loose-YYYYMMDD_HHMMSS.csv."""
    stem = csv_path.stem
    try:
        return datetime.strptime(stem.rsplit("-", 1)[-1], "%Y%m%d_%H%M%S")
    except Exception:
        return datetime.min


def walk_fix_cib_history():
    """Return dict: product_title -> {"source", "when", "csv"}  where
    the latest APPLIED treatment wins."""
    latest = {}
    for csv_path in sorted(PROJECT.glob("data/logs/fix-cib-equals-loose-*.csv"),
                           key=parse_timestamp):
        ts = parse_timestamp(csv_path)
        with open(csv_path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("status") not in ("APPLIED", "APPLY"):
                    continue
                title = row["product"]
                latest[title] = {
                    "source": row.get("source", "unknown"),
                    "when": ts.isoformat(timespec="seconds"),
                    "csv": csv_path.name,
                    "loose_applied": row.get("loose_new", ""),
                    "cib_applied": row.get("cib_new", ""),
                }
    return latest


def walk_search_refresh_history():
    """Any product that got a real PriceCharting/eBay match via a refresh script
    OVERRIDES a prior uplift_1.8x treatment. Walk both legacy search-refresh-*.csv
    and the newer refresh-unified-*.csv logs, same 'latest wins' rule.

    APPLIED rows are real-market writes. NO_CHANGE rows ALSO count as overrides:
    they prove the current price already matches real market data (so the earlier
    synthetic treatment is effectively validated/replaced, or never actually
    caused the mis-price)."""
    latest = {}
    patterns = ["data/logs/search-refresh-*.csv", "data/logs/refresh-unified-*.csv"]
    paths = []
    for pat in patterns:
        paths.extend(PROJECT.glob(pat))
    for csv_path in sorted(paths, key=parse_timestamp):
        ts = parse_timestamp(csv_path)
        with open(csv_path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                status = row.get("status", "")
                if status not in ("APPLIED", "NO_CHANGE"):
                    continue
                # Only count CIB-variant rows as CIB overrides
                vtype = (row.get("type") or row.get("variant_type") or "").lower()
                if vtype and vtype != "cib":
                    continue
                title = row["product"]
                source = row.get("source") or "pc_search"
                latest[title] = {
                    "source": source,
                    "when": ts.isoformat(timespec="seconds"),
                    "csv": csv_path.name,
                }
    return latest


def fetch_live_prices(titles):
    """Fetch current loose + cib prices for a list of product titles."""
    # Walk all active products and match by title
    all_products = {}
    cursor = None
    query = """
    query($cursor: String) {
      products(first: 250, after: $cursor, query: "status:active") {
        pageInfo { hasNextPage endCursor }
        nodes {
          id handle title
          variants(first: 5) { nodes { title price compareAtPrice } }
        }
      }
    }
    """
    import time
    while True:
        r = requests.post(GQL_URL, headers=HEADERS,
                          json={"query": query, "variables": {"cursor": cursor}}, timeout=30)
        if r.status_code == 429:
            time.sleep(2); continue
        r.raise_for_status()
        data = r.json()["data"]["products"]
        for p in data["nodes"]:
            all_products[p["title"]] = p
        if not data["pageInfo"]["hasNextPage"]:
            break
        cursor = data["pageInfo"]["endCursor"]
    return all_products


def is_cib(t):
    t = t.lower()
    return "complete" in t or "cib" in t or "box" in t


def main():
    if not SHOP or not TOKEN:
        print("ERROR: credentials not set"); return

    print("Walking fix-cib-equals-loose history...", flush=True)
    fix_history = walk_fix_cib_history()
    print(f"  {len(fix_history)} products received a fix-cib treatment (latest wins)")

    print("Walking search-refresh history...", flush=True)
    refresh_history = walk_search_refresh_history()
    print(f"  {len(refresh_history)} products matched via PC search (any time)")

    # Synthetic = uplift_1.8x fix-cib treatment, AND no later pc_search override
    synthetic_titles = []
    for title, info in fix_history.items():
        if info["source"] != "uplift_1.8x":
            continue
        # Was there a later pc_search that overrode it?
        later_match = refresh_history.get(title)
        if later_match and later_match["when"] > info["when"]:
            continue
        synthetic_titles.append((title, info))

    print(f"\nSynthetic-CIB products (no subsequent real-market override): {len(synthetic_titles)}")

    print("\nFetching current live prices for those products...", flush=True)
    live = fetch_live_prices([t for t, _ in synthetic_titles])

    out_rows = []
    missing_live = 0
    for title, info in synthetic_titles:
        p = live.get(title)
        if not p:
            missing_live += 1
            continue
        loose = next((v for v in p["variants"]["nodes"] if not is_cib(v["title"])), None)
        cib = next((v for v in p["variants"]["nodes"] if is_cib(v["title"])), None)
        if not loose or not cib:
            continue
        lp = float(loose["price"])
        cp = float(cib["price"])
        out_rows.append({
            "title": title,
            "handle": p["handle"],
            "shopify_product_id": p["id"],
            "loose_price": lp,
            "cib_price": cp,
            "ratio": round(cp / lp, 2) if lp else 0,
            "uplift_when": info["when"],
            "uplift_run": info["csv"],
        })

    print(f"  {len(out_rows)} confirmed live | {missing_live} products no longer live")

    # JSON output
    out_json = PROJECT / "data" / "synthetic-cib-products.json"
    with open(out_json, "w") as f:
        json.dump(out_rows, f, indent=2)
    print(f"\nWrote {out_json}")

    # CSV output
    out_csv = PROJECT / "data" / "synthetic-cib-products.csv"
    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["title", "handle", "shopify_product_id",
                                          "loose_price", "cib_price", "ratio",
                                          "uplift_when", "uplift_run"])
        w.writeheader()
        for r in out_rows:
            w.writerow(r)
    print(f"Wrote {out_csv}")

    # Summary stats
    by_console = defaultdict(int)
    price_bands = {"under_20": 0, "20_to_50": 0, "50_to_100": 0, "100_plus": 0}
    for r in out_rows:
        title = r["title"].lower()
        for k in ["nes", "snes", "n64", "gamecube", "gameboy", "ps1", "ps2",
                  "psp", "xbox", "wii", "dreamcast", "genesis", "saturn"]:
            if k in title or k in r["handle"]:
                by_console[k] += 1
                break
        else:
            by_console["other"] += 1
        lp = r["loose_price"]
        if lp < 20: price_bands["under_20"] += 1
        elif lp < 50: price_bands["20_to_50"] += 1
        elif lp < 100: price_bands["50_to_100"] += 1
        else: price_bands["100_plus"] += 1

    print("\nBy console:")
    for k, c in sorted(by_console.items(), key=lambda x: -x[1]):
        print(f"  {k:<12} {c}")
    print("\nBy loose price band:")
    for k, c in price_bands.items():
        print(f"  {k:<12} {c}")


if __name__ == "__main__":
    main()
