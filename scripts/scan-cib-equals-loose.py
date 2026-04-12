#!/usr/bin/env python3
"""
Scan all multi-variant retro games on Shopify and count how many still have
CIB variant price == Loose variant price.

Used as a verification step for `fix-cib-equals-loose.py`. Regenerates
`data/cib-equals-loose.json` with the current set of offenders so the fix
script can be re-run against the fresh list if needed.
"""
import json
import os
import sys
import time
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
      tags
      variants(first: 5) {
        nodes {
          id
          title
          price
          updatedAt
        }
      }
    }
  }
}
"""


def gql(query, variables=None, retries=6):
    for attempt in range(retries):
        try:
            r = requests.post(
                GQL_URL,
                headers=HEADERS,
                json={"query": query, "variables": variables or {}},
                timeout=30,
            )
            if r.status_code == 429:
                time.sleep(2 + attempt)
                continue
            r.raise_for_status()
            data = r.json()
            if any(
                e.get("extensions", {}).get("code") == "THROTTLED"
                for e in data.get("errors", [])
            ):
                time.sleep(2 + attempt)
                continue
            return data
        except requests.exceptions.RequestException as e:
            wait = min(2 ** attempt, 30)
            print(f"  Network error ({e.__class__.__name__}), retry {attempt+1}/{retries} in {wait}s", flush=True)
            time.sleep(wait)
    raise RuntimeError("gql max retries exceeded")


def is_cib_variant(title: str) -> bool:
    vt = title.lower()
    return "complete" in vt or "cib" in vt or "box" in vt


def main():
    if not SHOP or not TOKEN:
        print("ERROR: SHOPIFY_STORE_URL and SHOPIFY_ACCESS_TOKEN not set")
        sys.exit(1)

    print(f"Scanning all active products for CIB == Loose...")
    cursor = None
    total = 0
    multi_variant = 0
    cib_equals_loose = []
    cib_gt_loose = 0

    while True:
        data = gql(QUERY, {"cursor": cursor})
        pd = data["data"]["products"]
        for p in pd["nodes"]:
            total += 1
            variants = p["variants"]["nodes"]
            if len(variants) < 2:
                continue

            # Skip Pokemon
            tags_lc = [t.lower() for t in p.get("tags", [])]
            pt_lc = (p.get("productType") or "").lower()
            if "pokemon" in pt_lc or any("pokemon" in t for t in tags_lc):
                continue

            loose = None
            cib = None
            for v in variants:
                if is_cib_variant(v["title"]):
                    cib = v
                else:
                    loose = v
            if not loose or not cib:
                continue

            multi_variant += 1
            try:
                lp = float(loose["price"])
                cp = float(cib["price"])
            except (TypeError, ValueError):
                continue

            if abs(cp - lp) < 0.01:
                cib_equals_loose.append({
                    "id": p["id"],
                    "title": p["title"],
                    "tags": p.get("tags", []),
                    "loose_id": loose["id"],
                    "loose_price": lp,
                    "loose_title": loose["title"],
                    "loose_updated": loose["updatedAt"][:10],
                    "cib_id": cib["id"],
                    "cib_price": cp,
                    "cib_title": cib["title"],
                    "cib_updated": cib["updatedAt"][:10],
                })
            elif cp > lp:
                cib_gt_loose += 1

        if total % 500 == 0:
            print(f"  scanned {total} | multi-variant={multi_variant} | CIB==Loose={len(cib_equals_loose)}", flush=True)

        if not pd["pageInfo"]["hasNextPage"]:
            break
        cursor = pd["pageInfo"]["endCursor"]

    print()
    print("=" * 60)
    print(f"  Total active products:        {total}")
    print(f"  Multi-variant retro games:    {multi_variant}")
    print(f"  CIB > Loose (good):           {cib_gt_loose}")
    print(f"  CIB == Loose (BUG):           {len(cib_equals_loose)}")
    if multi_variant:
        pct = len(cib_equals_loose) / multi_variant * 100
        print(f"  Bug percentage:               {pct:.1f}%")
    print("=" * 60)

    out_path = PROJECT / "data" / "cib-equals-loose.json"
    out_path.write_text(json.dumps(cib_equals_loose, indent=2))
    print(f"\nWrote {out_path} ({len(cib_equals_loose)} entries)")


if __name__ == "__main__":
    main()
