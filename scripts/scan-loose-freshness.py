#!/usr/bin/env python3
"""
Scan all active products' Loose (Game Only) variants and report the
distribution of `updatedAt` timestamps. Answers: "when were the game-only
prices last refreshed, and what fraction are still stale from May 2025?"
"""
import json
import os
import sys
from collections import Counter
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

QUERY = """
query($cursor: String) {
  products(first: 100, after: $cursor, query: "status:active") {
    pageInfo { hasNextPage endCursor }
    nodes {
      id
      title
      productType
      variants(first: 5) {
        nodes { title price updatedAt }
      }
    }
  }
}
"""


def gql(q, v=None, retries=6):
    import time
    for a in range(retries):
        try:
            r = requests.post(GQL_URL, headers=HEADERS,
                              json={"query": q, "variables": v or {}}, timeout=30)
            if r.status_code == 429:
                time.sleep(2 + a); continue
            r.raise_for_status()
            data = r.json()
            if any(e.get("extensions", {}).get("code") == "THROTTLED"
                   for e in data.get("errors", [])):
                time.sleep(2 + a); continue
            return data
        except requests.exceptions.RequestException:
            time.sleep(min(2 ** a, 30))
    raise RuntimeError("gql retries exceeded")


def is_cib(title: str) -> bool:
    t = title.lower()
    return "complete" in t or "cib" in t or "box" in t


def main():
    if not SHOP or not TOKEN:
        print("ERROR: credentials not set"); sys.exit(1)

    print("Scanning loose variants for price updatedAt distribution...", flush=True)
    cursor = None
    total = 0
    multi = 0
    loose_by_month = Counter()
    stale_may_2025 = 0
    stale_pre_2026 = 0
    loose_same_as_cib = 0
    sample_stale = []
    sample_recent = []
    stale_product_ids = []  # Shopify GIDs whose loose variant is stale (pre-2026)

    while True:
        data = gql(QUERY, {"cursor": cursor})
        pd = data["data"]["products"]
        for p in pd["nodes"]:
            total += 1
            variants = p["variants"]["nodes"]
            if len(variants) < 2:
                continue
            multi += 1
            loose = next((v for v in variants if not is_cib(v["title"])), None)
            cib = next((v for v in variants if is_cib(v["title"])), None)
            if not loose:
                continue
            ts = loose["updatedAt"]
            month = ts[:7]
            loose_by_month[month] += 1
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            if dt.year == 2025 and dt.month == 5:
                stale_may_2025 += 1
                if len(sample_stale) < 5:
                    sample_stale.append((p["title"][:50], ts[:10], loose["price"]))
            if dt.year < 2026:
                stale_pre_2026 += 1
                stale_product_ids.append(p["id"])
            if cib and loose["price"] == cib["price"]:
                loose_same_as_cib += 1
            if dt.year == 2026 and dt.month >= 4 and len(sample_recent) < 3:
                sample_recent.append((p["title"][:50], ts[:10], loose["price"]))

        if total % 500 == 0:
            print(f"  scanned {total} | multi={multi} | stale_may_2025={stale_may_2025}", flush=True)
        if not pd["pageInfo"]["hasNextPage"]:
            break
        cursor = pd["pageInfo"]["endCursor"]

    print()
    print("=" * 60)
    print(f"  Total active products:        {total}")
    print(f"  Multi-variant retro games:    {multi}")
    print(f"  Loose stale (May 2025):       {stale_may_2025}")
    print(f"  Loose stale (pre-2026):       {stale_pre_2026}")
    print(f"  Loose == CIB (should be 36):  {loose_same_as_cib}")
    print("=" * 60)
    print()
    print("Loose variant updatedAt by month (top 20):")
    for m, c in loose_by_month.most_common(20):
        print(f"  {m}  {c:>5}")
    print()
    print("Sample of stale (May 2025) loose variants:")
    for t, d, p in sample_stale:
        print(f"  {d}  ${p:>7}  {t}")
    print()
    print("Sample of recently-refreshed (Apr 2026) loose variants:")
    for t, d, p in sample_recent:
        print(f"  {d}  ${p:>7}  {t}")

    out = PROJECT / "data" / "stale-loose-product-ids.json"
    with open(out, "w") as f:
        json.dump(stale_product_ids, f)
    print(f"\nWrote {len(stale_product_ids)} stale product IDs to {out}")


if __name__ == "__main__":
    main()
