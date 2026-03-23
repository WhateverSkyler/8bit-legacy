# 8-Bit Legacy — Google Shopping Ads Strategy

## Account Setup
- **Account:** Separate Google Ads account under personal email
- **Merchant Center:** Must be connected with Shopify product feed
- **Starting budget:** $5-10/day ($150-300/mo)

---

## Phase 1: Feed Optimization (Before Spending a Dollar)

### Shopify → Google Merchant Center
1. Install **Google & YouTube** Shopify app (free)
2. Connect Shopify to Google Merchant Center
3. Ensure product data is clean:

**Required fields (make sure every product has these):**
- Title: `[Game Name] - [Console] | 8-Bit Legacy` (front-load the game name)
- Description: Include condition, what's included, quality guarantee
- Price: Current and accurate
- Availability: In stock (since you dropship from eBay, always "in stock")
- Image: High quality product photo
- Product category: `Video Games > Video Game Software` or `Video Games > Video Game Consoles`
- Condition: Used (this is important — Google shows condition in Shopping ads)
- Brand: The game publisher or console manufacturer

**Nice-to-have fields:**
- GTIN/UPC (if available from PriceCharting data — improves match rate)
- Custom labels (see below)

### Custom Labels (for campaign segmentation)
Add custom labels to your Shopify products via tags or metafields:
- **custom_label_0:** Margin tier → `high_margin`, `medium_margin`, `low_margin`
- **custom_label_1:** Console → `nes`, `snes`, `n64`, `genesis`, `ps1`, etc.
- **custom_label_2:** Price tier → `under_20`, `20_to_50`, `over_50`
- **custom_label_3:** Category → `game`, `console`, `accessory`, `pokemon_card`

These let you bid differently on different product groups.

---

## Phase 2: Campaign Structure

### Performance Max Campaign (Recommended for 2026)
Google's AI-driven campaign type. Best for Shopping with limited budget.

**Setup:**
1. Create a Performance Max campaign
2. Link your Merchant Center feed
3. Set target ROAS based on your margins:

### ROAS Targets by Margin Tier

**The math:**
- Average margin at 1.35x multiplier: ~26% of selling price
- After Shopify fees (~3.2%): ~23% net margin
- To break even on ads: ROAS = 1 / 0.23 = **435%**
- To profit: ROAS needs to be **above 435%**

**Recommended targets:**
| Margin Tier | Target ROAS | Logic |
|-------------|-------------|-------|
| High margin (>30%) | 400% | Aggressive — maximize volume |
| Medium margin (20-30%) | 600% | Balanced — steady profit |
| Low margin (<20%) | 800%+ or EXCLUDE | Conservative — only show if very likely to convert |

Start with a single campaign at 500% target ROAS and adjust based on data.

### Budget Scaling Rules
- **Week 1-2:** $5/day — gathering data, don't touch anything
- **Week 3-4:** Review ROAS. If above 500%, increase to $10/day
- **Month 2:** If consistently profitable, scale to $15-20/day
- **Never:** Increase budget by more than 20% at a time

### Negative Keywords (Add Immediately)
```
free
download
rom
emulator
emulation
ISO
hack
mod
cheat
walkthrough
guide
review
gameplay
let's play
unboxing
repair
fix
broken
```

---

## Phase 3: Monitoring & Optimization (Claude Code Managed)

### Daily Check (Automated Script)
- Pull: spend, revenue, ROAS, impressions, clicks, conversions
- Alert if: daily spend > daily profit threshold
- Alert if: ROAS drops below 400% for 3+ consecutive days

### Weekly Optimization
1. **Search terms report:** Find irrelevant searches, add as negatives
2. **Product performance:** Pause products with high spend + zero conversions (after 50+ clicks)
3. **Bid adjustments:** Increase ROAS target on underperforming segments
4. **Device performance:** Mobile vs Desktop — adjust if one significantly outperforms

### Monthly Audit
1. **Feed health:** Check Merchant Center for disapprovals, fix issues
2. **Competitor pricing:** Spot-check that our prices are still competitive
3. **New products:** Ensure new Shopify products are flowing into the feed
4. **Budget reallocation:** Shift spend toward best-performing consoles/categories
5. **Profit calculation:** Total ad spend vs total attributed revenue vs actual profit (after eBay cost)

---

## Phase 4: Advanced (Month 3+)

### Profit-Based Bidding
Upload product-level cost data to Merchant Center:
- Each product gets a `cost_of_goods_sold` field
- Smart Bidding then optimizes for profit, not just revenue
- This is the ultimate optimization for the dropship model

### Remarketing
- Install Google tag on website
- Create remarketing audiences:
  - Visited product page but didn't buy
  - Added to cart but didn't checkout
  - Past customers (cross-sell)
- Run small remarketing campaign ($2-3/day)

### Seasonal Pushes
- **Black Friday / Cyber Monday:** Increase budget 2-3x, lower ROAS targets
- **Christmas:** Gift-buying season, big for retro gaming
- **Summer:** Kids home from school, good for Game Boy / handheld games
- **Tax refund season (Feb-Apr):** People spending refunds on hobbies

---

## Key Metrics to Track

| Metric | Target | Why |
|--------|--------|-----|
| ROAS | >500% | Ensures profitability at 1.35x multiplier |
| CPC (cost per click) | <$0.50 | Retro gaming clicks are cheap |
| Conversion rate | >1.5% | Healthy for niche ecom |
| Impression share | >30% | Room to grow with more budget |
| Daily spend | < daily margin | Never spend more than you make |

---

## Estimated Results (Conservative)

At $300/mo budget with 500% ROAS:
- Revenue from ads: $1,500/mo
- Margin (~23%): $345/mo
- **Net profit after ad spend: ~$45/mo**

At $300/mo budget with 700% ROAS (optimized):
- Revenue from ads: $2,100/mo
- Margin (~23%): $483/mo
- **Net profit after ad spend: ~$183/mo**

At $500/mo budget with 700% ROAS:
- Revenue from ads: $3,500/mo
- Margin (~23%): $805/mo
- **Net profit after ad spend: ~$305/mo**

*Note: These are conservative. Your actual margins may be higher since you buy the cheapest eBay listing (usually below PriceCharting average). And organic orders continue bringing in revenue with $0 ad cost.*
