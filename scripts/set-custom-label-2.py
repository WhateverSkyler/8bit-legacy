#!/usr/bin/env python3
"""Bulk-set mm-google-shopping.custom_label_2 metafield from category tags.

LAUNCH BLOCKER FIX (2026-05-05): The Google Ads campaign listing tree subdivides
on custom_label_2 == "game". Audit on 2026-05-05 revealed only 1/6,088 game
products had this metafield set — the rest got cl0 set on 2026-05-01 but cl2
was never touched. Without it, the campaign serves zero impressions because
nothing matches the listing tree.

This script mirrors force-mc-resync-metafields.py exactly except for the key.

Value derivation:
- tag "category:game"          → "game"          (the only one that matters
                                                  for the tree, but we set
                                                  the others for completeness)
- tag "category:pokemon_card"  → "pokemon_card"
- tag "category:console"       → "console"
- tag "category:accessory"     → "accessory"
- tag "category:sealed"        → "sealed"
- otherwise                    → "other"

Usage:
    python3 scripts/set-custom-label-2.py --dry-run
    python3 scripts/set-custom-label-2.py --execute
    python3 scripts/set-custom-label-2.py --status
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / "config" / ".env")
load_dotenv(ROOT / "dashboard" / ".env.local")

SHOPIFY_STORE = os.getenv("SHOPIFY_STORE_URL", "")
SHOPIFY_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN", "")
API_VERSION = "2024-10"
JSONL_PATH = Path("/tmp/set-cl2.jsonl")

MF_NAMESPACE = "mm-google-shopping"
MF_KEY = "custom_label_2"
MF_TYPE = "single_line_text_field"

CATEGORY_MAP = {
    "category:game": "game",
    "category:pokemon_card": "pokemon_card",
    "category:console": "console",
    "category:accessory": "accessory",
    "category:sealed": "sealed",
}


def gql(query: str, variables: dict | None = None) -> dict:
    if not SHOPIFY_STORE or not SHOPIFY_TOKEN:
        sys.exit("SHOPIFY_STORE_URL and SHOPIFY_ACCESS_TOKEN must be set")
    resp = requests.post(
        f"https://{SHOPIFY_STORE}/admin/api/{API_VERSION}/graphql.json",
        headers={"X-Shopify-Access-Token": SHOPIFY_TOKEN, "Content-Type": "application/json"},
        json={"query": query, "variables": variables or {}},
        timeout=120,
    )
    resp.raise_for_status()
    body = resp.json()
    if body.get("errors"):
        sys.exit(f"GraphQL errors: {json.dumps(body['errors'], indent=2)}")
    return body


def derive_label(tags: list[str]) -> str:
    for t in tags:
        if t in CATEGORY_MAP:
            return CATEGORY_MAP[t]
    return "other"


def enumerate_products() -> list[tuple[str, str]]:
    QUERY = """
    query Get($cursor: String) {
      products(first: 250, after: $cursor, query: "status:active") {
        edges { node { id tags } }
        pageInfo { hasNextPage endCursor }
      }
    }
    """
    out: list[tuple[str, str]] = []
    cursor = None
    page = 0
    while True:
        page += 1
        data = gql(QUERY, {"cursor": cursor})
        edges = data["data"]["products"]["edges"]
        for e in edges:
            n = e["node"]
            label = derive_label(n.get("tags", []))
            out.append((n["id"], label))
        info = data["data"]["products"]["pageInfo"]
        if not info["hasNextPage"]:
            break
        cursor = info["endCursor"]
        if page % 4 == 0:
            print(f"  page {page}: {len(out)} products collected so far", flush=True)
    return out


def write_jsonl(pairs: list[tuple[str, str]], path: Path) -> int:
    with path.open("w") as f:
        for gid, value in pairs:
            obj = {"metafields": [{
                "ownerId": gid,
                "namespace": MF_NAMESPACE,
                "key": MF_KEY,
                "type": MF_TYPE,
                "value": value,
            }]}
            f.write(json.dumps(obj) + "\n")
    return path.stat().st_size


def staged_upload(file_path: Path) -> str:
    STAGED = """
    mutation stagedUploadsCreate($input: [StagedUploadInput!]!) {
      stagedUploadsCreate(input: $input) {
        stagedTargets { url parameters { name value } }
        userErrors { field message }
      }
    }
    """
    data = gql(STAGED, {"input": [{
        "filename": file_path.name,
        "mimeType": "text/jsonl",
        "httpMethod": "POST",
        "resource": "BULK_MUTATION_VARIABLES",
    }]})
    res = data["data"]["stagedUploadsCreate"]
    if res.get("userErrors"):
        sys.exit(f"stagedUploadsCreate errors: {res['userErrors']}")
    target = res["stagedTargets"][0]
    fields = [(p["name"], (None, p["value"])) for p in target["parameters"]]
    with file_path.open("rb") as f:
        fields.append(("file", (file_path.name, f, "text/jsonl")))
        resp = requests.post(target["url"], files=fields, timeout=300)
    if resp.status_code >= 300:
        sys.exit(f"S3 upload failed {resp.status_code}: {resp.text[:500]}")
    key = next((p["value"] for p in target["parameters"] if p["name"] == "key"), None)
    if not key:
        sys.exit("S3 staged upload returned no `key` parameter")
    return key


METAFIELDS_SET = """
mutation call($metafields: [MetafieldsSetInput!]!) {
  metafieldsSet(metafields: $metafields) {
    metafields { id key namespace value }
    userErrors { field message code }
  }
}
""".strip()


def submit_bulk_op(staged_path: str) -> dict:
    BULK_RUN = """
    mutation bulkOperationRunMutation($mutation: String!, $stagedUploadPath: String!) {
      bulkOperationRunMutation(mutation: $mutation, stagedUploadPath: $stagedUploadPath) {
        bulkOperation { id status createdAt }
        userErrors { field message code }
      }
    }
    """
    data = gql(BULK_RUN, {"mutation": METAFIELDS_SET, "stagedUploadPath": staged_path})
    res = data["data"]["bulkOperationRunMutation"]
    if res.get("userErrors"):
        sys.exit(f"bulkOperationRunMutation errors: {res['userErrors']}")
    return res["bulkOperation"]


def get_current_bulk_op() -> dict | None:
    QUERY = """
    {
      currentBulkOperation(type: MUTATION) {
        id status errorCode createdAt completedAt objectCount fileSize url partialDataUrl
      }
    }
    """
    return gql(QUERY)["data"]["currentBulkOperation"]


def poll_until_done(timeout_sec: int = 7200) -> dict:
    start = time.time()
    last_count = 0
    while time.time() - start < timeout_sec:
        op = get_current_bulk_op()
        if not op:
            return {"status": "VANISHED"}
        status = op["status"]
        count = int(op.get("objectCount") or 0)
        delta = count - last_count
        elapsed = int(time.time() - start)
        print(f"  [t+{elapsed:>4}s] status={status} processed={count} (Δ={delta})", flush=True)
        last_count = count
        if status in ("COMPLETED", "FAILED", "CANCELED", "EXPIRED"):
            return op
        time.sleep(20)
    return {"status": "TIMEOUT", "objectCount": last_count}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--execute", action="store_true")
    g.add_argument("--status", action="store_true")
    args = parser.parse_args()

    if args.status:
        op = get_current_bulk_op()
        print(json.dumps(op, indent=2) if op else "No current bulk operation.")
        return 0

    print("=== set-custom-label-2 ===")
    print(f"Metafield: {MF_NAMESPACE}.{MF_KEY} (type {MF_TYPE})")
    print(f"Mode: {'EXECUTE' if args.execute else 'DRY RUN'}\n")

    print("Step 1: Enumerate ACTIVE products + derive label values")
    pairs = enumerate_products()
    print(f"  → {len(pairs)} products\n")
    if not pairs:
        sys.exit("No ACTIVE products found")

    dist = Counter(v for _, v in pairs)
    print("  Label distribution:")
    for v, c in sorted(dist.items(), key=lambda x: -x[1]):
        print(f"    {v:<15} {c:>5}")
    print()

    if args.dry_run:
        print("[DRY RUN] would write JSONL + run bulk operation. Stopping.")
        return 0

    existing = get_current_bulk_op()
    if existing and existing["status"] in ("CREATED", "RUNNING"):
        sys.exit(f"A bulk op is already RUNNING ({existing['id']}). Wait for it to finish.")

    print(f"Step 2: Write JSONL → {JSONL_PATH}")
    n_bytes = write_jsonl(pairs, JSONL_PATH)
    print(f"  → {n_bytes:,} bytes\n")

    print("Step 3: Staged upload to Shopify S3")
    key = staged_upload(JSONL_PATH)
    print(f"  → staged key: {key}\n")

    print("Step 4: Submit bulkOperationRunMutation (metafieldsSet)")
    op = submit_bulk_op(key)
    print(f"  → operation ID: {op['id']}, status: {op['status']}\n")

    print("Step 5: Poll until completion")
    final = poll_until_done()

    print("\n=== DONE ===")
    print(json.dumps(final, indent=2))
    return 0 if final.get("status") == "COMPLETED" else 1


if __name__ == "__main__":
    sys.exit(main())
