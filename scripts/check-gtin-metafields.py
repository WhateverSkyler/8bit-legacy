#!/usr/bin/env python3
"""
Scan all active products for Google Merchant Center identifier metafields.
Report counts of:
 - custom_product = true / false / unset
 - google_product_category correct (1279 for video games) / wrong / unset
 - MPN garbage values
"""
import os, sys, time, json, requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / "dashboard" / ".env.local")
load_dotenv(Path(__file__).parent.parent / "config" / ".env")

SHOP = os.getenv("SHOPIFY_STORE_URL", "")
TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN", "")
GQL_URL = f"https://{SHOP}/admin/api/2024-10/graphql.json"
HEADERS = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}


def gql(q, v=None):
    for attempt in range(5):
        r = requests.post(GQL_URL, json={"query": q, "variables": v or {}}, headers=HEADERS)
        if r.status_code != 200:
            time.sleep(2 ** attempt)
            continue
        data = r.json()
        if any(e.get("extensions", {}).get("code") == "THROTTLED" for e in data.get("errors", [])):
            time.sleep(2 + attempt)
            continue
        return data
    return data


FETCH = """
query($cursor: String) {
  products(first: 100, after: $cursor, query: "status:active") {
    pageInfo { hasNextPage endCursor }
    nodes {
      id
      title
      productType
      metafields(first: 30) {
        nodes { namespace key value }
      }
    }
  }
}
"""


def main():
    cursor = None
    stats = {
        "total": 0,
        "custom_product_true": 0,
        "custom_product_false": 0,
        "custom_product_unset": 0,
        "category_1279": 0,
        "category_other": 0,
        "category_apparel": 0,
        "category_unset": 0,
        "has_mpn": 0,
        "has_bogus_mpn": 0,
    }
    sample_bogus = []
    needs_fix_ids = []

    while True:
        data = gql(FETCH, {"cursor": cursor})
        edge = data.get("data", {}).get("products", {})
        nodes = edge.get("nodes", [])
        for p in nodes:
            stats["total"] += 1
            # Skip Pokemon cards (they have their own handling)
            title_lo = p["title"].lower()
            pt_lo = p["productType"].lower()
            if "pokemon" in pt_lo or "card" in title_lo and "memory" not in title_lo:
                continue

            mf_map = {(m["namespace"], m["key"]): m["value"] for m in p["metafields"]["nodes"]}

            # custom_product
            cp = mf_map.get(("mm-google-shopping", "custom_product"))
            if cp == "true":
                stats["custom_product_true"] += 1
            elif cp == "false":
                stats["custom_product_false"] += 1
            else:
                stats["custom_product_unset"] += 1

            # google_product_category
            cat = mf_map.get(("mm-google-shopping", "google_product_category"))
            if cat == "1279":
                stats["category_1279"] += 1
            elif cat and "apparel" in cat.lower():
                stats["category_apparel"] += 1
            elif cat:
                stats["category_other"] += 1
            else:
                stats["category_unset"] += 1

            # MPN
            mpn = mf_map.get(("global", "MPN"))
            if mpn:
                stats["has_mpn"] += 1
                # Bogus: short alphanumeric doesn't look like a real MPN
                if len(mpn) < 16 and any(c.isdigit() for c in mpn) and any(c.isalpha() for c in mpn):
                    stats["has_bogus_mpn"] += 1
                    if len(sample_bogus) < 10:
                        sample_bogus.append(f"{p['title']}: MPN={mpn}")

            # Flag for fix if anything wrong
            needs_fix = (
                cp != "true"
                or cat != "1279"
                or (mpn and len(mpn) < 16)
            )
            if needs_fix:
                needs_fix_ids.append({"id": p["id"], "title": p["title"]})

        page = edge.get("pageInfo", {})
        if not page.get("hasNextPage"):
            break
        cursor = page.get("endCursor")
        if stats["total"] % 500 == 0:
            print(f"  scanned {stats['total']}")
        time.sleep(0.3)

    print(f"\nScanned {stats['total']} active products\n")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    print(f"\n  needs_fix: {len(needs_fix_ids)}")
    if sample_bogus:
        print(f"\nSample bogus MPNs:")
        for b in sample_bogus:
            print(f"  - {b}")

    if "--save" in sys.argv:
        out = Path(__file__).parent.parent / "data" / "gtin-needs-fix.json"
        out.parent.mkdir(exist_ok=True)
        out.write_text(json.dumps(needs_fix_ids, indent=2))
        print(f"\nSaved: {out}")


if __name__ == "__main__":
    main()
