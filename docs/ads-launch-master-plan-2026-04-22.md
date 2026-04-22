# Google Ads Launch — Master Plan (2026-04-22)

**Status:** Campaign built + configured via API. **PAUSED.** Pre-launch gates remain before flipping to ENABLED.

This doc is the single source of truth for the current launch. Supersedes prior planning docs (`google-ads-launch-plan-v2.md`, `ads-launch-research-2026-04-20.md`, `claude-cowork-brief-2026-04-20-ads-launch.md`) as the operational runbook.

---

## 1. What exists right now (2026-04-22 live state)

Built via `scripts/ads_launch.py` at ~3:00 PM ET.

| Setting | Value | Source |
|---|---|---|
| Account | `8-Bit Legacy` (822-210-2291) via MCC 444-244-1892 | Google Ads |
| Campaign | `8BL-Shopping-Games` (ID 23766662629) | renamed from `8BL-Shopping-All` |
| Status | **PAUSED** | never enabled |
| Type | Standard Shopping | — |
| Networks | Google Search only (no Display, no Partners, no Content) | — |
| Geo | United States only | criterion 2840 |
| Budget | **$20.00/day** | raised from $14 |
| Bidding | Manual CPC (Enhanced CPC OFF) | Google deprecated eCPC for Shopping |
| Priority | High (campaignPriority=2) | — |
| Merchant Center | 5296797260 (12K+ products approved) | — |
| Ad group | `all-products` (ID 202385540384), default bid $0.40 (unused — bids come from leaves) | — |
| Negative keywords | **334** phrase-match, imported from `data/negative-keywords-google-ads-import-v2.csv` | — |

### 1.1 Listing group tree (the bid structure)

```
ROOT (SUBDIVISION)
├── custom_label_2 = "game"        → SUBDIVISION (games get subdivided further)
│   ├── custom_label_0 = "over_50"    → $0.35 CPC
│   ├── custom_label_0 = "20_to_50"   → $0.12 CPC
│   └── custom_label_0 = _else_       → EXCLUDED (catches under_20 + untagged)
└── custom_label_2 = _else_        → EXCLUDED (catches pokemon_card, console, accessory, sealed)
```

Addressable ad inventory after filters: **~2,480 products** (802 over_50 + 1,678 20_to_50, of ~6,088 total games in feed).

### 1.2 Bid math — why these CPCs

Per `ads-launch-research-2026-04-20.md` §3.3, using realistic dropship unit economics:

- **`over_50` (avg $85):** revenue $85 − COGS 70% − $2.77 fees = $22 gross margin. 2:1 ROI target = $11 CPA. At 3% CVR: $11 × 0.03 = **$0.33 ≈ $0.35**.
- **`20_to_50` (avg $32):** revenue $32 − 75% COGS − $1.23 fees = $6.77 gross margin. 2:1 target = $3.25 CPA. At 3% CVR: **$0.10 ≈ $0.12**.
- **`under_20`:** gross margin on a $15 game is ~$3. Can't pay for even one click. Excluded.

**These bids assume 3% CVR.** For a cold store with 0 reviews, real CVR is probably 1–1.5% — which means at these bids we're SLIGHTLY over-paying per click. That's intentional: at lower bids we'd never win auctions, and the $50 lifetime-no-conv kill switch (§4) catches the "bids are fine but the store can't convert" case fast.

### 1.3 Conversion tracking — current state

All 7 actions from the Shopify Google & YouTube app are **ENABLED** and set as **Primary** for their respective goals:

| Action | Category | Status |
|---|---|---|
| Google Shopping App Purchase | PURCHASE | ENABLED, primary |
| Google Shopping App Add To Cart | ADD_TO_CART | ENABLED, primary |
| Google Shopping App Begin Checkout | BEGIN_CHECKOUT | ENABLED, primary |
| Google Shopping App Page View | PAGE_VIEW | ENABLED, primary |
| Google Shopping App Search | PAGE_VIEW | ENABLED, primary |
| Google Shopping App View Item | PAGE_VIEW | ENABLED, primary |
| Google Shopping App Add Payment Info | DEFAULT | ENABLED, primary |

Plus 6 legacy actions from an earlier Shopify pixel app — all HIDDEN, non-blocking.

**Pixel is wired through Shopify's Web Pixel Manager** (sandboxed worker) with tag IDs `G-09HMHWDE5K` (GA4) + `AW-18056461576` (Google Ads) + `GT-TBZRNKQC` (server-side). Per the 2026-04-10 audit, the config is correct — but because it's sandboxed, verification has to happen in Google Ads UI (not DevTools).

**Risk:** actions showing ENABLED means "the action definition exists and is armed" — not "events are flowing." We don't have all-time conversion counts greater than zero on the Ads-attributed side because the campaign has been paused. Need to fire events in an incognito browser session + verify (§3.2 gate below).

---

## 2. What's NOT built via API + requires user action

### 2.1 🔴 CIB exclusion — Merchant Center supplemental feed upload

The strategy says advertise Game Only prices (lower, more competitive in auction) not CIB prices. The feed emits both variants — we exclude CIB at the Merchant Center layer via supplemental feed marking each CIB `item_id` with `excluded_destination=Shopping_ads`.

**File ready at:** `data/merchant-center-cib-exclusion.csv` (6,088 rows, `id,excluded_destination` format)

**Upload steps (Merchant Center UI, ~5 min):**
1. https://merchants.google.com/ → account 5296797260
2. Products → Feeds → **+ Add supplemental feed**
3. Name: `CIB Shopping Exclusion`
4. Country: United States. Language: English.
5. Method: **Upload file** → select the CSV from `~/Projects/8bit-legacy/data/merchant-center-cib-exclusion.csv`
6. Target primary feeds: select the Shopify feed
7. Save. Takes 24–48h to fully propagate.

**Without this upload**, CIB variants will still show in Shopping ads. They'll win auctions on the higher $150+ CIB price, hurting CTR vs competitors at Game Only prices. Not catastrophic, but sub-optimal.

**Not a hard launch blocker.** Launch can proceed without it; upload within Day 0–2.

### 2.2 🟡 Fire a real sample order (optional but recommended)

The `Purchase` action will report Inactive until a real purchase event fires. Options:
- **Wait for first real customer** — natural, zero cost, but first 1-3 days of data will lack Purchase attribution
- **Place a $5-10 real order + self-refund** — fires Purchase end-to-end, verifies the whole funnel works, costs ~$0.30 in Shopify fees. **Recommended.**

### 2.3 🟡 Fire sample events (Add to Cart, Checkout, etc.) in incognito

To verify the non-purchase actions are flowing (they already show ENABLED but no recent data):

1. Open https://8bitlegacy.com in a fresh incognito window (no ad blockers)
2. Navigate a product page → fires Page View + View Item
3. Use the store search bar → fires Search
4. Click Add to Cart → fires Add to Cart
5. Proceed to checkout, enter email + address → fires Begin Checkout
6. Enter card, abandon → fires Add Payment Info
7. Wait 2–4 hours, re-check Google Ads → Tools & Settings → Conversions → Summary
8. All 4 primary goals (Purchase, Add to cart, Begin checkout, Page view) should show **Recording** or **No recent conversions** — not **Inactive** or **Misconfigured**

**Hard gate** for flipping to ENABLED. Without confirmed tracking, spend goes blind.

### 2.4 🟡 VPS dashboard safety.ts redeploy

The repo's `dashboard/src/lib/safety.ts` has the correct new thresholds: $40 daily cap + $50 lifetime-no-conv ceiling. But the VPS at `8bit.tristanaddi.com` is running an older bundle with $25 daily cap + 3-day × $10 no-conv.

**If we launch at $20/day before redeploy:** Google can 2x daily budget ($40 actual), which would false-trip the old $25 cap in the VPS scheduler and auto-pause the campaign. First 3 days are probably safe (impressions ramp up), but a redeploy within 48h of launch is advisable.

Redeploy requires VPS SSH access — not configured in the current Mac session. **Workaround if no access:** temporarily lower daily budget to $15 so Google's 2x overshoot stays below $25. At $15/day × 39 days = $585 of the $700 promo credit. Not ideal but not catastrophic.

### 2.5 🟢 Monitor for first 72 hours (post-enable)

See §5 for the monitoring runbook.

---

## 3. Pre-launch gates (all required before ENABLED)

Leave the campaign PAUSED until every item here is green.

| # | Gate | Status | Action |
|---|---|---|---|
| 1 | OAuth token works, Ads API calls succeed | ✅ | Done 2026-04-22 |
| 2 | Campaign renamed, budget $20, tree built, 334 negatives imported | ✅ | Done via `scripts/ads_launch.py` |
| 3 | All 4 conversion goals show Recording or No recent conversions (not Inactive) | 🟡 | **§2.3** — fire test events, wait 2–4h, verify |
| 4 | Merchant Center diagnostics: <50 item disapprovals, no account-level issues, Shopping program Active | 🟡 | Open Merchant Center → Products → Diagnostics + Growth → Manage programs |
| 5 | At least 5 Winners landing pages spot-checked — fast load, variant pricing correct, trust signals visible | 🟢 | Per `docs/ads-winners-audit-2026-04-11.md` — was green 11 days ago, quick re-check |
| 6 | CIB exclusion feed uploaded to MC | 🟢 (soft) | **§2.1** — can upload after Day 0 |
| 7 | VPS safety.ts redeployed OR budget temporarily lowered to $15 | 🟡 | **§2.4** — or accept first-3-day risk |

**Flip to ENABLED when 3, 4, 5 are green. 6 + 7 can happen in parallel with first-day traffic.**

---

## 4. Kill switches (already wired)

The `google_ads` circuit breaker in `dashboard/src/lib/safety.ts` fires on any of these — auto-pauses the campaign via the Ads API:

| Condition | Threshold | Typical trigger time |
|---|---|---|
| Daily spend exceeds hard cap | **$40** (or $25 on VPS until redeploy) | Minutes |
| **Lifetime spend $50 with 0 conversions** ← user-specified | **$50** cumulative | ~3 days at $20/day |
| 3 consecutive days with $10+ spend and 0 conversions | $30 cumulative | 3 days |
| Store downtime detected | Instant | Minutes |
| Rolling 3-day ROAS < 200% after 7+ days of data | 200% | Day 8+ |

**Check frequency:** every 6 hours via the `ads-safety-check` scheduled job.

**Reset:** when a breaker trips, the campaign stays paused until someone manually resets. Reset path: dashboard `/scheduler` page → Circuit Breakers panel → `google_ads` → Reset.

---

## 5. Post-enable runbook

### Day 0 (flip day)
- [ ] Screenshot campaign state (budget, bids, status, negatives count) for baseline
- [ ] Log enable timestamp in `docs/session-handoff-{date}.md`
- [ ] Set a 24-hour calendar reminder for the first check-in

### Day 1 (first 24h)
Run `scripts/ads_daily_report.py` (see §6). Expected:
- **Spend**: near $20, ±30%. $0 = feed issue or bid too low. $30+ = budget escape (check breaker).
- **Impressions**: 500–2,000 across ~2,480 products
- **CTR**: 0.7–1.5% baseline; below 0.5% = title/image/price issue
- **Conversions**: probably 0 — Shopping takes 24-48h to season
- **Search terms**: top 20 already visible in Google Ads UI. Add any junk to negatives.

### Days 2–3
Daily 5-min check via `ads_daily_report.py`:
- Cumulative spend vs conversions (hard pause at $50 cumulative, 0 conv — handled by breaker)
- New search terms — add more negatives aggressively (expect 20–30% junk in week 1)
- Any high-spend / no-click product? Candidate for product-level exclusion.

### Day 7 — first optimization pass
- Pull 7-day report. Group by product.
- **Winners:** products with 1+ conversion → consider bid-up 10–15% within hard limits
- **Dead weight:** 20+ clicks, 0 conv → add to product exclusion list
- **New negatives:** add 10–30 from search terms

### Day 14 — decision point
Recompute actual ROAS from real data:
- **ROAS > 300%** → continue, tighten bids, raise budget 10%
- **ROAS 100–300%** → hold, investigate landing page UX + reviews
- **ROAS < 100% or 0 conv** → **pause**, escalate. Store needs work, not more ads.

### 2026-05-31 — promo credit expires
- Check Google Ads account → Billing → Promotional credit balance
- If any credit remains, it forfeits automatically at end of day — no rollover
- Decide: continue at $20/day out of pocket, OR drop to $5–10 baseline based on ROAS

---

## 6. Operational tooling

| Script | What it does | When to run |
|---|---|---|
| `scripts/ads_audit.py` | Read-only snapshot of account state (campaigns, bids, negatives, conversions) | Anytime — sanity check |
| `scripts/ads_launch.py` | Builds/rebuilds the campaign from the plan. Idempotent. | Only if re-building from scratch |
| `scripts/ads_daily_report.py` | Pulls last-24h spend/impr/CTR/conv by product + surfaces top new search terms | Every morning (or via scheduler) |
| `scripts/google_ads_reauth.py` | Mints a fresh OAuth refresh token | Only if consent screen expires (now in Production, so rarely) |

---

## 7. Risks + mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| VPS safety false-trips on Day 1 at $25 cap | Low (24h rarely hits $25) | Redeploy dashboard within 48h OR manually raise cap OR drop budget to $15 |
| CIB variants win auctions over Game Only | Medium (until MC supplemental uploaded) | Upload feed by end of Day 0 |
| Conversion tracking is actually broken despite ENABLED status | Low (infrastructure verified 2026-04-10) | §2.3 event-firing verification before enabling |
| Account re-suspends during launch | Low (freshly reviewed) | Pause, open support case, wait |
| Dropship COGS spike | Medium | Order validator runs every 30 min, catches before fulfillment |
| Seasonality (mid-April soft month) | Medium | 14-day minimum before any scaling decision |
| $50 cumulative spend, 0 conversions on first pass | Medium | Kill switch fires automatically; investigate store issues before re-enabling |

---

## 8. What this plan does NOT include (intentional)

- **Search campaigns / Brand bids / Discovery / Remarketing / PMax** — all deferred per `feedback_ads_strategy.md`. Shopping only for Phase 1.
- **Per-console bid modifiers** — not enough data to justify splitting. Revisit end of Week 2.
- **Subdividing `over_50` into `50_to_100` + `over_100`** — starves each tier of data. Revisit end of Week 2.
- **Microsoft Ads (Bing) import** — separate task, high ROI but not a launch blocker.
- **Homepage redesign + trust-signal work** — on the roadmap but not gating ads launch. If first 14 days convert poorly, the right response is to fix the store, not scale ads.

---

## 9. Decision log

| Date | Decision | Rationale |
|---|---|---|
| 2026-04-20 | Shopping-only, no Search/Brand/Discovery/PMax/Display | User direction (feedback memory) |
| 2026-04-20 | Exclude Pokemon singles, sealed, consoles, accessories, CIB | Margin + fraud risk + strategy |
| 2026-04-20 | $20/day budget (up from $14) | Burn $700 promo credit by 2026-05-31 at Google's ~85% of-budget delivery rate |
| 2026-04-20 | $50 lifetime no-conv hard pause | User direction — Shopping CPCs cheap; if $50 doesn't convert, store is broken |
| 2026-04-22 | API v17 → v21 | v17/v18/v19 all return 404; v20/v21 are the live versions |
| 2026-04-22 | Desktop OAuth client, consent screen Production | Unblocks long-lived refresh tokens |
| 2026-04-22 | Execute via `scripts/ads_launch.py` (API-driven) rather than UI | Idempotent, reproducible, audit-able |

---

## 10. Devil's advocate — every risk scenario I could think of, and how it's handled

Run `python3 scripts/ads_preflight_check.py` anytime for the automated-check version. Below covers everything I could think of, automated or not.

### 10.1 Scenarios with automated verification (all passing 2026-04-22)

| # | Scenario | Status |
|---|---|---|
| 1 | Multiple campaigns accidentally active | ✅ only one campaign exists |
| 2 | Campaign accidentally enabled | ✅ PAUSED |
| 3 | Listing tree wrong shape or bids wrong | ✅ 6-node tree, bids match plan |
| 4 | Negatives not imported | ✅ 334 imported |
| 5 | Display/Partners network leak | ✅ both OFF |
| 6 | Enhanced CPC active (deprecated, hurts Shopping) | ✅ OFF |
| 7 | Wrong Merchant Center linked | ✅ 5296797260 |
| 8 | Budget wrong or shared across campaigns | ✅ $20/day, dedicated |
| 9 | Wrong geo target (e.g., whole world, drives loss) | ✅ US only |
| 10 | Conversion actions not primary for goals | ✅ all 7 enabled + primary |
| 11 | `price_tier:over_50` tag drift (some products actually <$50) | ✅ sampled 10, all $50+ |
| 12 | Store offline | ✅ homepage 200 |
| 13 | Winners landing pages broken | ✅ 3 spot-checked, 200 + cart |

### 10.2 Scenarios with partial verification — needs your manual check

| # | Scenario | Mitigation |
|---|---|---|
| 14 | Conversion pixel wired but not firing | Fire events in incognito + wait 2-4h, verify Recording in UI (§2.3) |
| 15 | Merchant Center feed has recent disapprovals | Check MC → Products → Diagnostics (§2.4) |
| 16 | CIB variants win auctions, hurt CTR | Upload `data/merchant-center-cib-exclusion.csv` as supplemental feed (§2.1) |
| 17 | Sale wave active, compare_at_price bug disapproves products | Spot-check MC Diagnostics for `compare_at_price` warnings |
| 18 | 8BITNEW promo code not active | Shopify API lacks `read_discounts` scope, you verify in Shopify admin |

### 10.3 Scenarios covered by kill switches (automatic pause)

| # | Scenario | Switch |
|---|---|---|
| 19 | $40+ spent in a single day | `MAX_DAILY_AD_SPEND` = $40 |
| 20 | $50 cumulative spent, 0 conversions | `LIFETIME_NO_CONVERSION_CEILING` = $50 |
| 21 | 3 consecutive days × $10+ spend + 0 conv | backup check |
| 22 | Store downtime during ads | store-uptime check |
| 23 | ROAS drops below 200% after 7+ days | `rolling_roas_floor` |

### 10.4 Scenarios with known residual risk (accepted or flagged)

| # | Scenario | Risk | Handling |
|---|---|---|---|
| 24 | VPS dashboard still enforces old $25 cap (not $40) | Day 1 false-trip if Google 2x's daily budget | Low risk first 3 days (impressions ramp slow). Redeploy VPS within 7 days. If trips, manually reset breaker. |
| 25 | eBay sourcing cost spikes mid-campaign | Thins margin on individual orders | Order validator runs every 30 min, catches pre-fulfillment |
| 26 | Competitor raises bids, we lose all auctions | 0 impressions, no data | We're bid-capped; acceptable — we only want profitable auctions |
| 27 | Google algorithm favors PMax over Standard Shopping | Less inventory served | Acceptable — PMax excluded by strategy, review in 30 days |
| 28 | Shopping ad shows $50+ price but checkout charges shipping (threshold $50) | Customer disappointment at checkout | User accepted this; $50 threshold stays |
| 29 | Data-driven attribution undercounts non-click paths | Slight CPA underestimate | Default attribution model is fine for Phase 1 |
| 30 | Promo credit ($700) runs out before 2026-05-31 | Out-of-pocket spend starts earlier | Budget sized for Google's ~85% delivery rate; should land close to the line |
| 31 | Promo credit unused on 2026-05-31 | Forfeit $30-80 of credit | Acceptable — can't perfectly predict delivery rate |
| 32 | Account suspension risk (dropship policy) | Campaign pauses indefinitely | Fresh review, store has value-adds (warranty, returns, testing) documented |
| 33 | High return rate on dropshipped games | Net profit < gross profit | Dropship model, inherent risk, not ads-specific |
| 34 | First-week search terms report full of junk | 20-30% wasted budget | Expected. Daily negative additions via `ads_daily_report.py` |

### 10.5 Scenarios I explicitly chose NOT to mitigate pre-launch

| # | Scenario | Why not |
|---|---|---|
| 35 | Subdivide over_50 into over_100 + 50_to_100 | Requires feed relabeling, 24h propagation lag; premature without data |
| 36 | Build real per-product margin classifier | 2-3 hours; no evidence margin-tier actually predicts CVR |
| 37 | Per-console bid modifiers (N64 vs GBA) | Data-driven decision; wait for 14d perf data |
| 38 | Bid-up individual Winners products | Guess without data; let conversion data tell us |
| 39 | Remarketing / Brand / Search / Display campaigns | Strategy says Shopping only for Phase 1 |
| 40 | Microsoft Ads (Bing) import | Parallel track, not a launch blocker |

### 10.6 Things I can't check from my side

- Circuit-breaker state on the VPS dashboard — would require VPS access (nginx 401 blocks me)
- Merchant Center UI data (disapproval counts, feed errors, Shopping program status) — Ads API only gives partial visibility
- Shopify discount codes (need `read_discounts` scope on the token, not granted)

---

## 11. Ownership + monitoring

**Owner (primary):** Tristan — makes all "scale or pause" calls based on data.
**Assist:** Claude Code — runs daily reports, flags anomalies, proposes bid + negative adjustments weekly.
**Auto-safety:** dashboard circuit breaker — runs every 6h, pauses on any kill-switch condition (§4).
**Manual override:** Google Ads UI → Campaigns → pause at any time.
