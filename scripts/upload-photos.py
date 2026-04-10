#!/usr/bin/env python3
"""
8-Bit Legacy — Product Photo Uploader

Bulk upload product photos to Shopify. Matches image filenames to products
by title, SKU, or partial match, then uploads as the primary product image.

Usage:
  # Preview matches (no uploads)
  python3 scripts/upload-photos.py ~/Photos/Products/ --dry-run

  # Upload all photos from a directory
  python3 scripts/upload-photos.py ~/Photos/Products/ --apply

  # Upload a single photo to a specific product by SKU
  python3 scripts/upload-photos.py photo.jpg --sku NES-001

  # Upload with fuzzy matching (less strict title matching)
  python3 scripts/upload-photos.py ~/Photos/Products/ --fuzzy --dry-run

  # Set photos as primary (replaces existing main image)
  python3 scripts/upload-photos.py ~/Photos/Products/ --primary --apply

  # Match by product title substring in filename
  python3 scripts/upload-photos.py ~/Photos/Products/ --apply
  # File naming: "Super Mario Bros 3.jpg" → matches "Super Mario Bros 3 - NES Game"

Filename conventions:
  - Name files after the product: "Super Mario Bros 3.jpg"
  - Or use SKU: "NES-001.jpg" or "PKM-sv9-001.jpg"
  - Supports: .jpg, .jpeg, .png, .webp
  - Subdirectories are scanned recursively
"""

import argparse
import base64
import json
import os
import re
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
CONFIG_DIR = PROJECT_DIR / "config"

load_dotenv(CONFIG_DIR / ".env")
load_dotenv(PROJECT_DIR / "dashboard" / ".env.local")

SHOPIFY_STORE = os.getenv("SHOPIFY_STORE_URL", "")
SHOPIFY_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN", "")
SHOPIFY_API_VERSION = "2024-10"

SHOPIFY_DELAY = 0.5  # Slightly longer delay for media uploads

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


# ── Shopify API ──────────────────────────────────────────────────────

def shopify_gql(query, variables=None):
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    resp = requests.post(
        f"https://{SHOPIFY_STORE}/admin/api/{SHOPIFY_API_VERSION}/graphql.json",
        headers={"X-Shopify-Access-Token": SHOPIFY_TOKEN, "Content-Type": "application/json"},
        json=payload,
    )
    resp.raise_for_status()
    return resp.json()


def fetch_all_products():
    """Fetch all active products with their images and SKUs."""
    products = []
    cursor = None
    page = 0

    while True:
        page += 1
        after = f', after: "{cursor}"' if cursor else ""
        query = f"""
        {{
          products(first: 50, query: "status:active"{after}) {{
            edges {{
              cursor
              node {{
                id
                title
                handle
                featuredImage {{ url }}
                media(first: 5) {{
                  edges {{
                    node {{
                      ... on MediaImage {{
                        id
                        image {{ url }}
                      }}
                    }}
                  }}
                }}
                variants(first: 10) {{
                  edges {{
                    node {{
                      sku
                    }}
                  }}
                }}
              }}
            }}
            pageInfo {{ hasNextPage }}
          }}
        }}
        """
        data = shopify_gql(query)
        edges = data.get("data", {}).get("products", {}).get("edges", [])

        for edge in edges:
            node = edge["node"]
            skus = []
            for ve in node.get("variants", {}).get("edges", []):
                sku = ve["node"].get("sku")
                if sku:
                    skus.append(sku)

            media_count = len(node.get("media", {}).get("edges", []))
            has_image = node.get("featuredImage") is not None

            products.append({
                "id": node["id"],
                "title": node["title"],
                "handle": node["handle"],
                "skus": skus,
                "has_image": has_image,
                "media_count": media_count,
            })

        has_next = data.get("data", {}).get("products", {}).get("pageInfo", {}).get("hasNextPage", False)
        if not has_next or not edges:
            break
        cursor = edges[-1]["cursor"]
        time.sleep(0.3)

        if page % 10 == 0:
            print(f"  Fetched {len(products)} products...")

    return products


def get_staged_upload_url(filename, mime_type, file_size):
    """Get a staged upload URL from Shopify for file upload."""
    mutation = """
    mutation stagedUploadsCreate($input: [StagedUploadInput!]!) {
      stagedUploadsCreate(input: $input) {
        stagedTargets {
          url
          resourceUrl
          parameters { name value }
        }
        userErrors { field message }
      }
    }
    """

    result = shopify_gql(mutation, {
        "input": [{
            "filename": filename,
            "mimeType": mime_type,
            "httpMethod": "POST",
            "resource": "IMAGE",
            "fileSize": str(file_size),
        }]
    })

    targets = result.get("data", {}).get("stagedUploadsCreate", {}).get("stagedTargets", [])
    errors = result.get("data", {}).get("stagedUploadsCreate", {}).get("userErrors", [])

    if errors:
        print(f"  Stage error: {errors[0]['message']}")
        return None

    if not targets:
        return None

    return targets[0]


def upload_to_staged_url(staged_target, file_path):
    """Upload a file to the staged URL."""
    url = staged_target["url"]
    params = {p["name"]: p["value"] for p in staged_target["parameters"]}

    with open(file_path, "rb") as f:
        files = {"file": (file_path.name, f)}
        resp = requests.post(url, data=params, files=files)

    return resp.status_code in (200, 201, 204)


def attach_image_to_product(product_id, resource_url, alt_text, set_primary=False):
    """Attach an uploaded image to a product."""
    mutation = """
    mutation productCreateMedia($productId: ID!, $media: [CreateMediaInput!]!) {
      productCreateMedia(productId: $productId, media: $media) {
        media {
          ... on MediaImage {
            id
            image { url }
          }
        }
        mediaUserErrors { field message }
      }
    }
    """

    result = shopify_gql(mutation, {
        "productId": product_id,
        "media": [{
            "originalSource": resource_url,
            "mediaContentType": "IMAGE",
            "alt": alt_text,
        }],
    })

    errors = result.get("data", {}).get("productCreateMedia", {}).get("mediaUserErrors", [])
    if errors:
        print(f"  Attach error: {errors[0]['message']}")
        return False

    return True


def upload_photo_to_product(product, file_path, set_primary=False):
    """Full workflow: stage → upload → attach."""
    filename = file_path.name
    ext = file_path.suffix.lower()
    mime_types = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
    mime_type = mime_types.get(ext, "image/jpeg")
    file_size = file_path.stat().st_size

    # Stage the upload
    staged = get_staged_upload_url(filename, mime_type, file_size)
    if not staged:
        return False

    time.sleep(SHOPIFY_DELAY)

    # Upload to staged URL
    if not upload_to_staged_url(staged, file_path):
        print(f"  Failed to upload {filename} to staged URL")
        return False

    time.sleep(SHOPIFY_DELAY)

    # Attach to product
    resource_url = staged["resourceUrl"]
    alt_text = product["title"]
    if not attach_image_to_product(product["id"], resource_url, alt_text, set_primary):
        return False

    return True


# ── Matching ─────────────────────────────────────────────────────────

def normalize(s):
    """Normalize for matching."""
    return re.sub(r"[^a-z0-9 ]", "", s.lower()).strip()


def match_file_to_product(file_path, products, fuzzy=False):
    """Try to match a file to a Shopify product."""
    stem = file_path.stem  # Filename without extension
    stem_norm = normalize(stem)

    # 1. Exact SKU match
    for p in products:
        for sku in p["skus"]:
            if normalize(sku) == stem_norm:
                return p, "sku_exact"

    # 2. SKU in filename
    for p in products:
        for sku in p["skus"]:
            if normalize(sku) in stem_norm:
                return p, "sku_partial"

    # 3. Exact title match (after stripping console suffix)
    for p in products:
        title_norm = normalize(p["title"])
        # Strip console suffix for comparison
        title_clean = re.sub(r"\s*(nes|snes|n64|gamecube|genesis|playstation|ps1|ps2|gameboy|gba|dreamcast|saturn|xbox|wii|sega|game)\s*$", "", title_norm).strip()
        if stem_norm == title_norm or stem_norm == title_clean:
            return p, "title_exact"

    # 4. Title contained in filename or filename in title
    for p in products:
        title_norm = normalize(p["title"])
        if len(stem_norm) >= 5:  # Avoid short false matches
            if stem_norm in title_norm or title_norm in stem_norm:
                return p, "title_contains"

    # 5. Fuzzy — filename words in title
    if fuzzy and len(stem_norm) >= 5:
        stem_words = set(stem_norm.split())
        best_match = None
        best_score = 0

        for p in products:
            title_words = set(normalize(p["title"]).split())
            overlap = len(stem_words & title_words)
            score = overlap / max(len(stem_words), 1)
            if score > best_score and score >= 0.6:
                best_score = score
                best_match = p

        if best_match:
            return best_match, f"fuzzy_{best_score:.0%}"

    return None, "no_match"


# ── Main ─────────────────────────────────────────────────────────────

def find_images(path):
    """Find all supported image files in a path."""
    p = Path(path)
    if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS:
        return [p]

    images = []
    if p.is_dir():
        for ext in SUPPORTED_EXTENSIONS:
            images.extend(p.rglob(f"*{ext}"))
            images.extend(p.rglob(f"*{ext.upper()}"))
    # Deduplicate
    seen = set()
    unique = []
    for img in images:
        if img.resolve() not in seen:
            seen.add(img.resolve())
            unique.append(img)
    return sorted(unique)


def main():
    parser = argparse.ArgumentParser(description="Upload product photos to Shopify")
    parser.add_argument("path", help="Photo file or directory to upload from")
    parser.add_argument("--sku", help="Upload to a specific product by SKU")
    parser.add_argument("--dry-run", action="store_true", help="Preview matches without uploading")
    parser.add_argument("--apply", action="store_true", help="Upload matched photos to Shopify")
    parser.add_argument("--fuzzy", action="store_true", help="Enable fuzzy title matching")
    parser.add_argument("--primary", action="store_true", help="Set uploaded photo as primary image")
    parser.add_argument("--no-image-only", action="store_true",
                        help="Only match products that don't have an image yet")

    args = parser.parse_args()

    if not args.dry_run and not args.apply:
        parser.print_help()
        print("\nUse --dry-run to preview or --apply to upload.")
        return

    if not SHOPIFY_STORE or not SHOPIFY_TOKEN:
        print("ERROR: Shopify credentials not configured")
        sys.exit(1)

    # Find images
    images = find_images(args.path)
    if not images:
        print(f"No supported images found in: {args.path}")
        print(f"Supported formats: {', '.join(SUPPORTED_EXTENSIONS)}")
        return

    print(f"Found {len(images)} image(s)")

    # Fetch products
    print("Fetching Shopify products...")
    products = fetch_all_products()
    print(f"  {len(products)} active products loaded")

    if args.no_image_only:
        products = [p for p in products if not p["has_image"]]
        print(f"  {len(products)} products without images")

    # Match and upload
    matched = 0
    uploaded = 0
    failed = 0
    no_match = 0

    print(f"\n  {'Image':<40} {'Match Type':<15} {'Product':<50}")
    print(f"  {'-'*40} {'-'*15} {'-'*50}")

    for img_path in images:
        if args.sku:
            # Direct SKU match
            product = None
            for p in products:
                if args.sku in p["skus"]:
                    product = p
                    break
            match_type = "sku_direct" if product else "no_match"
        else:
            product, match_type = match_file_to_product(img_path, products, fuzzy=args.fuzzy)

        if not product:
            no_match += 1
            print(f"  {img_path.name[:40]:<40} {'NO MATCH':<15}")
            continue

        matched += 1
        print(f"  {img_path.name[:40]:<40} {match_type:<15} {product['title'][:50]}")

        if args.apply:
            success = upload_photo_to_product(product, img_path, set_primary=args.primary)
            if success:
                uploaded += 1
                print(f"  {'':>40} {'':>15} -> Uploaded!")
            else:
                failed += 1
                print(f"  {'':>40} {'':>15} -> FAILED")
            time.sleep(SHOPIFY_DELAY)

    # Summary
    print(f"\n{'='*60}")
    print(f"  SUMMARY")
    print(f"{'='*60}")
    print(f"  Images found:    {len(images)}")
    print(f"  Matched:         {matched}")
    print(f"  No match:        {no_match}")
    if args.apply:
        print(f"  Uploaded:        {uploaded}")
        print(f"  Failed:          {failed}")
    else:
        print(f"  [DRY RUN] Would upload {matched} images")


if __name__ == "__main__":
    main()
