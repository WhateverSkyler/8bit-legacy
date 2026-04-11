#!/usr/bin/env python3
"""
Fix Google Merchant Center identifier metafields on retro game products.

Findings from scripts/check-gtin-metafields.py (2026-04-11 scan of 7,290 products):
  - 6,102 products are missing `mm-google-shopping.custom_product = true`
  - 3 products have `mm-google-shopping.google_product_category = apparel` (wrong)
  - 3 products have bogus short MPN values in `global.MPN`

Why custom_product=true matters: retro games are used/custom items without standard
UPC barcodes. Setting this metafield tells Google Merchant Center to bypass the
GTIN/MPN requirement so the products stay approved in Shopping ads.

Usage:
    # Preview
    python3 scripts/fix-gtin-metafields.py --dry-run

    # Apply
    python3 scripts/fix-gtin-metafields.py
"""
import json
import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / "dashboard" / ".env.local")
load_dotenv(Path(__file__).parent.parent / "config" / ".env")

SHOP = os.getenv("SHOPIFY_STORE_URL", "")
TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN", "")
API_VERSION = "2024-10"
GQL_URL = f"https://{SHOP}/admin/api/{API_VERSION}/graphql.json"
HEADERS = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}

DRY_RUN = "--dry-run" in sys.argv


def gql(query, variables=None):
    for attempt in range(5):
        resp = requests.post(GQL_URL, headers=HEADERS, json={"query": query, "variables": variables or {}})
        if resp.status_code == 429:
            time.sleep(2 + attempt)
            continue
        if resp.status_code != 200:
            print(f"  HTTP {resp.status_code}: {resp.text[:200]}")
            time.sleep(2 ** attempt)
            continue
        data = resp.json()
        if any(e.get("extensions", {}).get("code") == "THROTTLED" for e in data.get("errors", [])):
            time.sleep(2 + attempt)
            continue
        return data
    return data


# Fetch products with their current metafield state. We re-scan rather than trust
# the snapshot in data/gtin-needs-fix.json because metafields can change between
# runs (e.g., from other tools / the Google & YouTube app).
FETCH = """
query($cursor: String) {
  products(first: 100, after: $cursor, query: "status:active") {
    pageInfo { hasNextPage endCursor }
    nodes {
      id
      title
      productType
      metafields(first: 30) {
        nodes { id namespace key value type }
      }
    }
  }
}
"""

SET_METAFIELDS = """
mutation($metafields: [MetafieldsSetInput!]!) {
  metafieldsSet(metafields: $metafields) {
    metafields { id namespace key value }
    userErrors { field message code }
  }
}
"""

DELETE_METAFIELD = """
mutation($input: MetafieldDeleteInput!) {
  metafieldDelete(input: $input) {
    deletedId
    userErrors { field message }
  }
}
"""


def collect_fixes():
    """Scan all active products and decide what to change."""
    to_set = []      # list of MetafieldsSetInput
    to_delete = []   # list of metafield IDs (for bogus MPN removal)
    stats = {
        "total": 0,
        "set_custom_product": 0,
        "fix_category": 0,
        "delete_bogus_mpn": 0,
        "skipped_pokemon": 0,
    }

    cursor = None
    while True:
        data = gql(FETCH, {"cursor": cursor})
        edge = data.get("data", {}).get("products", {})
        nodes = edge.get("nodes", [])
        for p in nodes:
            stats["total"] += 1
            title_lo = p["title"].lower()
            pt_lo = p["productType"].lower()

            # Pokemon cards handled separately — don't touch them
            if "pokemon" in pt_lo or ("card" in title_lo and "memory" not in title_lo):
                stats["skipped_pokemon"] += 1
                continue

            mf_map = {(m["namespace"], m["key"]): m for m in p["metafields"]["nodes"]}

            # 1) Set custom_product=true if not already true.
            # Retro games are used/custom items without GTIN — this bypasses
            # Merchant Center's GTIN requirement.
            cp = mf_map.get(("mm-google-shopping", "custom_product"))
            if not cp or cp["value"] != "true":
                to_set.append({
                    "ownerId": p["id"],
                    "namespace": "mm-google-shopping",
                    "key": "custom_product",
                    "type": "boolean",
                    "value": "true",
                })
                stats["set_custom_product"] += 1

            # 2) Fix wrong google_product_category (apparel or other) → 1279 (Video Games)
            cat = mf_map.get(("mm-google-shopping", "google_product_category"))
            if not cat or cat["value"] != "1279":
                to_set.append({
                    "ownerId": p["id"],
                    "namespace": "mm-google-shopping",
                    "key": "google_product_category",
                    "type": "single_line_text_field",
                    "value": "1279",
                })
                stats["fix_category"] += 1

            # 3) Delete bogus short MPN (looks like placeholder junk)
            mpn = mf_map.get(("global", "MPN"))
            if mpn and mpn["value"] and len(mpn["value"]) < 16 \
                    and any(c.isdigit() for c in mpn["value"]) \
                    and any(c.isalpha() for c in mpn["value"]):
                to_delete.append({"id": mpn["id"], "title": p["title"], "value": mpn["value"]})
                stats["delete_bogus_mpn"] += 1

        page = edge.get("pageInfo", {})
        if stats["total"] % 500 == 0:
            print(f"  scanned {stats['total']} — will set {stats['set_custom_product']} custom_product, fix {stats['fix_category']} category, delete {stats['delete_bogus_mpn']} bogus MPN")
        if not page.get("hasNextPage"):
            break
        cursor = page.get("endCursor")
        time.sleep(0.3)

    return to_set, to_delete, stats


def apply_metafield_batches(to_set, batch_size=25):
    """metafieldsSet accepts up to 25 metafields per call."""
    total = len(to_set)
    applied = 0
    errors = 0
    for i in range(0, total, batch_size):
        batch = to_set[i:i + batch_size]
        result = gql(SET_METAFIELDS, {"metafields": batch})
        user_errors = result.get("data", {}).get("metafieldsSet", {}).get("userErrors", [])
        if user_errors:
            print(f"  ERROR batch {i}-{i+len(batch)}: {user_errors[:3]}")
            errors += len(batch)
        else:
            applied += len(batch)
        if (i // batch_size) % 20 == 0 and i > 0:
            print(f"  applied {applied}/{total} metafields ({errors} errors)")
        time.sleep(0.4)
    return applied, errors


def apply_deletes(to_delete):
    deleted = 0
    errors = 0
    for d in to_delete:
        result = gql(DELETE_METAFIELD, {"input": {"id": d["id"]}})
        user_errors = result.get("data", {}).get("metafieldDelete", {}).get("userErrors", [])
        if user_errors:
            print(f"  ERROR deleting MPN on {d['title']}: {user_errors}")
            errors += 1
        else:
            deleted += 1
            print(f"  deleted bogus MPN '{d['value']}' on {d['title']}")
        time.sleep(0.4)
    return deleted, errors


def main():
    print(f"{'[DRY RUN] ' if DRY_RUN else ''}Scanning active products for metafield fixes...")
    to_set, to_delete, stats = collect_fixes()

    print(f"\nScanned {stats['total']} products ({stats['skipped_pokemon']} Pokemon skipped)")
    print(f"  Set custom_product=true: {stats['set_custom_product']}")
    print(f"  Fix google_product_category=1279: {stats['fix_category']}")
    print(f"  Delete bogus MPN: {stats['delete_bogus_mpn']}")
    print(f"  Total metafieldsSet calls: {len(to_set)} (batched 25/call)")

    if DRY_RUN:
        print("\n[DRY RUN] Sample of metafields that would be set:")
        for m in to_set[:5]:
            print(f"  {m['ownerId']}: {m['namespace']}.{m['key']}={m['value']}")
        print("\n[DRY RUN] Sample of bogus MPNs that would be deleted:")
        for d in to_delete[:5]:
            print(f"  {d['title']}: {d['value']}")
        print("\nRe-run without --dry-run to apply.")
        return

    print(f"\nApplying {len(to_set)} metafield sets...")
    applied, set_errors = apply_metafield_batches(to_set)
    print(f"  Applied {applied}/{len(to_set)} ({set_errors} errors)")

    print(f"\nDeleting {len(to_delete)} bogus MPN metafields...")
    deleted, del_errors = apply_deletes(to_delete)
    print(f"  Deleted {deleted}/{len(to_delete)} ({del_errors} errors)")

    print(f"\nDone. Set {applied}, deleted {deleted}, errors {set_errors + del_errors}")


if __name__ == "__main__":
    main()
