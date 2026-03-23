#!/usr/bin/env python3
"""
8-Bit Legacy — eBay Cheapest Listing Finder

Given a Shopify order (or manual search), finds the cheapest matching eBay listing
that meets quality standards. Designed to speed up the fulfillment workflow.

Usage:
  python3 ebay-finder.py "Super Mario Bros 3 NES"              # Search for a specific item
  python3 ebay-finder.py "Super Mario Bros 3 NES" --max 30     # Set max price
  python3 ebay-finder.py --pending-orders                       # Find listings for all pending Shopify orders
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus

import requests
from dotenv import load_dotenv

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
CONFIG_DIR = PROJECT_DIR / "config"

load_dotenv(CONFIG_DIR / ".env")

SHOPIFY_STORE_URL = os.getenv("SHOPIFY_STORE_URL")
SHOPIFY_ACCESS_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")
EBAY_APP_ID = os.getenv("EBAY_APP_ID")

# eBay Browse API (public, no auth needed for search)
EBAY_SEARCH_URL = "https://api.ebay.com/buy/browse/v1/item_summary/search"


def search_ebay_api(query: str, max_price: float = None, condition: str = "USED") -> list[dict]:
    """Search eBay via Browse API for matching listings."""
    if not EBAY_APP_ID:
        print("  Note: No eBay API key configured. Using web search URL fallback.")
        return search_ebay_web_fallback(query, max_price)

    headers = {
        "Authorization": f"Bearer {EBAY_APP_ID}",
        "X-EBAY-C-MARKETPLACE-ID": "EBAY_US",
        "Content-Type": "application/json",
    }

    params = {
        "q": query,
        "sort": "price",
        "limit": 20,
        "filter": "buyingOptions:{FIXED_PRICE},deliveryCountry:US",
    }

    if max_price:
        params["filter"] += f",price:[..{max_price}],priceCurrency:USD"

    if condition == "USED":
        params["filter"] += ",conditions:{USED}"

    try:
        resp = requests.get(EBAY_SEARCH_URL, headers=headers, params=params)
        resp.raise_for_status()
        data = resp.json()

        results = []
        for item in data.get("itemSummaries", []):
            price = float(item.get("price", {}).get("value", 0))
            shipping_cost = 0
            shipping = item.get("shippingOptions", [{}])
            if shipping:
                shipping_cost = float(shipping[0].get("shippingCost", {}).get("value", 0))

            results.append({
                "title": item.get("title", ""),
                "price": price,
                "shipping": shipping_cost,
                "total": round(price + shipping_cost, 2),
                "condition": item.get("condition", ""),
                "url": item.get("itemWebUrl", ""),
                "seller": item.get("seller", {}).get("username", ""),
                "seller_feedback": item.get("seller", {}).get("feedbackPercentage", ""),
                "image": item.get("image", {}).get("imageUrl", ""),
            })

        return sorted(results, key=lambda x: x["total"])

    except Exception as e:
        print(f"  eBay API error: {e}")
        return search_ebay_web_fallback(query, max_price)


def search_ebay_web_fallback(query: str, max_price: float = None) -> list[dict]:
    """Generate eBay search URLs as fallback when API isn't configured."""
    base = f"https://www.ebay.com/sch/i.html?_nkw={quote_plus(query)}&_sop=15&LH_BIN=1&LH_PrefLoc=1"
    if max_price:
        base += f"&_udhi={max_price}"

    return [{
        "title": f"[Open eBay Search: {query}]",
        "price": 0,
        "shipping": 0,
        "total": 0,
        "url": base,
        "note": "eBay API not configured — open this URL to search manually",
    }]


def fetch_pending_shopify_orders() -> list[dict]:
    """Fetch unfulfilled orders from Shopify."""
    if not SHOPIFY_STORE_URL or not SHOPIFY_ACCESS_TOKEN:
        print("  Error: Shopify credentials not configured.")
        return []

    url = f"https://{SHOPIFY_STORE_URL}/admin/api/2024-10/graphql.json"
    headers = {
        "X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN,
        "Content-Type": "application/json",
    }

    query = """
    {
      orders(first: 25, query: "fulfillment_status:unfulfilled") {
        edges {
          node {
            id
            name
            createdAt
            displayFulfillmentStatus
            shippingAddress {
              name
              city
              provinceCode
              zip
            }
            lineItems(first: 20) {
              edges {
                node {
                  title
                  quantity
                  variant {
                    price
                    sku
                  }
                }
              }
            }
          }
        }
      }
    }
    """

    resp = requests.post(url, json={"query": query}, headers=headers)
    resp.raise_for_status()
    data = resp.json()

    orders = []
    for edge in data.get("data", {}).get("orders", {}).get("edges", []):
        node = edge["node"]
        items = []
        for li_edge in node["lineItems"]["edges"]:
            li = li_edge["node"]
            items.append({
                "title": li["title"],
                "quantity": li["quantity"],
                "price": float(li["variant"]["price"]) if li.get("variant") else 0,
                "sku": li["variant"]["sku"] if li.get("variant") else "",
            })

        shipping = node.get("shippingAddress") or {}
        orders.append({
            "order_number": node["name"],
            "created_at": node["createdAt"],
            "customer_city": f"{shipping.get('city', '')}, {shipping.get('provinceCode', '')} {shipping.get('zip', '')}",
            "items": items,
        })

    return orders


def print_ebay_results(query: str, results: list[dict], shopify_price: float = None):
    """Print formatted eBay search results."""
    print(f"\n  Search: {query}")
    if shopify_price:
        print(f"  Shopify price: ${shopify_price:.2f}")
    print(f"  {'#':<3} {'Total':>8} {'Price':>8} {'Ship':>6} {'Seller':<15} {'Title':<50}")
    print(f"  {'-' * 3} {'-' * 8} {'-' * 8} {'-' * 6} {'-' * 15} {'-' * 50}")

    for i, r in enumerate(results[:10], 1):
        margin = ""
        if shopify_price and r["total"] > 0:
            profit = shopify_price - r["total"] - (shopify_price * 0.029 + 0.30)
            margin = f" → profit: ${profit:.2f}"

        title = r["title"][:50]
        seller = r.get("seller", "")[:15]
        print(
            f"  {i:<3} ${r['total']:>7.2f} ${r['price']:>7.2f} ${r['shipping']:>5.2f} "
            f"{seller:<15} {title}{margin}"
        )

    if results and results[0].get("note"):
        print(f"\n  {results[0]['note']}")
        print(f"  URL: {results[0]['url']}")


def main():
    parser = argparse.ArgumentParser(description="Find cheapest eBay listings for fulfillment")
    parser.add_argument("query", nargs="?", help="Item to search for on eBay")
    parser.add_argument("--max", type=float, help="Maximum price filter")
    parser.add_argument("--pending-orders", action="store_true", help="Find listings for all pending Shopify orders")
    args = parser.parse_args()

    if args.pending_orders:
        print("\nFetching pending Shopify orders...")
        orders = fetch_pending_shopify_orders()
        if not orders:
            print("  No unfulfilled orders found.")
            return

        print(f"  Found {len(orders)} unfulfilled orders\n")
        print("=" * 70)

        for order in orders:
            print(f"\n  Order {order['order_number']} — {order['customer_city']}")
            print(f"  Placed: {order['created_at']}")

            for item in order["items"]:
                results = search_ebay_api(item["title"], max_price=item["price"])
                print_ebay_results(item["title"], results, shopify_price=item["price"])

        print()

    elif args.query:
        results = search_ebay_api(args.query, max_price=args.max)
        print_ebay_results(args.query, results)
        print()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
