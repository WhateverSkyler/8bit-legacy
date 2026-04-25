#!/usr/bin/env python3
"""
One-off: set all Pokemon cards with min variant price < $2.00 to DRAFT status.

Reasoning: at $1.99 sale, Shopify fees ($0.36) + typical eBay LP cost ($2-3)
guarantee a loss. These should not be live for sale. Drafting (vs deleting)
preserves the SKU/handle so they can be re-activated if pricing improves.

Usage:
  python3 scripts/draft-sub2-pokemon.py            # dry-run
  python3 scripts/draft-sub2-pokemon.py --apply    # actually mutate
"""
import os
import sys
import time
from pathlib import Path
import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / "config" / ".env")
SHOP = os.environ["SHOPIFY_STORE_URL"]
TOK = os.environ["SHOPIFY_ACCESS_TOKEN"]
URL = f"https://{SHOP}/admin/api/2024-10/graphql.json"
H = {"X-Shopify-Access-Token": TOK, "Content-Type": "application/json"}

THRESHOLD = 2.00


def gql(q, v=None):
    p = {"query": q}
    if v:
        p["variables"] = v
    r = requests.post(URL, headers=H, json=p, timeout=30)
    r.raise_for_status()
    return r.json()


def fetch_pokemon():
    q = """
    query($cursor: String) {
      products(first: 250, after: $cursor, query: "tag:'category:pokemon_card' status:active") {
        edges {
          node {
            id
            title
            status
            variants(first: 5) { edges { node { price } } }
          }
        }
        pageInfo { hasNextPage endCursor }
      }
    }
    """
    cursor = None
    out = []
    pages = 0
    while pages < 20:
        pages += 1
        res = gql(q, {"cursor": cursor})
        data = res["data"]["products"]
        for e in data["edges"]:
            n = e["node"]
            prices = [float(v["node"]["price"]) for v in n["variants"]["edges"]]
            if prices and min(prices) < THRESHOLD:
                out.append({"id": n["id"], "title": n["title"], "min": min(prices)})
        if not data["pageInfo"]["hasNextPage"]:
            break
        cursor = data["pageInfo"]["endCursor"]
    return out


def set_draft(pid):
    m = """
    mutation($input: ProductInput!) {
      productUpdate(input: $input) {
        product { id status }
        userErrors { field message }
      }
    }
    """
    return gql(m, {"input": {"id": pid, "status": "DRAFT"}})


def main():
    apply = "--apply" in sys.argv
    print(f"Mode: {'APPLY' if apply else 'DRY-RUN'}")
    targets = fetch_pokemon()
    print(f"Found {len(targets)} active Pokemon products with min price < ${THRESHOLD:.2f}\n")
    for t in targets[:10]:
        print(f"  ${t['min']:.2f}  {t['title'][:70]}")
    if len(targets) > 10:
        print(f"  ... +{len(targets) - 10} more")

    if not apply:
        print("\nDry-run. Re-run with --apply to set them to DRAFT.")
        return

    print(f"\nDrafting {len(targets)} products...")
    ok = fail = 0
    for i, t in enumerate(targets, 1):
        try:
            res = set_draft(t["id"])
            errs = res.get("data", {}).get("productUpdate", {}).get("userErrors", [])
            if errs:
                print(f"  [{i}/{len(targets)}] ERR {t['title'][:50]}: {errs}")
                fail += 1
            else:
                ok += 1
                if i % 20 == 0 or i == len(targets):
                    print(f"  [{i}/{len(targets)}] drafted {ok} so far")
        except Exception as e:
            print(f"  [{i}/{len(targets)}] EXC {t['title'][:50]}: {e}")
            fail += 1
        time.sleep(0.25)  # gentle rate limiting
    print(f"\nDone: {ok} drafted, {fail} failed")


if __name__ == "__main__":
    main()
