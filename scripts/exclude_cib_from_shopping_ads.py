#!/usr/bin/env python3
"""Exclude every CIB (Complete-In-Box) variant from Google Shopping ads by
setting the `mm-google-shopping.excluded_destination` metafield on each
variant. This is the canonical per-variant destination-exclusion path that
the Shopify Google & YouTube app syncs to Merchant Center — it works when
the Merchant Center "supplemental feed" UI path is blocked (as it is on
Merchant-API primary feeds today).

Effect:
- CIB variants stay fully purchasable on 8bitlegacy.com
- CIB variants stay in organic free Google listings (SEO neutral-plus)
- CIB variants are BLOCKED from paid Shopping ads, Local Inventory Ads,
  and Display Ads — so they never impress in paid auctions next to
  competitors' Game Only prices.

Rationale: Shopping auction CTR tanks when our $150 CIB Silent Hill 2
shows next to DKOldies' $80 Game Only. The whole campaign strategy is
built around advertising Game Only prices exclusively.

Propagation: Shopify → Merchant Center sync is ~4h; MC → Ads reprocess
is 12–24h. Expect CIB to be fully out of ad auctions within 36–48h of
running this with --execute.

Usage:
  python3 scripts/exclude_cib_from_shopping_ads.py                 # dry-run (default)
  python3 scripts/exclude_cib_from_shopping_ads.py --limit 10      # dry-run, first 10
  python3 scripts/exclude_cib_from_shopping_ads.py --execute       # full batch
  python3 scripts/exclude_cib_from_shopping_ads.py --execute --limit 10  # first 10 for real

Idempotent: re-running after first execute is a no-op — skips variants
whose metafield already holds Shopping_ads.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / "dashboard" / ".env.local")
load_dotenv(ROOT / "config" / ".env")

SHOP_URL = os.getenv("SHOPIFY_STORE_URL", "").rstrip("/").replace("https://", "")
TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN", "")
API_VERSION = "2024-10"

if not SHOP_URL or not TOKEN:
    print("ERROR: SHOPIFY_STORE_URL and SHOPIFY_ACCESS_TOKEN must be set", file=sys.stderr)
    sys.exit(2)

GRAPHQL_URL = f"https://{SHOP_URL}/admin/api/{API_VERSION}/graphql.json"
HEADERS = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}

METAFIELD_NAMESPACE = "mm-google-shopping"
METAFIELD_KEY = "excluded_destination"
METAFIELD_TYPE = "list.single_line_text_field"
# List payload must be a JSON-encoded array string for list-typed metafields.
METAFIELD_VALUE = '["Shopping_ads"]'


def gql(query: str, variables: dict | None = None) -> dict:
    r = requests.post(GRAPHQL_URL, headers=HEADERS,
                      json={"query": query, "variables": variables or {}}, timeout=30)
    r.raise_for_status()
    data = r.json()
    if "errors" in data:
        raise RuntimeError(f"GraphQL errors: {data['errors']}")
    # Shopify GraphQL returns userErrors inside specific mutation wrappers — caller checks.
    return data["data"]


def fetch_cib_variants() -> list[dict]:
    """Return every variant whose title contains 'Complete' or 'CIB' (case-insensitive).
    Filters to active products only. Also returns the current excluded_destination
    metafield value if already set, so we can skip those.
    """
    variants: list[dict] = []
    cursor = None
    page = 0
    while True:
        page += 1
        query = """
        query($cursor: String) {
          products(first: 50, after: $cursor, query: "status:active") {
            pageInfo { hasNextPage endCursor }
            edges {
              node {
                id title
                variants(first: 20) {
                  edges {
                    node {
                      id title
                      metafield(namespace: "mm-google-shopping", key: "excluded_destination") {
                        value
                      }
                    }
                  }
                }
              }
            }
          }
        }"""
        data = gql(query, {"cursor": cursor})
        products = data["products"]
        for p_edge in products["edges"]:
            p = p_edge["node"]
            for v_edge in p["variants"]["edges"]:
                v = v_edge["node"]
                title = (v["title"] or "").lower()
                if "complete" in title or "cib" in title:
                    existing = (v.get("metafield") or {}).get("value")
                    variants.append({
                        "variant_id": v["id"],
                        "product_title": p["title"],
                        "variant_title": v["title"],
                        "has_exclusion": existing is not None and "Shopping_ads" in existing,
                    })
        if not products["pageInfo"]["hasNextPage"]:
            break
        cursor = products["pageInfo"]["endCursor"]
        if page % 10 == 0:
            print(f"  …scanned {page * 50} products, {len(variants)} CIB variants found so far", file=sys.stderr)
        time.sleep(0.5)  # polite pacing on the product-scan phase
    return variants


def set_exclusion_bulk(variant_ids: list[str]) -> tuple[int, list[str]]:
    """Set metafield on up to 25 variants per call via metafieldsSet."""
    if not variant_ids:
        return 0, []
    mutation = """
    mutation metafieldsSet($metafields: [MetafieldsSetInput!]!) {
      metafieldsSet(metafields: $metafields) {
        metafields { id }
        userErrors { field message }
      }
    }"""
    payload = [{
        "ownerId": vid,
        "namespace": METAFIELD_NAMESPACE,
        "key": METAFIELD_KEY,
        "type": METAFIELD_TYPE,
        "value": METAFIELD_VALUE,
    } for vid in variant_ids]
    data = gql(mutation, {"metafields": payload})
    res = data["metafieldsSet"]
    errors = [f"{e.get('field')}: {e['message']}" for e in res.get("userErrors", [])]
    return len(res.get("metafields", [])), errors


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--execute", action="store_true", help="Actually set metafields (default: dry-run)")
    p.add_argument("--limit", type=int, default=None, help="Process only the first N CIB variants")
    args = p.parse_args()

    print(f"[exclude_cib] shop={SHOP_URL}  execute={args.execute}  limit={args.limit}")
    print(f"[exclude_cib] target metafield: {METAFIELD_NAMESPACE}.{METAFIELD_KEY} = {METAFIELD_VALUE}")
    print()

    print("[scan] pulling CIB variants across all active products…")
    all_variants = fetch_cib_variants()
    print(f"[scan] {len(all_variants)} CIB variants total")

    todo = [v for v in all_variants if not v["has_exclusion"]]
    skipped = len(all_variants) - len(todo)
    print(f"[scan] {skipped} already have exclusion → skipping")
    print(f"[scan] {len(todo)} need the metafield set")

    if args.limit is not None:
        todo = todo[: args.limit]
        print(f"[scan] --limit applied → {len(todo)} to process this run")

    if not todo:
        print("[done] nothing to do")
        return 0

    print()
    print("[preview] first 5 targets:")
    for v in todo[:5]:
        print(f"  {v['variant_id']}  {v['product_title']!r:60.60}  variant={v['variant_title']!r}")

    if not args.execute:
        print("\n[dry-run] pass --execute to apply.")
        return 0

    print(f"\n[execute] writing metafields to {len(todo)} variants in batches of 25…")
    ok_total = 0
    err_total = 0
    batches = [todo[i : i + 25] for i in range(0, len(todo), 25)]
    for idx, batch in enumerate(batches, 1):
        vids = [v["variant_id"] for v in batch]
        try:
            n_ok, errs = set_exclusion_bulk(vids)
            ok_total += n_ok
            if errs:
                err_total += len(errs)
                for e in errs[:3]:
                    print(f"  [ERR] {e}", file=sys.stderr)
            print(f"  batch {idx}/{len(batches)}: wrote {n_ok}/{len(vids)}  errors={len(errs)}")
        except Exception as exc:
            err_total += len(batch)
            print(f"  batch {idx}/{len(batches)}: EXCEPTION {exc}", file=sys.stderr)
        time.sleep(0.3)  # polite pacing

    print()
    print(f"[done] wrote {ok_total}, errored {err_total} (of {len(todo)} attempted)")
    return 0 if err_total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
