#!/usr/bin/env python3
"""Check a sample of CIB variants' inventoryItem.tracked state."""
import os, sys, time, requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / "dashboard" / ".env.local")
load_dotenv(Path(__file__).parent.parent / "config" / ".env")

SHOP = os.getenv("SHOPIFY_STORE_URL", "")
TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN", "")
API_VERSION = "2024-10"
GQL_URL = f"https://{SHOP}/admin/api/{API_VERSION}/graphql.json"
HEADERS = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}

Q = """
query {
  products(first: 10, query: "status:active") {
    nodes {
      title
      variants(first: 10) {
        nodes {
          title
          inventoryPolicy
          inventoryQuantity
          inventoryItem {
            id
            tracked
          }
        }
      }
    }
  }
}
"""

resp = requests.post(GQL_URL, headers=HEADERS, json={"query": Q})
data = resp.json()
for p in data["data"]["products"]["nodes"]:
    print(f"\n{p['title']}")
    for v in p["variants"]["nodes"]:
        ii = v.get("inventoryItem") or {}
        print(f"  {v['title']}: policy={v['inventoryPolicy']} qty={v['inventoryQuantity']} tracked={ii.get('tracked')}")
