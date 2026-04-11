#!/usr/bin/env python3
"""
Quick scan: how many products have wrong category:console tag?
Checks all active products and reports any where productType is a games-system name
but the product is tagged as console.
"""
import os
import sys
import time
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / "dashboard" / ".env.local")
load_dotenv(Path(__file__).parent.parent / "config" / ".env")

SHOP_URL = os.getenv("SHOPIFY_STORE_URL", "")
TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN", "")
API_VERSION = "2024-10"
GQL_URL = f"https://{SHOP_URL}/admin/api/{API_VERSION}/graphql.json"
HEADERS = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}


def gql(query, variables=None):
    for attempt in range(5):
        resp = requests.post(GQL_URL, headers=HEADERS, json={"query": query, "variables": variables or {}})
        if resp.status_code != 200:
            time.sleep(2 ** attempt)
            continue
        data = resp.json()
        if any(e.get("extensions", {}).get("code") == "THROTTLED" for e in data.get("errors", [])):
            time.sleep(2 ** attempt)
            continue
        return data
    return data


def main():
    cursor = None
    scanned = 0
    miscategorized = []
    console_tagged = 0
    # Scan all active products; can't filter by tag:category:console reliably
    while True:
        after = f', after: "{cursor}"' if cursor else ""
        q = f"""
        {{
          products(first: 100{after}, query: "status:active") {{
            pageInfo {{ hasNextPage endCursor }}
            nodes {{
              id
              title
              productType
              tags
            }}
          }}
        }}
        """
        data = gql(q)
        nodes = data.get("data", {}).get("products", {}).get("nodes", [])
        for n in nodes:
            scanned += 1
            tags_lo = [t.lower() for t in n["tags"]]
            if "category:console" not in tags_lo:
                continue
            console_tagged += 1
            pt = n["productType"]
            title = n["title"]
            # Disguised game: productType is a console family name (contains parens + 'system')
            # OR title ends with " Game"
            is_game_disguised = False
            if "(" in pt and "system" in pt.lower():
                is_game_disguised = True
            elif title.lower().rstrip().endswith("game") or " game -" in title.lower() or "- snes game" in title.lower() or "- nes game" in title.lower():
                is_game_disguised = True
            if is_game_disguised:
                miscategorized.append({
                    "id": n["id"], "title": title, "productType": pt,
                })
        page_info = data.get("data", {}).get("products", {}).get("pageInfo", {})
        if not page_info.get("hasNextPage"):
            break
        cursor = page_info.get("endCursor")
        if scanned % 500 == 0:
            print(f"  scanned {scanned}, {console_tagged} tagged category:console so far")
        time.sleep(0.4)

    print(f"Scanned {scanned} active products")
    print(f"  Tagged category:console: {console_tagged}")
    print(f"  Games miscategorized: {len(miscategorized)}")
    if miscategorized:
        print("\nFirst 20 miscategorized:")
        for m in miscategorized[:20]:
            print(f"  - {m['title']}  (productType='{m['productType']}')")

    if len(sys.argv) > 1 and sys.argv[1] == "--save":
        import json
        out = Path(__file__).parent.parent / "data" / "miscategorized-products.json"
        out.parent.mkdir(exist_ok=True)
        out.write_text(json.dumps(miscategorized, indent=2))
        print(f"\nSaved: {out}")


if __name__ == "__main__":
    main()
