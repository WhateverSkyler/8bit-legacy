# Ads Launch Log

Append-only record of campaign state transitions + daily monitoring notes
for `8BL-Shopping-Games` (ID 23766662629, account 822-210-2291).

---

## 2026-04-23 — Pre-launch state verified

**Status:** PAUSED. Awaiting two final gates before flip.

**Automated preflight:** 18/18 pass (`python3 scripts/ads_preflight_check.py`)

**Conversion tracking (Ads UI, 2026-04-23 11:03 ET screenshots):**
- Purchase: Active · "No recent conversions" (will flip to Recording on first real purchase)
- Add to cart: Active · "No recent conversions"
- Begin checkout: Active · "No recent conversions"
- Page view goal: Needs attention (soft warning, not a hard block — noted in `docs/ads-conversion-tracking-status-2026-04-16.md`)

**Order history (180 days, live pull):** 5 orders total.
- Fulfillment rate: 100% on non-refunded (3/3 shipped successfully; 1 in transit)
- Refund rate: 40% — both historical refunds (2026-03-03 and 2026-04-04) were
  explicitly "not in stock" at the time of fulfillment attempt. Root cause was
  stale pricing on the source side (refresh completed 2026-04-15 per
  `docs/session-handoff-2026-04-15.md`). No operational failures.

**eBay sourceability audit (2026-04-23 ~11:50 ET, 25 over_50 games, live API):**
- ✅ 18/25 green (≥1 active used listing at ≤65% of our list price)
- 🟡 5/25 thin (min price OK, median tight)
- 🔴 2/25 no matches — cosmetic cleanup later:
  - "X-men Wolveri - NES Game Rage - Gameboy Color Game" (corrupted feed title)
  - "WWF Raw - Sega 32X Game" (ultra-niche, no supply)
- **Mystical Ninja N64** (previously refunded 2026-04-04 for stock): 15 active
  listings at $3.99 min, $13.19 median. Far below our $113.74 cost ceiling.
  Previous refund was a timing fluke.
- **Aidyn Chronicles N64** (previously refunded 2026-04-04 for stock): 15 active
  listings at $7.95 min, $24.99 median. Well within margin.

**My honest probability estimate (conservative, as of 2026-04-23 ~noon):**
- P(positive or breakeven ROAS in 30 days): 35-45%
- P(useful learning regardless of ROAS): 85%
- P(account re-suspension from refund/chargeback spike): 10-15%

**Launching today is +EV.** Promo credit ($700, expires 2026-05-31) covers the
experiment cost. Worst case = $50 hard kill on lifetime-no-conv ceiling, telling
us the store needs pre-ad work (reviews, trust signals) before paid traffic
converts.

## Outstanding gates before ENABLED

1. Shipping threshold $35 → $50 (Shopify admin — cowork brief
   `docs/claude-cowork-brief-2026-04-23-final-gates.md`)
2. $5-10 real test order + refund to flip Purchase action to "Recording"
   (same cowork brief)

## Accepted residual risks (not blocking)

- CIB exclusion supplemental feed: Merchant Center Next UI rejects supplemental
  feeds on Merchant-API primaries. Auction optimizer should favor the cheaper
  Game Only variant naturally. Revisit in 14d if CIB impression share >20%.
- VPS dashboard `safety.ts` redeploy: $40/$50 limits in repo, VPS still on $25.
  First few days at $20/day unlikely to exceed $25 overshoot. Manual daily
  monitoring in week 1.
- Page View goal "Needs attention": per prior audit, soft warning not blocker.
- 2 products with bad feed titles / no sourceability: $94 + $51 list price
  combined, <0.3% of the 802 over_50 universe. Will surface in daily report
  if they spend without converting.
