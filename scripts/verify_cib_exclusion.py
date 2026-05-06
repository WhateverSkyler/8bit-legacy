#!/usr/bin/env python3
"""Pre-flight verification that the Google Ads listing tree will not serve CIB variants.

This is the gate that should have existed before today's $17.66 leak. Three checks:

  1. Tree integrity — pull every item_id negative criterion from the campaign's ad
     group; the set must equal data/cib-offer-ids.txt. Every match must have
     negative=true.

  2. MC cross-check — for every CIB row currently visible in the Google Ads
     `shopping_product` view, confirm the offer_id is in our negative set. Any CIB
     in MC that's NOT in our negatives is a leakage path.

  3. Game-Only sanity — confirm at least 100 non-CIB rows are visible in
     shopping_product with cl0 ∈ {over_50, 20_to_50}, so we know we haven't
     over-excluded everything.

Exit code:
  0 → all three pass; safe to enable
  1 → at least one check failed; do NOT enable
  2 → environment / API error
"""

from __future__ import annotations

import os
import random
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent.parent
CIB_LIST = ROOT / "data" / "cib-offer-ids.txt"
AD_GROUP_ID = "202385540384"
CAMPAIGN_RESOURCE = "customers/8222102291/campaigns/23766662629"


def fatal(msg: str) -> None:
    print(f"FATAL: {msg}", file=sys.stderr)
    sys.exit(2)


def load_client():
    from dotenv import load_dotenv
    load_dotenv(ROOT / "config" / ".env")
    from google.ads.googleads.client import GoogleAdsClient
    return GoogleAdsClient.load_from_dict({
        "developer_token": os.environ["GOOGLE_ADS_DEVELOPER_TOKEN"],
        "client_id": os.environ["GOOGLE_ADS_CLIENT_ID"],
        "client_secret": os.environ["GOOGLE_ADS_CLIENT_SECRET"],
        "refresh_token": os.environ["GOOGLE_ADS_REFRESH_TOKEN"],
        "login_customer_id": os.environ["GOOGLE_ADS_LOGIN_CUSTOMER_ID"],
        "use_proto_plus": True,
    })


def load_desired() -> set[str]:
    if not CIB_LIST.exists():
        fatal(f"CIB list not found: {CIB_LIST} — run scripts/list_cib_offer_ids.py first")
    return {line.strip() for line in CIB_LIST.read_text().splitlines() if line.strip()}


def check1_tree_integrity(service, customer_id: str, desired: set[str]) -> bool:
    print("\n[CHECK 1] Tree integrity — every CIB offer ID has a negative criterion in the ad group")
    rows = list(service.search(
        customer_id=customer_id,
        query=(
            "SELECT ad_group_criterion.criterion_id, "
            "ad_group_criterion.listing_group.case_value.product_item_id.value, "
            "ad_group_criterion.negative "
            "FROM ad_group_criterion "
            f"WHERE ad_group_criterion.type = LISTING_GROUP "
            f"AND ad_group.id = {AD_GROUP_ID}"
        ),
    ))

    have_negatives: set[str] = set()
    bad_positives: list[str] = []
    for r in rows:
        v = r.ad_group_criterion.listing_group.case_value.product_item_id.value
        if not v:
            continue  # skip non-item_id nodes
        if r.ad_group_criterion.negative:
            have_negatives.add(v)
        else:
            bad_positives.append(v)

    missing = desired - have_negatives
    extra = have_negatives - desired

    print(f"  desired CIB negatives: {len(desired)}")
    print(f"  found CIB negatives:   {len(have_negatives)}")
    if bad_positives:
        print(f"  ✗ FAIL — {len(bad_positives)} item_id criteria are NOT negative (would serve!): "
              f"{bad_positives[:5]}")
        return False
    if missing:
        print(f"  ✗ FAIL — {len(missing)} desired offer IDs missing from tree (would leak): "
              f"{sorted(missing)[:5]}")
        return False
    if extra:
        print(f"  ⚠ WARN — {len(extra)} extra negatives in tree not in desired list: "
              f"{sorted(extra)[:5]} (not blocking; they're stricter than desired)")
    print("  ✓ PASS")
    return True


def check2_mc_crosscheck(service, customer_id: str, desired: set[str]) -> bool:
    print("\n[CHECK 2] MC cross-check — every CIB visible in shopping_product is in our negative set")
    rows = list(service.search(
        customer_id=customer_id,
        query=(
            "SELECT shopping_product.item_id, shopping_product.title "
            "FROM shopping_product "
            "WHERE shopping_product.title LIKE '%Complete (CIB)%'"
        ),
    ))
    mc_cib_ids = [(r.shopping_product.item_id, r.shopping_product.title) for r in rows]
    print(f"  CIBs in MC shopping_product: {len(mc_cib_ids)}")

    leaks = [(oid, title) for oid, title in mc_cib_ids if oid not in desired]
    if leaks:
        print(f"  ✗ FAIL — {len(leaks)} CIB offers in MC are NOT in our negative set:")
        for oid, title in leaks[:5]:
            print(f"     {oid}  {title[:60]}")
        return False

    # Spot-check 20 random ones for human-readable confirmation
    sample = random.sample(mc_cib_ids, min(20, len(mc_cib_ids)))
    print(f"  spot-check (20 random CIBs all in negatives):")
    for oid, title in sample[:5]:
        print(f"     ✓ {oid}  {title[:55]}")
    print("  ✓ PASS")
    return True


def check3_game_only_sanity(service, customer_id: str) -> bool:
    print("\n[CHECK 3] Game-Only sanity — non-CIB inventory exists in target tiers")
    rows = list(service.search(
        customer_id=customer_id,
        query=(
            "SELECT shopping_product.item_id, shopping_product.title, "
            "shopping_product.custom_attribute0 "
            "FROM shopping_product "
            "WHERE shopping_product.title NOT LIKE '%Complete (CIB)%' "
            "AND shopping_product.title NOT LIKE '%Loose%' "
            "AND shopping_product.custom_attribute0 IN ('over_50', '20_to_50')"
        ),
    ))
    print(f"  Game-Only / non-CIB / cl0=tiered: {len(rows)}")
    if len(rows) < 100:
        print(f"  ✗ FAIL — fewer than 100 Game-Only offers visible. Tree may be over-excluding "
              f"or cl0 propagation hasn't completed. Investigate.")
        return False
    sample = random.sample(rows, 5)
    print(f"  sample:")
    for r in sample:
        sp = r.shopping_product
        print(f"     {sp.item_id}  cl0={sp.custom_attribute0}  {sp.title[:55]}")
    print("  ✓ PASS")
    return True


def main() -> int:
    desired = load_desired()
    print(f"Loaded {len(desired)} desired CIB offer IDs from {CIB_LIST}")

    client = load_client()
    service = client.get_service("GoogleAdsService")
    customer_id = os.environ.get("GOOGLE_ADS_CUSTOMER_ID", "8222102291").replace("-", "")

    results = [
        check1_tree_integrity(service, customer_id, desired),
        check2_mc_crosscheck(service, customer_id, desired),
        check3_game_only_sanity(service, customer_id),
    ]

    print()
    if all(results):
        print("=" * 60)
        print(" ALL 3 CHECKS PASSED — safe to enable campaign")
        print("=" * 60)
        return 0
    failed = [i + 1 for i, r in enumerate(results) if not r]
    print("=" * 60)
    print(f" {len(failed)} CHECK(S) FAILED: {failed} — do NOT enable campaign")
    print("=" * 60)
    return 1


if __name__ == "__main__":
    sys.exit(main())
