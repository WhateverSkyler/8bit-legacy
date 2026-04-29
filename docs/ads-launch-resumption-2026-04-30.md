# Ads Launch Resumption — Pickup 2026-04-30+

**EOD state 2026-04-29 16:57 ET. Campaign still PAUSED. Pixel verification incomplete. Read this file first when resuming.**

---

## TL;DR

Today (2026-04-29) ate the day on a chain of MC + pixel issues. End state:
- ✅ MC duplicate feed cleanup complete (Feed B `USD_88038604834` is canonical)
- ✅ Pixel infrastructure correctly installed in storefront (curl-verified)
- ✅ 4 conversion actions receiving events (Add to Cart, Begin Checkout, Page View, View Item show "No recent conversions")
- ❌ **Purchase + Add Payment Info conversion actions stuck "Inactive"** — never received pixel events
- ❌ Order #1072 ($0.54 test, paid via Shop Pay) did NOT fire Purchase event to Google Ads
- ⚠️ Custom labels on products: pilot set on 1 product, awaiting MC propagation verification (~tomorrow)
- ✅ Manual conversion upload via API works (proved with #1072 via Enhanced Conversions for Web)

**Hard blocker preventing flip: no organic Purchase event has ever reached Google Ads. We can flip and rely on server-side upload, but server-side upload without `gclid` capture isn't useful for Smart Bidding ML.**

---

## What ACTUALLY broke (root cause analysis)

### The Shop Pay gap (most likely cause)

Test order #1072 was placed via cowork-staged checkout that used the saved Shop Pay session (Mastercard •••• 4889 was pre-filled — that's a returning Shop Pay user signal). Shop Pay's flow on `shop.app` domain bypasses the merchant's storefront pixel for the late-checkout events:
- `add_payment_info` fires DURING checkout → Shop Pay → no merchant pixel
- `purchase` fires AFTER checkout → Shop Pay thank-you → no merchant pixel

This pattern fits the data perfectly: every action that fires BEFORE Shop Pay redirect works, every action AFTER doesn't.

**Tristan's pushback (valid):** "Shopify says it works for Shop Pay." Per Shopify docs the Web Pixels API SHOULD track checkout_completed across Shop Pay since they own both. In practice there are documented gaps for returning-Shop-Pay-user flows. Empirical test required to disambiguate.

### Untested alternative: maybe pixel is just slow

Possible the Purchase event DID fire but Google's verification window (up to 3 hours per their docs) hasn't completed. Status was "Inactive" 2.5h after the order, so technically still in the window. Worth re-checking 6+ hours after order placement.

### The previous pixel re-link from 4/27 may be incomplete

Storefront still has `AW-11389531744` (wrong account) double-tagged on every event. Per 4/27 fix, this was supposed to be removed but wasn't fully cleaned. Not blocking but introduces noise.

---

## What's needed for the REAL 100% solution

The user wants:
1. Real attribution — purchases tied back to ad clicks so Smart Bidding ML can optimize
2. Works for Shop Pay AND non-Shop-Pay flows
3. No "goofy workarounds" — proper integration

This requires `gclid` capture + propagation:
1. **Capture gclid** — when a customer clicks an ad, URL contains `?gclid=XYZ`. Need to grab it on the first page-view and persist it across the session.
2. **Persist gclid** — store in cookie/localStorage AND attach it to the cart/checkout so Shopify's order has it.
3. **Pass gclid in conversion event** — either via the browser pixel (auto-handled by Shopify's Google channel app IF it's configured correctly) or via server-side webhook (we extract from order metadata).
4. **Verify gclid arrives at Google Ads** — Google attributes the conversion to the original ad click, Smart Bidding learns.

### Two implementation paths

**Path A: Fix Shopify's native pixel integration so it works for Shop Pay**

This is the "Shopify says it should work" path. Steps:
1. Check Shopify Admin → Sales channels → Google & YouTube → **Configuration** for any tracking toggle that's off
2. Look for "Conversion measurement" or "Customer events" settings — verify they're all on
3. Verify Shopify's Customer Events recorder shows `checkout_completed` firing for order #1072 (Admin → Settings → Customer events)
4. If Shopify ISN'T firing the event for Shop Pay returning users, file a Shopify support ticket — this is a known gap
5. As a stopgap, **disable Shop Pay** for guest checkouts (Settings → Checkout → Accelerated checkouts → Shop Pay → off). Ugly but reliable.

**Path B: Server-side webhook with gclid capture (more robust)**

1. **Front-end gclid capture** (~10 min):
   - Add a small JS snippet to `theme.liquid` that reads `?gclid=` from URL on page load
   - Stores it in a cookie (90-day expiry, matches Google's attribution window)
   - On Add to Cart / cart attribute update, attaches the gclid as a `note_attribute` on the cart
2. **Shopify webhook → Google Ads upload** (~30 min):
   - Subscribe to `orders/paid` webhook in the dashboard or a small Worker
   - Webhook receives order data including `note_attributes` (gclid, user_agent, conversion_env)
   - Upload to Google Ads via `UploadClickConversions` with gclid (proper attribution) OR `user_identifiers` (Enhanced Conversions match)
   - Idempotent via `order_id` for de-dup
3. **Run BOTH** — pixel fires AND webhook fires. Google de-dups by order_id. Belt-and-suspenders.

**Path C: Both** (recommended for production)

Run Path B as backstop. If pixel works, conversions are de-duped. If pixel breaks, webhook still works. This is what e-commerce stores running real money typically do.

---

## Suggested resumption sequence

### Step 1: Quick re-check (5 min, do this first thing)

When picking up tomorrow, before doing anything:
1. Re-check Google Ads → Conversions → Today filter → Purchase action status
2. If Purchase has shifted to "Recording" or "No recent conversions" with at least 1 conversion → pixel DID fire, was just delayed. Skip to Step 4.
3. If still "Inactive" → proceed to Step 2.

### Step 2: Investigate Shopify Customer Events log (15 min)

1. Shopify Admin → Settings → Customer events
2. Filter to today / yesterday
3. Find order #1072's events. Look specifically for:
   - `checkout_completed` event — did it fire?
   - Which pixel apps received it (look for "Google & YouTube" in the subscribers list)
   - If `checkout_completed` fired AND was delivered to Google & YouTube pixel → pixel-side bug or attribution issue at Google's end
   - If `checkout_completed` did NOT fire → Shopify's Web Pixels Manager isn't catching the event (the Shop Pay gap is real)

### Step 3: Decide path based on Step 2 finding

**If Shopify event log shows `checkout_completed` did NOT fire:**
- Confirms Shop Pay gap
- Implement Path B (server-side webhook) as the proper fix
- Optionally also disable Shop Pay temporarily until Path B is live

**If Shopify event log shows it DID fire but Google didn't receive it:**
- Pixel-side delivery issue
- Reinstall Google & YouTube app (Sales channels → Google & YouTube → Settings → bottom of page → Disconnect → re-add)
- This is the fix path Shopify support typically suggests for this symptom

### Step 4: Implement Path B (server-side webhook)

Detailed scope (full implementation, ~45 min):

1. **Front-end gclid capture** — append `<script>` block to active theme's `theme.liquid` (or via Shopify's "Custom Pixel" feature for cleaner separation):
   ```js
   (function(){
     var p = new URLSearchParams(location.search);
     var g = p.get('gclid') || p.get('wbraid') || p.get('gbraid');
     if (g) document.cookie = '_gcl_aw=' + g + '; max-age=7776000; path=/; samesite=lax';
     var stored = (document.cookie.match(/_gcl_aw=([^;]+)/)||[])[1];
     if (stored && window.Shopify && Shopify.theme) {
       fetch('/cart/update.js', {
         method:'POST', headers:{'Content-Type':'application/json'},
         body: JSON.stringify({attributes:{'_gclid': stored}})
       });
     }
   })();
   ```
2. **Webhook endpoint** — extend the dashboard's existing API routes:
   - New route: `POST /api/webhooks/shopify/orders-paid`
   - Verify Shopify HMAC signature using `SHOPIFY_WEBHOOK_SECRET`
   - Extract: order_id, total, currency, customer_email, note_attributes._gclid, customer_phone
   - Upload to Google Ads via existing `dashboard/src/lib/google-ads.ts` (extend with conversion upload method)
   - Use `UploadClickConversions` with gclid if present, else `user_identifiers` with hashed email/phone
3. **Register webhook in Shopify**:
   - Shopify Admin → Settings → Notifications → Webhooks
   - Topic: `orders/paid`, Format: JSON, URL: `https://8bit.tristanaddi.com/api/webhooks/shopify/orders-paid`
4. **Test** with a real order in incognito (apply gclid manually via URL `?gclid=test_xyz`) and verify:
   - Cart gets the `_gclid` note attribute
   - Order webhook fires with the gclid in note_attributes
   - Google Ads receives the conversion with proper gclid
   - Conversion appears in reports within 6h with attribution

### Step 5: Flip the campaign

Once Path B is verified working with one real test order:
1. Run `python3 scripts/ads_audit.py` to confirm campaign config still good
2. Enable the campaign via API:
   ```python
   # campaign_id = 23766662629
   # Mutation: campaign.status = ENABLED
   ```
3. Monitor for first hour: budget pacing, impressions, clicks
4. Hard pause if no conversion at $50 spend (per existing safety rules)

---

## Don't redo / state from today

| Item | Status | Don't redo |
|---|---|---|
| MC Feed cleanup (Feed A deleted, Feed B canonical) | ✅ Done 2026-04-29 cowork | |
| Pixel storefront installation (AW-18056461576 + tokens) | ✅ Verified via curl 2026-04-29 | |
| Conversion action token mapping (storefront ↔ Google Ads) | ✅ Verified all 7 match | |
| Custom labels metafield pilot (`mm-google-shopping.custom_label_*` on variant level) | ⏳ Set on 1 product, awaiting verification | Verify in MC tomorrow |
| Order #1072 manual conversion upload | ✅ Done via API, processing 3-6h | Conversion will appear with no gclid attribution; harmless |
| Pixel test discount codes (PIXELTEST 99% + PIXELSHIP) | ✅ Active in Shopify, max 1 use, 24h expiry | Don't recreate |
| Test order #1072 ($0.54 paid 18× Black Xbox Game) | ✅ Placed, can refund tomorrow via Shopify Admin | |
| Google Ads OAuth refresh token | ✅ Re-authed 2026-04-29 16:46 ET | Should still work tomorrow |
| Billing payment | ✅ Done | |
| Campaign config (8BL-Shopping-Games, $20/day, manual CPC, 334 negatives, listing tree) | ✅ Built, PAUSED | Don't rebuild |
| Pre-launch ad safety hard limits ($40 daily / $50 lifetime no-conv) | ✅ Live in `dashboard/src/lib/safety.ts` | |
| Shorts pipeline fixes (multi-cascade face detection, scene continuity, QA preview) | ✅ Deployed to NAS container 2026-04-29 14:00 ET | |
| Buffer scheduler fixes (pagination, evergreen filter, low-fresh alert, state-based throttle) | ✅ Deployed 2026-04-29 15:00 ET | |

## Active blocker

**Tristan needs to refund Order #1072** ($0.54 18× Black Xbox Game) tomorrow via Shopify Admin (NOT cancel — refund). Add a note "Pixel test order — refund post-attribution check".

The PIXELTEST + PIXELSHIP discounts are 1-use limited and self-expiring; no cleanup needed.

## Files to read on resume

In order:
1. `docs/ads-launch-resumption-2026-04-30.md` — this file
2. `docs/cowork-session-2026-04-29-pixel-verify.md` — last verification (pixel-not-firing finding from cowork)
3. `docs/cowork-session-2026-04-29-pixel-test-discount.md` — order #1072 setup
4. `docs/session-handoff-2026-04-27-ads-launch-blockers.md` — original 5 blockers (#3 superseded by today's metafield discovery)
5. Memory: `project_ads_launch_state.md`, `feedback_mc_supplemental_disaster.md`, `reference_mc_feed_offer_ids.md`

## Critical pieces of state

- **Campaign**: `8BL-Shopping-Games` ID `23766662629`, PAUSED, $20/day
- **Conversion action IDs**: Purchase=7590907627, Add to Cart=7590907633, Begin Checkout=7590907630, Page View=7590907636, View Item=7590907639, Search=7590907642, Add Payment Info=7590907645
- **Customer ID**: 8222102291 (8-Bit Legacy, 822-210-2291)
- **Manager Customer ID**: 4442441892
- **Conversion tracking ID**: 18056461576 (the AW account)
- **Wrong/leftover account**: AW-11389531744 (still tagged in storefront, cleanup item)
- **MC Feed B**: `USD_88038604834` (13,252 items, offer ID prefix `shopify_ZZ_`)
- **Order #1072**: Shopify Order ID `gid://shopify/Order/6363501494306`, $0.54, paid 2026-04-29 13:27 ET, 18× Black Xbox Game (qty hack to clear Shopify's $0.50 minimum)
- **Test product for metafield pilot**: 3 Ninjas Kick Back - Sega Genesis Game (`gid://shopify/Product/7956600029218`), variants: Game Only `43794752700450`, CIB `43794687295522`. Both have `mm-google-shopping.custom_label_0=over_50` and `custom_label_2=game` set 2026-04-29 ~10:00 ET. Verify in MC tomorrow whether labels propagated.
