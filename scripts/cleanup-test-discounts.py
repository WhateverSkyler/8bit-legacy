#!/usr/bin/env python3
"""
One-off cleanup: delete the auto-applied "Test order free shipping v2 (pixel-fix 2026-04-24)"
discount that lingered past pixel-fix testing and is now applying $0 to every real order.

Also lists/deletes the v2 + v3 code discounts if still present.
"""
import os
import sys
from pathlib import Path
import requests
from dotenv import load_dotenv

CONFIG_DIR = Path(__file__).parent.parent / "config"
load_dotenv(CONFIG_DIR / ".env")
load_dotenv(Path(__file__).parent.parent / "dashboard" / ".env.local")

SHOPIFY_STORE = os.getenv("SHOPIFY_STORE_URL", "")
SHOPIFY_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN", "")
API = "2024-10"


def gql(query, variables=None):
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    r = requests.post(
        f"https://{SHOPIFY_STORE}/admin/api/{API}/graphql.json",
        headers={"X-Shopify-Access-Token": SHOPIFY_TOKEN, "Content-Type": "application/json"},
        json=payload,
    )
    r.raise_for_status()
    return r.json()


def list_discounts():
    q = """
    query {
      discountNodes(first: 50, query: "status:active OR status:scheduled") {
        edges {
          node {
            id
            discount {
              __typename
              ... on DiscountAutomaticBasic { title startsAt endsAt status }
              ... on DiscountAutomaticBxgy { title startsAt endsAt status }
              ... on DiscountAutomaticFreeShipping { title startsAt endsAt status }
              ... on DiscountCodeBasic { title startsAt endsAt status codes(first: 3){edges{node{code}}} }
              ... on DiscountCodeFreeShipping { title startsAt endsAt status codes(first: 3){edges{node{code}}} }
            }
          }
        }
      }
    }
    """
    res = gql(q)
    if "errors" in res or not res.get("data"):
        import json as _j
        print("GraphQL response:", _j.dumps(res, indent=2)[:2000])
        sys.exit(2)
    return res.get("data", {}).get("discountNodes", {}).get("edges", [])


def delete_automatic(node_id):
    m = """
    mutation($id: ID!) {
      discountAutomaticDelete(id: $id) {
        deletedAutomaticDiscountId
        userErrors { field message }
      }
    }
    """
    return gql(m, {"id": node_id})


def delete_code(node_id):
    m = """
    mutation($id: ID!) {
      discountCodeDelete(id: $id) {
        deletedCodeDiscountId
        userErrors { field message }
      }
    }
    """
    return gql(m, {"id": node_id})


def main():
    print("Listing active/scheduled discounts...\n")
    edges = list_discounts()
    targets = []
    for e in edges:
        n = e["node"]
        d = n.get("discount", {})
        title = d.get("title", "")
        typename = d.get("__typename", "")
        codes = [c["node"]["code"] for c in d.get("codes", {}).get("edges", [])] if "codes" in d else []
        marker = ""
        if "Test order free shipping" in title or "pixel-fix" in title.lower():
            marker = "  <-- DELETE (auto-applied test free shipping)"
            targets.append(("automatic", n["id"], title))
        elif any("TESTZERO" in c for c in codes):
            marker = "  <-- DELETE (test zero code)"
            targets.append(("code", n["id"], title))
        print(f"  [{typename}] {title}  codes={codes}{marker}")

    if not targets:
        print("\nNo test discounts found. Nothing to delete.")
        return 0

    if "--apply" not in sys.argv:
        print(f"\nFound {len(targets)} discount(s) to delete. Re-run with --apply to delete.")
        return 0

    print(f"\nDeleting {len(targets)} discount(s)...")
    for kind, node_id, title in targets:
        if kind == "automatic":
            res = delete_automatic(node_id)
            data = res.get("data", {}).get("discountAutomaticDelete", {})
        else:
            res = delete_code(node_id)
            data = res.get("data", {}).get("discountCodeDelete", {})
        errs = data.get("userErrors", [])
        if errs:
            print(f"  FAILED: {title} -> {errs}")
        else:
            print(f"  DELETED: {title}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
