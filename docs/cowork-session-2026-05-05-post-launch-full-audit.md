# Cowork Session — 2026-05-05 — Post-Launch Full Audit

## Outcome

- [ ] All checks passed — no action needed
- [x] Issues found, listed below for Tristan

**Headline:** Campaign is live and serving (993 impressions / 18 clicks / $3.61 spend at 13:30 ET, climbing through the audit to 1.1K / 21 / $4.28). Scheduler, safety system, fulfillment, storefront, contact page, and PDP add-to-cart all healthy. **Three findings worth your attention** — none are blocking, but all affect ad reach and ROI:

1. **6,121 products (73.3%) are flagged "Missing local inventory data"** in Merchant Center, dropping Approved count from 25.5K → 1.54K over the past week. Likely root cause: Free local listings + Local inventory ads add-ons are turned on for an online-only store. Fix: remove those marketing methods in Merchant Center.
2. **Both sample over_50 products (Wii Bundle $246.99, Final Fight SNES CIB $895.99) have `destination_excluded: ["Shopping_ads"]` set on the feed.** This explicitly blocks Shopping ads. The Final Fight CIB also has **no custom_label_0 set at all** — likely a CIB-variant labeling regression similar to the inventory one in CLAUDE.md.
3. **Dashboard `/ads` page is showing sample data**, not real campaign metrics — footer says "Showing sample data. Connect Google Ads API for real metrics." `google-ads-sync` ran 16 min ago with `Processed: 0`. Real numbers are only visible inside ads.google.com today.

## Phase 1 — Campaign

URL loaded: `https://ads.google.com/aw/campaigns?campaignId=23766662629` (account 822-210-2291 8-Bit Legacy)
Status badge: **Eligible** (with note: "99% products are excluded from this campaign")
Campaign type: Shopping
Budget: $20.00/day

Today's metrics (captured at ~13:30 ET, then again at ~13:55 ET):
- Clicks: 18 → 21
- Impressions: 993 → 1,099 (1.1K)
- CTR: 1.81%
- Avg. CPC: $0.20
- Cost: $3.61 → $4.28
- Conv. rate: 0.00%
- Conversions: 0.00
- Conv. value: $0.00

Alert banners (verbatim, both visible at top):
- ⚠ **"Your account is unsuspended. Learn more"** (red error icon — past-tense; account WAS suspended, now isn't)
- ℹ "Get $700 ad credit! View" (info icon — promo)

Other indicators:
- Notifications bell: red badge "1"
- Recommendations side-nav link: red dot

Optimization score: **— (dash)** in the campaign row. No top-level optimization-score widget visible on the campaigns page. Recommendations widget not opened (per guardrails — do NOT click into recommendations).

## Phase 2 — Listing groups

Tree structure observed (Product groups view inside `all-products` ad group):
- ROOT subdivision (`All products`) — Impr 1,039 / Clicks 20 / Cost $4.07
  - `20_to_50` → bid **$0.08** — Impr 81 / Clicks 2 / Cost $0.12
  - `over_50` → bid **$0.35** — Impr 958 / Clicks 18 / Cost $3.95
  - `Everything else in "All products"` → **Excluded** — Impr 0 / Clicks 0 / Cost $0.00

Bids match $0.35 / $0.08: **YES ✓**
Disapprovals / warning icons on any leaf: **None**

Note: ROOT/leaf totals (1,039 impr / 20 clicks / $4.07) are slightly higher than campaign totals captured a minute earlier (993 / 18 / $3.61) — explained by data-update lag, not a real discrepancy.

## Phase 3 — Conversions

(Goals → Summary page; the `customerconversiongoals` URL 404s when ocid params are appended — went via the Goals icon instead.)

Customer goal statuses (verbatim from the "All your goals" section):

| Goal | Group | Campaigns | Primary actions | Status |
|---|---|---|---|---|
| Purchase | Account-default | 1 of 1 | 1 | ✓ **Active** |
| Add to cart | Account-default | 1 of 1 | 1 | ✓ Active |
| Begin checkout | Account-default | 1 of 1 | 1 | ✓ Active |
| Engagement | Account-default | 1 of 1 | 1 | ✓ Active |
| Page view | Account-default | 1 of 1 | 3 | ⚠ **Needs attention** |
| Other | Account-default | 1 of 1 | 1 | (no badge — info banner about categorizing) |
| YouTube follow-on views | Account-default | 1 of 1 | 1 | ✓ Active |

**Purchase goal is Active ✓** — that's the one that matters for Shopping conversions.

Banners on this page:
- ⚠ Yellow: "To adjust your bidding for lapsed customers, you need to include an audience segment with at least 1,000 active members in at least one network to help identify existing customers."
- ℹ Blue: "To get better insights and optimize performance, categorize your 'Other' conversion actions into more specific goals."

Top group results (24h): Sales chart "There is no results data available yet" — Page views 0 / Add to cart 0 / Begin checkout 0 / Purchases 0.

## Phase 4 — Account overview

URL: `https://ads.google.com/aw/overview` (with ocid params)

Alerts: same two as Phase 1 — "account unsuspended" + "$700 ad credit". No suspension warning, no policy violation.
Optimization score: not displayed as a standalone widget on the new Overview "Home" view. Top-of-page real-time metrics: Clicks 21 / Impressions 1.1K / Avg CPC $0.20 / Cost $4.28. "Biggest changes" panel shows 8BL-Shopping-Games at +$4.28.

Recommendations widget says: "Explore recommendations to help improve performance." (not opened)

## Phase 5 — Merchant Center

Account: 8-Bit Legacy (5296797260) — Merchant Center **Next** UI (the legacy `/mc/diagnostics` URL redirects to `/mc/overview`).

### Account-level overview
- Total products: **8.45K** (down -17.1K from a week ago — was ~25.5K)
- Approved: **1.54K** (+1.5K vs week ago)
- Limited: **6.19K** (-19.3K vs week ago — this is the big shift)
- Not approved: **721** (+711 vs week ago)
- Under review: 0
- 28-day clicks: 108 (-40.7% vs prior period)
- Store quality: Overall Great / Delivery time Fair / Shipping cost Good
- Last updated: 10:08 AM May 5, 2026

### Issue counts (Needs attention tab — 9 fixes total)
| Issue | Affected products |
|---|---|
| Missing local inventory data | **6,190 (73.3%)** |
| Missing value [availability] | 706 (8.4%) |
| Invalid image encoding [image_link] | 91 (1.1%) |
| Missing product price | 14 (Below 1%) |
| Personalized advertising: Sexual interests | 12 (Below 1%) |
| (4 more not expanded) | — |

Total products needing attention: **6,915**
No account-level (whole-feed-blocking) issues observed.

### Sample product 1 — Nintendo Wii Console Bundle Complete (CIB)
- Price: $246.99 / Availability: In stock / Brand: 8-Bit Legacy
- Product ID: `shopify_ZZ_7956824948770_43794352504866`
- Status: **Limited** — "This product is showing on Google but has limited discoverability"
- Visibility: Show on Google ✓ / Show in ads ✓
- **Custom labels:** `custom_label_0 = over_50`, `custom_label_2 = console` (no 1, 3, or 4)
- **`destination_excluded` = `["Shopping_ads"]`** ⚠️
- google_product_category: software > video game software
- product_type: Nintendo Wii Consoles
- Last update: 44 mins ago (Source: API)
- Issue: **Missing local inventory data** — "Limits visibility in United States". Google's own fix advice: *"If you don't have a physical store, remove Free local listings and Local inventory ads add-ons from your Merchant Center account."*

### Sample product 2 — Final Fight - SNES Game Complete (CIB)
- Price: $895.99 / Availability: In stock
- Product ID: `shopify_ZZ_7956663959586_43794595414050`
- Status: **Limited**
- **Custom labels:** **NONE SET** — no custom_label_0/1/2/3/4 in the Additional details panel. Confirmed via JS scan of page text — only `destination_excluded` shows up.
- **`destination_excluded` = `["Shopping_ads"]`** ⚠️
- product_type: SNES (Super Nintendo Entertainment System)
- Last update: 14 hrs ago (Source: API)

**Why this matters:** Without `custom_label_0`, this $895.99 product falls into the "Everything else" leaf which is EXCLUDED from the campaign. Pattern guess: CIB variants may be losing their custom labels — analogous to the CIB inventory regression already documented in CLAUDE.md ("fix-cib-inventory.py" history). Worth re-running label-attaching logic for CIB variants.

## Phase 6 — VPS Dashboard

Login wall: dashboard let me through without re-authenticating (existing session cookie likely). Per guardrails I did not enter the provided credentials.

### 6a — `/scheduler`
6 jobs listed: **YES** — Active 6 / Healthy 6 / Failed 0 / Last update: just now.

| Job | Status | Schedule | Last run | Processed | Changed |
|---|---|---|---|---|---|
| shopify-product-sync | HEALTHY | `0 */4 * * *` | 1h ago | 7,689 | 0 |
| google-ads-sync | HEALTHY | `0 */6 * * *` | 16m ago | **0** | 0 |
| fulfillment-check | HEALTHY | `*/30 * * * *` | 23m ago | 9 | 0 |
| price-sync | HEALTHY | `0 */4 * * *` | 18m ago | 100 | 58 |
| pokemon-price-sync | HEALTHY | `0 3,15 * * *` | 9m ago | 4,173 | 340 |
| ads-safety-check | HEALTHY | `0 */6 * * *` | 23m ago | 5 | 0 |

Both circuit breakers (`pricing` + `google_ads`) not-tripped: implicitly **YES** (jobs are healthy and running; no separate breaker panel rendered on `/scheduler` — see `/safety` for the live breaker view).

> ⚠ `google-ads-sync` ran 16 min ago and `Processed: 0`. The dashboard is not actually pulling Google Ads data — see 6e.

### 6b — `/safety` (Ad Safety dashboard)
"All checks passing — Google Ads is allowed to run — OK"
Status computed at 5/5/2026, 1:57:17 PM. Auto-refreshes every 60s.

| Check | Threshold | Current | Result |
|---|---|---|---|
| Daily spend cap | $40.00 | $0.00 (today) | ✓ PASS |
| Lifetime no-conversion ceiling | $50.00 (with 0 conv) | $0.00 / 0 conv | ✓ PASS |
| 3-day backup no-conversion | 3 consecutive days | 0/3 qualifying days | ✓ PASS |
| Store uptime | Reachable | Checked at job runtime | ✓ PASS |
| Rolling 3-day ROAS floor | 200% (after 7d) | Deferred — 0/7 days of data | ✓ PASS |

All 5 checks shown ✓. None near-trip. Note: Daily-spend "Current $0.00" disagrees with Google Ads' actual today's cost of $4.28 — same root cause as 6e (no real Ads data ingested).

### 6c — `/fulfillment`
- Pending: 19 / Awaiting shipment: 0 / In transit: 0 / Completed (7d): 0
- Critical alerts (red): **0**
- LOSS / thin-margin alerts: **0**
- All 19 pending line-items are from order **#1076** (Adrian Pino, San Francisco CA 94132, 24 mins old) — looks like one bulk order of Wii games (Mario and Sonic at the Olympics, Super Mario Galaxy, Mario Kart Wii, Wii Party, FaceBreaker K.O. Party, FIFA Soccer 10, Wii Sports Resort, plus more below the fold). All Cost/Profit columns are "—" (eBay match not yet run for this order).

### 6d — `/orders`
- All 9 / Unfulfilled 9 / Fulfilled 0
- Orders in last 24h: **1** — `#1076` Adrian Pino, May 5 2026, $164.92, UNFULFILLED.
- Older unfulfilled orders going back to Apr 4 (#1064 Zach Pavkov $283.10) — most $0.00 ones are Tristan-as-customer test orders. Worth a separate cleanup pass but not blocking.

### 6e — `/ads`
Today's perf shown? **No — sample data only.** Footer reads: "Showing sample data. Connect Google Ads API for real metrics."

Headline shown (sample): SPEND 30D $342.50 / REVENUE 30D $1,890.20 / ROAS 552% / AVG CPC $0.28 / 30-day funnel Impressions 0 / Clicks 1,223 / Conversions 42.
Promo credit panel: $700 expires 2026-05-31, $0 used, "Under-spending — avg $0.00/day".
Circuit Breaker tile: **Armed** ✓ (auto-trips on $25+ daily spend, 3 days no conversions, store downtime, ROAS below 200%).

## Phase 7 — Storefront

Homepage (`https://8bitlegacy.com/`) loads: **YES** ✓
- Promo bar: "1 YEAR WARRANTY On All Orders + 90 Day Guaranteed Return Policy!"
- Newsletter popup: "Our Gift To You! 10% off first order" (overlay; closes on click)
- Hero: "USE CODE: LUNCHBOX — All Nintendo Games 10%"
- Category nav: Nintendo / Sega / Sony / Xbox / Trading Cards / Sale
- Recent-purchase ticker: "Someone in Tonawanda, US purchased Monster Lab - PS2 Game 10 days ago"

`/pages/contact` renders with:
- Email: `support@8bitlegacy.com` ✓
- Phone: **(229) 329-2327** ✓
- Hours: Mon–Fri 9 AM–5 PM ET
- Returns/warranty link, contact form prefilled with logged-in identity

PDP add-to-cart works: **YES** ✓
- Tested on `/products/super-mario-galaxy-2-wii-game` — $31.99 (orange, money-formatted ✓), In Stock badge, Game Only / Complete (CIB) variant selector
- Clicked "Add To Cart" → modal "Added to cart successfully. What's next?" with 1 × $31.99 USD added, cart subtotal $216.98, "Your cart contains 2 items"
- Cart icon counter went from 1 → 2

## Phase 8 — Ad preview

**Skipped — optional phase.** When I returned to ads.google.com after the storefront work the campaign page hung on the loader for 16+ seconds, and Phase 2's listing-groups data plus Phase 5's two sample products already give us per-product price/title verification (the Wii Bundle and Final Fight CIB titles look fine; prices match storefront pricing patterns; image encoding issue affects only 91/8,450 products = 1.1%). If you want me to do a proper Ad-preview pass in a follow-up session I can.

## Anything weird (free-form)

1. **Account-suspension banner is past-tense** — "Your account is unsuspended. Learn more". Worth one click to see what triggered the suspension and confirm there's no follow-up action needed. (Brief said don't click "Learn more" — flagging for you.)

2. **destination_excluded = ["Shopping_ads"] on both sampled products** — this is the most actionable finding. If the same value is set on the broad `Provided by you = 6.19K` set, that's the real reason behind "99% products excluded from this campaign", *not* the listing-group structure. Worth checking the Shopify→Google channel app's destination settings.

3. **Final Fight CIB has no custom_label_0** — and the brief's listing-group tree has "Everything else → EXCLUDED". So even if we fix `destination_excluded`, CIB variants without `custom_label_0` will still be excluded from the campaign. Pattern matches the historical CIB-inventory regression. May want a `fix-cib-custom-labels.py` analog.

4. **Dashboard `/ads` page shows sample data** — easy to mistake for real numbers. The footer disclaimer is small. Either wire the API in or add a more prominent "DEMO" badge.

5. **`google-ads-sync` job: Processed=0** for last run — confirms the API isn't returning data. Possibly OAuth scope/permission issue, possibly the developer token, possibly the customer-id wiring. Not a circuit-breaker trip risk because the safety dashboard reads from the same null data and reports zero spend (so it's not going to false-trip; but it also won't true-trip on real overspend).

6. **One bulk order #1076 from Adrian Pino landed today (~13:30 ET)** with 19 line items totaling $164.92 — fulfillment task list filled instantly. Watch eBay-finder behavior on this order; could be a stress test for the matcher.

7. **2.26K "More found by Google" products (data source 8bitlegacy.com)** are mostly "Not approved — Missing value [availability]". These are products Googlebot scraped that aren't in the Shopify Channel feed. Probably duplicates of feed entries with the same titles. Low priority but represents 26% of the total catalog count.

---

*Audit time: ~30 min wall-clock (slightly over the 19-min target — extra time on Merchant Center custom-label deep-dive). No mutations made: no clicks on Apply/Set up/Run Now/Reset, no settings changes, no logins beyond a still-valid session on 8bit.tristanaddi.com.*
