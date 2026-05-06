#!/usr/bin/env python3
"""Configure the 8-Bit Legacy Google Ads Shopping campaign end-to-end.

Target tree (post 2026-05-05 leakage incident — see
docs/eod-handoff-2026-05-05-ads-launch-and-leakage.md):

    ROOT (SUBDIVISION on product_item_id)
    ├── product_item_id="shopify_ZZ_<p>_<v>" [UNIT, NEGATIVE]   × ~6,102 CIB offers
    ├── ... (one per CIB offer, loaded from data/cib-offer-ids.txt)
    └── product_item_id=else (SUBDIVISION on cl0)
        ├── cl0="over_50"  → $0.35
        ├── cl0="20_to_50" → $0.08
        └── cl0=else       → NEGATIVE

Why item_id negatives instead of cl3 metafield: the Shopify G&Y app does NOT
propagate variant-level metafields to MC. Item ID exclusion bypasses the broken
propagation entirely.

Why no cl2 layer: cl2 was set 2026-05-05 morning at product level but barely
propagated (0% after 8h, 2/6194 visible). It was blocking serving entirely.
Pokemon / console / accessory exclusion is handled at MC level via product-level
mm-google-shopping.excluded_destination metafield (which DOES propagate).

Idempotent: re-running with the same CIB list is a no-op (or only diff-syncs
new/removed items). Full rebuild only triggers when structural skeleton drifts
or --rebuild-from-scratch is passed.
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / "config" / ".env")

DEV_TOKEN = os.environ["GOOGLE_ADS_DEVELOPER_TOKEN"]
CLIENT_ID = os.environ["GOOGLE_ADS_CLIENT_ID"]
CLIENT_SECRET = os.environ["GOOGLE_ADS_CLIENT_SECRET"]
REFRESH_TOKEN = os.environ["GOOGLE_ADS_REFRESH_TOKEN"]
CUSTOMER_ID = os.environ["GOOGLE_ADS_CUSTOMER_ID"].replace("-", "")
LOGIN_CUSTOMER_ID = os.environ.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID", "").replace("-", "")

API_VERSION = "v21"
BASE = f"https://googleads.googleapis.com/{API_VERSION}/customers/{CUSTOMER_ID}"

TARGET_NAME = "8BL-Shopping-Games"
DEFAULT_BUDGET_MICROS = 20_000_000  # $20.00/day default
NEGATIVES_CSV = ROOT / "data" / "negative-keywords-google-ads-import-v2.csv"
CIB_LIST_DEFAULT = ROOT / "data" / "cib-offer-ids.txt"

BID_OVER_50_MICROS = 350_000    # $0.35
BID_20_TO_50_MICROS = 80_000    # $0.08

# Item ID negative tree node count safety guard (Google's hard limit is 20k)
MAX_TREE_NODES = 18_000


def die(msg: str) -> None:
    print(f"FATAL: {msg}", file=sys.stderr)
    sys.exit(2)


def get_token() -> str:
    r = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "refresh_token": REFRESH_TOKEN,
            "grant_type": "refresh_token",
        },
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def api(method: str, path: str, token: str, body: dict | None = None) -> dict:
    headers = {
        "Authorization": f"Bearer {token}",
        "developer-token": DEV_TOKEN,
        "Content-Type": "application/json",
    }
    if LOGIN_CUSTOMER_ID:
        headers["login-customer-id"] = LOGIN_CUSTOMER_ID
    r = requests.request(method, f"{BASE}{path}", headers=headers, json=body, timeout=120)
    if r.status_code >= 400:
        try:
            err = r.json()
            for detail in err[0]["error"]["details"] if isinstance(err, list) else err.get("error", {}).get("details", []):
                for e in detail.get("errors", []):
                    print(f"  API ERROR: {e.get('message', '')} code={e.get('errorCode', {})}", file=sys.stderr)
        except Exception:
            pass
        r.raise_for_status()
    return r.json() if r.text else {}


def search(query: str, token: str) -> list[dict]:
    resp = api("POST", "/googleAds:searchStream", token, {"query": query})
    out: list[dict] = []
    for chunk in resp if isinstance(resp, list) else [resp]:
        out.extend(chunk.get("results", []))
    return out


# ───── Step helpers ─────

def find_campaign(token: str) -> dict | None:
    rows = search(
        "SELECT campaign.id, campaign.name, campaign.status, campaign.resource_name, "
        "campaign_budget.resource_name, campaign_budget.amount_micros "
        "FROM campaign WHERE campaign.name IN ('8BL-Shopping-All', '8BL-Shopping-Games')",
        token,
    )
    if not rows:
        return None
    r = rows[0]
    return {
        "id": r["campaign"]["id"],
        "name": r["campaign"]["name"],
        "status": r["campaign"]["status"],
        "resource_name": r["campaign"]["resourceName"],
        "budget_resource": r["campaignBudget"]["resourceName"],
        "budget_micros": int(r["campaignBudget"]["amountMicros"]),
    }


def find_ad_group(campaign_resource: str, token: str) -> dict | None:
    rows = search(
        f"SELECT ad_group.id, ad_group.name, ad_group.resource_name "
        f"FROM ad_group WHERE ad_group.campaign = '{campaign_resource}' LIMIT 1",
        token,
    )
    if not rows:
        return None
    a = rows[0]["adGroup"]
    return {"id": a["id"], "name": a["name"], "resource_name": a["resourceName"]}


def get_listing_groups(ad_group_id: str, token: str) -> list[dict]:
    """Return full listing-group criteria with parent + caseValue for diff logic."""
    rows = search(
        f"SELECT ad_group_criterion.criterion_id, "
        f"ad_group_criterion.listing_group.type, "
        f"ad_group_criterion.listing_group.case_value.product_custom_attribute.index, "
        f"ad_group_criterion.listing_group.case_value.product_custom_attribute.value, "
        f"ad_group_criterion.listing_group.case_value.product_item_id.value, "
        f"ad_group_criterion.listing_group.parent_ad_group_criterion, "
        f"ad_group_criterion.cpc_bid_micros, "
        f"ad_group_criterion.negative, "
        f"ad_group_criterion.resource_name "
        f"FROM ad_group_criterion WHERE ad_group_criterion.type = LISTING_GROUP "
        f"AND ad_group.id = {ad_group_id}",
        token,
    )
    return [r["adGroupCriterion"] for r in rows]


def get_negative_count(campaign_resource: str, token: str) -> int:
    rows = search(
        f"SELECT campaign_criterion.criterion_id "
        f"FROM campaign_criterion WHERE campaign_criterion.type = KEYWORD "
        f"AND campaign_criterion.negative = true "
        f"AND campaign_criterion.campaign = '{campaign_resource}'",
        token,
    )
    return len(rows)


# ───── CIB list loader ─────

def load_cib_offer_ids(path: Path) -> list[str]:
    if not path.exists():
        die(f"CIB list not found: {path}\n  Run: python3 scripts/list_cib_offer_ids.py")
    ids = sorted({line.strip() for line in path.read_text().splitlines() if line.strip()})
    if not ids:
        die(f"CIB list is empty: {path}")
    if len(ids) > MAX_TREE_NODES:
        die(f"CIB list ({len(ids)}) exceeds tree-size guard ({MAX_TREE_NODES}); investigate")
    return ids


# ───── Mutations ─────

def rename_campaign(campaign_resource: str, new_name: str, token: str, dry: bool) -> None:
    if dry:
        print(f"  [dry] would rename to '{new_name}'")
        return
    api("POST", "/campaigns:mutate", token, {
        "operations": [{
            "update": {"resourceName": campaign_resource, "name": new_name},
            "updateMask": "name",
        }],
    })
    print(f"  renamed → {new_name}")


def update_budget(budget_resource: str, amount_micros: int, token: str, dry: bool) -> None:
    if dry:
        print(f"  [dry] would update budget to ${amount_micros / 1_000_000:.2f}/day")
        return
    api("POST", "/campaignBudgets:mutate", token, {
        "operations": [{
            "update": {"resourceName": budget_resource, "amountMicros": str(amount_micros)},
            "updateMask": "amount_micros",
        }],
    })
    print(f"  budget → ${amount_micros / 1_000_000:.2f}/day")


# ───── Listing tree ─────

def _classify_node(node: dict) -> tuple[str, str]:
    """Identify a listing-group node by a stable key tuple.

    Returns one of:
      ("root",)
      ("item_id_neg", "<offer_id>")    — negative UNIT for product_item_id
      ("item_id_else",)                — SUBDIVISION on item_id "OTHERS" (no value)
      ("cl0_over_50",)                 — UNIT bid cl0=over_50
      ("cl0_20_to_50",)                — UNIT bid cl0=20_to_50
      ("cl0_else",)                    — UNIT negative cl0 OTHERS
      ("unknown", <repr>)              — anything else (full-rebuild trigger)
    """
    lg = node.get("listingGroup", {})
    case = lg.get("caseValue", {})
    parent = lg.get("parentAdGroupCriterion")

    if not case and not parent:
        return ("root",)
    if "productItemId" in case:
        v = case["productItemId"].get("value", "")
        if v == "":
            return ("item_id_else",)
        if node.get("negative"):
            return ("item_id_neg", v)
        return ("unknown", f"non-negative item_id {v}")
    if "productCustomAttribute" in case:
        pca = case["productCustomAttribute"]
        idx = pca.get("index")
        val = pca.get("value", "")
        if idx == "INDEX0":
            if val == "over_50":
                return ("cl0_over_50",)
            if val == "20_to_50":
                return ("cl0_20_to_50",)
            if val == "":
                return ("cl0_else",)
        return ("unknown", f"unexpected pca index={idx} val={val}")
    return ("unknown", repr(case))


def _structural_matches(existing: list[dict]) -> dict | None:
    """Return a dict mapping kind-key → node iff the tree has the expected structural skeleton.
    Returns None if the structure is wrong (caller should full-rebuild)."""
    by_kind: dict[tuple, list[dict]] = {}
    for n in existing:
        k = _classify_node(n)
        by_kind.setdefault(k, []).append(n)

    required_singletons = [
        ("root",),
        ("item_id_else",),
        ("cl0_over_50",),
        ("cl0_20_to_50",),
        ("cl0_else",),
    ]
    for k in required_singletons:
        if len(by_kind.get(k, [])) != 1:
            return None
    # Tolerate any number of item_id_neg nodes (we'll diff). Reject any "unknown".
    for k in by_kind:
        if k[0] == "unknown":
            return None
    return {k: nodes[0] for k, nodes in by_kind.items() if k[0] != "item_id_neg"}


def _existing_item_id_negatives(existing: list[dict]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for n in existing:
        k = _classify_node(n)
        if k[0] == "item_id_neg":
            out[k[1]] = n
    return out


def _batched_mutate(operations: list[dict], path: str, token: str, batch_size: int = 1000,
                    partial_failure: bool = False) -> int:
    """POST mutations in batches. Returns total ops attempted."""
    total = 0
    for i in range(0, len(operations), batch_size):
        batch = operations[i:i + batch_size]
        body: dict = {"operations": batch}
        if partial_failure:
            body["partialFailure"] = True
        api("POST", path, token, body)
        total += len(batch)
        time.sleep(0.4)  # rate courtesy
    return total


def rebuild_listing_tree(ad_group_id: str, ad_group_resource: str,
                         existing: list[dict], cib_offer_ids: list[str],
                         token: str, dry: bool, force_rebuild: bool) -> None:
    structural = None if force_rebuild else _structural_matches(existing)

    if structural:
        # Fast path: structure is right. Sync item_id negatives + bids only.
        existing_negs = _existing_item_id_negatives(existing)
        desired = set(cib_offer_ids)
        existing_set = set(existing_negs.keys())
        to_add = sorted(desired - existing_set)
        to_remove = sorted(existing_set - desired)

        # Bid drift check
        bid_updates = []
        for kind, target in [
            (("cl0_over_50",), BID_OVER_50_MICROS),
            (("cl0_20_to_50",), BID_20_TO_50_MICROS),
        ]:
            n = structural[kind]
            current = n.get("cpcBidMicros")
            if current != str(target):
                bid_updates.append({
                    "update": {"resourceName": n["resourceName"], "cpcBidMicros": str(target)},
                    "updateMask": "cpc_bid_micros",
                })

        print(f"  diff: +{len(to_add)} negatives, -{len(to_remove)} negatives, "
              f"{len(bid_updates)} bid update(s)")
        if dry:
            print(f"  [dry] would apply diff above")
            return

        # Apply removals first (no parent dependency change)
        if to_remove:
            ops = [{"remove": existing_negs[oid]["resourceName"]} for oid in to_remove]
            n_done = _batched_mutate(ops, "/adGroupCriteria:mutate", token,
                                     batch_size=1000, partial_failure=True)
            print(f"  removed {n_done} stale item_id negatives")
        if bid_updates:
            api("POST", "/adGroupCriteria:mutate", token, {"operations": bid_updates})
            print(f"  bid-updated {len(bid_updates)} UNIT(s)")
        if to_add:
            root_resource = structural[("root",)]["resourceName"]
            ops = [{
                "create": {
                    "adGroup": ad_group_resource,
                    "status": "ENABLED",
                    "negative": True,
                    "listingGroup": {
                        "type": "UNIT",
                        "caseValue": {"productItemId": {"value": oid}},
                        "parentAdGroupCriterion": root_resource,
                    },
                }
            } for oid in to_add]
            n_done = _batched_mutate(ops, "/adGroupCriteria:mutate", token,
                                     batch_size=1000, partial_failure=True)
            print(f"  created {n_done} new item_id negatives")
        return

    # Slow path: structural mismatch (or force_rebuild). Full nuke + create.
    print(f"  structural mismatch (or --rebuild-from-scratch): full rebuild")
    print(f"  removing {len(existing)} existing nodes, creating {5 + len(cib_offer_ids)} new")
    if dry:
        print(f"  [dry] would full-rebuild listing tree")
        return

    # Step 1: atomic remove-all + create the 5 structural nodes.
    def tmp(n: int) -> str:
        return f"customers/{CUSTOMER_ID}/adGroupCriteria/{ad_group_id}~-{n}"

    structural_ops: list[dict] = []
    for g in sorted(existing, key=lambda x: int(x.get("criterionId", 0)), reverse=True):
        structural_ops.append({"remove": g["resourceName"]})

    # 1: ROOT (subdivides on product_item_id)
    structural_ops.append({"create": {
        "resourceName": tmp(1),
        "adGroup": ad_group_resource,
        "status": "ENABLED",
        "listingGroup": {"type": "SUBDIVISION"},
    }})
    # 2: product_item_id=else (subdivision on cl0)
    structural_ops.append({"create": {
        "resourceName": tmp(2),
        "adGroup": ad_group_resource,
        "status": "ENABLED",
        "listingGroup": {
            "type": "SUBDIVISION",
            "caseValue": {"productItemId": {}},
            "parentAdGroupCriterion": tmp(1),
        },
    }})
    # 3: cl0=over_50 (UNIT bid)
    structural_ops.append({"create": {
        "resourceName": tmp(3),
        "adGroup": ad_group_resource,
        "status": "ENABLED",
        "cpcBidMicros": str(BID_OVER_50_MICROS),
        "listingGroup": {
            "type": "UNIT",
            "caseValue": {"productCustomAttribute": {"index": "INDEX0", "value": "over_50"}},
            "parentAdGroupCriterion": tmp(2),
        },
    }})
    # 4: cl0=20_to_50 (UNIT bid)
    structural_ops.append({"create": {
        "resourceName": tmp(4),
        "adGroup": ad_group_resource,
        "status": "ENABLED",
        "cpcBidMicros": str(BID_20_TO_50_MICROS),
        "listingGroup": {
            "type": "UNIT",
            "caseValue": {"productCustomAttribute": {"index": "INDEX0", "value": "20_to_50"}},
            "parentAdGroupCriterion": tmp(2),
        },
    }})
    # 5: cl0=else (UNIT negative)
    structural_ops.append({"create": {
        "resourceName": tmp(5),
        "adGroup": ad_group_resource,
        "status": "ENABLED",
        "negative": True,
        "listingGroup": {
            "type": "UNIT",
            "caseValue": {"productCustomAttribute": {"index": "INDEX0"}},
            "parentAdGroupCriterion": tmp(2),
        },
    }})

    api("POST", "/adGroupCriteria:mutate", token, {"operations": structural_ops})
    print(f"  structural skeleton: removed {len(existing)} + created 5 nodes")

    # Step 2: re-fetch root resource_name (server-assigned), then batch create item_id negatives
    refreshed = get_listing_groups(ad_group_id, token)
    by_kind = {_classify_node(n): n for n in refreshed if _classify_node(n)[0] != "item_id_neg"}
    root_resource = by_kind[("root",)]["resourceName"]

    cib_ops = [{
        "create": {
            "adGroup": ad_group_resource,
            "status": "ENABLED",
            "negative": True,
            "listingGroup": {
                "type": "UNIT",
                "caseValue": {"productItemId": {"value": oid}},
                "parentAdGroupCriterion": root_resource,
            },
        }
    } for oid in cib_offer_ids]

    n_done = _batched_mutate(cib_ops, "/adGroupCriteria:mutate", token,
                             batch_size=1000, partial_failure=True)
    print(f"  created {n_done} item_id negative UNITs (CIB exclusion)")


def import_negatives(campaign_resource: str, already_count: int, token: str, dry: bool) -> None:
    if not NEGATIVES_CSV.exists():
        die(f"negatives CSV not found: {NEGATIVES_CSV}")

    rows: list[dict] = []
    with NEGATIVES_CSV.open() as f:
        for row in csv.DictReader(f):
            kw = row.get("Keyword", "").strip().strip('"')
            mt = row.get("Match Type", "Phrase").strip()
            if kw:
                rows.append({
                    "text": kw,
                    "matchType": {"Phrase": "PHRASE", "Exact": "EXACT", "Broad": "BROAD"}.get(mt, "PHRASE"),
                })

    if already_count >= len(rows) * 0.9:
        print(f"  {already_count} negatives already on campaign ≥ 90% of {len(rows)} in CSV — skip")
        return

    if already_count > 0:
        print(f"  WARN: campaign has {already_count} negatives, CSV has {len(rows)} — will add more")

    if dry:
        print(f"  [dry] would add {len(rows)} negative keywords")
        return

    added = 0
    for i in range(0, len(rows), 50):
        batch = rows[i:i + 50]
        ops = [
            {"create": {
                "campaign": campaign_resource,
                "negative": True,
                "keyword": {"text": kw["text"], "matchType": kw["matchType"]},
            }}
            for kw in batch
        ]
        try:
            api("POST", "/campaignCriteria:mutate", token, {"operations": ops})
            added += len(batch)
        except requests.HTTPError:
            print(f"  WARN batch {i}-{i+len(batch)} failed — continuing")
        time.sleep(0.4)
    print(f"  added {added}/{len(rows)} negative keywords")


# ───── Main ─────

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="show what would change")
    ap.add_argument("--skip-negatives", action="store_true", help="don't touch negative keywords")
    ap.add_argument("--skip-tree", action="store_true", help="don't touch listing-group tree")
    ap.add_argument("--rebuild-from-scratch", action="store_true",
                    help="full-rebuild the listing tree even if structure looks right")
    ap.add_argument("--budget-micros", type=int, default=DEFAULT_BUDGET_MICROS,
                    help=f"daily budget in micros (default ${DEFAULT_BUDGET_MICROS/1_000_000:.2f}/day)")
    ap.add_argument("--cib-list", default=str(CIB_LIST_DEFAULT),
                    help=f"path to CIB offer ID list (default {CIB_LIST_DEFAULT})")
    args = ap.parse_args()

    print(f"Customer: {CUSTOMER_ID} (via MCC {LOGIN_CUSTOMER_ID or '-'})")
    print(f"Mode: {'DRY-RUN' if args.dry_run else 'LIVE'}")
    print(f"Budget: ${args.budget_micros/1_000_000:.2f}/day")

    cib_ids = load_cib_offer_ids(Path(args.cib_list))
    print(f"CIB list: {len(cib_ids)} offer IDs from {args.cib_list}")

    tok = get_token()

    camp = find_campaign(tok)
    if not camp:
        die("No existing campaign named 8BL-Shopping-All or 8BL-Shopping-Games found.")
    print(f"\n[campaign] id={camp['id']} name={camp['name']} status={camp['status']} "
          f"budget=${camp['budget_micros']/1_000_000:.2f}")

    ag = find_ad_group(camp["resource_name"], tok)
    if not ag:
        die(f"No ad group found under campaign {camp['id']}.")
    print(f"[ad_group] id={ag['id']} name={ag['name']}")

    neg_count = get_negative_count(camp["resource_name"], tok)
    lg = get_listing_groups(ag["id"], tok)
    print(f"[state] negatives={neg_count}  listing_groups={len(lg)}")

    print("\n--- STEP 1: rename campaign ---")
    if camp["name"] == TARGET_NAME:
        print(f"  already named '{TARGET_NAME}' — skip")
    else:
        rename_campaign(camp["resource_name"], TARGET_NAME, tok, args.dry_run)

    print("\n--- STEP 2: update budget ---")
    if camp["budget_micros"] == args.budget_micros:
        print(f"  already ${args.budget_micros/1_000_000:.2f}/day — skip")
    else:
        update_budget(camp["budget_resource"], args.budget_micros, tok, args.dry_run)

    print("\n--- STEP 3: rebuild listing-group tree (item_id negatives + cl2/cl0) ---")
    if args.skip_tree:
        print("  --skip-tree — leaving tree untouched")
    else:
        rebuild_listing_tree(ag["id"], ag["resource_name"], lg, cib_ids,
                             tok, args.dry_run, args.rebuild_from_scratch)

    print("\n--- STEP 4: import negative keywords ---")
    if args.skip_negatives:
        print("  --skip-negatives — leaving negatives untouched")
    else:
        import_negatives(camp["resource_name"], neg_count, tok, args.dry_run)

    print("\n--- Done. Campaign remains PAUSED. Flip to ENABLED only after verify_cib_exclusion.py passes. ---")
    return 0


if __name__ == "__main__":
    sys.exit(main())
