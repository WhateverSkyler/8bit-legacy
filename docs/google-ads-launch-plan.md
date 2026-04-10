# Google Ads Launch Plan — 8-Bit Legacy

**Drafted:** 2026-04-10
**Status:** Ready for review. DO NOT launch until conversion tracking is verified.

---

## Ground Truth (as of 2026-04-10)

Before deciding on strategy, here's the real data:

- **Past 6 months:** 5 orders, $507.91 revenue, $115 profit, 22.7% margin, $101 AOV
- **Past 40 days (shipped):** 1 order, $29, Wii remote
- **Conclusion:** The store is cold. The problem is not conversion optimization — it's traffic acquisition and trust-building. Ads strategy must reflect that.

**What's working organically:** Niche collector titles (Mystical Ninja N64, Phantasy Star Online GC, Galerians PS1, Aidyn Chronicles N64). AOV is healthy — enthusiasts are buying deep cuts at full price.

**What's not:** Basically no cold-traffic pipeline. No mainstream title searches resulting in purchases.

---

## Phase 0: Prerequisites (must complete before launch)

These are hard blockers. Do not spend a dollar until all are green.

### 0.1 — Conversion tracking
- [ ] Install Google Ads conversion tag on Shopify checkout (Purchase event)
- [ ] Verify tag fires on a test order using Google Tag Assistant
- [ ] Confirm the conversion is imported into Google Ads → Tools → Conversions
- [ ] Enable Enhanced Conversions for Leads/Sales (sends hashed email for better attribution)

**Why this matters:** With only 5 orders in 6 months, we cannot afford to miss a single conversion in Google's attribution model. Performance Max without conversion data is nearly useless — it'll optimize for clicks, not sales. Budget will burn with zero feedback loop.

**How:** The Google & YouTube Shopify app handles the pageview tag automatically. The Purchase conversion tag is a separate setup — follow https://help.shopify.com/en/manual/promoting-marketing/create-marketing/google-ads.

### 0.2 — Merchant Center feed
- [ ] Verify 12K products are actually approved (not just "submitted")
- [ ] Check Merchant Center → Products → Diagnostics for any disapprovals
- [ ] Fix any critical disapproval reasons (missing GTIN, image quality, etc.)

### 0.3 — Custom labels on products
Run `scripts/optimize-product-feed.py --dry-run` to preview custom label assignment. The script is already built to add:
- `custom_label_0` — price tier (under_20, 20_to_50, over_50)
- `custom_label_1` — console slug (nes, snes, n64, ps1, etc.)
- `custom_label_2` — category (game, pokemon_card, sealed)
- `custom_label_3` — margin tier (high, medium, low)

Apply it once the dry-run looks good. This enables campaign segmentation later.

### 0.4 — Budget safety
- [ ] Confirm `max_daily_ad_spend` hard limit in dashboard settings (CLAUDE.md says $25/day)
- [ ] Confirm google_ads circuit breaker is armed in `dashboard/src/lib/safety.ts`

---

## Phase 1: Campaign Launch (Week 1)

### Strategy: Start with Standard Shopping, NOT Performance Max

**This is a deviation from the old docs/google-ads-strategy.md.** That doc recommended Performance Max. I'm proposing Standard Shopping first for this specific reason:

**Performance Max needs conversion data to work. With 5 conversions in 6 months, it will flail.** It needs ~30 conversions in 30 days minimum to optimize. We don't have that. Standard Shopping lets us:
- Control bids manually at the product group level
- See exactly which search terms trigger clicks
- Build a negative keyword list quickly
- Learn the store's click-through economics before handing control to an AI

Switch to Performance Max in Month 2-3 once we have 20+ conversions to train on.

### Campaign Structure (Week 1)

**One campaign:** `8BL - Shopping - All Products`

- **Type:** Standard Shopping (NOT Performance Max)
- **Network:** Search Network only (no display)
- **Locations:** United States only
- **Language:** English
- **Budget:** $5/day (hard cap, max $35/week)
- **Bidding:** Manual CPC, max $0.50/click
- **Priority:** Low (lets you add higher-priority campaigns later)

**Ad groups (3 total, split by price tier so we can bid differently):**
1. **Entry-point items** (custom_label_0 = under_20) — max CPC $0.35
2. **Mid-tier items** (custom_label_0 = 20_to_50) — max CPC $0.45
3. **High-ticket items** (custom_label_0 = over_50) — max CPC $0.60

Rationale: high-ticket items justify a higher click cost because one conversion pays for ~150 clicks.

### Negative keywords (add at campaign level immediately)

```
rom
roms
emulator
emulation
iso
download
free
crack
cracked
hack
hacked
patched
repro
reproduction
bootleg
fake
replica
counterfeit
walkthrough
guide
cheats
review
reviews
let's play
gameplay
unboxing
trailer
repair
broken
parts only
for parts
not working
doesn't work
```

Why these: retro game searches are heavily polluted with free/pirate/video content. Without these, budget burns instantly.

### Week 1 Success Criteria

Don't optimize anything in Week 1. Just gather data.

- ✅ Impressions > 500
- ✅ CTR > 0.5%
- ✅ At least 1 conversion OR <$35 total spend
- ❌ Kill switch: if $35 spent with 0 conversions AND <0.3% CTR → pause campaign, review search terms

---

## Phase 2: Optimization (Week 2-4)

### Week 2 — Search term audit

Pull the search terms report daily. For every search term that got a click:
- **Relevant + converted:** leave it alone
- **Relevant + no conversion yet:** leave it, needs more data
- **Irrelevant:** add as negative keyword immediately
- **Brand terms from competitors:** add as negative (don't bid on "lukie games", etc.)

Expected finding: ~20-30% of initial clicks will be irrelevant. Cutting them will drop spend by 20-30%.

### Week 3 — Bid adjustments

- Check Auction Insights for each ad group
- If CPC > $0.50 for 3 days straight on a group with no conversions → lower bid by $0.05
- If impression share > 50% and converting → try raising bid by $0.05 to capture more volume
- If mobile vs desktop shows >2x difference in conversion rate → add device bid modifier

### Week 4 — Product-level review

Use the Products report in Google Ads:
- **Top 20%:** products with clicks + conversions → boost with custom_label bid modifier
- **Bottom 20%:** products with clicks + no conversions after 50+ clicks → exclude from campaign
- **No impressions:** products with zero impressions → check feed approval status

---

## Phase 3: Scaling (Month 2+)

### Budget ramp (conservative)

| Week | Daily Budget | Monthly | Trigger to advance |
|------|--------------|---------|---------------------|
| 1    | $5           | ~$150   | Baseline |
| 2    | $5           | ~$150   | After negatives added |
| 3    | $7           | ~$210   | If CTR > 1% |
| 4    | $10          | ~$300   | If ROAS > 300% |
| 5-8  | $10          | ~$300   | Stabilize |
| 9+   | $15          | ~$450   | If ROAS > 500% consistently |

**Never increase budget by more than 20% at a time** — Google's auction algorithm re-learns after big changes.

### Month 2: Add Performance Max

Once you have ~20+ conversions:
1. Keep Standard Shopping running at current budget
2. Launch a parallel Performance Max campaign at $5/day
3. Set Performance Max priority to High
4. Let Standard Shopping run on low priority as a fallback
5. After 2 weeks, compare ROAS. Shift budget to the winner.

### Month 3: Profit-based bidding

Upload `cost_of_goods_sold` to Merchant Center for each product. This lets Smart Bidding optimize for profit margin, not revenue — critical for dropship where a $100 sale of a $90-cost item is worse than a $40 sale of a $20-cost item.

---

## ROAS Targets

At 22.7% margin (from actual order data):
- **Break-even ROAS:** 1 / 0.227 = **440%**
- **Minimum profitable:** 500%
- **Target for scaling:** 700%+

Any ROAS below 440% is losing money. Any campaign that runs below 440% for 3 consecutive days should be paused for review.

---

## Monitoring Plan

### Daily (automated, via dashboard)
- Check ad spend vs $25/day hard limit
- Check for any disapproved products
- Log search terms for review

### Daily (manual, 5 min)
- Glance at spend, impressions, clicks, conversions
- Flag anomalies

### Weekly (manual, 20 min)
- Review search term report, add negatives
- Check product-level performance
- Adjust bids based on last 7 days

### Monthly (manual, 60 min)
- Full ROAS audit
- Reallocate budget between ad groups
- Review Auction Insights
- Check if competitors have entered the auction

---

## Emergency Stop Conditions

Trip the circuit breaker and pause all ads if ANY of these happen:
- Daily spend exceeds $25 (hard limit)
- 3 consecutive days of >$10 spend with zero conversions
- Disapproval rate on feed >5% suddenly
- Shopify store experiences any downtime

---

## Estimated Financials (Conservative, Month 1)

- **Spend:** $150/month
- **Clicks (at $0.40 avg):** 375
- **Conversions (at 1.5% rate):** 5-6
- **Revenue (at $100 AOV):** $500-600
- **Product cost (76.6%):** $380-460
- **Shopify fees (3.2%):** $16-19
- **Ad spend:** $150
- **Net profit:** **-$46 to $-29** (expected loss in month 1 — this is the learning tax)

Month 1 is a data-gathering exercise. Break-even or slight loss is the expected outcome. Month 2-3 is where we start actually profiting.

**Do not panic if Month 1 is a loss.** Panic if Month 2 is still a loss at the same budget.

---

## Handoff: What Tristan needs to do manually

1. **Install conversion tag on Shopify checkout** (blocks launch, 15 min)
2. **Verify tag fires with test order** (10 min)
3. **Review and approve this plan** (30 min reading)
4. **Create the campaign in Google Ads UI** — structure above (30 min)
5. **Add negative keywords** — list above (5 min)
6. **Set budget + bid strategy** (5 min)
7. **Enable campaign** (1 click — after all above is verified)

---

## Handoff: What the dashboard/scripts can do

- `scripts/optimize-product-feed.py` — apply custom labels for ad group segmentation
- `dashboard/src/lib/google-ads.ts` — already wired for GAQL queries + negative keyword management
- `dashboard/src/app/google-ads/` — performance dashboard for daily monitoring
- Scheduled job `google-ads-sync` (1 AM ET daily) — pulls campaign data into local DB

Once the campaign is live, the dashboard handles monitoring. Tristan's daily involvement drops to ~5 minutes.
