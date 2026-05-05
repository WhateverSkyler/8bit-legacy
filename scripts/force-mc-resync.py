#!/usr/bin/env python3
"""Force Merchant Center resync by bulk-touching all ACTIVE products.

Adds a hidden marker tag (default `__mc-resync-{today}`) to every product
via Shopify's bulkOperationRunMutation API. The tag itself is harmless —
it's the products/update webhook that fires as a side effect that we
actually need: the Google & YouTube channel app subscribes to that webhook
and re-pushes the product to Merchant Center.

Important: re-running with the SAME tag is a no-op (Shopify suppresses
no-op tagsAdd) and won't fire fresh webhooks. Use a unique tag per
re-sync wave (e.g. date-stamped, or task-specific like
`__cl2-resync-2026-05-05`).

Properties:
- IDEMPOTENT — `tagsAdd` appends; running twice doesn't add the tag twice.
- NON-DESTRUCTIVE — `tagsAdd` does NOT replace existing tags (productUpdate
  with `tags` field would). All existing tags + metafields preserved.
- HIDDEN — tag starts with `__` so it's invisible to customers / SEO /
  storefront search. Cleanup is a future tagsRemove.
- SERVER-SIDE — bulk operation runs on Shopify's side; this script just
  submits the JSONL and polls. Survives our process exiting.

Usage:
    python3 scripts/force-mc-resync.py --dry-run                              # enumerate products only
    python3 scripts/force-mc-resync.py --execute                              # use auto-dated default tag
    python3 scripts/force-mc-resync.py --execute --tag __cl2-resync-2026-05-05  # explicit tag
    python3 scripts/force-mc-resync.py --status                               # check current bulk op
    python3 scripts/force-mc-resync.py --cancel                               # cancel running bulk op
"""

from __future__ import annotations

import argparse
import datetime
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
DEFAULT_SYNC_TAG = f"__mc-resync-{datetime.date.today().isoformat()}"
JSONL_PATH = Path("/tmp/mc-resync-products.jsonl")


def gql(query: str, variables: dict | None = None) -> dict:
    """POST a GraphQL request and return the parsed body. Exits on errors."""
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
    if "errors" in body and body["errors"]:
        sys.exit(f"GraphQL errors: {json.dumps(body['errors'], indent=2)}")
    return body


def enumerate_active_products() -> list[str]:
    """Paginate ACTIVE products → list of GIDs."""
    QUERY = """
    query GetProducts($cursor: String) {
      products(first: 250, after: $cursor, query: "status:active") {
        edges { node { id } }
        pageInfo { hasNextPage endCursor }
      }
    }
    """
    gids: list[str] = []
    cursor: str | None = None
    page = 0
    while True:
        page += 1
        data = gql(QUERY, {"cursor": cursor})
        edges = data["data"]["products"]["edges"]
        gids.extend(e["node"]["id"] for e in edges)
        info = data["data"]["products"]["pageInfo"]
        if not info["hasNextPage"]:
            break
        cursor = info["endCursor"]
        if page % 4 == 0:
            print(f"  page {page}: {len(gids)} GIDs collected so far", flush=True)
    return gids


def write_jsonl(gids: list[str], path: Path, sync_tag: str) -> int:
    """Write JSONL with one tagsAdd input per line. Returns byte count."""
    with path.open("w") as f:
        for gid in gids:
            f.write(json.dumps({"id": gid, "tags": [sync_tag]}) + "\n")
    return path.stat().st_size


def staged_upload(file_path: Path) -> str:
    """Upload JSONL to Shopify's staged S3, return the `key` parameter for bulk op."""
    STAGED_UPLOADS_CREATE = """
    mutation stagedUploadsCreate($input: [StagedUploadInput!]!) {
      stagedUploadsCreate(input: $input) {
        stagedTargets {
          url
          parameters { name value }
        }
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

    # Multipart upload to S3 — parameters first, then file last (S3 is order-sensitive)
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


# Mutation: tagsAdd (NON-destructive — appends to existing tags, idempotent).
# DO NOT replace this with productUpdate(input: {tags: ...}) — that would
# REPLACE all tags on every product, wiping legitimate tags.
TAGS_ADD_MUTATION = """
mutation call($id: ID!, $tags: [String!]!) {
  tagsAdd(id: $id, tags: $tags) {
    node { id }
    userErrors { field message }
  }
}
""".strip()


def submit_bulk_op(staged_path: str) -> dict:
    """Kick off bulkOperationRunMutation. Returns the bulkOperation node."""
    BULK_RUN = """
    mutation bulkOperationRunMutation($mutation: String!, $stagedUploadPath: String!) {
      bulkOperationRunMutation(mutation: $mutation, stagedUploadPath: $stagedUploadPath) {
        bulkOperation { id status createdAt }
        userErrors { field message code }
      }
    }
    """
    data = gql(BULK_RUN, {
        "mutation": TAGS_ADD_MUTATION,
        "stagedUploadPath": staged_path,
    })
    res = data["data"]["bulkOperationRunMutation"]
    if res.get("userErrors"):
        sys.exit(f"bulkOperationRunMutation errors: {res['userErrors']}")
    return res["bulkOperation"]


def get_current_bulk_op() -> dict | None:
    """Return the current MUTATION-type bulk operation (if any)."""
    QUERY = """
    {
      currentBulkOperation(type: MUTATION) {
        id status errorCode createdAt completedAt objectCount fileSize url partialDataUrl
      }
    }
    """
    data = gql(QUERY)
    return data["data"]["currentBulkOperation"]


def cancel_current_bulk_op() -> dict:
    op = get_current_bulk_op()
    if not op or op["status"] not in ("CREATED", "RUNNING"):
        return {"status": "no-op", "current": op}
    CANCEL = """
    mutation bulkOperationCancel($id: ID!) {
      bulkOperationCancel(id: $id) {
        bulkOperation { id status }
        userErrors { field message }
      }
    }
    """
    data = gql(CANCEL, {"id": op["id"]})
    return data["data"]["bulkOperationCancel"]


def poll_until_done(initial_op: dict, timeout_sec: int = 7200) -> dict:
    """Poll currentBulkOperation until it terminates or timeout."""
    start = time.time()
    last_count = 0
    while time.time() - start < timeout_sec:
        op = get_current_bulk_op()
        if not op:
            print("  no current bulk op (vanished?)", flush=True)
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
    g.add_argument("--dry-run", action="store_true", help="Enumerate products only (no mutations)")
    g.add_argument("--execute", action="store_true", help="Submit the bulk operation")
    g.add_argument("--status", action="store_true", help="Show current bulk op status")
    g.add_argument("--cancel", action="store_true", help="Cancel running bulk op")
    parser.add_argument(
        "--tag",
        default=DEFAULT_SYNC_TAG,
        help=f"Marker tag to add (default: {DEFAULT_SYNC_TAG}). Re-using a tag already on a product is a no-op and won't fire fresh webhooks — pick a unique tag per resync wave.",
    )
    args = parser.parse_args()

    if args.status:
        op = get_current_bulk_op()
        if not op:
            print("No current bulk operation.")
            return 0
        print(json.dumps(op, indent=2))
        return 0

    if args.cancel:
        res = cancel_current_bulk_op()
        print(json.dumps(res, indent=2))
        return 0

    print("=== force-mc-resync ===")
    print(f"Tag to add:  {args.tag}")
    print(f"Mode:        {'EXECUTE' if args.execute else 'DRY RUN'}\n")

    print("Step 1: Enumerate ACTIVE products")
    gids = enumerate_active_products()
    print(f"  → {len(gids)} ACTIVE products\n")
    if not gids:
        sys.exit("No ACTIVE products found — bailing")

    if args.dry_run:
        print("[DRY RUN] would write JSONL + run bulk operation. Stopping.")
        return 0

    # Belt-and-suspenders: refuse to start if a bulk op is already running.
    existing = get_current_bulk_op()
    if existing and existing["status"] in ("CREATED", "RUNNING"):
        sys.exit(
            f"A bulk op is already RUNNING ({existing['id']}, status={existing['status']}). "
            f"Wait for it to finish or use --cancel."
        )

    print(f"Step 2: Write JSONL → {JSONL_PATH}")
    n_bytes = write_jsonl(gids, JSONL_PATH, args.tag)
    print(f"  → {n_bytes:,} bytes\n")

    print("Step 3: Staged upload to Shopify S3")
    key = staged_upload(JSONL_PATH)
    print(f"  → staged key: {key}\n")

    print("Step 4: Submit bulkOperationRunMutation")
    op = submit_bulk_op(key)
    print(f"  → operation ID: {op['id']}, status: {op['status']}\n")

    print("Step 5: Poll until completion")
    final = poll_until_done(op)

    print("\n=== DONE ===")
    print(json.dumps(final, indent=2))
    if final.get("status") != "COMPLETED":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
