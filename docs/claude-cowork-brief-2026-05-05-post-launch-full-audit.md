# Cowork Brief — 2026-05-05 — Post-Launch Full System Audit

## Goal

Campaign `8BL-Shopping-Games` was flipped to ENABLED at 12:21 ET today. After flip, multiple infrastructure issues were discovered and fixed (circuit breaker reset, dashboard redeployed, OAuth token synced, 4 broken jobs restored). Now I need a thorough **read-only browser-side audit** of every system to confirm everything is healthy.

This brief is **READ-ONLY** — capture verbatim what's visible, do NOT change anything.

Time budget: ~15-20 minutes.

## Hard guardrails — READ BEFORE STARTING

✗ Do NOT click "Apply" on ANY recommendation in Google Ads
✗ Do NOT pause / enable / remove / edit any campaign, ad group, product group, or conversion goal
✗ Do NOT change budget, bid strategy, daily cap, networks, or geo targeting
✗ Do NOT add/remove negative keywords or product groups
✗ Do NOT click "Set up Smart Bidding" / "Try Performance Max" / any campaign-type migration
✗ Do NOT click "Auto-apply recommendations" toggle
✗ Do NOT modify any product attribute in Merchant Center
✗ Do NOT modify the Shopify storefront, theme, pages, or apps
✗ Do NOT click "Run Now" on any scheduler job in the VPS dashboard
✗ Do NOT click "Reset" on any circuit breaker
✗ Do NOT modify any settings in the VPS dashboard
✗ Do NOT log in for Tristan — surface login walls if hit
✗ Do NOT take any "Optimization score" actions

This is a *report only* audit. Look, capture, don't touch.

If a confirmation dialog appears for any of the above — screenshot, click Cancel, surface back.

## Phase 1 — Google Ads campaign (3 min)

URL: `https://ads.google.com/aw/campaigns?campaignId=23766662629`

Capture verbatim:
- Campaign status badge (expected: "Eligible")
- Today's headline metrics (Impressions / Clicks / CTR / Avg CPC / Cost / Conversions / Conv. value)
- Any **alert banner** at the top (red/yellow/orange) — list ALL of them verbatim
- "Recommendations" / "Optimization score" widget — score number + top 3 recommendation titles (do NOT click into any)
- The "Status" pill on the campaign row — color and text

## Phase 2 — Listing groups / Product groups view (3 min)

Click into the **all-products** ad group → **Listing groups** tab (or "Product groups").

Capture verbatim:
- The tree structure shown. Expected:
  - ROOT (subdivision)
  - ├── custom_label_0 = over_50 → bid $0.35
  - ├── custom_label_0 = 20_to_50 → bid $0.08
  - └── custom_label_0 = (else) → EXCLUDED
- Per-leaf metrics today (Impressions / Clicks / Cost)
- Bids match $0.35 and $0.08 — confirm yes/no
- Any leaf showing "Disapproved" or warning icon

## Phase 3 — Conversions page (1 min)

URL: `https://ads.google.com/aw/conversions/customerconversiongoals`

Capture:
- For each row in the customer conversion goals table, the Status column verbatim
- Specifically: **Purchase** row should say something like "Active" / "Recording conversions" with a green dot
- Any banner at top about conversion tracking issues

## Phase 4 — Account-level diagnostics (1 min)

URL: `https://ads.google.com/aw/overview`

Capture:
- Any red/yellow alert banner at the top
- Any "Account suspension" or policy warning
- Account-level "Optimization score" if visible

## Phase 5 — Merchant Center diagnostics (4 min)

URL: `https://merchants.google.com/mc/diagnostics?a=5296797260`

Capture:
- Item issues — count by severity:
  - Errors (red): __
  - Warnings (yellow): __
  - Notifications (blue/gray): __
- Account-level issues (if any) — these block the whole feed
- Top 5 issues by frequency: title + affected item count

URL: `https://merchants.google.com/mc/products/list?a=5296797260`

- Click into any product where the title contains "Game" and is over $50 (e.g. NES Game over $50)
- Capture the product detail page:
  - **Custom labels** section: what values are shown for custom_label_0, custom_label_1, custom_label_2, custom_label_3, custom_label_4?
  - **Issues** section: any disapprovals or warnings on this specific product?
  - **Sync status** — when was it last synced?

Pick a 2nd product (a different over_50 game) and repeat the custom labels + issues capture.

## Phase 6 — VPS Dashboard health (4 min)

URL: `https://8bit.tristanaddi.com/`
Username: `admin`
Password: `obuIactQbEBq0HeO`

Visit these dashboard pages and capture:

### 6a. `/scheduler` page
- Are all 6 jobs listed with status pills?
- For each job, capture its last run time + status (success/failed):
  - shopify-product-sync: ___
  - google-ads-sync: ___
  - fulfillment-check: ___
  - price-sync: ___
  - pokemon-price-sync: ___
  - ads-safety-check: ___
- Circuit Breakers panel — are both `pricing` and `google_ads` showing `not tripped`?

### 6b. `/safety` page (the Ads Safety dashboard)
- All 5 safety checks shown? (daily_spend_limit, lifetime_no_conversion_ceiling, consecutive_no_conversions, store_uptime, rolling_roas_floor)
- Each showing pass/fail badge + threshold + current value?
- Any check failing or about to trip?

### 6c. `/fulfillment` page
- Are there any active CRITICAL alerts (red)?
- Any unfulfilled orders being flagged as LOSS or thin margin?

### 6d. `/orders` page
- Any orders in the last 24h?

### 6e. `/ads` page (if it loads)
- Does it show today's campaign performance (impressions/clicks/cost)?
- Any alerts on this page?

## Phase 7 — Storefront sanity (1 min)

URL: `https://8bitlegacy.com/`

- Page loads OK?
- Visit `https://8bitlegacy.com/pages/contact` — does the new Contact page render with email + phone (229) 329-2327 visible?
- Spot-check 1 product PDP — does the Add to Cart button work (don't actually checkout, just verify it adds)?

## Phase 8 — Ad preview (2 min, optional)

Inside the Google Ads campaign or ad group, find "Ad preview" or "Inventory" or "Products" tab.

Capture:
- Screenshot of 1-2 sample products as Shopping ads (image + title + price)
- Whether the price displayed matches the storefront price
- Whether the title looks weird/truncated/spammy

If "Ad preview" not directly available: paste a search like "ace combat 2 ps1 game" into ads.google.com search preview tool.

## Handoff

Write `docs/cowork-session-2026-05-05-post-launch-full-audit.md` with:

```markdown
# Cowork Session — 2026-05-05 — Post-Launch Full Audit

## Outcome
- [ ] All checks passed — no action needed
- [ ] Issues found, listed below for Tristan

## Phase 1 — Campaign
URL loaded: ___
Status badge: ___
Today's metrics: impr=___ clicks=___ cost=___ conv=___
Alert banners (all, verbatim): ___
Optimization score: ___
Top 3 recommendations: 1.___ 2.___ 3.___

## Phase 2 — Listing groups
Tree structure observed: ___
Per-leaf metrics today: ___
Bids match $0.35/$0.08: ___
Any disapprovals: ___

## Phase 3 — Conversions
Purchase status: ___
Other action statuses: ___
Any banner: ___

## Phase 4 — Account overview
Alerts: ___
Optimization score: ___

## Phase 5 — Merchant Center
Errors: ___  Warnings: ___  Notifications: ___
Account-level issues: ___
Top 5 item issues: ___
Sample product 1 — title: ___ custom labels: ___ issues: ___ last sync: ___
Sample product 2 — title: ___ custom labels: ___ issues: ___ last sync: ___

## Phase 6 — VPS Dashboard
6a Scheduler — 6 jobs listed: yes/no
  shopify-product-sync: ___
  google-ads-sync: ___
  fulfillment-check: ___
  price-sync: ___
  pokemon-price-sync: ___
  ads-safety-check: ___
  Both breakers not-tripped: ___

6b Safety — 5 checks shown: yes/no
  All passing: ___
  Any near-trip: ___

6c Fulfillment — critical alerts: ___ thin-margin alerts: ___
6d Orders — recent count: ___
6e Ads — today's perf shown: ___

## Phase 7 — Storefront
Homepage loads: yes/no
/pages/contact renders with email + phone (229) 329-2327: yes/no
PDP add-to-cart works: yes/no

## Phase 8 — Ad preview
Sample 1 OK: ___
Sample 2 OK: ___

## Anything weird (free-form)
<verbatim screenshots / unexpected dialogs / banners>
```

Commit + Syncthing-propagate. **Do NOT git push** (Tristan handles that).

## Time budget

Phase 1: 3 min
Phase 2: 3 min
Phase 3: 1 min
Phase 4: 1 min
Phase 5: 4 min
Phase 6: 4 min
Phase 7: 1 min
Phase 8: 2 min
Total: ~19 min wall clock

If exceeding 30 minutes, surface progress to Tristan rather than burning more time.
