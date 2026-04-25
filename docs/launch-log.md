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

---

## 2026-04-25 — Pixel verification FAILED, campaign stays PAUSED

**Status:** PAUSED. 2C pixel fix from 2026-04-24 did not resolve the issue.

**Real-order test:** Order #1070 placed 2026-04-25 10:49 ET, $146.92, 3 items
(Tekken 3 PS1, Monster Lab PS2, Lucario ex Stellar Crown). Both Google Ads
GAQL (read at 12:13, 13:20, 14:21 ET) and the Ads UI Webpages tab (cowork
session, ~14:30 ET, "All time" range) show 0 Purchase conversions.

**Diagnostic finding (per `docs/cowork-session-2026-04-25-cleanup-and-pixel.md`):**
ALL 7 Google Shopping App conversion actions show 0 count — Purchase,
Page View, View Item, Add To Cart, Begin Checkout, Add Payment Info, Search.
The G&Y tag isn't loading on the storefront at all, not just failing on the
thank-you page. 4 actions show "Needs attention" tracking status.

**Discounts cleanup (collateral, also done in this session):** 3 lingering
test discounts deleted from Shopify admin. Customer checkout no longer shows
the `Test order free shipping v2 (pixel-fix 2026-04-24)` line. Commit `5e00017`.

**Next-pass diagnosis (not done this session, queued for next cowork):**
1. Confirm MonsterInsights fully removed (theme.liquid + apps page)
2. Complete G&Y app's pending Online Store contact-info confirmation gate
3. Tag Assistant Companion + DevTools manual order with storefront tab open
   to capture exactly which gtag events do/don't fire
4. Verify URL-match rule for `Google Shopping App Purchase` still matches
   the current Shopify checkout-extensibility thank-you path
   (`/checkouts/c/.../thank_you`)

**No campaign mutation today.** Spend stays at $0. TrueNAS safety crons
still active and not needed (nothing to safeguard while paused).
