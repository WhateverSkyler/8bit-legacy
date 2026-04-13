#!/usr/bin/env python3
"""
Build a product-ID file from the NO_MATCH rows in the 2026-04-13 refresh CSV.
Used as input to `search-price-refresh.py --only-ids-file` for a focused
re-run against only the products that failed to match.
"""
from __future__ import annotations

import csv
import json
import os
import sys
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

CSV = PROJECT / "data" / "logs" / "search-refresh-20260413_104335.csv"

QUERY = """
query($cursor: String) {
  products(first: 250, after: $cursor, query: "status:active") {
    pageInfo { hasNextPage endCursor }
    nodes { id title }
  }
}
"""


def main():
    # Load NO_MATCH titles
    no_match_titles = set()
    with open(CSV) as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            if row and row[-1] == "NO_MATCH":
                no_match_titles.add(row[0])

    print(f"NO_MATCH titles to look up: {len(no_match_titles)}", flush=True)

    # Walk all active products, map title → id
    title_to_id = {}
    cursor = None
    scanned = 0
    while True:
        import time
        r = requests.post(GQL_URL, headers=HEADERS,
                          json={"query": QUERY, "variables": {"cursor": cursor}}, timeout=30)
        if r.status_code == 429:
            time.sleep(2); continue
        r.raise_for_status()
        data = r.json()["data"]["products"]
        for p in data["nodes"]:
            scanned += 1
            if p["title"] in no_match_titles:
                title_to_id[p["title"]] = p["id"]
        if not data["pageInfo"]["hasNextPage"]:
            break
        cursor = data["pageInfo"]["endCursor"]

    print(f"Scanned {scanned} products, matched {len(title_to_id)} of {len(no_match_titles)} NO_MATCH titles")
    missing = no_match_titles - set(title_to_id.keys())
    if missing:
        print(f"\n{len(missing)} titles not found (may have been deleted/renamed):")
        for t in list(missing)[:10]:
            print(f"  {t}")
        if len(missing) > 10:
            print(f"  ...and {len(missing) - 10} more")

    ids = sorted(title_to_id.values())
    out = PROJECT / "data" / "nomatch-product-ids.json"
    with open(out, "w") as f:
        json.dump(ids, f)
    print(f"\nWrote {len(ids)} IDs to {out}")


if __name__ == "__main__":
    main()
