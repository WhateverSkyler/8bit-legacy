#!/usr/bin/env python3
"""Pull 15 random multi-variant retro games and print Loose vs CIB prices."""
import os
import random
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

QUERY = """
query($cursor: String) {
  products(first: 250, after: $cursor, query: "status:active") {
    pageInfo { hasNextPage endCursor }
    nodes {
      handle
      title
      variants(first: 5) { nodes { title price } }
    }
  }
}
"""


def is_cib(t: str) -> bool:
    t = t.lower()
    return "complete" in t or "cib" in t or "box" in t


def main():
    all_games = []
    cursor = None
    while True:
        r = requests.post(GQL_URL, headers=HEADERS,
                          json={"query": QUERY, "variables": {"cursor": cursor}}, timeout=30)
        r.raise_for_status()
        data = r.json()["data"]["products"]
        for p in data["nodes"]:
            vs = p["variants"]["nodes"]
            if len(vs) < 2:
                continue
            loose = next((v for v in vs if not is_cib(v["title"])), None)
            cib = next((v for v in vs if is_cib(v["title"])), None)
            if loose and cib:
                # Skip console bundles — false positives
                title_l = p["title"].lower()
                if any(k in title_l for k in ["bundle", "player pack", "pack ", "console"]):
                    continue
                all_games.append((p["handle"], p["title"], float(loose["price"]), float(cib["price"])))
        if not data["pageInfo"]["hasNextPage"]:
            break
        cursor = data["pageInfo"]["endCursor"]

    print(f"Total multi-variant retro games (excluding bundles/consoles): {len(all_games)}")
    print()

    # Random sample of 15
    random.seed(42)
    sample = random.sample(all_games, 15)

    print(f"{'Handle':<50} {'Loose':>8}  {'CIB':>8}  Status")
    print("-" * 90)
    for handle, title, loose, cib in sample:
        diff = cib - loose
        status = "FIXED" if cib > loose + 0.5 else ("BUG (CIB==LOOSE)" if abs(diff) < 0.5 else "?")
        print(f"{handle[:50]:<50} ${loose:>7.2f}  ${cib:>7.2f}  {status}")

    # Overall stats
    fixed = sum(1 for _, _, l, c in all_games if c > l + 0.5)
    bug = sum(1 for _, _, l, c in all_games if abs(c - l) < 0.5)
    inverted = sum(1 for _, _, l, c in all_games if l > c + 0.5)
    print()
    print(f"Of {len(all_games)} retro games:")
    print(f"  CIB > Loose (correct):        {fixed}  ({100*fixed/len(all_games):.1f}%)")
    print(f"  CIB == Loose (bug):           {bug}  ({100*bug/len(all_games):.1f}%)")
    print(f"  Loose > CIB (inverted):       {inverted}  ({100*inverted/len(all_games):.1f}%)")


if __name__ == "__main__":
    main()
