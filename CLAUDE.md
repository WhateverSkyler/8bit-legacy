# 8-Bit Legacy — Project Instructions

## Overview
Retro gaming + Pokemon card ecommerce store. eBay arbitrage/dropship model on Shopify (Basic plan).
- **Shopify store:** 8-Bit Legacy (8bitlegacy.com)
- **Business model:** Customer orders → buy cheapest matching eBay listing → ship direct to customer
- **Pricing:** PriceCharting loose price × 1.35 multiplier (adjustable in config)
- **Google Ads:** Separate account under personal email
- **Podcast:** The 8-Bit Legacy Podcast (3 person, biweekly, YouTube + socials)
- **GitHub:** WhateverSkyler/8bit-legacy (synced between macOS + Linux)

## Project Structure
```
scripts/          — Python automation scripts (pricing, ads, social, fulfillment)
config/           — API keys, multipliers, settings (gitignored secrets)
data/             — PriceCharting CSVs, exports, price snapshots
docs/             — Business docs, SOPs, content plans
assets/           — Brand assets, templates, ad creatives
dashboard/        — Next.js 16 management dashboard (see below)
```

## Dashboard (dashboard/)
Next.js 16.2.1 SaaS dashboard for managing the store. Light theme, Nintendo Switch-inspired UI.

**Tech stack:** TypeScript, Tailwind v4, Framer Motion, Recharts, Lucide React, TanStack Query/Table, better-sqlite3 + Drizzle ORM

**Brand:** Nunito font, orange (#ff9526) from 8bitlegacy.com, sky-blue accent (#0EA5E9)

**To run:**
```bash
cd dashboard && npm install && npm run dev -- --port 3001
```

**Pages:** Dashboard, Orders, Inventory, Price Sync, eBay Finder, Social Media, Analytics, Settings

**Architecture:**
- `src/lib/` — TypeScript ports of Python pricing/matching/Shopify/eBay logic
- `src/app/api/` — 10 API routes with sample data fallbacks (works without API keys)
- `db/` — SQLite + Drizzle ORM schema for local caching
- `src/hooks/` — TanStack Query hooks for all data fetching
- `src/components/ui/` — Reusable component library (button, card, badge, tabs, dialog, etc.)

**Pages:** Dashboard, Orders, Fulfillment, Inventory, Price Sync, eBay Finder, Social Media, Google Ads, Analytics, Settings

**Automation Systems (built):**
- `src/lib/scheduler.ts` — node-cron job scheduler with locking and run logging
- `src/lib/safety.ts` — Hard/soft limits, circuit breakers for pricing and ads
- `src/lib/buffer.ts` — Buffer API client for social media scheduling
- `src/lib/google-ads.ts` — Google Ads API client (GAQL queries, negative keywords)
- Fulfillment Tracker — order lifecycle: pending → ordered → shipped → delivered → fulfilled
- Automated Pricing Engine — scrape PriceCharting → match → safety check → auto-apply
- Smart Margin Engine — factors ad cost/order into profit calculations
- Social Auto-Scheduling — generate posts → schedule to Buffer
- Google Ads Management — sync performance, auto-optimize bids, manage negative keywords

**DB tables (14 total):** products, variants, orders, orderLineItems, priceSyncRuns, priceSyncItems, ebaySearches, socialPosts, settings, automationRuns, fulfillmentTasks, fulfillmentAlerts, priceSnapshots, googleAdsPerformance, googleAdsSearchTerms, googleAdsActions

**Remaining work:**
- Fill in dashboard/.env.local with real API credentials (Shopify, eBay, Google Ads, Buffer)
- Apply for Google Ads developer token (can take days)
- Connect Shopify to Google Merchant Center for Shopping feed
- Deploy to VPS and start scheduler

## Key APIs
- **Shopify Admin API** (GraphQL) — product CRUD, order data, bulk operations
- **PriceCharting** — free collection export (CSV) for retro game prices
- **Pokemon TCG API** — free, card data + images
- **Google Ads API** — campaign management, reporting
- **eBay Browse API** — search active listings for fulfillment
- **Buffer API** — social media scheduling

## Pricing Rules
- Default multiplier: 1.35x PriceCharting loose price
- Minimum profit threshold: $3.00 per item (after Shopify fees)
- Shopify fees: 2.9% + $0.30 per transaction (Basic plan, Shopify Payments)
- Items below minimum profit threshold get flagged for manual review

## Secrets
All API keys and tokens go in `config/.env` and `dashboard/.env.local` (both gitignored). Never commit secrets.
