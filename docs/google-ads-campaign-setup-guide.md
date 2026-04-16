# Google Ads Campaign Setup Guide — 8BL-Shopping-All

**Date:** 2026-04-16
**Supersedes:** The v2 launch plan's two-campaign Winners/Discovery approach
**Strategy:** ONE Standard Shopping campaign, full product catalog, high-intent search capture only

---

## Campaign: `8BL-Shopping-All`

Create this in Google Ads UI. Do NOT use "Smart Campaign" or "Express" modes.

### Step 1: Create Campaign
1. Google Ads → Campaigns → **+ New campaign**
2. Goal: **Sales**
3. Campaign type: **Shopping**
4. Sub-type: **Standard Shopping campaign** (NOT Performance Max)
5. Merchant Center account: **5296797260**
6. Country of sale: **United States**

### Step 2: Campaign Settings
| Setting | Value |
|---|---|
| Campaign name | `8BL-Shopping-All` |
| Networks | **Search Network ONLY** (UNCHECK "Include Google search partners", UNCHECK "Include Google Display Network") |
| Location | United States |
| Bidding | **Manual CPC** (may need to click "Or, select a bid strategy directly") |
| Enhanced CPC | **ON** (checkbox under Manual CPC) |
| Daily budget | **$14.00** |
| Campaign priority | **High** |
| Start date | Today (or whenever you're ready to enable) |
| Status | **Paused** (do NOT enable yet) |

### Step 3: Ad Group
1. Ad group name: `all-products`
2. Default max CPC bid: `$0.40`

### Step 4: Product Groups (Bid Tiering)

After creating the campaign, go into the ad group and subdivide product groups:

1. Click on "All products" → **Subdivide** → by **Custom label 2** (category)
2. You'll see categories: `game`, `pokemon_card`, `console`, `accessory`, `sealed`, etc.
3. Set bids:

| Product Group | Max CPC | Action |
|---|---|---|
| `category:game` | (subdivide further) | See step 5 |
| `category:console` | **$0.35** | Set bid |
| `category:accessory` | **$0.25** | Set bid |
| `category:sealed` | **$0.30** | Set bid |
| `category:pokemon_card` | — | **EXCLUDE** (click the exclude icon) |
| Everything else | — | **EXCLUDE** |

4. **Subdivide `category:game`** → by **Custom label 0** (price_tier):

| Product Group | Max CPC |
|---|---|
| `game` + `price_tier:over_50` | **$0.55** |
| `game` + `price_tier:20_to_50` | **$0.40** |
| `game` + `price_tier:under_20` | **$0.20** |

### Step 5: Negative Keywords

**Quick method (recommended):** Use Google Ads Editor (desktop app)
1. Download Google Ads Editor: https://ads.google.com/intl/en/home/tools/ads-editor/
2. Download account → select `8BL-Shopping-All`
3. Go to Keywords → Campaign Negative Keywords → Import
4. Import from CSV: `data/negative-keywords-google-ads-import.csv`
5. Post changes → upload

**Manual method:** Google Ads UI → Campaign → Keywords → Negative keywords → + → paste keywords from `docs/ads-negative-keywords-master.md` (use phrase match)

### Step 6: Pre-Launch Verification
Before enabling:
- [ ] Conversion tracking shows all 4 goals as "Configured" (not "Misconfigured")
- [ ] All 7 conversion events are "Recording" or "No recent conversions" (not "Inactive")
- [ ] Merchant Center feed healthy (< 50 disapproved products)
- [ ] Product pages show correct prices when switching variants (fixed April 13)
- [ ] Free shipping badge says $35 (not $50)
- [ ] Return policy shows 90 days everywhere
- [ ] Circuit breaker is armed on the dashboard (8bit.tristanaddi.com)
- [ ] 334 negative keywords loaded in the campaign

### Step 7: Enable
1. Campaigns → `8BL-Shopping-All` → change status to **Enabled**
2. Screenshot the campaigns page with timestamp
3. Set a reminder: check back in 6 hours for first data

---

## Budget Math

| Period | Daily Budget | Duration | Total |
|---|---|---|---|
| Now → May 31 (promo credit) | $14/day | ~45 days | ~$630 |
| June 1+ (if profitable) | $6-8/day | ongoing | — |
| June 1+ (if not profitable) | PAUSE | — | — |

Break-even ROAS: **440%** ($4.40 revenue per $1 ad spend)

## Daily Review (First 14 Days)

**Days 1-3 (check every 6 hours):**
- Is spend happening? ($0 after 12h = feed or bid problem)
- Pull search terms → add negatives aggressively (expect 70% garbage initially)
- Don't panic if zero conversions yet

**Days 4-7 (check 2x/day):**
- Target CTR > 1% (Shopping ads average 1.5-3%)
- Look at which products get traffic — are they the right ones?
- Continue adding negatives from search terms

**Days 8-14 (once daily, 10 min):**
- Calculate actual ROAS by product group
- Identify top 5 products by ROAS (these are your real winners)
- Reduce bids on products with 20+ clicks and 0 conversions

**Day 14 Decision:**
- ROAS > 300%: Continue and optimize
- ROAS 100-300%: Reduce to $8/day, investigate
- ROAS < 100% or 0 conversions: PAUSE — fix the store first, not the ads

---

## What's Excluded and Why

| Category | Reason |
|---|---|
| Pokemon singles | 1.15x margin ($2.25 gross on a $15 card) can't support any ad cost |
| Products below $10 | After Shopify fees + ad cost, every sale loses money |

## Kill Switches (Automated)

The dashboard safety system runs every 6 hours and will automatically pause all campaigns if:
1. Daily spend exceeds $25
2. 3 consecutive days with $10+ spend and 0 conversions
3. 8bitlegacy.com goes down
4. Rolling 3-day ROAS drops below 200% (after 7+ days of data)

Manual reset required after any trip — go to the dashboard settings or reset the circuit breaker.
