#!/usr/bin/env python3
"""
Landing-page audit for the Google Ads "Winners" campaign.

For each LIVE winner (from docs/ads-winners-curation-list.md), check the
product's landing-page quality signals that affect Shopping ad approval,
Quality Score, and conversion rate:

  - Has >= 1 image (required by Merchant Center)
  - Has a non-trivial description (not empty, not just HTML boilerplate)
  - Has a SEO title + meta description
  - Is published to the Online Store channel
  - Every variant is in stock + purchasable (policy CONTINUE or qty > 0)
  - Has `category:game` tag (not console/accessory)
  - Handle resolves to 8bitlegacy.com/products/<handle> (sanity format check)
  - Has correct Google Merchant metafields (custom_product, google_product_category)

Run:
    python3 scripts/audit-winners-landing-pages.py
    python3 scripts/audit-winners-landing-pages.py --save       # write markdown report

Reads the Winners handle list from docs/ads-winners-curation-list.md so the
source of truth stays in one place.
"""
import json
import os
import re
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / "dashboard" / ".env.local")
load_dotenv(Path(__file__).parent.parent / "config" / ".env")

SHOP = os.getenv("SHOPIFY_STORE_URL", "")
TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN", "")
API_VERSION = "2024-10"
GQL_URL = f"https://{SHOP}/admin/api/{API_VERSION}/graphql.json"
HEADERS = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}

PROJECT = Path(__file__).parent.parent
WINNERS_DOC = PROJECT / "docs" / "ads-winners-curation-list.md"
AUDIT_JSON = PROJECT / "data" / "ads-winners-audit-2026-04-11.json"

# Description length below which we flag as "too short for Quality Score"
MIN_DESCRIPTION_CHARS = 80


def gql(query, variables=None):
    for attempt in range(5):
        resp = requests.post(GQL_URL, headers=HEADERS, json={"query": query, "variables": variables or {}})
        if resp.status_code == 429:
            time.sleep(2 + attempt)
            continue
        if resp.status_code != 200:
            time.sleep(2 ** attempt)
            continue
        data = resp.json()
        if any(e.get("extensions", {}).get("code") == "THROTTLED" for e in data.get("errors", [])):
            time.sleep(2 + attempt)
            continue
        return data
    return data


PRODUCT_BY_HANDLE = """
query($query: String!) {
  products(first: 1, query: $query) {
    nodes {
      id
      title
      handle
      status
      descriptionHtml
      vendor
      productType
      tags
      seo { title description }
      featuredImage { url altText }
      images(first: 10) { nodes { url altText } }
      onlineStoreUrl
      variants(first: 20) {
        nodes {
          id
          title
          sku
          price
          inventoryQuantity
          inventoryPolicy
          availableForSale
          image { url }
        }
      }
      metafields(first: 30) {
        nodes { namespace key value }
      }
    }
  }
}
"""


def extract_live_handles_from_doc():
    """Parse the curation list markdown table, collect handles of LIVE rows."""
    if not WINNERS_DOC.exists():
        print(f"ERROR: {WINNERS_DOC} not found")
        sys.exit(1)

    text = WINNERS_DOC.read_text()
    handles = []
    # Match markdown table rows with a backtick-wrapped handle and a LIVE status
    row_re = re.compile(r"\|\s*\d+\s*\|[^|]+\|[^|]+\|[^|]+\|\s*`([^`]+)`\s*\|\s*✅\s*LIVE")
    for m in row_re.finditer(text):
        handle = m.group(1).strip()
        if handle not in handles:
            handles.append(handle)
    return handles


def strip_html(html):
    """Crude HTML → text for length/heuristic checks."""
    if not html:
        return ""
    return re.sub(r"<[^>]+>", " ", html).strip()


def audit_product(handle):
    """Fetch one product and return a dict of findings."""
    data = gql(PRODUCT_BY_HANDLE, {"query": f"handle:{handle}"})
    nodes = data.get("data", {}).get("products", {}).get("nodes", [])
    if not nodes:
        return {"handle": handle, "found": False, "issues": ["PRODUCT NOT FOUND"]}
    node = nodes[0]

    issues = []
    warnings = []

    # Status
    if node["status"] != "ACTIVE":
        issues.append(f"status={node['status']} (must be ACTIVE)")

    # Images
    image_count = len(node.get("images", {}).get("nodes", []))
    if image_count == 0:
        issues.append("no images (Merchant Center will reject)")
    elif image_count == 1:
        warnings.append("only 1 image (recommend 3+ for Quality Score)")

    # Description
    desc_text = strip_html(node.get("descriptionHtml", ""))
    desc_len = len(desc_text)
    if desc_len == 0:
        issues.append("description is empty")
    elif desc_len < MIN_DESCRIPTION_CHARS:
        warnings.append(f"description too short ({desc_len} chars, recommend 80+)")

    # SEO
    seo = node.get("seo") or {}
    if not seo.get("title"):
        warnings.append("missing SEO title")
    if not seo.get("description"):
        warnings.append("missing SEO meta description")

    # Online store publication
    online_url = node.get("onlineStoreUrl")
    if not online_url:
        issues.append("not published to Online Store (onlineStoreUrl is null)")

    # Tags
    tags_lo = [t.lower() for t in node.get("tags", [])]
    if "category:game" not in tags_lo:
        issues.append("missing category:game tag")
    if "category:console" in tags_lo:
        issues.append("WRONG tag category:console (should be category:game)")
    if "category:accessory" in tags_lo:
        issues.append("WRONG tag category:accessory (should be category:game)")

    # Variants — need at least one purchasable
    variants = node.get("variants", {}).get("nodes", [])
    if not variants:
        issues.append("no variants")
    else:
        purchasable = [v for v in variants if v.get("availableForSale")]
        if not purchasable:
            issues.append(f"no purchasable variants (all {len(variants)} unavailable)")
        else:
            # Check each variant for stock/policy
            for v in variants:
                if not v.get("availableForSale"):
                    warnings.append(f"variant '{v['title']}' not available (policy={v.get('inventoryPolicy')} qty={v.get('inventoryQuantity')})")

    # Handle sanity
    if not re.match(r"^[a-z0-9][a-z0-9-]*$", handle):
        issues.append(f"handle format bad: {handle}")

    # Google Merchant metafields
    mf_map = {(m["namespace"], m["key"]): m["value"] for m in node.get("metafields", {}).get("nodes", [])}
    cp = mf_map.get(("mm-google-shopping", "custom_product"))
    if cp != "true":
        warnings.append(f"mm-google-shopping.custom_product != true (is {cp!r}) — will be fixed by fix-gtin-metafields.py")
    cat_mf = mf_map.get(("mm-google-shopping", "google_product_category"))
    if cat_mf != "1279":
        warnings.append(f"google_product_category != 1279 (is {cat_mf!r})")

    return {
        "handle": handle,
        "found": True,
        "title": node["title"],
        "status": node["status"],
        "online_url": online_url,
        "image_count": image_count,
        "description_chars": desc_len,
        "variant_count": len(variants),
        "purchasable_variants": sum(1 for v in variants if v.get("availableForSale")),
        "tags": node.get("tags", []),
        "issues": issues,
        "warnings": warnings,
    }


def render_report(results):
    """Build a markdown report from audit results."""
    lines = []
    lines.append("# Winners Landing-Page Audit")
    lines.append("")
    lines.append(f"**Generated:** `scripts/audit-winners-landing-pages.py`")
    lines.append("")

    blocking = [r for r in results if r.get("issues")]
    warn_only = [r for r in results if not r.get("issues") and r.get("warnings")]
    clean = [r for r in results if not r.get("issues") and not r.get("warnings")]

    lines.append(f"- **Total audited:** {len(results)}")
    lines.append(f"- **Blocking issues (fix before launch):** {len(blocking)}")
    lines.append(f"- **Warnings only (recommended fixes):** {len(warn_only)}")
    lines.append(f"- **Clean:** {len(clean)}")
    lines.append("")

    if blocking:
        lines.append("## Blocking issues")
        lines.append("")
        for r in blocking:
            lines.append(f"### {r.get('title', r['handle'])}")
            lines.append(f"Handle: `{r['handle']}`")
            if r.get("online_url"):
                lines.append(f"URL: {r['online_url']}")
            lines.append("")
            for i in r["issues"]:
                lines.append(f"- ❌ {i}")
            for w in r.get("warnings", []):
                lines.append(f"- ⚠️ {w}")
            lines.append("")

    if warn_only:
        lines.append("## Warnings only")
        lines.append("")
        for r in warn_only:
            lines.append(f"### {r.get('title', r['handle'])}")
            lines.append(f"Handle: `{r['handle']}`")
            lines.append("")
            for w in r["warnings"]:
                lines.append(f"- ⚠️ {w}")
            lines.append("")

    if clean:
        lines.append("## Clean — ready for ads")
        lines.append("")
        for r in clean:
            lines.append(f"- ✅ `{r['handle']}` — {r.get('title', '')}")
        lines.append("")

    return "\n".join(lines)


def main():
    save = "--save" in sys.argv

    handles = extract_live_handles_from_doc()
    print(f"Auditing {len(handles)} LIVE winners from {WINNERS_DOC.name}")

    results = []
    for i, h in enumerate(handles, 1):
        result = audit_product(h)
        results.append(result)
        status_marker = "❌" if result.get("issues") else ("⚠️" if result.get("warnings") else "✅")
        print(f"  [{i}/{len(handles)}] {status_marker} {h}")
        if result.get("issues"):
            for issue in result["issues"]:
                print(f"      - {issue}")
        time.sleep(0.3)

    report = render_report(results)
    print("\n" + "=" * 60)
    print(report)

    if save:
        out_md = PROJECT / "docs" / "winners-landing-page-audit.md"
        out_md.write_text(report)
        out_json = PROJECT / "data" / "winners-landing-page-audit.json"
        out_json.write_text(json.dumps(results, indent=2))
        print(f"\nSaved: {out_md}")
        print(f"Saved: {out_json}")


if __name__ == "__main__":
    main()
