# Google Ads Launch Research — 2026-04-20

**Author:** Claude (Opus 4.7, 1M context)
**For:** Tristan, 8-Bit Legacy
**Supersedes:** `docs/google-ads-launch-plan-v2.md` (drafted 2026-04-10, predates suspension/lift + strategy re-scope)
**Status:** Research complete. Launch BLOCKED on 5 items in Part 5. Campaign should NOT be enabled until all 5 are green.

---

## Executive summary

Three sentences:

1. The paused campaign `8BL-Shopping-All` at $14/day is close but needs a strategy re-scope per Tristan's 2026-04-20 direction: Shopping-only, games-only, Game Only variants only (no CIB), $50+ games weighted highest, hard pause at $50 cumulative with 0 conversions.
2. Five pre-launch blockers (Google Ads OAuth expired, Merchant Center diagnostics unverified, conversion tracking "Recording" unconfirmed, CIB supplemental feed not yet built, safety.ts trip threshold still at old $10×3-day instead of $50 cumulative) — none are hard, all need a ~90 min cowork + 30 min terminal work session.
3. Unit economics math supports max CPC of $0.35 on the `over_50` tier and $0.12 on the `20_to_50` tier at 3% CVR and 2:1 ROI targets; `under_20` must be excluded because margins can't support even a single click.

---

## Part 1 — Current state (verified 2026-04-20)

### 1.1 Store inventory (from Shopify GraphQL)

| Category | Active products | Notes |
|----------|-----------------|-------|
| Games | **6,088** | Primary ad target |
| Pokemon cards | 1,176 | **EXCLUDE** from ads (1.15x margin) |
| Consoles | 15 | Exclude (high return/fraud risk) |
| Accessories | 11 | Exclude (low AOV) |
| Sealed | 0 | Currently untagged; if added, exclude |

### 1.2 Games by price tier

| Tier | Count | % | Ad treatment |
|------|-------|---|--------------|
| Under $20 | 3,608 | 59% | **EXCLUDE** — can't pay for a single click at realistic CVR |
| $20-$50 | 1,678 | 28% | Low bid tier |
| Over $50 | 802 | 13% | Primary bid tier (user's emphasis) |

**Addressable ad inventory after filters: ~2,480 products.** Half a feed — tight enough to matter per-click, wide enough to let Google find converting SKUs.

### 1.3 Winners products spot-check (4 of 17)

| Product | Game Only | CIB | Tags correct | In stock |
|---------|-----------|-----|--------------|----------|
| Galerians (PS1) | $59.99 | $132.99 | ✓ | ✓ |
| Mystical Ninja Starring Goemon (N64) | $174.99 | $452.99 | ✓ | ✓ |
| Silent Hill 2 (PS2) | $175.99 | $258.99 | ✓ | ✓ |
| Phantasy Star Online I & II (GC) | $162.99 | $303.99 | ✓ | ✓ |

All ACTIVE, correctly tagged (`category:game`, `console:*`, `margin:medium`, `price_tier:over_50`), both variants purchasable, image + SEO meta present, `mm-google-shopping.custom_product=true` metafield (GTIN bypass for used goods). **Winners list is feed-healthy.**

### 1.4 Landing page check (Galerians)

- Response 200, variant-price-display fix intact (`money` class present)
- Default shown price: $59.99 (Game Only, as expected — lower number)
- Free shipping over $35 banner live
- 90-day return policy displayed
- Trust signals consistent with previous audits

### 1.5 Campaign state

- Paused campaign `8BL-Shopping-All` exists (ID `23766662629`)
- $14/day budget, Manual CPC, High priority, US, Search Network only — all correct for our direction
- Product group subdivisions: **not saved** (mid-save when suspension hit on 2026-04-16)
- 334 negative keywords: **not imported**
- Conversion tracking events re-fired 2026-04-16 but **"Recording" state not verified**

### 1.6 Google Ads API access

- `GOOGLE_ADS_REFRESH_TOKEN` in `config/.env` — **expired** (tested 2026-04-20 via `grant_type=refresh_token` against `oauth2.googleapis.com/token` → `invalid_grant`)
- Means: no API-driven campaign edits until cowork refreshes the token
- Dashboard monitoring jobs (google-ads-sync, ads-safety-check) are also blocked until refresh

### 1.7 Shopify API access

- Working. Verified via multiple GraphQL calls this session.

---

## Part 2 — Strategy (locked in with Tristan 2026-04-20)

Per explicit direction, the strategy is:

- **Format:** Shopping campaigns only. No Search, no Brand, no Discovery, no PMax, no Display remarketing.
- **Fulfillment constraint:** None — unlimited capacity.
- **Risk:** HARD PAUSE at $50 cumulative spent with 0 conversions. Reason: Shopping CPCs are cheap and intent-driven; if $50 doesn't convert, the funnel is broken, not the ads.
- **Inventory in:** Games (retro + Pokemon *games* — distinguish from Pokemon cards).
- **Inventory out:** Pokemon singles, sealed, accessories, consoles, **CIB variants**.
- **Price emphasis:** $50+ games strongly preferred; $20-$50 allowed at lower bids; under $20 excluded.
- **Variant selection:** Advertise Game Only prices only. Lower price = more competitive in Shopping auction vs DKOldies/Lukie = higher CTR. Customer upsells to CIB on the product page if desired.
- **Optimize for:** Highest ROI per dollar spent. Not impressions, not volume, not brand awareness.

---

## Part 3 — Recommended campaign architecture

### 3.1 Campaign settings

| Setting | Value | Rationale |
|---------|-------|-----------|
| Name | `8BL-Shopping-Games-Only` (rename from `8BL-Shopping-All`) | Reflects the new scope |
| Type | Standard Shopping | Not PMax — cold store, no conversion history |
| Merchant Center | 5296797260 | Unchanged |
| Networks | **Search only** | Display + Partners off (data quality priority) |
| Geo | United States only | Dropship constraint |
| Language | English | |
| Bidding | **Manual CPC** | Best for cold store; switch to Target ROAS only after 20+ conversions |
| Budget | **$17/day** | $700 promo ÷ 41 days ≈ $17.07; burns full credit before 2026-05-31 expiry |
| Priority | High | Only one campaign — priority meaningless but set high |
| Status | Paused (until all pre-launch blockers green) | |

### 3.2 Product group tree (the bid tiers)

```
All products
├── Custom label 2 = "game"                  ← include only
│   ├── Custom label 0 = "over_50"    → max CPC $0.35   ← primary bid tier
│   ├── Custom label 0 = "20_to_50"   → max CPC $0.12   ← secondary
│   └── Custom label 0 = "under_20"   → EXCLUDE
├── Custom label 2 = "pokemon_card"   → EXCLUDE
├── Custom label 2 = "console"        → EXCLUDE
├── Custom label 2 = "accessory"      → EXCLUDE
├── Custom label 2 = "sealed"         → EXCLUDE
└── Everything else                    → EXCLUDE
```

**Bid math (shown in 3.3). Simplifications chosen over detail:**
- Not further subdividing `over_50` into $50-$100 and $100+ because we only have 802 products there; splitting further starves each tier of data. Revisit after 14 days if data supports.
- Not bidding by console (e.g., higher on N64 than GBA) — same reason; let Google learn which products drive conversions organically and adjust.

### 3.3 Bidding math (per-tier CPC ceiling derivation)

**`over_50` tier (avg price ~$85):**
- Revenue: $85
- COGS (eBay dropship, 70% typical): $60
- Shopify fees (2.9% + $0.30): $2.77
- Gross margin before ads: **$22.23**
- Break-even CPA: $22
- Target 2:1 ROI CPA (ad spend = 50% of gross): **$11**
- Max CPC at 3% CVR: 11 × 0.03 = $0.33 → round to **$0.35**
- Max CPC at 5% CVR (optimistic, strong intent match): $0.55 — reserve for Phase 2 bid-up after we see real CVR data

**`20_to_50` tier (avg price ~$32):**
- Revenue: $32
- COGS (75%): $24
- Fees: $1.23
- Gross: **$6.77**
- Break-even CPA: $6.50
- 2:1 CPA: $3.25
- Max CPC at 3% CVR: 3.25 × 0.03 ≈ $0.10 → round to **$0.12**
- Marginally profitable; include only so Google has a bid floor that doesn't constrain auction access

**`under_20` tier: EXCLUDE.** Gross margin on a $15 game is ~$3. Can't buy even one click and still profit.

### 3.4 CIB exclusion — supplemental feed approach

**Problem:** The Shopify Google & YouTube app emits one offer per variant. Both Game Only and CIB variants appear in the Merchant Center feed as separate items with separate `item_id`s. Google Ads product group subdivisions don't support variant-title filtering.

**Solution:** Merchant Center supplemental feed with `excluded_destination=Shopping_ads` on each CIB variant's item_id.

**Implementation:** Write `scripts/generate-cib-exclusion-feed.py` which:
1. Queries Shopify for all products with 2+ variants in `category:game`
2. Identifies CIB variants (title contains "Complete" or "CIB")
3. Computes the Merchant Center item_id (Shopify app convention: `shopify_US_<productId>_<variantId>`)
4. Outputs CSV with columns `id,excluded_destination` — one row per CIB variant
5. Output goes to `data/merchant-center-cib-exclusion.csv`

**Upload:** Manual via Merchant Center → Products → Feeds → Add supplemental feed → upload CSV → schedule refresh weekly. One-time ~5 min task; auto-refreshes after.

Expected row count: ~6,112 CIB variants (per prior audits).

### 3.5 Negative keywords

- Existing list at `data/negative-keywords-google-ads-import.csv` — 334 terms, phrase match
- Campaign name in that CSV is `8BL-Shopping-All` — regenerate or rename via find/replace before import
- Master list at `docs/ads-negative-keywords-master.md` has ~400 terms; 66 additional covering edge cases (hardware mods, graded versions, parts listings) — import if we hit those queries in first week
- No urgent additions for 2026. The retro gaming vocabulary hasn't shifted meaningfully.

---

## Part 4 — Safety / kill switches

### 4.1 Current `dashboard/src/lib/safety.ts` triggers (reviewed in this session)

| Check | Current threshold | Verdict |
|-------|-------------------|---------|
| MAX_DAILY_AD_SPEND | $25 | **Too low for $17/day base** — Google can 2x daily budget ($34), would false-trip. Recommend $40. |
| 3 consecutive days with $10+ spend and 0 conversions | 3 days × $10 = $30 before trip | Close to user's $50 rule but slower. **Replace or augment.** |
| Store downtime (async) | Handler-level | Keep |
| Rolling 3-day ROAS < 200% after 7+ days | Floor at 200% | Keep |

### 4.2 Required safety.ts updates (not yet applied — flagged as follow-up)

```typescript
// NEW Check 2B: Lifetime cumulative trip (per user direction 2026-04-20)
// Fires immediately at $50 cumulative spent with 0 conversions total.
const lifetime = db
  .select({
    totalCost: sql<number>`coalesce(sum(cost), 0)`,
    totalConv: sql<number>`coalesce(sum(conversions), 0)`,
  })
  .from(googleAdsPerformance)
  .get();

const lifetimeCost = lifetime?.totalCost ?? 0;
const lifetimeConv = lifetime?.totalConv ?? 0;
const fiftyPassed = lifetimeCost < 50 || lifetimeConv > 0;
if (!fiftyPassed && !shouldTrip) {
  shouldTrip = true;
  tripReason = `Hard pause: $${lifetimeCost.toFixed(2)} spent cumulative with 0 conversions (floor $50)`;
}
```

Plus bump `MAX_DAILY_AD_SPEND: 25 → 40`.

Requires dashboard rebuild + VPS redeploy. Deferred as a follow-up since dashboard deprioritization applies everywhere except fulfillment/eBay — but this one IS safety-critical, so it's the exception.

### 4.3 Check cadence

Currently `ads-safety-check` runs every 6 hours per `scheduler.ts`. At $17/day base with a failing campaign, $50 hits in ~3 days. 6-hour check means max lag between trip and pause is 6 hours. At worst, ~$4 of overshoot. Acceptable.

Bumping to every 2 hours would reduce overshoot to ~$1.40 max but adds API load. **Not worth it in Phase 1.** Revisit if we actually trip.

### 4.4 Circuit breaker propagation

When the breaker trips, `pauseAllCampaigns()` in `dashboard/src/lib/google-ads.ts` hits the Ads API to pause. **This also needs the refreshed OAuth token** — another dependency on Blocker #1 in Part 5.

---

## Part 5 — Pre-launch blockers (all must clear before enabling)

### 5.1 Refresh the Google Ads OAuth token 🔴

Current token returns `invalid_grant`. Blocks: API-based campaign edits, dashboard monitoring jobs, circuit breaker's automated pause.

**Fix:** 5-min cowork browser flow:
1. Visit: `https://accounts.google.com/o/oauth2/v2/auth?client_id={GOOGLE_ADS_CLIENT_ID}&redirect_uri=urn:ietf:wg:oauth:2.0:oob&response_type=code&scope=https://www.googleapis.com/auth/adwords&access_type=offline&prompt=consent`
2. Sign in with `sideshowtristan@gmail.com` (account that owns `822-210-2291`)
3. Grant AdWords scope
4. Copy auth code → exchange for refresh token via `curl` to `https://oauth2.googleapis.com/token`
5. Update `config/.env` on Mac + push the same token to `dashboard/.env.local` on VPS

Full recipe included in cowork brief (see Part 9).

### 5.2 Merchant Center deep diagnostics audit 🟡

Last audit: 2026-04-16. Claimed feed healthy at that time (12.2K products, <50 disapproved). Need to re-verify BEFORE enabling because: ad suspension lift triggered a feed reprocessing per Google's docs, and any changes in the last 4 days need a look.

**Cowork browser task** — steps in the brief (Part 9).

### 5.3 Conversion tracking "Recording" state 🔴

Events re-fired 2026-04-16. State was "events captured, waiting 2-4h for propagation". Never re-verified after the lift. Need to confirm each of 4 primary goals (Purchase, Add to Cart, Begin Checkout, Page View) shows "Recording" not "Inactive" in Google Ads UI.

**Cowork browser task** — if any is still Inactive, fire new events in incognito before campaign enable.

### 5.4 CIB supplemental feed generated + uploaded 🟡

- Write `scripts/generate-cib-exclusion-feed.py` (I'll do this locally; ~30 min)
- Run it (~5-10 min against Shopify API)
- Cowork uploads the resulting CSV to Merchant Center → Products → Feeds → supplemental feed
- Wait 24 hours for feed to process

**Blocker for clean campaign.** Without this, CIB offers compete in auction against Game Only; we lose price-competitiveness vs DKOldies (whole reason Tristan picked Game Only-only strategy).

### 5.5 safety.ts patched for $50 trip 🟡

See Part 4.2. Edit + dashboard rebuild + VPS redeploy.

**Can go live without this** but then first-line safety is 3-days-$10-each ($30 before trip) which is close but not what user asked for. Worth getting right before money moves.

---

## Part 6 — First 14 days playbook

### Day 0 — Enable (only after Part 5 all green)

- Screenshot campaign state (budget, tier bids, negative count, status=Enabled)
- Log enable timestamp in a handoff doc
- Set a 24h reminder to come back for the first check-in

### Day 1 — First 24 hours

Check every 6 hours. Look for:
- **Spend pacing** — should be near $17/day after 24h. $0 = feed issue or bid too low. $30+ = budget escape (trip safety).
- **Impressions** — expect 500-2,000 on first day across ~2,480 products.
- **CTR** — Shopping ads baseline is 0.7-1.5%. Below 0.5% = title/image/price issue.
- **Search terms** — read the top 20 even at this early point. Add any junk to negatives.
- **Any disapproved products** — feed health check in Merchant Center.

Emit a Navi task to Tristan if spend > $10 with 0 clicks (data pipeline issue).

### Days 2-3 — Data accumulation

Daily 5-min check:
- Cumulative spend vs. conversions
- New search terms in report — negate aggressively (expect 20-30% junk in first week)
- Any high-spend / no-click products? Bid-down candidates.

### Day 7 — First optimization pass

- Pull 7-day report. Group by product.
- **Top performers:** products with 1+ conversions → bid up 10-15% within hard limits
- **Dead weight:** products with 20+ clicks and 0 conversions → exclude them individually
- **Review negatives:** add 10-30 new ones from search terms

### Day 14 — Decision point

- Recompute actual ROAS. If > 200%: continue, tighten bids.
- If 100-200%: reduce budget to $10/day, investigate landing pages.
- If < 100% or still 0 conversions: **pause**, escalate. The store needs work, not more ads.

---

## Part 7 — Go/no-go decision tree

```
Start of week 1:
  $50 cumulative, 0 conversions? → PAUSE, investigate (circuit breaker handles)
  $50 cumulative, ≥1 conversion? → CONTINUE
  $0 cumulative after 24h? → INVESTIGATE (feed/bid issue) before continuing

End of week 1 (day 7):
  ROAS > 300%? → Scale within hard cap; consider bumping over_50 bid to $0.45
  ROAS 100-300%? → Hold, optimize
  ROAS < 100%, >= 1 conversion? → Tighten bids, review landing pages, hold
  Still 0 conversions? → Safety breaker should have tripped at $50

End of week 2 (day 14):
  ROAS > 500%? → Promote 3-5 winners to Winners-only Phase 2 campaign at $25/day each
  ROAS 200-500%? → Continue, compound weekly optimizations
  ROAS < 200%? → Pause, fix store issues (reviews, landing page UX)
```

---

## Part 8 — Risks + mitigations

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Account re-suspends during launch | Low — freshly reviewed | Pause campaigns, open support case, wait for lift; don't create new campaigns |
| CIB supplemental feed doesn't propagate | Low | Wait 48h post-upload; if still no effect, fall back to item-ID exclusion in campaign (tedious but works) |
| Content ID / copyright on product images | Very Low | All product images are retail box art we legally use. No issue expected. |
| Dropship COGS spike (eBay listing churn) | Medium | Order validator runs every 30 min per `dashboard/src/lib/order-validator.ts`; catches before fulfillment |
| Competitor brand bid contention | Low | We explicitly don't bid on "8bit legacy" / competitor brand terms |
| Seasonality (mid-April softness) | Medium | First 14 days may underperform the eventual run-rate; don't extrapolate linearly |
| Conversion tracking gaps (missing purchase attribution) | Medium | Part 5.3 gate must show "Recording" before enable; post-launch, spot-check first real purchase |
| Google Ads algorithm penalty for API-uploaded catalog | Very Low | No evidence in Google's own docs of differential treatment |

---

## Part 9 — Cowork brief needed

Separate doc: `docs/claude-cowork-brief-2026-04-20-ads-launch.md` — covers the 5 pre-launch blockers with click-by-click steps. Will draft after this research doc is committed.

---

## Part 10 — Open questions / decisions still needed from Tristan

None of these block cowork work but good to pre-answer before Day 0:

1. **Subdividing `over_50` into `50_to_100` and `over_100`?** My recommendation is NOT in Phase 1 (too-thin data per sub-tier). Revisit end of week 2. Agree?
2. **Per-console bid modifiers?** I'm skipping for Phase 1. Would you want a higher bid on N64 / PS1 specifically (observed organic bestsellers)?
3. **First sanity real-purchase test?** Placing a $5-10 real order + refund would fire the Purchase conversion action and flip it from "Inactive" to "Recording". Safer than waiting for first real customer. Worth doing?
4. **Promo credit expiry plan:** $700 burns to ~$0 by 2026-05-31. Post-expiry, continue at $17/day out of pocket, OR drop to $5-7/day baseline? Depends on ROAS.

---

## Followup work (not blocking launch, but flag for after Day 0)

- [ ] Write `scripts/generate-cib-exclusion-feed.py` (part of blocker 5.4)
- [ ] Patch `dashboard/src/lib/safety.ts` (blocker 5.5)
- [ ] Redeploy dashboard to VPS with new safety rules
- [ ] Refresh `config/.env` and `dashboard/.env.local` on both Mac and VPS with the new Google Ads refresh token (post-cowork)
- [ ] Write the cowork brief (next, this session)
- [ ] Set up 24h / 7d / 14d calendar reminders for the check-in cadence
