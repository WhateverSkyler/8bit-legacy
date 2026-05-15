#!/usr/bin/env python3
"""Rebuild ONLY the Google Ads listing tree's CIB item_id negatives.

Does NOT touch:
  - Campaign status (stays PAUSED)
  - Campaign budget
  - Negative keywords
  - Anything outside the ad group's listing tree

Reuses the rebuild_listing_tree function from ads_launch.py, but skips every
other step in main(). This is the safe path to complete the CIB exclusion
rebuild that was started 2026-05-05 and got blocked on Google Ads daily
mutation quota — without re-running any other ads_launch.py side effects.

Usage:
  python3 scripts/ads_rebuild_cib_tree.py                 # apply
  python3 scripts/ads_rebuild_cib_tree.py --dry-run       # preview only
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ads_launch import (  # noqa: E402
    find_ad_group,
    find_campaign,
    get_listing_groups,
    get_token,
    load_cib_offer_ids,
    rebuild_listing_tree,
)

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CIB_LIST = ROOT / "data" / "cib-offer-ids.txt"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cib-list", default=str(DEFAULT_CIB_LIST))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--rebuild-from-scratch", action="store_true",
                    help="Tear down tree and rebuild from zero (slower; needed if structure drifted)")
    args = ap.parse_args()

    cib_ids = load_cib_offer_ids(Path(args.cib_list))
    print(f"CIB list: {len(cib_ids)} offer IDs from {args.cib_list}")

    tok = get_token()
    camp = find_campaign(tok)
    if not camp:
        print("FATAL: no 8BL-Shopping campaign found", file=sys.stderr)
        return 1
    print(f"[campaign] id={camp['id']} status={camp['status']} (will NOT be modified)")

    ag = find_ad_group(camp["resource_name"], tok)
    if not ag:
        print(f"FATAL: no ad group under campaign {camp['id']}", file=sys.stderr)
        return 1
    print(f"[ad_group] id={ag['id']}")

    lg = get_listing_groups(ag["id"], tok)
    print(f"[state] listing_groups={len(lg)}")

    print("\n--- Rebuilding CIB item_id negatives in listing tree ---")
    rebuild_listing_tree(
        ag["id"], ag["resource_name"], lg, cib_ids,
        tok, args.dry_run, args.rebuild_from_scratch
    )

    print(f"\n--- Done. Campaign status is still {camp['status']} (untouched). ---")
    return 0


if __name__ == "__main__":
    sys.exit(main())
