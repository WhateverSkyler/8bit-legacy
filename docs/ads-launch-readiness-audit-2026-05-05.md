# Ads Launch Readiness Audit — 2026-05-05

**Auditor:** Claude (max-effort, treat-it-as-my-money mode)
**Initial verdict:** 🔴 NO-GO until cl2 fix → 🟢 GO
**Updated verdict (after deep audit):** 🟡 GO with one quick fix + two known soft risks

## Quick scoreboard

| # | Finding | Severity | Status |
|---|---|---|---|
| 1 | `custom_label_2` missing on 6,087/6,088 games | 🔴 BLOCKER | ✅ FIXED 2026-05-05 14:08 UTC |
| 2 | 2 Chrono Trigger SNES variants with invalid compare_at_price | 🟡 MC disapproval | ✅ FIXED 2026-05-05 |
| 3 | `/pages/contact` → 404 (footer link is broken) | 🟡 FIX BEFORE LAUNCH | Pending — your task in Shopify Admin |
| 4 | No product reviews app on PDP | 🟡 SOFT RISK | Acceptable (cold-store CVR risk) |
| 5 | $20/day budget likely under-burns $700 promo by ~$258 | 🟡 SOFT RISK | Plan: bump to $30/day on day 5 if converting |
| 6 | VPS scheduler liveness can't be verified from Mac (behind 401) | 🟢 NICE-TO-HAVE | User to spot-check dashboard |
| 7 | Stale `AW-11389531744` pixel still in storefront HTML | 🟢 NICE-TO-HAVE | Cleanup post-launch |
| 8 | Phase B server-side webhook backstop not deployed | 🟢 NICE-TO-HAVE | Belt-and-suspenders only |

---

## 1. ✅ FIXED — `custom_label_2` metafield

**Was:** 6,087 of 6,088 game products missing `custom_label_2 = "game"` → listing tree would have served zero impressions.

**Fix:** `scripts/set-custom-label-2.py --execute` ran 2026-05-05 14:07-14:10 UTC. 7,142 products updated. 100% coverage verified across all `category:game` products. Pokemon/console/accessory products correctly labeled with their categories (still excluded by tree).

**MC propagation:** in flight — expect 1-4h. Loop polling at 25-min intervals.

---

## 2. ✅ FIXED — Compare_at_price MC disapproval bug

**Was:** Chrono Trigger SNES had `compareAtPrice = $299.99` with actual prices `$352.99` (Game Only) / `$949.99` (CIB). Invalid sale state would trigger MC disapproval.

**Fix:** Cleared `compareAtPrice` to `null` on both variants via `productVariantsBulkUpdate` mutation. 2026-05-05 ~10:23 ET. UserErrors: empty.

**Scope:** scanned all 12,176 game variants — only these 2 were broken.

---

## 3. 🟡 BROKEN CONTACT PAGE — `/pages/contact` → 404

The footer of every page on `8bitlegacy.com` links to `/pages/contact` but it returns HTTP 404. All other policy/info pages return 200.

**Why it matters:**
- Bad customer experience (cannot reach support from footer)
- Google Merchant Center policy requires a contact method — could trigger a manual review or "Limited" status
- Slight CVR drag (customers want to know support exists)

**Fix (your task, ~3 min):**
1. Shopify Admin → Online Store → **Pages** → "Add page"
2. Title: `Contact` (this auto-generates URL `/pages/contact`)
3. Body: name, email (e.g. support@8bitlegacy.com or your tristanaddi1@gmail.com), maybe a Shopify contact form (Theme settings can embed one)
4. Save → Publish
5. Verify: `curl -sI https://8bitlegacy.com/pages/contact` returns 200

Alternative quick fix: change the footer link to a `mailto:` link in the theme — but creating the page is better for SEO and trust.

**Not strictly blocking launch** if you're willing to absorb a possible MC "Limited" warning. Strongly recommend fixing in the next 30 min while we wait for MC propagation anyway.

---

## 4. 🟡 No reviews app installed

I scanned the storefront for the common review app integrations (judge.me, yotpo, stamped.io, loox, reviews.io) — none detected. The PDP shows "warranty" and "guarantee" copy but no star ratings or social proof.

**Why it matters:**
- Cold store + no reviews + retro gaming niche = CVR drag of 20-40% vs same store with even a few reviews
- Google Shopping ads display review stars when present, dramatically increasing CTR
- Without reviews, the listing is one of N visually-identical Shopping ads

**Acceptable for launch** — adding a reviews app needs at least a few orders first to seed. Strategy:
- Day 1-7: launch ads with current state
- Day 7+: install judge.me (free for first 100 orders) and import any organic order reviews
- Day 14+: review-stars enabled — measure CVR delta

This is a known constraint per the master plan §8 ("Homepage redesign + trust-signal work — on the roadmap but not gating ads launch").

---

## 5. 🟡 Budget vs $700 promo credit

| Daily budget | Days × 85% delivery | Expected spend by 5/31 | Unused credit |
|---|---|---|---|
| **$20** (current) | 26 × 0.85 | $442 | $258 |
| $25 | 26 × 0.85 | $552 | $148 |
| $30 | 26 × 0.85 | $663 | $37 |

**Plan:** launch at $20/day. After day 5, if conversions are happening and ROAS > 200%, raise to $30/day. To do that safely, also raise `MAX_DAILY_AD_SPEND` in `dashboard/src/lib/safety.ts` from $40 → $65 (Google can 2x daily budget; $30×2=$60 would false-trip $40 cap).

**I'll handle the bump autonomously when the data justifies it.**

---

## 6. 🟢 Scheduler health (VPS)

### Architecture (verified by code review)

Six jobs registered in `dashboard/src/lib/jobs.ts`:

| Job | Cron | Risk | Touches Ads? |
|---|---|---|---|
| `shopify-product-sync` | every 4h | None — read-only | No |
| `google-ads-sync` | every 6h | None — read-only | Read perf data |
| `fulfillment-check` | every 30m | Reads orders, creates DB alerts (no Shopify writes) | No |
| `price-sync` | every 4h | Updates Shopify prices for safe (<15%) changes only | No (but see "Soft Risk A" below) |
| `pokemon-price-sync` | 3 AM + 3 PM ET | Updates Pokemon prices | No (Pokemon excluded from ads) |
| `ads-safety-check` | every 6h | **Auto-pauses campaign if any kill switch trips** | YES — the kill switch |

**Safety properties:**
- Per-job lock (`runningJobs` map) — no concurrent self-runs
- 2 retries on transient errors (timeout/ECONNRESET/429/502/503)
- All runs logged to `automation_runs` table
- TZ-aware (America/New_York)
- Circuit breaker pause action goes through Google Ads API (`pauseAllCampaigns` in `google-ads.ts:307`)

### What I CANNOT verify autonomously

The dashboard at `8bit.tristanaddi.com` is behind nginx Basic Auth (HTTP 401). I can't reach `/api/scheduler/status` or `/scheduler` to confirm jobs are firing on cadence. Local DB at `dashboard/db/8bitlegacy.db` last shows runs from 2026-04-10 (your last local-dev session).

**Recommended spot-check before launch (~1 min):**
1. Open `https://8bit.tristanaddi.com/scheduler` (login if prompted)
2. Verify the 6 jobs listed above all show recent successful runs (within last 24h for hourly-tier jobs)
3. Confirm `ads-safety-check` has fired in last 6h

If any job has been failing for days, that's a separate issue to investigate before flipping campaign.

### Soft Risk A — price-sync vs cl0 metafield drift

If `price-sync` repriclassifies a $94 over_50 game down to $40 (now a 20_to_50 game), the **`custom_label_0` metafield does NOT auto-update**. The listing tree's bid decision uses cl0, so we'd overbid (or underbid) the new price.

**Realistic impact:** PriceCharting changes are typically <10% per cycle. A $90 game dropping to $40 in one sync is rare. Worst-case waste over 7 days = ~$5-10 of mis-bid spend.

**Mitigation:** I can add a follow-up cl0 refresh script that runs daily after price-sync. Not blocking; can deploy in week 1.

### Soft Risk B — VPS as single point of failure

If the VPS goes down, NO kill switches fire. Google would still cap at the campaign daily budget × 2x ($40), but there's no $50 lifetime no-conv pause until VPS comes back. Worst case: VPS down for 5 days = $200 wasted with no automated pause.

**Mitigation:** the user already monitors via the dashboard. If you don't log in for 3+ days, set a Calendar reminder "/check 8bit dashboard" daily for week 1.

---

## 7. 🟢 Stale AW-11389531744 pixel

Storefront HTML still includes a previous Google Ads pixel `AW-11389531744`. It's not used by the active campaign or the new conversion actions.

**Don't touch pre-launch** — risk of breaking the working `AW-18056461576` pixel for a cosmetic fix. Cleanup task for week 2+.

---

## 8. 🟢 Phase B server-side webhook backstop

Already coded but not deployed:
- `dashboard/src/lib/shopify-webhook.ts` (HMAC verifier)
- `dashboard/src/lib/google-ads-conversions.ts` (uploadClickConversion + uploadEnhancedConversion)
- `dashboard/src/app/api/webhooks/shopify/orders-paid/route.ts`
- `scripts/register_shopify_webhook.py`

**Why it exists:** if Shopify changes another default (like the Jan 2026 pixel throttle), the storefront pixel could silently break. Server-side webhook backstop posts conversions directly to Google Ads from Shopify's `orders/paid` webhook.

**Why not deploy yet:**
- Requires VPS auth (out of scope here)
- Requires nginx bypass for `/api/webhooks/`
- Requires `SHOPIFY_WEBHOOK_SECRET` env var on VPS
- Belt-and-suspenders only — primary pixel is verified working (Purchase = Active)

**When to deploy:** Day 7-14 after launch, once we have proof the primary pixel reliably tracks conversions over time.

---

## 9. ✅ Catalog economics (confirmed)

### Game tier distribution (Game Only variants)
- over_50: 802 products, mean $94, breakeven CVR 1.40% at $0.35 bid
- 20_to_50: 1,678 products, mean $32, breakeven CVR 1.77% at **$0.08 bid** (more conservative than the original plan's $0.12)
- under_20: 3,608 products excluded (correctly)

### Live eBay sourcing check (7 over_50 samples)
Every sample profitable: $8.96 (FF3 SNES tightest) to $75.15 (Adventures of Lolo 3 widest). Pricing model holds.

### Image / GTIN
50-product sample: 0 missing images, 49/50 missing GTIN (acceptable for retro games — MC labels "Limited" but still serves).

### cl0 freshness
0/50 mismatches. Tier metafield matches actual current price.

---

## 10. ✅ Conversion tracking (confirmed)

- Purchase = **Active** in Google Ads (real conversions firing)
- All 3 app pixels = `unrestricted` (Always On) on storefront
- AW-18056461576 present in storefront HTML
- Conversion actions all primary_for_goal=True
- `always_use_default_value = False` on all 7 Shopping App actions → real transaction values flow through (not the $1 fallback)
- Attribution model: GOOGLE_SEARCH_ATTRIBUTION (data-driven default — appropriate)

---

## 11. ✅ Negative keywords

335 phrase-match negatives. Coverage strong: piracy/emulation, repro/bootleg, walkthrough/guide/cheats, repair/broken, vs/should-i/worth-it, mobile/digital/PSN/Steam. No obvious gaps.

---

## 12. ✅ CIB exclusion

All 6,088 CIB variants have `mm-google-shopping.excluded_destination = ["Shopping_ads"]` at the **variant level**. Only Game Only variants will appear in ads.

---

## 13. Devil's advocate scenarios

| # | Scenario | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| 1 | Google rejects campaign on policy review when flipped | Low (already reviewed Apr 24) | Pause until resolved | Resubmit; have contact info, returns policy ready (after #3 fix) |
| 2 | First customer order's eBay listing is gone before we buy | Medium | Order delay 1-3 days | order-validator job creates alert; eBay search has fallback to next-cheapest |
| 3 | Cloudflare WAF blocks Google's pixel server-side | Very low (unrestricted dataSharing → outbound calls from worker, not server) | Pixel data lost | Phase B webhook backstop covers this when deployed |
| 4 | High-value test order ($300+) lands, eBay supply gone | Medium (rare items have thin supply) | Refund customer | order-validator catches loss/gap pre-fulfillment |
| 5 | Customer disputes charge before we ship | Low | $200-500 chargeback | Ship within 24h, provide tracking; standard ecommerce risk |
| 6 | Multiple orders for same product, eBay supply limit (1) | Low (most retro games have N>5 listings) | One customer waits for restock | order-validator alerts; offer refund |
| 7 | cl0/cl2 metafields nuked by another sync | Very low (no automation touches them) | Listing tree breaks again | Re-run set-custom-label-2.py; takes 5 min |
| 8 | VPS down for 3+ days during launch | Medium-low (uptime hist OK) | No kill switch | Daily dashboard check; Google's own daily budget caps spend at ~$40 |
| 9 | $20/day campaign converts well but VPS scheduler false-trips | Low | Campaign auto-paused | Manual reset via dashboard `/scheduler` |
| 10 | First-week search terms 50%+ junk (vs expected 20-30%) | Medium | More wasted spend | Add 10-30 negatives daily via `ads_daily_report.py` |
| 11 | Account suspension during launch | Low (fresh review) | Pause indefinitely | Open MC support case; resubmit with fixes |
| 12 | Pokemon products somehow leak into ads | Very low | Wasted spend on $5 cards | cl2=pokemon_card excludes them at root level + listing tree else branch double-excludes |
| 13 | Sale tax cost exceeds margin on out-of-state orders | Medium-high (known issue per memory) | Net profit < gross profit | Multi-state MTC fix when volume justifies (post-launch); for now eat the cost |
| 14 | First-week CVR < 0.5% (kill switch fires at $50) | Medium (cold store risk) | $50 wasted | Investigate funnel before re-enabling: PDP UX, mobile, trust signals, reviews |
| 15 | Email automation broken for order confirmations | Low (Shopify default works) | Customer anxiety | Verify Shopify "Order confirmation" template is enabled |
| 16 | Test order #1072 from 4/29 still pending fulfillment | Medium | Customer waits | Per user 2026-05-05: not refunding $0.54 test order |

---

## 14. Pre-launch gates — final checklist

| # | Gate | Status |
|---|---|---|
| 1 | `custom_label_2` set on all games | ✅ Done (Shopify side; MC propagation pending) |
| 2 | Compare_at_price MC bug fixed | ✅ Done |
| 3 | Conversion tracking proven (Purchase = Active) | ✅ Done |
| 4 | All 3 storefront pixels = Always On | ✅ Done |
| 5 | CIB exclusion at variant level | ✅ Done |
| 6 | 335 negative keywords loaded | ✅ Done |
| 7 | Safety system + circuit breakers wired | ✅ Done |
| 8 | MC catalog ≥ 5,000 approved | ✅ Done (6,082 approved) |
| 9 | Listing tree structure correct | ✅ Done |
| 10 | Bid economics positive at expected CVR | ✅ Done |
| 11 | `/pages/contact` page exists (or footer link fixed) | 🟡 Your task |
| 12 | MC propagation verified (cl2 visible in MC product detail) | ⏳ Polling |
| 13 | VPS scheduler liveness spot-check | 🟡 Your task (~1 min in dashboard) |

---

## 15. Recommended launch sequence

1. **Now:** create `/pages/contact` in Shopify Admin (you, ~3 min)
2. **Now:** spot-check `8bit.tristanaddi.com/scheduler` for recent successful runs (you, ~1 min)
3. **Wait:** MC propagation completes (loop polling; ~30-90 min more from now)
4. **At T+0:** I flip campaign to ENABLED (one command)
5. **T+30 min:** I manually trigger `ads-safety-check` job to verify no immediate issues
6. **T+24h:** `python3 scripts/ads_daily_report.py` for first-day report
7. **T+5 days:** if conversions exist & ROAS > 200%, bump to $30/day + raise safety cap

Total time-to-launch from this moment: **~30-90 min** (mostly MC propagation wait).

---

## Files written this session

- `scripts/set-custom-label-2.py` — fix script (executed)
- `docs/ads-launch-readiness-audit-2026-05-05.md` — this doc

## Files modified this session

- Chrono Trigger SNES variants (productVariantsBulkUpdate to clear compareAtPrice)
- 7,142 product metafields (custom_label_2 set via bulk op)
