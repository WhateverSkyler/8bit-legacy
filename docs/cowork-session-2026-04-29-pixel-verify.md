# Cowork Session — 2026-04-29 — Pixel Verification

## Check 1 — Google Ads conversion statuses (TODAY filter)

Date filter applied: **Today — Apr 29, 2026** (page header confirmed "Today" / "Apr 29, 2026")
Account confirmed: **822-210-2291 / 8-Bit Legacy** (top-right account selector + URL `__e=8222102291`)

| Action | Status | All conv. |
|---|---|---|
| Purchase (Google Shopping App Purchase (1)) | **Inactive** | not displayed |
| Add To Cart (Google Shopping App Add To Cart (1)) | No recent conversions | not displayed |
| Begin Checkout (Google Shopping App Begin Checkout (1)) | No recent conversions | not displayed |
| Page View (Google Shopping App Page View (1)) | No recent conversions | not displayed |
| View Item (Google Shopping App View Item (1)) | No recent conversions | not displayed |
| Search (Google Shopping App Search (1)) | **Inactive** | not displayed |
| Add Payment Info (Google Shopping App Add Payment Info (1)) | **Inactive** | not displayed |

Notes on the table view: the default columns in the Goals-grouped Conversions table are `Conversion action / Conversion source / Tracking status / Action optimization / Count / Click-through window / Included in account-level goals`. There is no "All conv." column in this view (changing column visibility would have required modifying a setting, which was outside the read-only guardrails). The "Count" column shows `Every` / `One` (count behavior), not numeric counts. None of the 7 actions show evidence of having received any events today — 4 are "No recent conversions", 3 are flat-out "Inactive".

Goal-level summary (separate `Goals` accordion view above the table) showed:
- **Purchases** goal — primary action: Google Shopping App Purchase (1) — Status: **Misconfigured**

Webpages tab on Purchase action: **empty — "You don't have any entries yet"**. The columns (Webpage / Tracking status / Tags / All conv. / All conv. value) are all blank. Google has never seen a webpage fire this conversion. No Diagnostic / Troubleshoot tab is exposed at the per-action level (URL had `showDiagnosticsTab=false`).

Account-level Diagnostics tab (verbatim):
- "Drive ads performance with high quality measurement"
- Enhanced conversions overview: Total enhanced conversion actions = 7 — Excellent: 0, Good: 0, Needs attention: 2, **Urgent: 5**
- Banner: "Some enhanced conversion actions have urgent issues"
- Urgent block heading: **"Your enhanced conversions setup is not active."**
  - "No recent data" — Affects **5** conversion actions
  - "Some of your enhanced conversions weren't processed because they are missing user-provided data" — Affects **2** conversion actions
- Enhanced Conversions Coverage (website only) chart, Last 7 days (Apr 23–27 visible): line sits at ~0% across the entire window.

## Check 2 — Live pixel fire

Methodology note: the Chrome-MCP browser does not expose an incognito mode toggle, so the checks ran in the connected Personal Chrome window rather than a fresh incognito window. Because the question is whether the Google Ads scripts load *at all*, the cookie/login state is not material — if the gtag bootstrap is missing, no incognito state would change that. Network signals were captured via `performance.getEntriesByType('resource')` (which sees every resource the page loaded, equivalent to the DevTools Network panel).

### 2A — Page load (https://8bitlegacy.com/)
- Total googleads requests: **0**
- AW-18056461576 instances: **0**
- AW-11389531744 instances: **0**
- All status codes: n/a — no Google Ads requests were issued
- `window.gtag`: **undefined**
- `window.google_tag_manager`: **undefined**
- `window.dataLayer`: **undefined / length 0**
- Total resources actually loaded by the page: 277 (page fully rendered)

### 2B — View product (PS2 Slim - Player Pack)
- URL: `https://8bitlegacy.com/products/ps2-slim-player-pack-controller-cables?variant=43794906382370`
- New googleads requests fired: **NO**
- URL/token of any matching request: none. No `view_item` token, no `--mzCPSd0KMcEIj6_qFD`, no `5fn7CPed0KMcEIj6_qFD`
- Total resources: 260; matches against `googleads|doubleclick|google-analytics|googletagmanager|gtag.js|gtm.js|google.com/pagead`: **0**
- gtag/dataLayer still undefined

### 2C — Add to cart
- "Add to Cart" click succeeded — confirmation popup showed item added, cart subtotal $184.99, "Your cart contains 1 items"
- add_to_cart request fired (token VJ6hCPGd0KMcEIj6_qFD): **NO**
- Status: n/a — the request was never made
- Resource count went from 260 → 274 (14 new requests during the AJAX add) — none were Google Ads

### 2D — Begin checkout
- Clicking "Check Out" in the cart popup redirected to **Shop Pay express checkout** (`shop.app/checkout/...`) rather than the standard Shopify storefront checkout (`8bitlegacy.com/checkouts/c/...`). This happened because the Personal Chrome session is logged into Shop Pay — payment method, ship-to, and email auto-populated. Shop Pay is on a separate domain (shop.app) and JS introspection there returned `BLOCKED: Cookie/query string data` — could not directly query its DOM.
- begin_checkout request fired (token HDu_CO6d0KMcEIj6_qFD): **NO** at the storefront layer. To rule out the Shop Pay redirect masking it, also visited `https://8bitlegacy.com/cart` directly and queried: 212 total resources, **0** matches against the Google Ads patterns, gtag still undefined, dataLayer still undefined. The pixel would have to load *before* checkout to fire on click — and it never loads.
- Stopped before entering any payment info or pressing "Pay now" (the Shop Pay page had a Mastercard pre-selected and a "Pay now" button visible).

## Verdict

Based on Check 1 + 2:
- [ ] Pixel infrastructure works, Google's verification is just lagging → wait it out, flip when ready
- [ ] Pixel fires for everything EXCEPT purchase → real bug at thank-you page level, need fresh test order
- [x] **Pixel doesn't fire at all → real broken config, deeper fix needed**

Reasoning: across four storefront page types (homepage, product detail, cart, in-AJAX add-to-cart) the page never loads gtag.js, GTM, or any other Google Ads / Analytics script. `window.gtag` is undefined, `window.dataLayer` is undefined, `window.google_tag_manager` is undefined, and zero requests hit `googleads.g.doubleclick.net`, `googletagmanager.com`, or `google-analytics.com`. The 7 conversion actions in Google Ads correctly reflect this: 3 marked "Inactive" (never received an event) and 4 marked "No recent conversions" (likely armed via the Google & YouTube channel app's first-party / API path, but no client-side pixel events arriving). The Purchase action's Webpages tab is empty — Google has never observed a purchase event from any URL.

The $0.54 test order at 1:27 PM ET on order #1072 was therefore correctly *not* counted by Google — the pixel that should have fired on `/thank_you` simply isn't on the page. This is not a verification lag.

## Anything weird

- The "Google Shopping App ..." conversion actions are auto-generated by the Google & YouTube Shopify channel app. Their existence in the Conversions list does not by itself mean a pixel is wired into the storefront theme — they can be created server-side via the channel/Merchant Center handshake. The actual web-side gtag.js install is a separate step (typically `gtag` snippet in `theme.liquid` or via Google Tag Assistant / a Custom Pixel for `purchase`), and that step appears to be missing.
- CLAUDE.md mentions a Custom Pixel installed for **Google Customer Reviews** (Pixel ID 149717026) firing on `checkout_completed`. That is a different system (review opt-in, not Ads conversion) and does not satisfy the Google Ads `purchase` conversion event.
- The two AW IDs the brief flagged (correct `AW-18056461576` vs. leftover `AW-11389531744`) are both absent from the page — the question of which ID is wired is moot until *some* gtag tag is wired.
- Because Tristan is signed into Shop Pay, the in-popup "Check Out" button shortcut-redirects to `shop.app` and skips the Shopify checkout pages entirely. Even if a `begin_checkout` pixel were wired into the storefront theme, the Shop Pay path would bypass it. Worth keeping in mind when planning a fix — the pixel needs to fire upstream of that redirect, e.g. on the Add-to-Cart event or on `cart.js`-fetch, not on a checkout page that the user never sees.
- One non-blocking 404 was observed during reload: `https://8bitlegacy.com/products/lucario-ex-51-131-prismatic-evolutions.js` returned 404. Unrelated to the pixel question, but a stale reference somewhere in the theme/scripts.
