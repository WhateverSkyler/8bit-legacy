# 8-Bit Legacy — Project Instructions

## Overview
Retro gaming + Pokemon card ecommerce store. eBay arbitrage/dropship model on Shopify (Basic plan).
- **Shopify store:** 8-Bit Legacy (8bitlegacy.com)
- **Business model:** Customer orders → buy cheapest matching eBay listing → ship direct to customer (no physical inventory)
- **Pricing:** Market price × multiplier (1.35x default, configurable per category in `config/pricing.json`)
- **Google Ads:** Separate account under personal email (Customer ID: 822-210-2291)
- **Podcast:** The 8-Bit Legacy Podcast (3 person, biweekly, YouTube + socials)
- **GitHub:** WhateverSkyler/8bit-legacy (synced between macOS + Linux)

## Product Lines
- **Retro Games:** NES, SNES, N64, Game Boy, Genesis, PS1, PS2, GameCube, Dreamcast, Saturn, GBA — priced via PriceCharting
- **Pokemon Cards:** Singles priced via TCGPlayer market prices (Pokemon TCG API), tagged by set/rarity. Sealed products (booster packs, ETBs, boxes) via CSV import.

## Project Structure
```
scripts/          — Python automation scripts
  price-sync.py              — PriceCharting CSV → Shopify price updater
  pricecharting-scraper.py   — Scrape prices from PriceCharting (no API key)
  ebay-finder.py             — Find cheapest eBay listing for fulfillment
  social-generator.py        — Generate social media post batches
  pokemon-card-importer.py   — Import Pokemon cards from Pokemon TCG API
config/           — Pricing config, API keys (gitignored .env)
data/             — CSVs, exports, price snapshots, sealed product templates
docs/             — Business docs, SOPs, content plans
assets/           — Brand assets, templates, ad creatives
dashboard/        — Next.js 16 management dashboard (see below)
```

## Dashboard (dashboard/)
Next.js 16.2.1 SaaS dashboard for managing the store. Light theme, Nintendo Switch-inspired UI.

**Tech stack:** TypeScript, Tailwind v4, Framer Motion, Recharts, Lucide React, TanStack Query/Table, better-sqlite3 + Drizzle ORM

**Brand:** Nunito font, orange (#ff9526) from 8bitlegacy.com, sky-blue accent (#0EA5E9). Light theme only (no dark mode).

**To run:**
```bash
cd dashboard && npm install && npm run dev -- --port 3001
```

**Pages:** Dashboard, Orders, Fulfillment, Inventory, Price Sync, eBay Finder, Social Media, Google Ads, Analytics, Settings

**Architecture:**
- `src/lib/` — TypeScript business logic (pricing, matching, Shopify/eBay/Google Ads APIs, Pokemon price sync)
- `src/app/api/` — API routes with sample data fallbacks (works without API keys)
- `db/` — SQLite + Drizzle ORM schema for local caching
- `src/hooks/` — TanStack Query hooks for all data fetching
- `src/components/ui/` — Reusable component library

**Automation Systems:**
- `src/lib/scheduler.ts` — node-cron job scheduler with locking and run logging
- `src/lib/safety.ts` — Hard/soft limits, circuit breakers for pricing and ads
- `src/lib/order-validator.ts` — Validates order prices against market before fulfillment
- `src/lib/pokemon-price-sync.ts` — Refreshes Pokemon card prices from TCGPlayer API
- `src/lib/google-ads.ts` — Google Ads API client (GAQL queries, negative keywords)
- Fulfillment Tracker — order lifecycle: pending → ordered → shipped → delivered → fulfilled
- Automated Pricing Engine — scrape PriceCharting → match → safety check → auto-apply
- Smart Margin Engine — factors ad cost/order into profit calculations

**Scheduled Jobs (5 total):**
| Job | Cron | Description |
|-----|------|-------------|
| shopify-product-sync | Every 4 hours | Sync products and orders from Shopify into local DB |
| google-ads-sync | Daily 1 AM ET | Pull campaign performance data from Google Ads |
| fulfillment-check | Every 30 min | Check unfulfilled orders + validate prices against market |
| price-sync | Every 4 hours | Sync game prices from PriceCharting, auto-apply safe changes |
| pokemon-price-sync | 3 AM + 3 PM ET | Refresh Pokemon card prices from TCGPlayer API |

**DB tables (16 total):** products, variants, orders, orderLineItems, priceSyncRuns, priceSyncItems, ebaySearches, socialPosts, settings, automationRuns, fulfillmentTasks, fulfillmentAlerts, priceSnapshots, googleAdsPerformance, googleAdsSearchTerms, googleAdsActions

**API Routes (30+):**
- `/api/shopify/` — products, orders, sync
- `/api/price-sync/` — upload, diff, apply, history, staleness
- `/api/automation/price-sync/run` — full automated pricing workflow
- `/api/fulfillment/` — tasks, alerts, validate, complete
- `/api/pokemon/import` — list sets (GET), trigger import (POST)
- `/api/google-ads/` — performance, search-terms, sync
- `/api/social/` — generate, schedule, analytics
- `/api/scheduler/status` — scheduler dashboard
- `/api/settings` — config management

## Pokemon Card Import
```bash
# Preview a set (no products created)
python3 scripts/pokemon-card-importer.py --set sv9 --dry-run --min-price 1

# Import a set to Shopify (as DRAFT products)
python3 scripts/pokemon-card-importer.py --set sv9 --min-price 1

# When a new set releases, auto-detect and import
python3 scripts/pokemon-card-importer.py --new-sets

# Import sealed products from CSV
python3 scripts/pokemon-card-importer.py --sealed data/pokemon-sealed-template.csv

# List all available sets
python3 scripts/pokemon-card-importer.py --list-sets
```
- Cards priced using TCGPlayer market price × 1.15 (via free Pokemon TCG API)
- $500 max price cap — no high-value cards
- Minimum market price: $5 (below this, fees eat all profit)
- Condition listed as "Lightly Played" — sourced from eBay USED/LP listings
- Products created as DRAFT — must manually activate and publish to Online Store when ready
- Sealed product template: `data/pokemon-sealed-template.csv`

## Key APIs
- **Shopify Admin API** (GraphQL) — product CRUD, order data, fulfillment
- **PriceCharting** — free CSV export + web scraping for retro game prices
- **Pokemon TCG API** — free, card data + images + TCGPlayer market prices
- **Google Ads API** — campaign management, reporting (Customer ID: 822-210-2291)
- **eBay Browse API** — search active listings for fulfillment (App: "Navi")

## Pricing Rules
- Default multiplier: 1.35x market price
- Category multipliers: pokemon_cards 1.35x, retro_games 1.35x, consoles 1.30x, accessories 1.40x
- Minimum profit threshold: $3.00 per item (after Shopify fees)
- Shopify fees: 2.9% + $0.30 per transaction (Basic plan, Shopify Payments)
- Auto-apply: enabled for changes under 15%. Changes 15-30% need manual review. Over 30% rejected.
- Circuit breaker trips if >20 items have >15% change in a single run.
- Pokemon cards: $500 max market price cap

## Safety System
- **Hard limits:** 30% max price change, $25 max daily ad spend, never price below cost
- **Soft limits:** configurable in Settings page (auto-apply threshold, ROAS minimums, etc.)
- **Circuit breakers:** pricing + google_ads — trip automatically, reset manually
- **Order validation:** every 30 min, checks unfulfilled orders against market prices, creates critical alerts for potential losses

## Secrets
All API keys and tokens go in `config/.env` and `dashboard/.env.local` (both gitignored). Never commit secrets.

## Remaining Work
- Deploy dashboard to VPS for 24/7 scheduler operation
- Plan and launch first Google Ads campaign (Ads connected, Merchant Center live with 12K+ products)
- Set up conversion tracking (Google Ads tag on Shopify checkout) before running ads
- Import newest Pokemon sets when TCGPlayer pricing becomes available (me3 Perfect Order, me2pt5 Ascended Heroes)
- Website frontend revamp (banners, styling consistency, homepage updates)
- YouTube Shopping — unlocks at 1,000 subscribers

## Completed
- Google & YouTube Shopify app installed, Merchant Center connected (ID: 5296797260, 12K products approved)
- Google Ads account linked (822-210-2291)
- Pokemon cards live — 1,176+ cards at 1.15x TCGPlayer market, 9 collections, nav added
- All CIB variants purchasable (6,112 fixed)
- Full price refresh completed — 6,121 products scanned, 5,000+ prices updated
- Inventory API scopes (read + write) added
- Automation hardened — retry logic, title matching safety, price caps, timeouts
- First podcast episode recorded April 9, 2026
