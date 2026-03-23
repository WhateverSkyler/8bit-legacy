#!/usr/bin/env python3
"""
8-Bit Legacy — Social Media Post Generator

Generates social media post batches from Shopify product data.
Creates post copy + image suggestions for scheduling on Buffer/Later.

Usage:
  python3 social-generator.py --batch 20                  # Generate 20 posts
  python3 social-generator.py --type deal-of-the-day      # Generate specific post type
  python3 social-generator.py --batch 20 --output posts/  # Save to folder
"""

import argparse
import json
import os
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
CONFIG_DIR = PROJECT_DIR / "config"
DATA_DIR = PROJECT_DIR / "data"

load_dotenv(CONFIG_DIR / ".env")

SHOPIFY_STORE_URL = os.getenv("SHOPIFY_STORE_URL")
SHOPIFY_ACCESS_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")
STORE_URL = "https://8bitlegacy.com"  # Update to actual store URL

# Post templates
POST_TEMPLATES = {
    "new_arrival": {
        "captions": [
            "Just added to the shop! {product_name} for only ${price}. Tested, cleaned, and ready to play. Link in bio!",
            "New drop alert! {product_name} — ${price}. Every game is quality-checked before it ships. Shop now at 8bitlegacy.com",
            "{product_name} just hit the shelves for ${price}. Grab it before it's gone! Link in bio.",
        ],
        "hashtags": "#retrogaming #{console_tag} #8bitlegacy #retrogames #vintagegaming #gamecollecting #gamecollector",
    },
    "deal_of_the_day": {
        "captions": [
            "Deal of the Day! {product_name} — just ${price}. Compare that to what other retro stores charge... we'll wait. 8bitlegacy.com",
            "Today's pick: {product_name} for ${price}. Quality games, fair prices. That's the 8-Bit Legacy difference.",
            "Why overpay? {product_name} is just ${price} at 8-Bit Legacy. Every order quality-checked. Link in bio!",
        ],
        "hashtags": "#retrogaming #{console_tag} #8bitlegacy #retrogamedeals #gamingdeals #cheapgames #retrocollecting",
    },
    "nostalgia": {
        "captions": [
            "Remember spending hours playing {product_name}? Those were the days. Relive the memories — ${price} at 8bitlegacy.com",
            "This one hits different. {product_name} — a certified classic. Pick it up for just ${price}. Link in bio.",
            "Tell us your favorite memory with {product_name}. This classic is available now for ${price}!",
        ],
        "hashtags": "#retrogaming #{console_tag} #nostalgia #90sgaming #80sgaming #childhoodmemories #8bitlegacy #throwback",
    },
    "collection_spotlight": {
        "captions": [
            "Building your {console} collection? We've got you covered with tested, affordable games starting at prices way below the competition. 8bitlegacy.com",
            "The {console} library is stacked. Browse our full selection of tested games at 8bitlegacy.com — link in bio!",
            "Your {console} collection deserves better than eBay gambles. Every 8-Bit Legacy game is quality-checked before it ships.",
        ],
        "hashtags": "#retrogaming #{console_tag} #gamecollection #gamecollecting #8bitlegacy #retrocollection",
    },
    "did_you_know": {
        "captions": [
            "Did you know? {trivia}\n\nShop retro games at fair prices: 8bitlegacy.com",
            "Gaming history: {trivia}\n\nWe carry thousands of retro titles at prices that don't make you cry. Link in bio!",
        ],
        "hashtags": "#retrogaming #gamingtrivia #gaminghistory #8bitlegacy #retrogames #gamingfacts",
    },
}

GAMING_TRIVIA = [
    "The original Super Mario Bros. cartridge has sold for over $2 million at auction — but you can play it for way less at 8-Bit Legacy.",
    "The Nintendo Entertainment System saved the video game industry after the crash of 1983.",
    "Sonic the Hedgehog was designed to be Sega's answer to Mario — and the rivalry defined a generation of gaming.",
    "The Game Boy sold over 118 million units worldwide. Its library of games is still one of the best ever.",
    "The Legend of Zelda was one of the first console games to include a battery-backed save feature.",
    "Street Fighter II is considered the game that popularized the fighting game genre worldwide.",
    "The N64 controller was the first major console controller with an analog stick.",
    "Pokémon Red and Blue were originally released in Japan in 1996 as Pocket Monsters Red and Green.",
    "The PlayStation was originally designed as a CD-ROM add-on for the Super Nintendo.",
    "Tetris is the best-selling game of all time with over 500 million copies sold across all platforms.",
    "The Sega Genesis was the first 16-bit console to gain significant traction in North America.",
    "Super Metroid is consistently ranked as one of the greatest video games ever made.",
    "The SNES had a secret chip in Star Fox called the Super FX chip that enabled 3D graphics.",
    "Donkey Kong was originally going to be a Popeye game, but Nintendo couldn't get the license.",
    "The Atari 2600 was the first console to use swappable game cartridges.",
]

CONSOLE_TAGS = {
    "NES": "nes #nintendo",
    "Nintendo": "nintendo",
    "Super Nintendo": "snes #supernintendo",
    "SNES": "snes #supernintendo",
    "Nintendo 64": "n64 #nintendo64",
    "N64": "n64 #nintendo64",
    "Game Boy": "gameboy #nintendo",
    "Game Boy Color": "gameboycolor #gbc",
    "Game Boy Advance": "gameboyadvance #gba",
    "GameCube": "gamecube #nintendo",
    "Sega Genesis": "segagenesis #sega",
    "Genesis": "segagenesis #sega",
    "Sega Saturn": "segasaturn #sega",
    "Dreamcast": "dreamcast #sega",
    "PlayStation": "playstation #ps1 #sony",
    "PS1": "playstation #ps1",
    "PlayStation 2": "ps2 #playstation2",
    "PS2": "ps2 #playstation2",
    "Xbox": "xbox #originalxbox",
    "Atari 2600": "atari #atari2600",
}


def fetch_shopify_products(limit: int = 100) -> list[dict]:
    """Fetch products from Shopify for post generation."""
    if not SHOPIFY_STORE_URL or not SHOPIFY_ACCESS_TOKEN:
        print("  Shopify not configured — using sample data")
        return get_sample_products()

    url = f"https://{SHOPIFY_STORE_URL}/admin/api/2024-10/graphql.json"
    headers = {
        "X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN,
        "Content-Type": "application/json",
    }

    query = f"""
    {{
      products(first: {min(limit, 250)}, query: "status:active") {{
        edges {{
          node {{
            title
            handle
            tags
            images(first: 1) {{
              edges {{
                node {{
                  url
                }}
              }}
            }}
            variants(first: 1) {{
              edges {{
                node {{
                  price
                }}
              }}
            }}
          }}
        }}
      }}
    }}
    """

    resp = requests.post(url, json={"query": query}, headers=headers)
    resp.raise_for_status()
    data = resp.json()

    products = []
    for edge in data.get("data", {}).get("products", {}).get("edges", []):
        node = edge["node"]
        price = float(node["variants"]["edges"][0]["node"]["price"]) if node["variants"]["edges"] else 0
        image = node["images"]["edges"][0]["node"]["url"] if node["images"]["edges"] else None

        # Try to extract console from title or tags
        console = ""
        for tag in node.get("tags", []):
            if tag in CONSOLE_TAGS:
                console = tag
                break

        products.append({
            "title": node["title"],
            "handle": node["handle"],
            "price": price,
            "image_url": image,
            "console": console,
            "url": f"{STORE_URL}/products/{node['handle']}",
        })

    return products


def get_sample_products() -> list[dict]:
    """Sample products for testing without Shopify connection."""
    return [
        {"title": "Super Mario Bros 3", "handle": "super-mario-bros-3", "price": 34.99, "console": "NES", "image_url": None, "url": f"{STORE_URL}/products/super-mario-bros-3"},
        {"title": "The Legend of Zelda: A Link to the Past", "handle": "zelda-link-to-the-past", "price": 44.99, "console": "Super Nintendo", "image_url": None, "url": f"{STORE_URL}/products/zelda-link-to-the-past"},
        {"title": "Sonic the Hedgehog 2", "handle": "sonic-2", "price": 14.99, "console": "Sega Genesis", "image_url": None, "url": f"{STORE_URL}/products/sonic-2"},
        {"title": "GoldenEye 007", "handle": "goldeneye-007", "price": 29.99, "console": "Nintendo 64", "image_url": None, "url": f"{STORE_URL}/products/goldeneye-007"},
        {"title": "Pokemon Red", "handle": "pokemon-red", "price": 49.99, "console": "Game Boy", "image_url": None, "url": f"{STORE_URL}/products/pokemon-red"},
        {"title": "Final Fantasy VII", "handle": "final-fantasy-vii", "price": 39.99, "console": "PlayStation", "image_url": None, "url": f"{STORE_URL}/products/final-fantasy-vii"},
        {"title": "Super Smash Bros", "handle": "super-smash-bros", "price": 39.99, "console": "Nintendo 64", "image_url": None, "url": f"{STORE_URL}/products/super-smash-bros"},
        {"title": "Mega Man 2", "handle": "mega-man-2", "price": 24.99, "console": "NES", "image_url": None, "url": f"{STORE_URL}/products/mega-man-2"},
    ]


def generate_post(product: dict, post_type: str = None) -> dict:
    """Generate a single social media post."""
    if not post_type:
        post_type = random.choice(["new_arrival", "deal_of_the_day", "nostalgia"])

    template = POST_TEMPLATES.get(post_type)
    if not template:
        print(f"  Unknown post type: {post_type}")
        return None

    console_tag = CONSOLE_TAGS.get(product.get("console", ""), "retro")

    if post_type == "did_you_know":
        trivia = random.choice(GAMING_TRIVIA)
        caption = random.choice(template["captions"]).format(trivia=trivia)
    elif post_type == "collection_spotlight":
        caption = random.choice(template["captions"]).format(
            console=product.get("console", "retro gaming")
        )
    else:
        caption = random.choice(template["captions"]).format(
            product_name=product["title"],
            price=f"{product['price']:.2f}",
            console=product.get("console", ""),
        )

    hashtags = template["hashtags"].format(console_tag=console_tag)

    return {
        "type": post_type,
        "caption": f"{caption}\n\n{hashtags}",
        "product": product["title"],
        "product_url": product.get("url", ""),
        "image_url": product.get("image_url", ""),
        "image_suggestion": f"Product photo of {product['title']}" + (f" for {product.get('console', '')}" if product.get("console") else ""),
    }


def generate_batch(products: list[dict], count: int = 20) -> list[dict]:
    """Generate a batch of posts with varied types."""
    posts = []

    # Mix of post types
    type_rotation = [
        "new_arrival", "deal_of_the_day", "nostalgia",
        "new_arrival", "did_you_know", "deal_of_the_day",
        "collection_spotlight", "new_arrival", "nostalgia", "deal_of_the_day",
    ]

    for i in range(count):
        post_type = type_rotation[i % len(type_rotation)]
        product = random.choice(products)
        post = generate_post(product, post_type)
        if post:
            posts.append(post)

    return posts


def main():
    parser = argparse.ArgumentParser(description="Generate social media posts for 8-Bit Legacy")
    parser.add_argument("--batch", type=int, default=10, help="Number of posts to generate")
    parser.add_argument("--type", choices=list(POST_TEMPLATES.keys()), help="Specific post type")
    parser.add_argument("--output", help="Output directory for posts")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    print("\n8-BIT LEGACY — Social Media Post Generator")
    print("=" * 50)

    products = fetch_shopify_products()
    print(f"  Loaded {len(products)} products\n")

    if args.type:
        posts = []
        for _ in range(args.batch):
            product = random.choice(products)
            post = generate_post(product, args.type)
            if post:
                posts.append(post)
    else:
        posts = generate_batch(products, args.batch)

    if args.json:
        print(json.dumps(posts, indent=2))
    else:
        for i, post in enumerate(posts, 1):
            print(f"\n--- Post {i} [{post['type'].upper()}] ---")
            print(f"Product: {post['product']}")
            print(f"Caption:\n{post['caption']}")
            print(f"Image: {post['image_suggestion']}")
            if post.get("product_url"):
                print(f"Link: {post['product_url']}")

    if args.output:
        os.makedirs(args.output, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d")
        filepath = Path(args.output) / f"posts_{timestamp}.json"
        with open(filepath, "w") as f:
            json.dump(posts, f, indent=2)
        print(f"\n  Saved {len(posts)} posts to: {filepath}")

    print(f"\n  Generated {len(posts)} posts. Schedule these on Buffer/Later!")


if __name__ == "__main__":
    main()
