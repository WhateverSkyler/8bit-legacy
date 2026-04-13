#!/usr/bin/env python3
"""
Scan all active multi-variant retro games and find products where the
Loose <-> CIB pricing relationship is broken. Two patterns:

  1. CIB == Loose (within $0.50) — CIB never got its own market price
  2. Loose > CIB (by > $0.50) — inverted, CIB is wrong because either:
     - loose was refreshed but CIB is stale, or
     - CIB was seeded low by an earlier bulk operation

Excludes console bundles, player packs, and hardware (where "Complete"
doesn't mean CIB — it means a bundle configuration).

Outputs `data/cib-equals-loose.json` in the same format consumed by
`fix-cib-equals-loose.py` so the existing fix machinery can run against
the combined broken set.
"""
from __future__ import annotations

import json
import os
import sys
import time
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


def gql(q, v=None, retries=6):
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


def is_bundle(product_title: str) -> bool:
    """Exclude console bundles / hardware — 'Complete' there is a bundle
    configuration name, not the CIB variant type."""
    t = product_title.lower()
    return any(k in t for k in [
        "bundle", "player pack", "pack ", " console", "console ",
        "console-", "system -", "system bundle",
    ])


def is_accessory(product_title: str, tags: list) -> bool:
    """Exclude controllers/accessories — loose and 'complete' controllers
    have essentially the same market value (CIB premium is minimal/noise)."""
    t = product_title.lower()
    if any(k in t for k in ["controller", "wiimote", "nunchuck", "gamepad",
                            "joystick", "memory card", "adapter", "cable",
                            "power supply", "ac adapter"]):
        return True
    if "category:accessory" in tags or "category:accessories" in tags:
        return True
    return False


def to_entry(p, loose, cib):
    return {
        "id": p["id"],
        "title": p["title"],
        "tags": p["tags"],
        "loose_id": loose["id"],
        "loose_price": float(loose["price"]),
        "loose_title": loose["title"],
        "loose_updated": loose["updatedAt"][:10],
        "cib_id": cib["id"],
        "cib_price": float(cib["price"]),
        "cib_title": cib["title"],
        "cib_updated": cib["updatedAt"][:10],
    }


def main():
    if not SHOP or not TOKEN:
        print("ERROR: credentials not set"); sys.exit(1)

    print("Scanning for broken CIB/Loose pricing...", flush=True)
    cursor = None
    total = 0
    multi = 0
    stuck = []       # CIB == Loose (within $0.50), excluding bundles
    inverted = []    # Loose > CIB (by > $0.50)

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
            if not loose or not cib:
                continue
            if is_bundle(p["title"]):
                continue
            if is_accessory(p["title"], p.get("tags", [])):
                continue

            lp = float(loose["price"])
            cp = float(cib["price"])
            diff = cp - lp

            if abs(diff) < 0.5:
                stuck.append(to_entry(p, loose, cib))
            elif diff < -0.5:
                inverted.append(to_entry(p, loose, cib))

        if total % 500 == 0:
            print(f"  scanned {total} | stuck={len(stuck)} | inverted={len(inverted)}", flush=True)
        if not pd["pageInfo"]["hasNextPage"]:
            break
        cursor = pd["pageInfo"]["endCursor"]

    combined = stuck + inverted

    print()
    print("=" * 60)
    print(f"  Total active products:            {total}")
    print(f"  Multi-variant retro games:        {multi}")
    print(f"  CIB == Loose (stuck, non-bundle): {len(stuck)}")
    print(f"  Loose > CIB (inverted):           {len(inverted)}")
    print(f"  Combined broken set:              {len(combined)}")
    print("=" * 60)

    # Back up any existing file
    out = PROJECT / "data" / "cib-equals-loose.json"
    if out.exists():
        backup = PROJECT / "data" / f"cib-equals-loose.prev.json"
        out.rename(backup)
        print(f"\nMoved previous file to {backup.name}")

    with open(out, "w") as f:
        json.dump(combined, f, indent=2)
    print(f"Wrote {len(combined)} entries to {out}")

    # Also dump the split views for inspection
    split_file = PROJECT / "data" / "cib-broken-detail.json"
    with open(split_file, "w") as f:
        json.dump({"stuck": stuck, "inverted": inverted}, f, indent=2)
    print(f"Wrote detail split to {split_file}")


if __name__ == "__main__":
    main()
