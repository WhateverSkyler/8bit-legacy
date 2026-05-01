# EOD Handoff 2026-05-01 — MC Recovery In Progress

**Resume here.** Read this first when picking up next session.

## TL;DR

- **MC catalog: NOT YET RESTORED.** 162 products in MC (up from 2 at start of day; Shopify still has 7,142 ACTIVE). Two bulk operations completed today (tagsAdd + metafieldsSet, 14,284 fresh webhooks fired). G&Y app's queue is processing slowly. Next escalation if not recovered overnight: **Tier 2C — disconnect/reconnect G&Y from Google.**
- **Pixel data sharing: FIXED on infrastructure, NOT END-TO-END VERIFIED.** All 3 app pixels (Google, Facebook, TikTok) flipped to "Always On". Test order through incognito + gclid still required to confirm Purchase event fires.
- **Shorts QA: DONE + DEPLOYED.** Title validator + hashtag dedup live on the NAS pipeline container. Existing scheduled posts protected by 21-day cooldown.
- **Campaign: STILL PAUSED.** Cannot launch until MC has > 5,000 products AND pixel is verified end-to-end.

## Day timeline (2026-05-01)

| Time ET | Action | Outcome |
|---|---|---|
| 09:00 | Diagnose MC collapse via API | Confirmed 7,689 products in Shopify, only 2 in Feed B, all 3 pixels stuck on "optimized" |
| 09:30 | Cowork: MC Collapse Diagnosis | Account healthy, no suspension, Feed B = `USD_88038604834` only has 3 Ninjas Kick Back variants |
| 10:51 | Cowork: MC Restoration (Tier 2A1) | Cowork couldn't drive iframe; Tristan toggled Local inventory off himself at 11:01 ET |
| 11:01 | Tier 2A1: Local inventory toggled off | **No observable effect.** No product `updatedAt` deltas in 3.5h |
| 11:11 | Cowork: Pixel Flip | All 3 app pixels confirmed Always On (G&Y + FB were already, TikTok flipped) |
| 11:51 | Shorts QA deployed to NAS | Container Up, imports OK, hashtag output byte-identical pre/post-deploy |
| 15:12 | Bulk tagsAdd completed | 7,142 products tagged with `__mc-resync-2026-05-01`. 7,142 webhooks fired |
| 16:22 | G&Y count check (Tristan) | **Total: 162** (158 Approved / 0 Limited / 4 Not Approved) — first signal of recovery |
| 16:35 | Bulk metafieldsSet completed | All 7,142 products got `mm-google-shopping.custom_label_0` set. 7,142 more webhooks fired |
| 16:50 | Tristan reported count "hasn't changed" — still ~162 after metafield-set | Recovery rate insufficient |
| 16:51 | EOD handoff begins | |

## Critical state at EOD

### Shopify Admin
- 7,689 total products / 7,142 ACTIVE
- All 7,142 ACTIVE products have:
  - Tag `__mc-resync-2026-05-01` (set 15:12 ET via bulk tagsAdd)
  - Metafield `mm-google-shopping.custom_label_0` set to `over_50` / `20_to_50` / `under_20` (set 16:35 ET via bulk metafieldsSet)
  - Fresh `updatedAt` ≈ 2026-05-01T20:35:56Z
- Markets: single US market, Active, USD, market ID `88038604834`
- Customer Events / App pixels: all 3 flipped to "Always On" (`unrestricted` in API)

### Merchant Center (`5296797260`)
- 162 products in feed (158 Approved / 0 Limited / 4 Not Approved)
- Feed B: `USD_88038604834` / Source ID `10643774057` (canonical)
- "Found by Google" web crawl: ~3,996 (separate, not part of Shopify push)
- No suspension, no policy violations, no reconnect prompts
- Both GMC and Google Ads links Active

### Google Ads (`8222102291`)
- Campaign `8BL-Shopping-Games` (ID `23766662629`) — **PAUSED**
- 7 conversion actions: Purchase=`7590907627`, AtC=`7590907633`, BeginCheckout=`7590907630`, PageView=`7590907636`, ViewItem=`7590907639`, Search=`7590907642`, AddPaymentInfo=`7590907645`
- Conversion AW: `AW-18056461576`
- OAuth re-authed 2026-04-29 16:46 ET, refresh token still valid
- $700 promo credit active, expires 2026-05-31

### Pixel state (storefront)
- Storefront HTML edge cache flickering between cached states; not all CDN nodes have propagated yet
- Underlying Shopify-side state: all 3 app pixels = Always On (`unrestricted`)
- Storefront `web-pixels-manager` config still includes legacy `AW-11389531744` in action_label arrays (cleanup deferred, not blocking)
- Existing Custom Pixels: Google Customer Reviews (ID 149717026 — leave alone, working as designed)

## What was tried today

1. **Tier 2A1**: Local inventory toggle off (Tristan, 11:01) — no effect
2. **Tier 2A2**: Countries and languages toggle — never executed (Tristan didn't reach iframe expander; cowork couldn't drive)
3. **Bulk tagsAdd** (autonomous): 7,142 products tagged → 162 products appeared in MC over ~70 min. **Partial recovery.**
4. **Bulk metafieldsSet** (autonomous): 7,142 products got custom_label_0 set → no immediate further movement at 16:50 ET (15 min after completion)

## Forcing functions ranked by aggressiveness (still available)

| Tier | Action | Status | Risk |
|---|---|---|---|
| 2A2 | Toggle Countries and languages off → on | NOT YET TRIED | Low |
| 2C | **Disconnect + reconnect G&Y from Google** | NOT YET TRIED | Medium — conversion-action IDs may reset, pixel infrastructure may need re-mapping |
| 2D | Uninstall + reinstall G&Y app entirely | NOT YET TRIED | High — full re-sync takes 4–24h, all settings reset |
| Variant-level metafield set | Bulk-set `mm-google-shopping.custom_label_0` on all 24,500+ variants (vs product-level we just did) | NOT YET TRIED | Low-medium — more invasive but matches 3 Ninjas pattern more precisely (3 Ninjas had the metafield at variant AND product level) |

## Next session — resume sequence

### Step 1: Check current G&Y count

Glance at https://admin.shopify.com/store/dpxzef-st/apps/google/overview "Total products synced". Compare to 162 from EOD.

| Count next session | Meaning | Next action |
|---|---|---|
| > 5,000 | Recovered overnight via natural webhook drain | Skip to Step 4 (test order + flip campaign) |
| 500 – 5,000 | Recovering but slow | Wait another hour, OR run variant-level metafield set to accelerate |
| Still ~162 | Stuck. Webhooks didn't accelerate the recovery. | Tier 2C |
| Lower than 162 | Something regressed | Stop, escalate |

### Step 2 (if stuck): Tier 2C disconnect/reconnect

Tristan does this himself in normal browser (cowork can't reliably drive the iframe):

1. Shopify Admin → Sales channels → Google & YouTube → Settings → Google services → **Disconnect** the Google account
2. Confirm the disconnect dialog
3. Click **Connect Google account** → OAuth as `tristanaddi1@gmail.com`
4. Grant scopes (Google identity, MC `5296797260`, Ads `8222102291`, Business Profile)
5. Walk through any post-connect setup wizard fully — don't skip steps
6. Wait 1-2h for fresh full sync

**KNOWN RISKS of Tier 2C:**
- Conversion-action IDs may reset (the AW-18056461576/TS3uCOud0KMcEIj6_qFD-style tokens are tied to the install). After reconnect, query the storefront HTML to see new tokens, update Phase B's conversion-action constant if those changed.
- "Always On" data sharing flip may need to be redone post-reconnect.
- The custom_label_0 metafields written today PERSIST (they're stored in Shopify, not the app installation).

### Step 3 (alternative if 2C feels too risky): variant-level metafield set

Same approach as `force-mc-resync-metafields.py` but on PRODUCTVARIANT instead of PRODUCT:
- 24,500+ variants total (each product has 2-3 variants on average)
- Same metafield namespace + key
- Replicates 3 Ninjas pattern at variant level

Would need a small new script, ~50 lines following the same pattern. Estimated 5-15 min wall clock.

### Step 4: Once MC recovered (≥ 5,000 products)

1. **Place test order** (Tristan, Chrome incognito, NOT Shop Pay):
   - URL: `https://8bitlegacy.com/?gclid=launch_test_<epoch>`
   - Add Black - Xbox Game (Game Only), qty 18
   - Apply discounts `PIXELTEST1239341735` + `PIXELSHIP` → $0.54 total
   - Pay with real card
2. **Verify pixel fires**:
   - Real-time: Google Tag Assistant Companion Chrome extension on the thank-you page
   - Async (3-6h): Google Ads → Conversions → Today filter → Purchase row → status flips to `Recording conversions` with ≥ 1
3. **Flip campaign** (Claude, ~1 min): use existing `enableCampaign(config, '23766662629')` from `dashboard/src/lib/google-ads.ts:307`
4. **Refund test orders** (Tristan): Order #1072 from 4/29 + the new test order. Shopify Admin → Orders → Refund (NOT Cancel). Internal note "Pixel test — refund post-attribution".
5. **Monitor** first hour for impressions/clicks. `dashboard/src/lib/safety.ts` will auto-pause at $50 spend with no conversions.

### Step 5 (post-launch): Phase B server-side webhook backstop

Already coded but not deployed. Files:
- `dashboard/src/lib/shopify-webhook.ts` (HMAC verifier)
- `dashboard/src/lib/google-ads-conversions.ts` (uploadClickConversion + uploadEnhancedConversion)
- `dashboard/src/app/api/webhooks/shopify/orders-paid/route.ts` (handler)
- `scripts/register_shopify_webhook.py` (registration)
- `scripts/test_orders_paid_webhook.py` (replay harness)
- DB table `googleAdsConversionUploads` already in `dashboard/db/schema.ts` + `dashboard/db/index.ts`

Deployment pre-reqs:
- nginx bypass for `/api/webhooks/` on the dashboard VPS (currently behind 401 basic auth)
- `SHOPIFY_WEBHOOK_SECRET` env var set in `dashboard/.env.local` on VPS (= Shopify Custom App API secret)
- Run `scripts/register_shopify_webhook.py` once

Belt-and-suspenders for if/when Shopify changes another default and breaks the pixel again.

## What was deployed today (running in production)

- **Shorts QA on NAS pipeline container** (`8bit-pipeline`, deployed 11:51 ET): title validator, dry-run warnings, centralized hashtag config. Verified imports clean. Buffer scheduler ran 12:51 + 13:51 successfully without modifying existing schedule.

## What was NOT deployed (in repo, awaiting deploy)

- Phase B server-side conversion backstop (see Step 5 above)
- Bulk-tag/metafield cleanup script (would tagsRemove + metafieldsDelete the resync-day artifacts) — only deploy after MC is fully recovered

## Cleanup tasks (NOT urgent — separate session)

- Remove `__mc-resync-2026-05-01` tag from all products (Shopify admin bulk action, OR new script following the same bulk-op pattern)
- Decide whether to keep `mm-google-shopping.custom_label_0` populated (it's actually useful for future Google Ads bid strategy — recommend KEEP)
- Remove stale `AW-11389531744` from G&Y app config (low priority, not blocking ads)

## Critical IDs / state pinned

```
SHOPIFY_STORE_URL=dpxzef-st.myshopify.com
SHOPIFY_ACCESS_TOKEN=shpat_*** (in config/.env)

Google Merchant Center ID: 5296797260
Google Ads Customer ID:    8222102291 (= 822-210-2291)
Manager Customer ID:       4442441892
Conversion AW:             AW-18056461576
Stale (cleanup later):     AW-11389531744

Campaign:        8BL-Shopping-Games (ID 23766662629), PAUSED, $20/day
Test product:    3 Ninjas Kick Back (gid 7956600029218), survived the prune via custom_label metafields
Pixel test:      Black - Xbox Game (gid 7956619460642), qty 18 = $0.54 with PIXELTEST1239341735 + PIXELSHIP

Bulk op IDs:
  tagsAdd:         gid://shopify/BulkOperation/5500173189154 (completed 15:12 ET, 7142 objects)
  metafieldsSet:   gid://shopify/BulkOperation/5500460269602 (completed 16:35 ET, 7142 objects)

Shopify webhook scopes (current):
  read/write_products, read/write_orders, read/write_inventory, read/write_fulfillments
  MISSING (would help): read_publications, read_markets, read_pixels
```

## Files to read on resume

In order:
1. `docs/eod-handoff-2026-05-01-mc-recovery-in-progress.md` — this file
2. `docs/cowork-session-2026-05-01-mc-collapse-diagnosis.md` — root cause analysis
3. `docs/cowork-session-2026-05-01-mc-restoration.md` — initial restoration attempt + iframe limitations
4. `docs/cowork-session-2026-05-01-mc-count-check.md` — last G&Y count reading (162 at 16:22 ET)
5. `scripts/force-mc-resync.py` — bulk tagsAdd (already executed)
6. `scripts/force-mc-resync-metafields.py` — bulk metafieldsSet (already executed)
7. Memory: `project_ads_launch_state.md`, `feedback_mc_supplemental_disaster.md`, `reference_mc_feed_offer_ids.md`

## What I'd do first thing tomorrow

If Tristan is in front of me at start of session:

1. Glance G&Y count (10 sec) → most important data point
2. Branch on count:
   - High (recovered) → straight to test order + flip campaign
   - Medium (recovering) → wait + monitor, run variant-level metafield set if rate is too slow
   - Stuck (still ~162) → coordinate Tier 2C with Tristan (he disconnects/reconnects G&Y in browser)
3. After MC recovered: place test order via incognito, verify pixel fires, flip campaign, refund test order

Total estimated time to launched ads from a clean morning: **15-90 minutes** depending on which path.
