#!/usr/bin/env python3
"""Produce the canonical list of CIB Merchant Center offer IDs, sorted + deduped.

Source of truth for the Google Ads listing-tree negative item_id criteria built by
ads_launch.py. Bypasses Shopify metafield → MC propagation entirely (which is
unreliable per 2026-05-05 measurements — see reference_gy_metafield_propagation.md).

Strategy:
  Primary source = Shopify GraphQL (every active product tagged category:game,
                   scan variants, pick CIB by title via _is_cib_variant).
  Cross-check    = Google Ads shopping_product view ('%Complete (CIB)%' titles).

Outputs:
  data/cib-offer-ids.txt  — newline-delimited, sorted, deduped offer IDs
  stdout                  — counts + Shopify-only / MC-only deltas

Re-runnable any time. Idempotent.
"""

from __future__ import annotations

import argparse
import os
import sys
import warnings
from pathlib import Path

# Suppress noisy googleads/urllib3 warnings on this machine's Python 3.9
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

# Reuse battle-tested helpers from generate-cib-exclusion-feed.py
import importlib.util
spec = importlib.util.spec_from_file_location(
    "_cib_feed", ROOT / "scripts" / "generate-cib-exclusion-feed.py"
)
_cib_feed = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_cib_feed)

OUTPUT = ROOT / "data" / "cib-offer-ids.txt"


def shopify_cib_ids(limit: int | None = None) -> set[str]:
    products = _cib_feed._iter_game_products(limit=limit)
    rows = _cib_feed._collect_cib_item_ids(products)
    return {r["id"] for r in rows}


def mc_cib_ids() -> set[str]:
    """Cross-check via Google Ads shopping_product view."""
    from dotenv import load_dotenv
    load_dotenv(ROOT / "config" / ".env")
    from google.ads.googleads.client import GoogleAdsClient

    client = GoogleAdsClient.load_from_dict({
        "developer_token": os.environ["GOOGLE_ADS_DEVELOPER_TOKEN"],
        "client_id": os.environ["GOOGLE_ADS_CLIENT_ID"],
        "client_secret": os.environ["GOOGLE_ADS_CLIENT_SECRET"],
        "refresh_token": os.environ["GOOGLE_ADS_REFRESH_TOKEN"],
        "login_customer_id": os.environ["GOOGLE_ADS_LOGIN_CUSTOMER_ID"],
        "use_proto_plus": True,
    })
    service = client.get_service("GoogleAdsService")
    cust = os.environ.get("GOOGLE_ADS_CUSTOMER_ID", "8222102291")
    rows = service.search(
        customer_id=cust,
        query=(
            "SELECT shopping_product.item_id, shopping_product.title "
            "FROM shopping_product "
            "WHERE shopping_product.title LIKE '%Complete (CIB)%'"
        ),
    )
    return {r.shopping_product.item_id for r in rows}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int, help="Test mode: scan only N Shopify products")
    p.add_argument("--skip-mc-check", action="store_true",
                   help="Skip MC cross-check (faster, less safe)")
    p.add_argument("--output", default=str(OUTPUT))
    args = p.parse_args()

    print("[1/3] Scanning Shopify for CIB variants…", file=sys.stderr)
    shop = shopify_cib_ids(limit=args.limit)
    print(f"      Shopify CIB count: {len(shop)}", file=sys.stderr)

    if not args.skip_mc_check:
        print("[2/3] Cross-checking against Merchant Center shopping_product…",
              file=sys.stderr)
        mc = mc_cib_ids()
        print(f"      MC CIB count: {len(mc)}", file=sys.stderr)
        only_shop = shop - mc
        only_mc = mc - shop
        print(f"      Shopify-only (not yet in MC or never propagated): {len(only_shop)}",
              file=sys.stderr)
        print(f"      MC-only (Shopify scan missed — investigate if >0): {len(only_mc)}",
              file=sys.stderr)
        if only_mc:
            print(f"      Sample MC-only IDs: {list(only_mc)[:5]}", file=sys.stderr)
        # UNION: belt-and-suspenders. We want every CIB excluded — current and
        # eventually-propagating.
        ids = sorted(shop | mc)
    else:
        ids = sorted(shop)

    print(f"[3/3] Writing {len(ids)} offer IDs → {args.output}", file=sys.stderr)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(ids) + "\n")
    print(f"OK ({len(ids)} ids written)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
