# 8-Bit Legacy — Project Instructions

## Overview
Retro gaming + Pokemon card ecommerce store. eBay arbitrage/dropship model on Shopify (Basic plan).
- **Shopify store:** 8-Bit Legacy
- **Business model:** Customer orders → buy cheapest matching eBay listing → ship direct to customer
- **Pricing:** PriceCharting loose price × 1.35 multiplier (adjustable in config)
- **Google Ads:** Separate account under personal email
- **Podcast:** The 8-Bit Legacy Podcast (3 person, biweekly, YouTube + socials)

## Project Structure
```
scripts/          — Automation scripts (pricing, ads, social, fulfillment)
config/           — API keys, multipliers, settings (gitignored secrets)
data/             — PriceCharting CSVs, exports, price snapshots
docs/             — Business docs, SOPs, content plans
assets/           — Brand assets, templates, ad creatives
```

## Key APIs
- **Shopify Admin API** (GraphQL) — product CRUD, order data, bulk operations
- **PriceCharting** — free collection export (CSV) for retro game prices
- **Pokemon TCG API** — free, card data + images
- **PokemonPriceTracker / PokeTrace** — card pricing (free tier: 100 calls/day)
- **Google Ads API** — campaign management, reporting
- **eBay Browse API** — search active listings for fulfillment
- **Buffer API** — social media scheduling

## Pricing Rules
- Default multiplier: 1.35x PriceCharting loose price
- Minimum profit threshold: $3.00 per item (after Shopify fees)
- Shopify fees: 2.9% + $0.30 per transaction (Basic plan, Shopify Payments)
- Items below minimum profit threshold get flagged for manual review

## Secrets
All API keys and tokens go in `config/.env` (gitignored). Never commit secrets.
