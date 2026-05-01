#!/usr/bin/env python3
"""Force MC resync — phase 2: bulk-set mm-google-shopping.custom_label_0 metafield.

Backup forcing function for `force-mc-resync.py`. Use ONLY if the bulk tagsAdd
in phase 1 did not trigger Shopify's G&Y app to push products back to MC.

Hypothesis: the G&Y app's eligibility filter requires
mm-google-shopping.custom_label_X to be set. The 3 Ninjas Kick Back product
(the lone survivor of the 4/29 catalog prune) has these metafields set;
products without them got pruned. Setting custom_label_0 on every product
replicates that pattern at scale.

What this script sets:
- Namespace:  mm-google-shopping
- Key:        custom_label_0
- Type:       single_line_text_field
- Value:      derived from product tags
              - tag "price_tier:over_50"   → "over_50"
              - tag "price_tier:20_to_50"  → "20_to_50"
              - tag "price_tier:under_20"  → "under_20"
              - no price_tier tag          → "synced"  (catch-all)
- Owner:      product-level (not variant)

Properties:
- IDEMPOTENT — metafieldsSet replaces value, re-running is a no-op if values match.
- ADDITIVE — does NOT touch any other metafield, tag, price, status, etc.
- REVERSIBLE — can be removed via metafieldsDelete in a future script.
- SERVER-SIDE — bulkOperationRunMutation runs on Shopify; we just submit + poll.

Usage:
    python3 scripts/force-mc-resync-metafields.py --dry-run    # preview values
    python3 scripts/force-mc-resync-metafields.py --execute    # submit bulk op
    python3 scripts/force-mc-resync-metafields.py --status     # check op status
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / "config" / ".env")
load_dotenv(ROOT / "dashboard" / ".env.local")

SHOPIFY_STORE = os.getenv("SHOPIFY_STORE_URL", "")
SHOPIFY_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN", "")
API_VERSION = "2024-10"
JSONL_PATH = Path("/tmp/mc-resync-metafields.jsonl")

MF_NAMESPACE = "mm-google-shopping"
MF_KEY = "custom_label_0"
MF_TYPE = "single_line_text_field"


def gql(query: str, variables: dict | None = None) -> dict:
    if not SHOPIFY_STORE or not SHOPIFY_TOKEN:
        sys.exit("SHOPIFY_STORE_URL and SHOPIFY_ACCESS_TOKEN must be set")
    resp = requests.post(
        f"https://{SHOPIFY_STORE}/admin/api/{API_VERSION}/graphql.json",
        headers={
            "X-Shopify-Access-Token": SHOPIFY_TOKEN,
            "Content-Type": "application/json",
        },
        json={"query": query, "variables": variables or {}},
        timeout=120,
    )
    resp.raise_for_status()
    body = resp.json()
    if body.get("errors"):
        sys.exit(f"GraphQL errors: {json.dumps(body['errors'], indent=2)}")
    return body


def derive_label(tags: list[str]) -> str:
    """Map a product's tags to a custom_label_0 value."""
    for t in tags:
        if t.startswith("price_tier:"):
            return t.split(":", 1)[1]
    return "synced"


def enumerate_products_with_tags() -> list[tuple[str, str]]:
    """Paginate ACTIVE products and return [(gid, label_value)] pairs."""
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
    """One product per line: list of one metafield input."""
    with path.open("w") as f:
        for gid, value in pairs:
            obj = {
                "metafields": [{
                    "ownerId": gid,
                    "namespace": MF_NAMESPACE,
                    "key": MF_KEY,
                    "type": MF_TYPE,
                    "value": value,
                }]
            }
            f.write(json.dumps(obj) + "\n")
    return path.stat().st_size


def staged_upload(file_path: Path) -> str:
    STAGED_UPLOADS_CREATE = """
    mutation stagedUploadsCreate($input: [StagedUploadInput!]!) {
      stagedUploadsCreate(input: $input) {
        stagedTargets { url parameters { name value } }
        userErrors { field message }
      }
    }
    """
    data = gql(STAGED_UPLOADS_CREATE, {
        "input": [{
            "filename": file_path.name,
            "mimeType": "text/jsonl",
            "httpMethod": "POST",
            "resource": "BULK_MUTATION_VARIABLES",
        }]
    })
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


METAFIELDS_SET_MUTATION = """
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
    data = gql(BULK_RUN, {
        "mutation": METAFIELDS_SET_MUTATION,
        "stagedUploadPath": staged_path,
    })
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
    data = gql(QUERY)
    return data["data"]["currentBulkOperation"]


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
    g.add_argument("--dry-run", action="store_true", help="Enumerate + show derived value distribution")
    g.add_argument("--execute", action="store_true", help="Submit bulk metafieldsSet operation")
    g.add_argument("--status", action="store_true", help="Show current bulk op status")
    args = parser.parse_args()

    if args.status:
        op = get_current_bulk_op()
        if not op:
            print("No current bulk operation.")
            return 0
        print(json.dumps(op, indent=2))
        return 0

    print("=== force-mc-resync-metafields ===")
    print(f"Metafield: {MF_NAMESPACE}.{MF_KEY} (type {MF_TYPE})")
    print(f"Mode: {'EXECUTE' if args.execute else 'DRY RUN'}\n")

    print("Step 1: Enumerate ACTIVE products + derive label values")
    pairs = enumerate_products_with_tags()
    print(f"  → {len(pairs)} products\n")
    if not pairs:
        sys.exit("No ACTIVE products found")

    # Distribution sanity check
    from collections import Counter
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
    if final.get("status") != "COMPLETED":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
