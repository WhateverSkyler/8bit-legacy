#!/usr/bin/env python3
"""
8-Bit Legacy — Profit Report

Generates a comprehensive profit report by analyzing Shopify orders,
comparing sell prices against estimated market prices (PriceCharting).
Factors in Shopify fees and estimated eBay fulfillment costs.

Usage:
  # Full report for the current month
  python3 scripts/profit-report.py

  # Report for a specific date range
  python3 scripts/profit-report.py --from 2026-04-01 --to 2026-04-30

  # Include unfulfilled orders
  python3 scripts/profit-report.py --include-unfulfilled

  # CSV export
  python3 scripts/profit-report.py --csv data/profit-report.csv

  # Summary only (no per-order breakdown)
  python3 scripts/profit-report.py --summary
"""

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
CONFIG_DIR = PROJECT_DIR / "config"
DATA_DIR = PROJECT_DIR / "data"

load_dotenv(CONFIG_DIR / ".env")
load_dotenv(PROJECT_DIR / "dashboard" / ".env.local")

SHOPIFY_STORE = os.getenv("SHOPIFY_STORE_URL", "")
SHOPIFY_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN", "")
SHOPIFY_API_VERSION = "2024-10"

with open(CONFIG_DIR / "pricing.json") as f:
    PRICING = json.load(f)

MULTIPLIER = PRICING["default_multiplier"]
FEE_PCT = PRICING["shopify_fee_percent"]
FEE_FIXED = PRICING["shopify_fee_fixed"]

# Estimated eBay cost as a percentage of sell price (for profit estimation)
# In reality, we'd look up the actual eBay purchase price, but this serves as
# a good estimate when actual cost data isn't available
ESTIMATED_COST_RATIO = 1.0 / MULTIPLIER  # Inverse of multiplier = ~74% of sell price


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


def fetch_orders(from_date=None, to_date=None, include_unfulfilled=False):
    """Fetch orders from Shopify within a date range."""
    orders = []
    cursor = None

    # Build date filter
    query_parts = []
    if from_date:
        query_parts.append(f"created_at:>={from_date}")
    if to_date:
        query_parts.append(f"created_at:<={to_date}")
    if not include_unfulfilled:
        query_parts.append("fulfillment_status:shipped OR fulfillment_status:fulfilled")

    query_filter = " AND ".join(query_parts) if query_parts else ""

    while True:
        after = f', after: "{cursor}"' if cursor else ""
        query_str = f', query: "{query_filter}"' if query_filter else ""
        gql = f"""
        {{
          orders(first: 50{query_str}{after}, sortKey: CREATED_AT, reverse: true) {{
            edges {{
              cursor
              node {{
                id
                name
                createdAt
                displayFulfillmentStatus
                displayFinancialStatus
                totalPriceSet {{ shopMoney {{ amount currencyCode }} }}
                subtotalPriceSet {{ shopMoney {{ amount }} }}
                totalShippingPriceSet {{ shopMoney {{ amount }} }}
                totalTaxSet {{ shopMoney {{ amount }} }}
                lineItems(first: 20) {{
                  edges {{
                    node {{
                      title
                      quantity
                      originalUnitPriceSet {{ shopMoney {{ amount }} }}
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

        data = shopify_gql(gql)
        edges = data.get("data", {}).get("orders", {}).get("edges", [])

        for edge in edges:
            node = edge["node"]
            line_items = []
            for li_edge in node.get("lineItems", {}).get("edges", []):
                li = li_edge["node"]
                line_items.append({
                    "title": li["title"],
                    "quantity": li["quantity"],
                    "price": float(li["originalUnitPriceSet"]["shopMoney"]["amount"]),
                    "sku": li.get("sku") or "",
                })

            orders.append({
                "id": node["id"],
                "number": node["name"],
                "created_at": node["createdAt"],
                "fulfillment_status": node["displayFulfillmentStatus"],
                "financial_status": node["displayFinancialStatus"],
                "total": float(node["totalPriceSet"]["shopMoney"]["amount"]),
                "subtotal": float(node["subtotalPriceSet"]["shopMoney"]["amount"]),
                "shipping": float(node["totalShippingPriceSet"]["shopMoney"]["amount"]),
                "tax": float(node["totalTaxSet"]["shopMoney"]["amount"]),
                "line_items": line_items,
            })

        has_next = data.get("data", {}).get("orders", {}).get("pageInfo", {}).get("hasNextPage", False)
        if not has_next or not edges:
            break
        cursor = edges[-1]["cursor"]
        time.sleep(0.3)

    return orders


def analyze_order(order):
    """Analyze a single order for profit."""
    subtotal = order["subtotal"]

    # Shopify fees
    shopify_fee = subtotal * FEE_PCT + FEE_FIXED

    # Estimated cost (market price ~ sell price / multiplier)
    estimated_cost = subtotal * ESTIMATED_COST_RATIO

    # Gross profit estimate
    gross_profit = subtotal - estimated_cost - shopify_fee

    # Margin
    margin_pct = (gross_profit / subtotal * 100) if subtotal > 0 else 0

    return {
        **order,
        "shopify_fee": round(shopify_fee, 2),
        "estimated_cost": round(estimated_cost, 2),
        "gross_profit": round(gross_profit, 2),
        "margin_pct": round(margin_pct, 1),
    }


def print_report(analyzed_orders, summary_only=False):
    """Print a formatted profit report."""
    if not analyzed_orders:
        print("\n  No orders found in the specified date range.")
        return

    total_revenue = sum(o["subtotal"] for o in analyzed_orders)
    total_shipping = sum(o["shipping"] for o in analyzed_orders)
    total_fees = sum(o["shopify_fee"] for o in analyzed_orders)
    total_cost = sum(o["estimated_cost"] for o in analyzed_orders)
    total_profit = sum(o["gross_profit"] for o in analyzed_orders)
    avg_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0
    avg_order_value = total_revenue / len(analyzed_orders) if analyzed_orders else 0

    # Per-order breakdown
    if not summary_only:
        print(f"\n  {'Order':<10} {'Date':<12} {'Items':<4} {'Revenue':>9} {'Est Cost':>9} {'Fees':>7} {'Profit':>8} {'Margin':>7}")
        print(f"  {'-'*10} {'-'*12} {'-'*4} {'-'*9} {'-'*9} {'-'*7} {'-'*8} {'-'*7}")

        for o in analyzed_orders:
            date_str = o["created_at"][:10]
            item_count = sum(li["quantity"] for li in o["line_items"])
            profit_color = "" if o["gross_profit"] >= 0 else "!"
            print(
                f"  {o['number']:<10} {date_str:<12} {item_count:>4} "
                f"${o['subtotal']:>7.2f} ${o['estimated_cost']:>7.2f} "
                f"${o['shopify_fee']:>5.2f} ${o['gross_profit']:>6.2f} "
                f"{o['margin_pct']:>5.1f}%"
            )

    # Summary
    print(f"\n{'='*70}")
    print(f"  PROFIT SUMMARY")
    print(f"{'='*70}")
    print(f"  Orders:              {len(analyzed_orders)}")
    print(f"  Total Revenue:       ${total_revenue:>10.2f}")
    print(f"  Shipping Collected:  ${total_shipping:>10.2f}")
    print(f"  Est. Product Cost:   ${total_cost:>10.2f}")
    print(f"  Shopify Fees:        ${total_fees:>10.2f}")
    print(f"  ─────────────────────────────────────")
    print(f"  Estimated Profit:    ${total_profit:>10.2f}")
    print(f"  Average Margin:      {avg_margin:>9.1f}%")
    print(f"  Avg Order Value:     ${avg_order_value:>10.2f}")
    print(f"  Profit per Order:    ${total_profit / len(analyzed_orders):>10.2f}")

    # Top items by revenue
    item_revenue = {}
    for o in analyzed_orders:
        for li in o["line_items"]:
            key = li["title"]
            if key not in item_revenue:
                item_revenue[key] = {"title": key, "units": 0, "revenue": 0}
            item_revenue[key]["units"] += li["quantity"]
            item_revenue[key]["revenue"] += li["price"] * li["quantity"]

    if item_revenue:
        top_items = sorted(item_revenue.values(), key=lambda x: x["revenue"], reverse=True)[:10]
        print(f"\n  TOP 10 PRODUCTS BY REVENUE")
        print(f"  {'Product':<50} {'Units':>5} {'Revenue':>9}")
        print(f"  {'-'*50} {'-'*5} {'-'*9}")
        for item in top_items:
            print(f"  {item['title'][:50]:<50} {item['units']:>5} ${item['revenue']:>7.2f}")

    # Console breakdown (from SKUs and titles)
    console_revenue = {}
    for o in analyzed_orders:
        for li in o["line_items"]:
            # Try to detect console from title
            title_lower = li["title"].lower()
            console = "Other"
            for c in ["nes", "snes", "n64", "gamecube", "genesis", "playstation", "ps1", "ps2",
                       "gameboy", "gba", "dreamcast", "saturn", "xbox", "wii", "pokemon", "3ds", "ds"]:
                if c in title_lower:
                    console = c.upper()
                    break

            if console not in console_revenue:
                console_revenue[console] = 0
            console_revenue[console] += li["price"] * li["quantity"]

    if len(console_revenue) > 1:
        print(f"\n  REVENUE BY CATEGORY")
        for console, rev in sorted(console_revenue.items(), key=lambda x: x[1], reverse=True):
            bar = "=" * int(rev / total_revenue * 30) if total_revenue > 0 else ""
            print(f"  {console:<12} ${rev:>8.2f} {bar}")


def export_csv(analyzed_orders, csv_path):
    """Export profit report to CSV."""
    rows = []
    for o in analyzed_orders:
        for li in o["line_items"]:
            rows.append({
                "order_number": o["number"],
                "date": o["created_at"][:10],
                "product": li["title"],
                "sku": li["sku"],
                "quantity": li["quantity"],
                "unit_price": li["price"],
                "line_total": li["price"] * li["quantity"],
                "order_subtotal": o["subtotal"],
                "shopify_fee": o["shopify_fee"],
                "estimated_cost": o["estimated_cost"],
                "gross_profit": o["gross_profit"],
                "margin_pct": o["margin_pct"],
                "fulfillment_status": o["fulfillment_status"],
            })

    if rows:
        Path(csv_path).parent.mkdir(parents=True, exist_ok=True)
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        print(f"\n  CSV exported: {csv_path}")


def main():
    parser = argparse.ArgumentParser(description="Generate profit report from Shopify orders")
    parser.add_argument("--from", dest="from_date", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--to", dest="to_date", help="End date (YYYY-MM-DD)")
    parser.add_argument("--include-unfulfilled", action="store_true",
                        help="Include unfulfilled orders in the report")
    parser.add_argument("--csv", help="Export to CSV file")
    parser.add_argument("--summary", action="store_true", help="Show summary only, no per-order breakdown")

    args = parser.parse_args()

    if not SHOPIFY_STORE or not SHOPIFY_TOKEN:
        print("ERROR: Shopify credentials not configured")
        sys.exit(1)

    # Default to current month
    if not args.from_date:
        now = datetime.now()
        args.from_date = now.replace(day=1).strftime("%Y-%m-%d")
    if not args.to_date:
        args.to_date = datetime.now().strftime("%Y-%m-%d")

    print(f"  Profit Report: {args.from_date} to {args.to_date}")
    print(f"  {'Including' if args.include_unfulfilled else 'Excluding'} unfulfilled orders")

    # Fetch orders
    print("\n  Fetching orders from Shopify...")
    orders = fetch_orders(args.from_date, args.to_date, args.include_unfulfilled)
    print(f"  Found {len(orders)} orders")

    if not orders:
        print("\n  No orders in this date range.")
        return

    # Analyze
    analyzed = [analyze_order(o) for o in orders]

    # Report
    print_report(analyzed, summary_only=args.summary)

    # CSV export
    if args.csv:
        export_csv(analyzed, args.csv)


if __name__ == "__main__":
    main()
