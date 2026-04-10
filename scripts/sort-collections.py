#!/usr/bin/env python3
"""
8-Bit Legacy — Collection Sort by Popularity

Reorders products within Shopify collections so popular/iconic titles
appear first. Uses a scoring system based on price, title recognition,
and known iconic game rankings.

Usage:
  # Preview sort order for all collections
  python3 scripts/sort-collections.py --dry-run

  # Apply sort order to all game collections
  python3 scripts/sort-collections.py --apply

  # Sort a specific collection by handle
  python3 scripts/sort-collections.py --apply --collection nes-games

  # List all collections
  python3 scripts/sort-collections.py --list
"""

import argparse
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

SHOPIFY_DELAY = 0.3

# ── Iconic Games Boost ───────────────────────────────────────────────
# These titles get a massive sort boost to ensure they appear near the top.
# Score bonus: 1000 = top tier, 500 = second tier, 250 = third tier

ICONIC_TITLES = {
    # Nintendo — Top Tier
    "super mario bros": 1000,
    "super mario bros 3": 1000,
    "super mario world": 1000,
    "super mario 64": 1000,
    "super mario sunshine": 800,
    "super mario galaxy": 800,
    "legend of zelda": 1000,
    "zelda ii": 700,
    "link to the past": 1000,
    "ocarina of time": 1000,
    "majoras mask": 900,
    "wind waker": 900,
    "twilight princess": 800,
    "breath of the wild": 900,
    "super metroid": 900,
    "metroid prime": 900,
    "metroid": 700,
    "super smash bros": 900,
    "super smash bros melee": 1000,
    "mario kart 64": 900,
    "mario kart": 800,
    "mario kart double dash": 800,
    "donkey kong country": 900,
    "donkey kong country 2": 800,
    "kirby": 600,
    "star fox 64": 700,
    "star fox": 600,
    "goldeneye": 900,
    "goldeneye 007": 900,
    "perfect dark": 700,
    "pokemon red": 900,
    "pokemon blue": 900,
    "pokemon yellow": 900,
    "pokemon gold": 800,
    "pokemon silver": 800,
    "pokemon crystal": 800,
    "pokemon ruby": 700,
    "pokemon sapphire": 700,
    "pokemon emerald": 800,
    "pokemon firered": 700,
    "pokemon leafgreen": 700,
    "pokemon diamond": 600,
    "pokemon pearl": 600,
    "pokemon platinum": 700,
    "pokemon heartgold": 800,
    "pokemon soulsilver": 800,
    "pokemon black": 700,
    "pokemon white": 700,
    "fire emblem": 600,
    "earthbound": 1000,
    "chrono trigger": 1000,
    "final fantasy": 700,
    "final fantasy ii": 700,
    "final fantasy iii": 800,
    "final fantasy vi": 900,
    "mega man": 700,
    "mega man 2": 800,
    "mega man x": 800,
    "castlevania": 800,
    "castlevania symphony of the night": 1000,
    "super castlevania iv": 700,
    "contra": 800,
    "mike tysons punch out": 900,
    "punch out": 800,
    "tetris": 700,
    "duck hunt": 500,
    "excitebike": 500,
    "f zero": 600,
    "pilotwings": 500,
    "paper mario": 800,
    "paper mario thousand year door": 900,
    "animal crossing": 700,
    "luigi mansion": 700,
    "luigis mansion": 700,
    "pikmin": 600,
    "pikmin 2": 600,

    # Sega — Top Tier
    "sonic the hedgehog": 900,
    "sonic the hedgehog 2": 900,
    "sonic the hedgehog 3": 800,
    "sonic and knuckles": 700,
    "sonic adventure": 800,
    "sonic adventure 2": 800,
    "streets of rage": 700,
    "streets of rage 2": 800,
    "phantasy star": 700,
    "shining force": 600,
    "golden axe": 600,
    "altered beast": 500,
    "shinobi": 600,
    "gunstar heroes": 700,
    "panzer dragoon saga": 1000,
    "nights into dreams": 700,
    "jet set radio": 700,
    "shenmue": 800,
    "shenmue ii": 700,
    "crazy taxi": 600,
    "skies of arcadia": 800,
    "power stone": 700,
    "soul calibur": 700,

    # PlayStation — Top Tier
    "final fantasy vii": 1000,
    "final fantasy viii": 700,
    "final fantasy ix": 800,
    "final fantasy x": 800,
    "metal gear solid": 900,
    "metal gear solid 2": 700,
    "metal gear solid 3": 800,
    "resident evil": 800,
    "resident evil 2": 900,
    "resident evil 3": 700,
    "resident evil 4": 900,
    "crash bandicoot": 800,
    "crash bandicoot 2": 700,
    "crash bandicoot warped": 700,
    "spyro the dragon": 700,
    "spyro 2": 600,
    "tekken 3": 700,
    "tekken": 500,
    "gran turismo": 600,
    "gran turismo 2": 600,
    "silent hill": 900,
    "silent hill 2": 1000,
    "silent hill 3": 700,
    "kingdom hearts": 800,
    "kingdom hearts ii": 700,
    "shadow of the colossus": 800,
    "ico": 700,
    "god of war": 800,
    "god of war ii": 700,
    "ratchet and clank": 700,
    "jak and daxter": 700,
    "sly cooper": 600,
    "devil may cry": 600,
    "dragon quest viii": 700,
    "persona 3": 700,
    "persona 4": 800,
    "dark cloud": 600,
    "dark cloud 2": 700,
    "xenosaga": 600,

    # Xbox
    "halo": 900,
    "halo 2": 800,
    "halo 3": 700,
    "fable": 600,
    "knights of the old republic": 800,
    "star wars knights of the old republic": 800,
    "gears of war": 600,
    "forza motorsport": 500,
}


def normalize(s):
    """Normalize a title for matching."""
    return re.sub(r"[^a-z0-9 ]", "", s.lower()).strip()


def strip_console_suffix(title):
    """Strip console name suffixes from product titles."""
    return re.sub(
        r"\s*[-–]\s*(NES|SNES|N64|Nintendo|Gameboy|Game Boy|Genesis|PS1|PS2|PSP|"
        r"Gamecube|Dreamcast|Saturn|GBA|Playstation|Xbox|Wii|Sega|Atari|TurboGrafx|"
        r"3DS|DS|Game Gear|Master System|Sega CD|32X).*$",
        "", title, flags=re.IGNORECASE
    )


def calculate_popularity_score(product):
    """Score a product by popularity. Higher = more popular = sorts first."""
    title = product["title"]
    clean_title = strip_console_suffix(title)
    norm = normalize(clean_title)
    price = product.get("max_price", 0)

    # Base score from price (higher value games tend to be more desirable)
    # Scale: $5 = 5 points, $50 = 50 points, $200 = 200 points
    score = min(price, 300)  # Cap price contribution at 300

    # Iconic title boost — check for substring matches
    best_boost = 0
    for iconic_title, boost in ICONIC_TITLES.items():
        iconic_norm = normalize(iconic_title)
        if iconic_norm in norm or norm in iconic_norm:
            # Prefer exact or near-exact matches
            if iconic_norm == norm:
                best_boost = max(best_boost, boost)
            elif len(iconic_norm) > 5:  # Avoid short string false matches
                best_boost = max(best_boost, boost * 0.8)

    score += best_boost

    return round(score, 2)


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


def fetch_collections():
    """Fetch all collections from Shopify."""
    collections = []
    cursor = None

    while True:
        after = f', after: "{cursor}"' if cursor else ""
        query = f"""
        {{
          collections(first: 50{after}) {{
            edges {{
              cursor
              node {{
                id
                title
                handle
                sortOrder
                productsCount {{ count }}
              }}
            }}
            pageInfo {{ hasNextPage }}
          }}
        }}
        """
        data = shopify_gql(query)
        edges = data.get("data", {}).get("collections", {}).get("edges", [])

        if not edges:
            # Fallback: try without productsCount (older API versions)
            query_fallback = f"""
            {{
              collections(first: 50{after}) {{
                edges {{
                  cursor
                  node {{
                    id
                    title
                    handle
                    sortOrder
                  }}
                }}
                pageInfo {{ hasNextPage }}
              }}
            }}
            """
            data = shopify_gql(query_fallback)
            edges = data.get("data", {}).get("collections", {}).get("edges", [])

        for edge in edges:
            node = edge["node"]
            pc = node.get("productsCount")
            count = pc.get("count", 0) if isinstance(pc, dict) else (pc or 0)
            collections.append({
                "id": node["id"],
                "title": node["title"],
                "handle": node["handle"],
                "sort_order": node.get("sortOrder", ""),
                "products_count": count,
            })

        has_next = data.get("data", {}).get("collections", {}).get("pageInfo", {}).get("hasNextPage", False)
        if not has_next or not edges:
            break
        cursor = edges[-1]["cursor"]
        time.sleep(SHOPIFY_DELAY)

    return collections


def fetch_collection_products(collection_id):
    """Fetch all products in a collection with their prices."""
    products = []
    cursor = None

    while True:
        after = f', after: "{cursor}"' if cursor else ""
        query = f"""
        {{
          collection(id: "{collection_id}") {{
            products(first: 50{after}) {{
              edges {{
                cursor
                node {{
                  id
                  title
                  tags
                  variants(first: 10) {{
                    edges {{
                      node {{
                        price
                      }}
                    }}
                  }}
                }}
              }}
              pageInfo {{ hasNextPage }}
            }}
          }}
        }}
        """
        data = shopify_gql(query)
        collection = data.get("data", {}).get("collection", {})
        edges = collection.get("products", {}).get("edges", [])

        for edge in edges:
            node = edge["node"]
            prices = [float(ve["node"]["price"]) for ve in node.get("variants", {}).get("edges", [])]
            products.append({
                "id": node["id"],
                "title": node["title"],
                "tags": node.get("tags", []),
                "max_price": max(prices) if prices else 0,
            })

        has_next = collection.get("products", {}).get("pageInfo", {}).get("hasNextPage", False)
        if not has_next or not edges:
            break
        cursor = edges[-1]["cursor"]
        time.sleep(SHOPIFY_DELAY)

    return products


def set_collection_sort_manual(collection_id):
    """Set a collection's sort order to MANUAL so we can reorder products."""
    mutation = """
    mutation collectionUpdate($input: CollectionInput!) {
      collectionUpdate(input: $input) {
        collection { id sortOrder }
        userErrors { field message }
      }
    }
    """
    result = shopify_gql(mutation, {
        "input": {
            "id": collection_id,
            "sortOrder": "MANUAL",
        }
    })
    errors = result.get("data", {}).get("collectionUpdate", {}).get("userErrors", [])
    if errors:
        print(f"  ERROR setting sort order: {errors[0]['message']}")
        return False
    return True


def reorder_collection(collection_id, product_ids):
    """Reorder products within a collection using moves."""
    if len(product_ids) < 2:
        return True

    # Shopify's collectionReorderProducts takes a list of moves
    # Each move has an id and a newPosition (0-indexed)
    moves = [{"id": pid, "newPosition": str(i)} for i, pid in enumerate(product_ids)]

    mutation = """
    mutation collectionReorderProducts($id: ID!, $moves: [MoveInput!]!) {
      collectionReorderProducts(id: $id, moves: $moves) {
        job { id }
        userErrors { field message }
      }
    }
    """

    result = shopify_gql(mutation, {"id": collection_id, "moves": moves})
    errors = result.get("data", {}).get("collectionReorderProducts", {}).get("userErrors", [])
    if errors:
        print(f"  ERROR reordering: {errors[0]['message']}")
        return False
    return True


# ── Main ─────────────────────────────────────────────────────────────

def sort_collection(collection, dry_run=True):
    """Sort a single collection by popularity."""
    col_id = collection["id"]
    col_title = collection["title"]
    count = collection["products_count"]

    print(f"\n{'='*60}")
    print(f"  {col_title} ({count} products)")
    print(f"{'='*60}")

    products = fetch_collection_products(col_id)
    if not products:
        print("  No products found")
        return

    # Score each product
    for p in products:
        p["score"] = calculate_popularity_score(p)

    # Sort by score descending (highest popularity first)
    sorted_products = sorted(products, key=lambda p: p["score"], reverse=True)

    # Show top 20
    print(f"\n  Top 20 (sorted by popularity):")
    for i, p in enumerate(sorted_products[:20], 1):
        print(f"  {i:>3}. {p['title'][:55]:<55} score: {p['score']:>7.1f}  (${p['max_price']:.2f})")

    if len(sorted_products) > 20:
        print(f"  ... and {len(sorted_products) - 20} more")

    if dry_run:
        print(f"\n  [DRY RUN] Would reorder {len(sorted_products)} products")
        return

    # Set sort order to MANUAL first
    print(f"\n  Setting sort order to MANUAL...")
    if not set_collection_sort_manual(col_id):
        return

    time.sleep(SHOPIFY_DELAY)

    # Reorder products
    product_ids = [p["id"] for p in sorted_products]
    print(f"  Reordering {len(product_ids)} products...")
    if reorder_collection(col_id, product_ids):
        print(f"  Done! {col_title} sorted by popularity.")
    else:
        print(f"  Failed to reorder {col_title}")

    time.sleep(SHOPIFY_DELAY)


def main():
    parser = argparse.ArgumentParser(description="Sort Shopify collections by product popularity")
    parser.add_argument("--dry-run", action="store_true", help="Preview sort order without applying")
    parser.add_argument("--apply", action="store_true", help="Apply sort order to Shopify")
    parser.add_argument("--collection", nargs="+", help="Specific collection handle(s) to sort")
    parser.add_argument("--list", action="store_true", help="List all collections")

    args = parser.parse_args()

    if not args.list and not args.dry_run and not args.apply:
        parser.print_help()
        print("\nUse --dry-run to preview or --apply to sort collections.")
        return

    if not SHOPIFY_STORE or not SHOPIFY_TOKEN:
        print("ERROR: Shopify credentials not configured")
        sys.exit(1)

    print("Fetching collections...")
    collections = fetch_collections()

    if args.list:
        print(f"\n  {'Handle':<35} {'Title':<40} {'Products':>8}  Sort Order")
        print(f"  {'-'*35} {'-'*40} {'-'*8}  {'-'*12}")
        for c in sorted(collections, key=lambda x: x["title"]):
            print(f"  {c['handle']:<35} {c['title']:<40} {c['products_count']:>8}  {c['sort_order']}")
        print(f"\n  Total: {len(collections)} collections")
        return

    # Filter collections if specific handles requested
    if args.collection:
        collections = [c for c in collections if c["handle"] in args.collection]
        if not collections:
            print(f"  No collections found matching: {', '.join(args.collection)}")
            return

    # Skip empty collections and special collections (like "All", "Frontpage")
    skip_handles = {"frontpage", "all", ""}
    collections = [c for c in collections if c["handle"] not in skip_handles and c["products_count"] > 0]

    dry_run = not args.apply
    mode = "DRY RUN" if dry_run else "APPLYING"
    print(f"\n  Mode: {mode}")
    print(f"  Collections to sort: {len(collections)}")

    for collection in sorted(collections, key=lambda x: x["title"]):
        sort_collection(collection, dry_run=dry_run)

    print(f"\n{'='*60}")
    print(f"  {'Preview' if dry_run else 'Sort'} complete for {len(collections)} collections")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
