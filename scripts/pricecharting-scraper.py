#!/usr/bin/env python3
"""
8-Bit Legacy — PriceCharting Price Scraper

Scrapes current prices from PriceCharting.com for items in your Shopify store.
Uses the public website (no API key needed). Respects rate limits.

This supplements the free CSV collection export — use this for:
  - On-demand price checks for specific items
  - Building a price database over time
  - Checking prices between weekly CSV exports

Usage:
  python3 pricecharting-scraper.py --from-shopify           # Scrape prices for all Shopify products
  python3 pricecharting-scraper.py --search "Mario Bros NES" # Search for a specific item
  python3 pricecharting-scraper.py --console "Nintendo NES"  # Scrape all items for a console
  python3 pricecharting-scraper.py --from-file items.txt     # Scrape items listed in a file
"""

import argparse
import csv
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
CONFIG_DIR = PROJECT_DIR / "config"
DATA_DIR = PROJECT_DIR / "data"

load_dotenv(CONFIG_DIR / ".env")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

# Rate limiting: be polite
REQUEST_DELAY = 2.0  # seconds between requests


def search_pricecharting(query: str) -> list[dict]:
    """Search PriceCharting for items matching a query."""
    url = f"https://www.pricecharting.com/search-products?q={quote_plus(query)}&type=videogames"

    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")

    results = []
    table = soup.find("table", {"id": "games_table"})
    if not table:
        return results

    rows = table.find("tbody").find_all("tr") if table.find("tbody") else []

    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 4:
            continue

        title_link = cols[0].find("a")
        if not title_link:
            continue

        title = title_link.get_text(strip=True)
        url_path = title_link.get("href", "")
        console = cols[1].get_text(strip=True) if len(cols) > 1 else ""

        # Price columns: loose, cib, new
        loose = parse_price_text(cols[2].get_text(strip=True)) if len(cols) > 2 else 0
        cib = parse_price_text(cols[3].get_text(strip=True)) if len(cols) > 3 else 0
        new = parse_price_text(cols[4].get_text(strip=True)) if len(cols) > 4 else 0

        results.append({
            "name": title,
            "console": console,
            "url": f"https://www.pricecharting.com{url_path}" if url_path.startswith("/") else url_path,
            "loose_price": loose,
            "cib_price": cib,
            "new_price": new,
        })

    return results


def get_item_price(url: str) -> dict:
    """Get detailed pricing for a specific PriceCharting item page."""
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")

    prices = {}

    # Try to find price info from the price boxes
    for price_div in soup.find_all("div", class_="price"):
        label = price_div.find("span", class_="label")
        value = price_div.find("span", class_="price")
        if label and value:
            key = label.get_text(strip=True).lower().replace(" ", "_")
            prices[key] = parse_price_text(value.get_text(strip=True))

    # Also try the main used price display
    used_price = soup.find("td", {"id": "used_price"})
    if used_price:
        prices["loose_price"] = parse_price_text(used_price.get_text(strip=True))

    cib_price = soup.find("td", {"id": "complete_price"})
    if cib_price:
        prices["cib_price"] = parse_price_text(cib_price.get_text(strip=True))

    new_price = soup.find("td", {"id": "new_price"})
    if new_price:
        prices["new_price"] = parse_price_text(new_price.get_text(strip=True))

    # Get title
    title_el = soup.find("h1", {"id": "product_name"})
    title = title_el.get_text(strip=True) if title_el else ""

    # Get console
    console_el = soup.find("h2", {"id": "product_console"})
    console = console_el.get_text(strip=True) if console_el else ""

    return {
        "name": title,
        "console": console,
        "url": url,
        **prices,
    }


def parse_price_text(text: str) -> float:
    """Extract a numeric price from text like '$12.99' or 'N/A'."""
    match = re.search(r"[\$]?([\d,]+\.?\d*)", text.replace(",", ""))
    if match:
        return float(match.group(1))
    return 0.0


def scrape_console_catalog(console_slug: str, max_pages: int = 5) -> list[dict]:
    """Scrape all items for a given console from PriceCharting."""
    items = []
    for page in range(1, max_pages + 1):
        url = f"https://www.pricecharting.com/console/{quote_plus(console_slug)}?sort=name&page={page}"
        print(f"  Scraping page {page}: {url}")

        resp = requests.get(url, headers=HEADERS)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        table = soup.find("table", {"id": "games_table"})
        if not table:
            break

        rows = table.find("tbody").find_all("tr") if table.find("tbody") else []
        if not rows:
            break

        for row in rows:
            cols = row.find_all("td")
            if len(cols) < 4:
                continue

            title_link = cols[0].find("a")
            if not title_link:
                continue

            items.append({
                "name": title_link.get_text(strip=True),
                "console": console_slug,
                "url": f"https://www.pricecharting.com{title_link.get('href', '')}",
                "loose_price": parse_price_text(cols[1].get_text(strip=True)) if len(cols) > 1 else 0,
                "cib_price": parse_price_text(cols[2].get_text(strip=True)) if len(cols) > 2 else 0,
                "new_price": parse_price_text(cols[3].get_text(strip=True)) if len(cols) > 3 else 0,
            })

        time.sleep(REQUEST_DELAY)

    return items


def save_results(items: list[dict], filename_prefix: str = "scraped-prices"):
    """Save scraped results to CSV."""
    if not items:
        print("  No items to save.")
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = DATA_DIR / f"{filename_prefix}_{timestamp}.csv"

    with open(filepath, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=items[0].keys())
        writer.writeheader()
        writer.writerows(items)

    print(f"  Saved {len(items)} items to: {filepath}")
    return filepath


def main():
    parser = argparse.ArgumentParser(description="Scrape PriceCharting prices")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--search", help="Search for a specific item")
    group.add_argument("--console", help="Scrape all items for a console (e.g., 'nes', 'super-nintendo', 'gameboy')")
    group.add_argument("--from-file", help="Scrape items listed in a text file (one per line)")
    group.add_argument("--url", help="Get prices for a specific PriceCharting URL")

    parser.add_argument("--pages", type=int, default=5, help="Max pages to scrape per console (default: 5)")
    parser.add_argument("--save", action="store_true", help="Save results to CSV")
    args = parser.parse_args()

    if args.search:
        print(f"\nSearching PriceCharting for: {args.search}")
        results = search_pricecharting(args.search)
        if results:
            print(f"\n  {'Item':<45} {'Console':<20} {'Loose':>8} {'CIB':>8} {'New':>8}")
            print(f"  {'-' * 45} {'-' * 20} {'-' * 8} {'-' * 8} {'-' * 8}")
            for r in results:
                name = r["name"][:45]
                console = r["console"][:20]
                print(f"  {name:<45} {console:<20} ${r['loose_price']:>7.2f} ${r['cib_price']:>7.2f} ${r['new_price']:>7.2f}")
        else:
            print("  No results found.")

        if args.save and results:
            save_results(results, "search-results")

    elif args.console:
        print(f"\nScraping console catalog: {args.console}")
        items = scrape_console_catalog(args.console, args.pages)
        print(f"  Found {len(items)} items")

        if args.save and items:
            save_results(items, f"console-{args.console}")

    elif args.url:
        print(f"\nGetting prices for: {args.url}")
        item = get_item_price(args.url)
        print(json.dumps(item, indent=2))

    elif args.from_file:
        print(f"\nScraping items from: {args.from_file}")
        all_results = []
        with open(args.from_file) as f:
            items = [line.strip() for line in f if line.strip()]

        for i, item_name in enumerate(items):
            print(f"  [{i + 1}/{len(items)}] Searching: {item_name}")
            results = search_pricecharting(item_name)
            if results:
                all_results.append(results[0])  # Take best match
                print(f"    Found: {results[0]['name']} — loose: ${results[0]['loose_price']:.2f}")
            else:
                print(f"    No results found")
            time.sleep(REQUEST_DELAY)

        if args.save and all_results:
            save_results(all_results, "batch-lookup")


if __name__ == "__main__":
    main()
