# Google Ads Launch Plan v2 — 8-Bit Legacy

**Drafted:** 2026-04-10 evening
**Author:** Linux desktop Claude
**Supersedes:** `docs/google-ads-launch-plan.md` (v1, 2026-04-10 morning)
**Revised:** 2026-04-11 — added $700 promo-credit budget overlay (see "Promo-credit budget overlay" below)
**Status:** Ready to execute the build-out work described here. DO NOT launch spend until all Phase 0 items are green. Launch is gated on Tristan's social media + podcast content schedule.

---

## ⚡ Promo-credit budget overlay (active until 2026-05-31)

**$700 Google Ads promotional credit** is active on account `822-210-2291` and expires **2026-05-31**. From 2026-04-11 to 2026-05-31 = **50 days**. To actually consume the credit before expiry, the account must spend an average of **$14/day**.

The conservative baseline plan below (Phases 1–3 at $4–$10/day) was built for *real-money* spending where every dollar is precious. The promo credit changes the calculus: unspent credit is worth $0 on May 31, so during the promo window we intentionally run wider campaigns and higher daily budgets *as long as* kill switches hold and ROAS data is still being logged.

**Promo-mode budget envelope (2026-04-11 → 2026-05-31):**

| Campaign | Baseline ($/day) | Promo-mode ($/day) | Why the delta |
|---|---|---|---|
| `8BL-Shopping-Winners` | $3 | **$6** | Doubles reach on the highest-CVR SKUs |
| `8BL-Shopping-Discovery` | $1 | **$4** | Widens exploration across the long tail — the credit is funding the learning |
| `8BL-Display-Remarketing` (from Week 2) | $1 | **$2** | Remarketing cost is bounded by audience size anyway |
| `8BL-PMax-Test` (new, Week 3) | 0 | **$2** | Parallel PMax test is "free" under promo credit — use it to A/B vs Standard Shopping early |
| **Total (Weeks 1–2)** | $4 | **$10** | $10/day × 14d = $140 from promo |
| **Total (Weeks 3–7)** | $6–$10 | **$14** | $14/day × 35d = $490 from promo |
| **Promo window total** | ~$200 | **~$630** | Leaves ~$70 headroom for bid experiments |

**Rules that still apply under promo mode:**
1. `dashboard/src/lib/safety.ts` hard cap of **$25/day** is untouched — the promo does not override safety.
2. The "3 consecutive days, $10+ spent, 0 conversions" kill switch still trips and pauses campaigns.
3. If Merchant Center feed health drops (disapprovals > 5%), pause — credit can't buy visibility you don't have.
4. Circuit breaker wins over promo. Always.

**Rollover on 2026-06-01:** Check promo balance. If unused credit exists past expiry, Google forfeits it automatically — no action needed. Then revert Winners → $3, Discovery → $1, Remarketing → $1, pause PMax-Test. Revisit PMax only if Phase 4 criteria are met.

**Hard prerequisite before promo-mode spending:** Conversion tracking must be **Recording** (not "Misconfigured"). See Phase 0.3 — the April 2026 screenshot shows all 4 primary conversion goals as Misconfigured and Purchase/Begin Checkout/Add Payment Info as Inactive. Spending $14/day without conversion tracking wastes the credit AND blinds us to whether it worked. **Fix conversion tracking first, then unlock promo-mode budgets.**

---

## What changed from v1 and why

v1 is structurally solid — correct call to use Standard Shopping over Performance Max for a cold store, correct budget starting point, correct negative keyword list direction. This v2 keeps all of that and changes four things that affect ROI materially:

1. **Smaller, narrower Phase 1.** v1 launches a single campaign targeting all 7,689 products at $5/day. v2 launches a focused 20–25 product "Winners" campaign at $3/day. Rationale: with 22.7% margin and a $101 AOV, break-even ROAS is 440%. At the store's current conversion rate (unknown, likely 0.5–1% given 0 reviews and weaker trust signals than competitors), a broad campaign will almost certainly burn budget across products that can't possibly convert at that ROAS. A narrow campaign concentrates spend on the products most likely to convert at profit.

2. **Three campaigns, not one.** v1 has a single Shopping campaign segmented into 3 ad groups by price tier. v2 adds a parallel Discovery campaign (for data generation) and plans Remarketing + Brand Search for Phase 3. Rationale: segmenting by *intent* (proven demand vs exploration vs retargeting) is a bigger lever than segmenting by *price*. A $60 Galerians click is 10x more likely to convert than a $18 random SNES click — but v1 would give them similar treatment.

3. **Explicit pre-launch landing-page fixes.** v1 treats the homepage as already done. It isn't. There's a `2025/05/07` countdown timer on Deals of the Week that's nearly a year expired — any ad click lands on a homepage that visually signals an abandoned store. v2 makes that, plus the empty banner sections and the Pokemon-below-fold gap, hard pre-launch blockers.

4. **Break-even ROAS reality check.** v1 says break-even is 440% and projects a $46 loss in Month 1 as the "learning tax." v2 pushes back: committing to a projected loss on a store with a fulfillment bottleneck is a weak bet. v2 only launches the narrow Winners campaign because that's the only segment where Month 1 has a plausible path to ≥440% ROAS. If even that doesn't break even in 30 days, the answer is to fix the store (reviews, trust, homepage) not to scale spend.

## Ground truth (as of 2026-04-10 pm)

- **Past 6 months:** 5 orders, $507.91 revenue, $115 profit, 22.7% margin, $101 AOV
- **Past 40 days:** 1 shipped order ($29 Wii remote)
- **Live products in feed:** 7,689 (all tagged with custom_label_0–3 as of 2026-04-10 feed optimizer run)
- **Conversion tracking:** fully wired via Google & YouTube Shopify app (pixel ID `900628514`, Ads ID `AW-18056461576`, 7 events mapped). Verifiable only in Google Ads UI, not DevTools.
- **Known blockers:** Google & YouTube Shopify app is connected to the wrong Ads account (`438-063-8976` under `tristanaddi1@gmail.com` instead of target `822-210-2291` under `sideshowtristan@gmail.com`).
- **Known landing page issues:** Stale countdown timer (2025/05/07), two 0px-height banner sections, Pokemon entirely missing from homepage, zero product reviews visible anywhere, trust signals weaker than main competitor DKOldies on every dimension except 1-year warranty.

## Devil's advocate — what could kill this campaign

Before building anything, list the failure modes and make sure each one has a mitigation.

### R1 — Traffic lands on a page that looks abandoned
**Symptom:** Sale countdown timer reading `2025/05/07`, empty banner sections rendering at 0px, stale "Special Products" nav link.
**Cost:** Every single ad click bounces. Budget burns with zero signal.
**Mitigation:** **Hard pre-launch blocker.** See Phase 0 fixes below. Do not spend a dollar until these are resolved.

### R2 — Zero social proof vs competitors with thousands of reviews
**Symptom:** DKOldies shows 80k+ reviews as a homepage headline. 8BL product pages show nothing.
**Cost:** Conversion rate ~50% lower than it would be with even 10 reviews per product.
**Mitigation:** Parallel non-ads work track. Install a free review app (Shopify Product Reviews, Judge.me free tier, or Loox free tier) and build a post-purchase email requesting reviews from the ~5 past buyers. Won't be a lot but 5 reviews > 0 reviews. Longer term: seed product reviews by asking the 853 email subscribers (once the email flow works).

### R3 — Shipping threshold is 2.5x higher than DKOldies ($50 vs $20)
**Symptom:** On a $30 N64 game, 8BL charges shipping; DKOldies doesn't. At identical ad CPCs, their landing page wins.
**Cost:** Direct conversion rate impact on all Winners products in the $30–$50 price band (which is most of them).
**Mitigation:** Tristan decision — lower free shipping threshold to $35 or $40. Dropship shipping costs ~$4–6 per game via eBay sellers, so absorbing this on $35+ orders still leaves margin. This is a one-click Shopify setting change.

### R4 — 30-day return policy is 12x shorter than DKOldies' 365 days
**Symptom:** Ad traffic comparing 8BL to DKOldies sees a dramatic policy gap on every product page.
**Cost:** Second-biggest conversion rate killer after the review gap.
**Mitigation:** Tristan decision — extend to 90 days to match Lukie Games. True 365-day match is hard for a dropship model but 90 days is reasonable. Again, a Shopify settings change + updating the announcement bar.

### R5 — Fulfillment bottleneck if ads actually work
**Symptom:** Ads drive 10 orders/day. Each dropship order is ~10–15 minutes of eBay sourcing + checkout + tracking entry. 10 orders = 2 hours of manual work.
**Cost:** Slower fulfillment = slower shipping = customer complaints = reviews that undo the review-gap work.
**Mitigation:** Tristan-defined fulfillment capacity limit. If Tristan can comfortably handle N orders/day, ad budget ceiling = N × AOV × break-even spend ratio. For N=5 orders/day and $101 AOV, max daily spend = 5 × $101 × 0.2 = $101. That's 4x the current $25/day hard limit, so fulfillment is not currently the binding constraint — budget is. But define it explicitly anyway.

### R6 — April seasonality masks results
**Symptom:** April is historically a slower month for collectibles ecommerce. Tax refunds end early April. Weak Week-1 results may be seasonality, not campaign quality.
**Cost:** Risk of wrongly pausing a campaign that would have worked in May/June.
**Mitigation:** Commit to **14-day minimum** before any scaling decision. Don't panic-kill on Week 1.

### R7 — Margin math is statistically weak
**Symptom:** 22.7% margin is based on ONLY 5 historical orders. Real margin could be anywhere from 15% to 35% on a larger sample.
**Cost:** Break-even ROAS target (440%) could be wrong by 50% in either direction, making "is this campaign profitable" an unanswerable question.
**Mitigation:** Compute per-order margin on every new order that flows in during the campaign. Weekly recalculation of break-even ROAS target.

### R8 — Google's daily-budget overspend rule
**Symptom:** Google Ads can spend up to 2x the daily budget on any given day to capture opportunity. At $3/day intended, actual daily spend can hit $6. Over a 30-day month, total is still capped at 30 × $3 = $90 (they balance it out), but a single day can spike.
**Cost:** Single-day anomalies during budget spikes. The $25/day hard limit in `dashboard/src/lib/safety.ts` is the real enforcement.
**Mitigation:** Verify the circuit breaker enforces at actual spend, not intended budget. Already wired per v1 Phase 0.4.

### R9 — Broad-match search terms pollute clicks
**Symptom:** Standard Shopping doesn't use keywords you pick — it uses Google's best guess from the product title + feed. A product titled "Galerians - PS1 Game" might show on queries like "ps1 games list" or "playstation 1 reviews" where the click has zero intent.
**Cost:** The negative keyword list defends against this, but only *after* the first clicks happen. Expect 20–30% of first-week budget to go to irrelevant clicks until the search terms report surfaces them.
**Mitigation:** Check search terms report **daily** for the first 7 days, not weekly. Add negatives aggressively. Then back off to weekly.

### R10 — Dropship COGS is dynamic (not uploadable to Merchant Center)
**Symptom:** v1's Phase 3 "profit-based bidding" strategy requires a static `cost_of_goods_sold` per product. Dropship COGS changes daily as eBay listings rotate.
**Cost:** Can't use Smart Bidding for profit optimization — stuck with Smart Bidding for revenue, which is weaker for margin-sensitive businesses.
**Mitigation:** Skip profit-based bidding entirely. Use `custom_label_3 = margin_tier` as a proxy and manually bid tier-aware. Long-term (Month 6+), could consider a nightly script that writes average 30-day COGS to a Merchant Center supplemental feed.

### R11 — Account suspension for "dropship without value-add"
**Symptom:** Google has gotten stricter about drop-shippers. If the account gets suspended, there's a lengthy appeal.
**Cost:** Weeks of lost traffic and re-verification work.
**Mitigation:** 8BL adds clear value: 1-year warranty, testing, returns, branded packaging, curation. Document this in a "merchant policies" page before launch. Keep receipts.

### R12 — Product feed has hidden disapprovals
**Symptom:** After the 2026-04-10 feed optimizer run, 7,689 products were tagged. Merchant Center approval state was not re-verified post-tagging.
**Cost:** Products that are disapproved for any reason (missing GTIN, image quality, policy violations) won't show in ads regardless of spend.
**Mitigation:** Merchant Center Diagnostics check is item #1 in Phase 0 pre-launch checklist.

### R13 — The Google Ads click IS the problem, not the price
**Symptom:** The store has organic traffic delivering 1 shipped order in 40 days. Paid traffic may not behave any better.
**Cost:** Fundamental strategy failure. Month 1 loses $50–100 with no learning.
**Mitigation:** This is actually the devil's advocate *for the whole plan*. If Phase 1 (just Winners, 14 days, tight targeting) shows no conversions, the right answer is: DO NOT scale to Phase 2. The answer is to pause ads and fix the store. Ads are amplifiers, not repair tools.

---

## Phase 0 — Pre-launch mandatory fixes (hard blockers)

Every one of these must be ✅ before spend enables.

### 0.1 — Homepage trust fixes (user-facing critical)
- [ ] **Update or remove the Deals of the Week countdown timer.** Currently set for `2025/05/07` — nearly 11 months expired. Fix by either (a) setting it to a real end date in the current sale wave (say, 2026-05-01), or (b) hiding the timer entirely if sale rotation cadence isn't predictable. **Theme editor change.**
- [ ] **Wire the Deals of the Week product row to the "On Sale" smart collection** (ID `483677044770`) so new sales auto-populate instead of staying hardcoded with stale items.
- [ ] **Delete the two empty `bs_banner_three_image` sections** rendering at 0px height. Theme editor → Homepage → delete sections.
- [ ] **Delete the "Shop Everything GameCube" section entirely** from the homepage per user directive. Theme editor change.
- [ ] **Kill the legacy `/collections/special-products` "Sale" nav link** and publish the "On Sale" smart collection to the Shop sales channel.

### 0.2 — Trust signal parity with competitors (Tristan decisions)
- [ ] **Decision: free shipping threshold.** Lower from $50 to $35 or $40 to reduce gap with DKOldies ($20). Cost analysis: at $35 threshold and ~$5 shipping absorbed, breakeven is a $35 order at 14.3% margin concession — still profitable at 22.7% base margin.
- [ ] **Decision: return policy.** Extend from 30 days to 90 days to match Lukie Games. Update announcement bar text, product page, and footer.
- [ ] **Install a review app.** Shopify Product Reviews (free, native) is the fastest install. Seed with the 5 past buyers via a manual outreach.

### 0.3 — Account linking + conversion tracking (Tristan manual, ~20 min)

**Status as of 2026-04-11 screenshot:** Account `822-210-2291` is linked, but ALL 4 primary conversion goals show **Misconfigured**:
- Purchase — 1 primary action, `Google Shopping App Purchase`: **Inactive**
- Add to cart — 0 primary actions, `Google Shopping App Add To Cart`: No recent conversions
- Begin checkout — 0 primary actions, `Google Shopping App Begin Checkout`: **Inactive**
- Page view — 0 primary actions, `Google Shopping App Page View`: Needs attention (plus Search, View Item: No recent conversions)
- Other — `Google Shopping App Add Payment Info`: **Inactive**, plus a prompt: "To get better insights and optimize performance, categorize your 'Other' conversion actions into more specific goals"

**Diagnosis:** The Google & YouTube Shopify app created all 7 conversion actions correctly, but only Purchase is marked Primary in its goal. Every other goal category ("Add to cart", "Begin checkout", "Page view") has 0 primary actions — which is why Google Ads reports them as Misconfigured. A goal with zero primary conversion actions cannot be used as an optimization target. Separately, three actions (Purchase, Begin Checkout, Add Payment Info) are "Inactive" because the tag has not fired a real event recently — no live checkout has happened since the account re-link.

**Fix recipe (15 min, clicks in Google Ads UI):**

1. **Promote secondary actions to primary in each goal.** Google Ads → Goals → Conversions → Summary. For each row showing "Misconfigured":
   - Click the row → **Edit goal**
   - Under the secondary action listed (e.g. `Google Shopping App Add To Cart`) → toggle **Primary action** on
   - Save
   - Repeat for Add to cart, Begin checkout, and Page view
2. **Categorize the "Other" → Add Payment Info action.** Edit goal → change category from "Other" to "Add payment info" under the Purchase funnel. This removes the "Other" warning banner.
3. **Fire one of each event live** on the store to clear "Inactive" / "No recent conversions":
   - Open https://8bitlegacy.com in an **incognito window** (no ad blockers)
   - View any product page (fires Page View + View Item)
   - Search for a product in the store search bar (fires Search)
   - Click Add to Cart (fires Add to Cart)
   - Proceed to checkout, enter email + address (fires Begin Checkout)
   - Enter a real card (fires Add Payment Info) — then abandon, don't complete
   - Optional: complete a $1 test order on a $1 product to fire Purchase (Shopify makes real payment hard to test; use a gift card or the real-order-then-refund method)
   - Wait **2–4 hours** for Google Ads to surface the event
4. **Re-check the Conversions page.** All 7 actions should move from Inactive → No recent conversions → then eventually Recording once real traffic flows.

**Customer lifecycle optimization warning** ("need audience segment with at least 1,000 active members") is **NOT a launch blocker.** It's a Smart Bidding enhancement that helps with existing-customer targeting. The 853-subscriber email list doesn't meet the 1,000 threshold yet, and we're launching with Manual CPC anyway. Revisit this in Phase 4.

- [ ] All 4 conversion goals moved from Misconfigured → Configured (at least 1 Primary action per goal)
- [ ] Live event test completed (one each: Page View, View Item, Search, Add to Cart, Begin Checkout, Add Payment Info)
- [ ] 2–4 hours elapsed, re-checked Conversions page, all 6 events show Recording or No recent conversions (NOT Inactive)

### 0.4 — Feed health audit
- [ ] **Merchant Center Diagnostics** — log into Merchant Center 5296797260, navigate to Products → Diagnostics, screenshot any item-level issues. Fix top 5 if material.
- [ ] **Verify custom labels populated** — spot-check 10 random products in Merchant Center to confirm `custom_label_0` through `custom_label_3` are non-empty (the feed optimizer log says 7,689 updated with 0 failures, but Shopify → Google Shopping propagation can lag).
- [ ] **Verify all Winners list products are "in stock" in the feed** (after the 2026-04-06 CIB inventory fix).

### 0.5 — Budget safety verification
- [ ] Confirm `max_daily_ad_spend` in `dashboard/src/lib/safety.ts` is set to $25 (or lower).
- [ ] Confirm the `google_ads` circuit breaker trips on (a) spend exceeding daily limit, (b) 3 consecutive days of spend with 0 conversions, (c) account disapproval events.
- [ ] Arm the circuit breaker. Test-trip it and confirm it cleanly pauses campaigns via the API.

### 0.6 — Content schedule alignment (user's constraint)
- [ ] Social media post calendar ready — at least 14 days of scheduled posts across Instagram, Facebook, TikTok linking back to the store.
- [ ] Podcast Episode 2 clips scheduled for YouTube Shorts + social.
- [ ] **Only after both are green → flip the campaigns on.**

---

## Phase 1 — The Focused Launch (Weeks 1–2)

**Hypothesis:** The store has proven organic demand for ~20 niche collector titles. Paid traffic targeting exactly those products will convert at rates similar to organic (2–3%), hitting break-even ROAS because AOV is high ($60–$175).

### Campaign 1: `8BL-Shopping-Winners` — the focused bet

| Setting | Value | Rationale |
|---|---|---|
| Type | Standard Shopping | Full control, no PMax black box on cold data |
| Network | Search Network only | No display, no YouTube (Phase 1 is data quality, not volume) |
| Location | United States | Dropship fulfillment only works domestically |
| Language | English | |
| Budget | **$3/day** (~$42 over 14 days) | Smaller than v1's $5/day — narrower target means less waste tolerance |
| Bidding | Manual CPC, max $0.75 | Higher than v1's $0.50 because long-tail niche auctions can spike on rare titles |
| Priority | High | This is the primary campaign |
| Inventory filter | Winners list SKUs only (see `docs/ads-winners-curation-list.md`) | ~20–24 products |
| Ad groups | 1 | Too small to split; avoid over-structuring early |
| Negative keywords | Master list from `docs/ads-negative-keywords-master.md` | All 10 categories, campaign-level |

**Daily check (5 min):**
1. Total spend (vs $3 budget)
2. Impressions, clicks, CTR
3. Search terms for the day — add any garbage to negatives
4. Any conversions? If yes, note product + search term
5. Any product in the Winners list showing zero impressions? Flag for feed health check

**14-day success criteria:**
- ✅ ≥500 impressions total
- ✅ ≥25 clicks total
- ✅ ≥1 conversion
- ✅ ROAS ≥ 200% (below break-even but shows signal worth continuing)
- ❌ Kill criterion: $40+ spent, 0 conversions, <0.8% CTR → pause Winners, investigate landing pages + negative list before retrying

### Campaign 2: `8BL-Shopping-Discovery` — the data engine

| Setting | Value | Rationale |
|---|---|---|
| Type | Standard Shopping | Same as Winners |
| Network | Search Network only | |
| Location | United States | |
| Budget | **$1/day** (~$14 over 14 days) | Tiny budget — this is a learning engine, not a sales engine |
| Bidding | Manual CPC, max $0.35 | Cheaper clicks only; if auction is expensive, we don't care |
| Priority | Low | Winners gets first dibs on any overlapping queries |
| Inventory filter | All products EXCEPT Winners, EXCEPT Pokemon singles, EXCEPT under $15, EXCEPT over $200, EXCEPT consoles, EXCEPT accessories | Cast a wide net but avoid guaranteed waste |
| Negative keywords | Same master list | |

**Purpose:** With Winners capped at ~20 products, we're not exploring the other 7,669. Discovery campaign at $1/day trickles clicks into the rest of the feed and surfaces which products/search-terms actually get traction. Any product that converts in Discovery gets promoted to Winners in Week 3.

**14-day success criteria:** Data only.
- ✅ 50+ unique search terms surfaced
- ✅ 0–2 conversions expected
- ❌ No kill criterion — this is a data budget

### Total Phase 1 spend
$4/day × 14 days = **$56 total**. Well under the $150/month projected by v1.

---

## Phase 2 — Optimization + Winners Expansion (Weeks 3–4)

Based on Phase 1 data:

### Winners campaign adjustments
- **Promote:** Any Discovery product with 1+ conversions → add to Winners
- **Pause:** Any Winners product with 10+ clicks and 0 conversions
- **Bid up:** Any Winners product with ROAS > 500% → raise max CPC by $0.10
- **Bid down:** Any Winners product with ROAS < 300% but converting → lower max CPC by $0.05
- **Budget:** Raise Winners to $5/day if Phase 1 ROAS > 300%

### Discovery campaign adjustments
- Add any new negatives from the first-week search terms
- Keep at $1/day unless clearly generating Winners candidates (then $2/day)

### New: Microsoft Ads import (free incremental traffic)
- Microsoft Ads (Bing + partner network) has 30–50% cheaper CPCs than Google on the same keywords and captures ~5–8% of US retail search.
- One-click import Google Ads campaigns into Microsoft Ads — reuses the structure, negative keywords, and feed.
- Budget: $2/day — minimal additional risk, free data, free brand impressions.
- Not a required Phase 2 step but a very high-ROI parallel track.

**Phase 2 total spend:** $6/day Google + $2/day Microsoft = $8/day × 14 days = **$112 total**.

---

## Phase 3 — Remarketing + Brand Protection (Weeks 5–8)

By Phase 3 we should have 50–200 site visitors in the Google Ads remarketing audience (built automatically via the Google & YouTube Shopify app pixel).

### Campaign 3: `8BL-Display-Remarketing`
| Setting | Value |
|---|---|
| Type | Display (dynamic remarketing) |
| Audience | All visitors to any product page, past 30 days, excluding converters |
| Budget | $1/day |
| Bid strategy | Max clicks or manual CPC at $0.25 |
| Creative | Dynamic remarketing using product feed — no manual ad creation needed |
| Frequency cap | 3 impressions per user per week (don't stalk) |

**Why:** Remarketing is the highest-CVR ad format for considered purchases. Cart abandoners and product page browsers convert at 5–10x the rate of cold traffic when shown a reminder. Tiny budget is fine — audience is small.

### Campaign 4: `8BL-Brand-Search` (conditional)
| Setting | Value |
|---|---|
| Type | Search |
| Keywords | `[8bit legacy]`, `[8 bit legacy]`, `[8bitlegacy]`, `[8bitlegacy.com]`, `"8 bit legacy"` |
| Budget | $1/day (likely spend = $0.30/day) |
| Bid strategy | Manual CPC, max $0.40 |

**Condition for launch:** Only create this if Google Trends / Google Ads Keyword Planner shows measurable monthly search volume for the brand terms. At current brand awareness level this is likely $0 spend and a waste of an hour of campaign setup. **Defer until Month 3 unless the podcast drives real brand search.**

### New Phase 3 non-ads priorities
- Install or verify Shopify review app + send review request emails to existing buyers
- Apply the homepage Pokemon product strip (per homepage-redesign-notes.md)
- Launch Shopify Email welcome flow for the 853 subscribers (separate track)

**Phase 3 total spend:** $6/day Shopping + $2/day Microsoft + $1/day Remarketing + $0–$1/day Brand = ~$9–10/day × 28 days = **$252–280 total**.

---

## Phase 4 — Performance Max Consideration (Month 3+)

Only enter this phase if **all** of these are true after Month 2:
- ✅ 20+ converted orders in the trailing 30 days
- ✅ Standard Shopping ROAS > 500% on Winners campaign
- ✅ Conversion tracking verified with no gaps
- ✅ Fulfillment capacity hasn't been stressed

If true: launch PMax as a parallel $5/day campaign, compare ROAS vs Standard Shopping over 4 weeks, shift budget to winner. If Standard Shopping wins, keep PMax small or off.

If not true: stay in Phase 3 structure. Performance Max is a scaling tool, not a fixer.

---

## Parallel free traffic track (runs alongside all phases)

These are not Google Ads but they complement the paid campaign at $0 cost.

| Channel | Effort | Expected traffic | Status |
|---|---|---|---|
| Google Merchant Center free listings | Already enabled | Some — verify in MC dashboard | Verify Phase 0 |
| Microsoft Merchant Center + Bing free listings | 30 min setup | ~20% of Google organic volume | Phase 2 |
| Facebook Marketplace listings (high-value items only) | 15 min per item | Local buyers, high intent | Phase 3 |
| TikTok Shop (Pokemon heavy) | 1 hour setup | High for Pokemon | Phase 3+ |
| Reddit organic (r/gamecollecting, console-specific subs) | Ongoing | Low volume, high trust | Phase 2+ |
| YouTube community posts (podcast) | Free | Gated at 100 subs | Podcast dependent |

---

## Budget math — the brutal reality check

At 22.7% margin, fees, and typical dropship cost structure:

**Per-order economics on a $101 average order:**
- Revenue: $101
- COGS (77.3%): $78.07
- Shopify fees (2.9% + $0.30): $3.23
- Max allowable ad cost to break even: $101 − $78.07 − $3.23 = **$19.70 per order**

**Break-even CPA targets by AOV tier:**
| Price tier | AOV | COGS | Fees | Max CPA | Target CPA (20% margin) |
|---|---|---|---|---|---|
| Under $30 | $22 | $17.00 | $0.94 | $4.06 | $3.25 |
| $30–$60 | $45 | $34.79 | $1.61 | $8.60 | $6.88 |
| $60–$100 | $80 | $61.84 | $2.62 | $15.54 | $12.43 |
| $100–$200 | $145 | $112.09 | $4.51 | $28.40 | $22.72 |
| **Winners-band avg** | **$105** | **$81.17** | **$3.35** | **$20.48** | **$16.38** |

**Clicks allowed per conversion at max CPA:**
- At $0.40 avg CPC and Winners tier: $20.48 / $0.40 = **51 clicks per conversion**
- Required conversion rate: 1 / 51 = **~1.95% CVR**

**Is 1.95% CVR achievable?** For a cold store with 0 reviews: **probably not in Phase 1.** Realistic CVR on a store in 8BL's current state is 0.5–1.2%. That means Phase 1 at face value will lose money — which is why the Winners campaign is designed to concentrate on the products with the *highest* individual CVR (proven organic winners). If organic CVR on Galerians is 3%, paid CVR might be 2%, which crosses the bar.

**TL;DR:** Break-even is tight. The Winners list is the only segment plausibly profitable at Month 1. Everything else either needs trust-signal repair first OR will operate as a paid loss-leader for data.

---

## Kill switches and circuit breakers

Automate these in `dashboard/src/lib/safety.ts` before launch if not already wired:

| Trigger | Action | Recovery |
|---|---|---|
| Daily spend > $25 (hard limit) | Pause all campaigns | Manual review + reset |
| 3 consecutive days with spend > $10 and 0 conversions | Pause all campaigns | Manual review (likely a feed or landing page issue) |
| Feed disapproval rate > 5% in 24h | Pause Shopping campaigns | Fix feed issues |
| Shopify store downtime detected | Pause all campaigns | Auto-resume on uptime |
| CPA > 2x target for 48h | Alert (not auto-pause) | Manual bid adjustment |
| CTR < 0.3% for 48h on Winners | Alert | Review search terms or feed titles |

---

## Monitoring playbook

### Daily (5 min, automated + manual)
- Dashboard auto-fetches yesterday's spend, impressions, clicks, conversions, CTR, CVR
- Tristan (or Claude) scans for anomalies + reads top 10 search terms

### Weekly (20 min, Monday mornings)
- Full search terms report review — add 5–20 new negatives
- Product performance report — promote/pause/bid-adjust
- Auction insights — note new competitors

### Monthly (60 min, first of month)
- Full ROAS audit by campaign, ad group, and product
- Recalculate break-even ROAS based on the month's actual margin (not historical)
- Reallocate budget between campaigns based on ROAS
- Review the 14-day success criteria from each Phase

---

## Seasonality note

The store is launching ads in **mid-April 2026.** Historically:
- **Mid-Apr → end of May:** softer collectibles ecommerce; tax refunds end; non-peak shopping season
- **June → August:** back-to-school warmup, handheld gaming uptick
- **October → November:** Q4 gift-buying ramp; peak season for collectibles
- **Black Friday → New Year:** best 5 weeks of the year for retro gaming
- **January:** gift card redemption bump

**Implication:** Launch data from April–May will look worse than the long-run average. Do NOT extrapolate linearly. Commit to at least 60 days of data before any irreversible strategic decision.

---

## What Claude can build now (before launch)

Completed in this session:
- ✅ `docs/google-ads-launch-plan-v2.md` (this doc)
- ✅ `docs/ads-winners-curation-list.md` (curated product list for Phase 1)
- ✅ `docs/ads-negative-keywords-master.md` (400-term master list)
- ⏳ `docs/ads-pre-launch-checklist.md` (next)

Can build in follow-up sessions if Tristan wants:
- `scripts/verify-winners-inventory.py` — query Shopify API for each SKU in the Winners list, confirm in-stock + image + price
- `scripts/ads-feed-audit.py` — full Shopify → Merchant Center feed health check with disapproval details
- `dashboard/src/lib/google-ads-v2.ts` — Phase 1/2/3 campaign management functions (create campaigns via API, pull daily performance, auto-pause)
- Dashboard page `/ads-launch` — single-view pre-launch checklist with live status for every blocker
- `scripts/post-purchase-review-request.py` — one-time email to the 5 past buyers asking for reviews (needs email flow infra first)

---

## What only Tristan can do (manual blockers)

Listed in execution order:

1. **Re-link the Google Ads account** (~10 min) — biggest unblocker
2. **Decide on shipping threshold + return policy updates** (5 min decision, 5 min Shopify setting changes)
3. **Update homepage** per Phase 0.1 (theme editor, ~30 min total)
4. **Install review app** and seed initial reviews (~30 min + ongoing)
5. **Verify conversion tracking in Google Ads UI** (5 min)
6. **Confirm social + podcast content is scheduled** (depends on Tristan's schedule)
7. **Click "Enable" on the campaigns** (1 minute, last step)

---

## Final note — what "MOST effective ROI" actually means here

It does not mean "biggest spend." It means: **smallest spend that still generates enough data to validate or invalidate the core hypothesis that paid traffic can convert profitably on 8BL.** Everything in this plan is designed to answer that question in 14 days at under $60. If the answer is yes, scale. If the answer is no, the plan correctly points at the non-ads work that must precede any further spend.

The biggest ROI lever at this stage is **not the ad configuration.** It is:
1. Fixing the landing page trust holes (stale timer, shipping threshold, return policy, reviews)
2. Curating a narrow target list instead of blanket feed targeting
3. Having a disciplined kill switch so a bad campaign caps at $60 instead of $500

All three are covered here. The rest is execution.
