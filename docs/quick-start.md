# 8-Bit Legacy 2026 — Quick Start Guide

## What We've Built

```
~/Projects/8bit-legacy/
├── CLAUDE.md                          # Project context for Claude Code
├── config/
│   ├── .env.example                   # API keys template (copy to .env)
│   └── pricing.json                   # Multiplier, min profit, fee config
├── scripts/
│   ├── price-sync.py                  # PriceCharting CSV → Shopify price updater
│   ├── pricecharting-scraper.py       # Scrape prices from PriceCharting (no subscription)
│   ├── ebay-finder.py                 # Find cheapest eBay listing for orders
│   └── social-generator.py            # Generate social media post batches
├── dashboard/                         # Next.js 16 management dashboard
│   ├── src/app/                       # 8 page routes + 10 API routes
│   ├── src/lib/                       # TypeScript business logic (pricing, matching, APIs)
│   ├── src/components/                # UI component library
│   ├── db/                            # SQLite + Drizzle ORM schema
│   └── public/                        # Logo, favicon, icons from 8bitlegacy.com
├── docs/
│   ├── quick-start.md                 # This file
│   ├── google-ads-strategy.md         # Full Google Shopping ads playbook
│   └── podcast-content-pipeline.md    # Podcast recording → editing → clips → scheduling
├── data/                              # PriceCharting CSVs, reports (gitignored)
└── assets/                            # Brand assets, templates, ad creatives
```

---

## Running the Dashboard

```bash
cd ~/Projects/8bit-legacy/dashboard
npm install
npm run dev -- --port 3001
# Open http://localhost:3001
```

The dashboard works out of the box with sample data. To connect real data, fill in `dashboard/.env.local` with your API keys.

---

## Setting Up API Access

### Step 1: Shopify API (~5 min)
1. Shopify admin → Settings → Apps and sales channels → Develop apps
2. Create app "8-Bit Legacy Automation"
3. Scopes: `read_products`, `write_products`, `read_orders`, `write_orders`
4. Install → copy access token
5. Fill in both `config/.env` and `dashboard/.env.local`:
   ```
   SHOPIFY_STORE_URL=your-store.myshopify.com
   SHOPIFY_ACCESS_TOKEN=shpat_xxxxx
   ```

### Step 2: PriceCharting Export (~10 min)
1. pricecharting.com → your collection → Export → download CSV
2. Save to `data/pricecharting-export.csv`
3. Use the dashboard Price Sync page or CLI:
   ```bash
   python3 scripts/price-sync.py data/pricecharting-export.csv --report
   ```

### Step 3: eBay API (Optional)
1. developer.ebay.com → create application
2. Get App ID (Client ID)
3. Add to `.env.local`: `EBAY_APP_ID=xxxxx`
4. Without this, eBay Finder shows manual search URLs instead of inline results

---

## CLI Scripts (Still Work Independently)

```bash
# Price sync — dry run
python3 scripts/price-sync.py data/pricecharting-export.csv --report

# Price sync — apply to Shopify
python3 scripts/price-sync.py data/pricecharting-export.csv --apply

# eBay search
python3 scripts/ebay-finder.py "Super Mario Bros 3 NES"

# eBay — check all pending orders
python3 scripts/ebay-finder.py --pending-orders

# Social media — generate 20 posts
python3 scripts/social-generator.py --batch 20

# PriceCharting — search
python3 scripts/pricecharting-scraper.py --search "Zelda Ocarina"
```

---

## Next Steps

1. **[ ] Set up Shopify API** — enables dashboard + all automation scripts
2. **[ ] Run first price sync** — refresh all product prices to current market
3. **[ ] Set up eBay API** — enables inline listing search in dashboard
4. **[ ] Install Google & YouTube Shopify app** — connect product feed to Merchant Center
5. **[ ] Set up Google Ads campaign** — follow docs/google-ads-strategy.md
6. **[ ] Create Buffer account** — connect FB/IG/TikTok for post scheduling
7. **[ ] Generate first social media batch** — start consistent posting
8. **[ ] Schedule first podcast recording** — get the guys together
9. **[ ] Get AutoPod trial** — test the editing workflow
10. **[ ] Start Pokemon card research** — next product line expansion
