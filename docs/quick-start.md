# 8-Bit Legacy 2026 — Quick Start Guide

## What We've Built

```
~/Projects/8bit-legacy/
├── CLAUDE.md                          # Project context for Claude Code
├── config/
│   ├── .env.example                   # API keys template (copy to .env)
│   ├── pricing.json                   # Multiplier, min profit, fee config
├── scripts/
│   ├── price-sync.py                  # PriceCharting CSV → Shopify price updater
│   ├── pricecharting-scraper.py       # Scrape prices from PriceCharting (no subscription)
│   ├── ebay-finder.py                 # Find cheapest eBay listing for orders
│   └── social-generator.py            # Generate social media post batches
├── docs/
│   ├── quick-start.md                 # This file
│   ├── google-ads-strategy.md         # Full Google Shopping ads playbook
│   └── podcast-content-pipeline.md    # Podcast recording → editing → clips → scheduling
├── data/                              # PriceCharting CSVs, reports (gitignored)
└── assets/                            # Brand assets, templates, ad creatives
```

---

## Step-by-Step: Getting Started

### Step 1: Set Up Shopify API Access (~5 min)
1. Go to your Shopify admin → Settings → Apps and sales channels → Develop apps
2. Create a new app called "8-Bit Legacy Automation"
3. Configure Admin API scopes: `read_products`, `write_products`, `read_orders`
4. Install the app → copy the Admin API access token
5. Copy `config/.env.example` to `config/.env` and fill in:
   ```
   SHOPIFY_STORE_URL=your-store.myshopify.com
   SHOPIFY_ACCESS_TOKEN=shpat_xxxxx
   ```

### Step 2: Export PriceCharting Collection (~10 min)
1. Go to pricecharting.com → your collection
2. Click "Export" → download CSV
3. Save to `data/pricecharting-export.csv`

### Step 3: Run Price Sync (Dry Run First)
```bash
cd ~/Projects/8bit-legacy
pip3 install -r requirements.txt

# Dry run — see what would change without touching Shopify
python3 scripts/price-sync.py data/pricecharting-export.csv --report

# When ready, apply changes
python3 scripts/price-sync.py data/pricecharting-export.csv --apply
```

### Step 4: Test eBay Finder
```bash
# Search for any item
python3 scripts/ebay-finder.py "Super Mario Bros 3 NES"

# With Shopify configured, check all pending orders:
python3 scripts/ebay-finder.py --pending-orders
```

### Step 5: Generate Social Media Posts
```bash
# Generate 20 posts
python3 scripts/social-generator.py --batch 20

# Save as JSON for scheduling
python3 scripts/social-generator.py --batch 20 --json --output data/posts/
```

---

## Next Steps (In Order)

1. **[ ] Set up Shopify API** — enables all automation scripts
2. **[ ] Run price sync** — refresh all product prices to current market
3. **[ ] Install Google & YouTube Shopify app** — connect product feed to Merchant Center
4. **[ ] Set up Google Ads campaign** — follow docs/google-ads-strategy.md
5. **[ ] Create Buffer account** — connect FB/IG/TikTok for post scheduling
6. **[ ] Generate first social media batch** — start consistent posting
7. **[ ] Schedule first podcast recording** — get the guys together
8. **[ ] Get AutoPod trial** — test the editing workflow
9. **[ ] Start Pokemon card research** — next product line expansion
