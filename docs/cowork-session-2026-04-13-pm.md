# Cowork Session — 2026-04-13 PM

## Session Summary

Follow-up session to the morning cowork. Four tasks completed: variant price display fix, Google Customer Reviews custom pixel (live), Google Ads account verification, and sale price variant display fix (show/hide compare-at on variant switch).

---

## ✅ Task 1: Variant Price Display Fix — GREEN

**The CIB pricing strategy is now visible to customers for the first time.**

**Root cause (confirmed in AM session):** Theme JS targets `span.money` but the Liquid template rendered the ProductPrice span without the `money` class. The jQuery selector silently failed, so variant switching never updated the displayed price.

**Fix applied:** Added `class="money"` to all `<span id="ProductPrice-{{ section.id }}">` elements in three files:
- `sections/bs-product.liquid` (2 spans fixed)
- `sections/product-2-columns-left.liquid` (2 spans fixed)
- `sections/product-2-columns-right.liquid` (2 spans fixed)

**Process:**
1. Duplicated live theme `bs-kidxtore-home6-v1-7` (ID: 173344522274) via Shopify GraphQL `themeDuplicate` mutation
2. Created `bs-kidxtore-home6-v1-7-price-fix` (ID: 185254740002) as UNPUBLISHED
3. Fetched all three product section files via `FetchThemeFiles` query
4. Applied regex fix: added `class="money"` to both ProductPrice spans in each file
5. Wrote files back via `themeFilesUpsert` mutation
6. Verified fix by re-reading the files — `class="money"` confirmed present
7. Previewed on live storefront with `?preview_theme_id=185254740002`
8. Tested variant switching on two products:
   - **Phantasy Star Online Episode I & II (GameCube):** Game Only $162.99 ↔ CIB $303.99 ✓
   - **.hack GU Rebirth (PS2):** Game Only $13.99 ↔ CIB $29.99 ✓
9. Published duplicate as MAIN via `themePublish` mutation
10. Old theme kept as UNPUBLISHED backup (Tristan's default preference)

**Current theme state:**
- **MAIN (live):** `bs-kidxtore-home6-v1-7-price-fix` (ID: 185254740002)
- **UNPUBLISHED (backup):** `bs-kidxtore-home6-v1-7` (ID: 173344522274)

---

## ✅ Task 2: Google Customer Reviews Opt-in — LIVE VIA CUSTOM PIXEL

**Resolved via Shopify Custom Pixel** (Settings → Customer events → Custom pixels).

The classic "Additional scripts" field is no longer available on extensible checkout. Instead, created a Custom Pixel named "Google Customer Reviews" (Pixel ID: 149717026) using Shopify's Web Pixel API.

**How it works:**
- Subscribes to `analytics.subscribe("checkout_completed", ...)` — fires after every completed checkout
- Loads Google's `platform.js` and renders the `surveyoptin` modal
- Passes order ID, customer email, shipping country, estimated delivery date (7 days out), and product GTINs (from variant SKUs)
- Merchant Center ID: 5296797260
- Access level: Permission (not consent-gated)

**Status:** Connected and live (button shows "Disconnect" in Shopify admin).

**Remaining for Tristan:**
- Enable the Customer Reviews program in Merchant Center (merchants.google.com → account 5296797260 → Growth → Manage programs → Customer Reviews)
- The custom pixel satisfies the "opt-in integration" requirement

---

## ✅ Task 3: Google Ads Account Verification — ALREADY LINKED CONFIRMED

Navigated to Shopify admin → Apps → Google & YouTube → Settings.

**Connected Google services (4 total):**
- Google Account: tristanaddi1@gmail.com
- Google Merchant Center: 5296797260
- **Google Ads: 8222102291 (8-Bit Legacy)** ← This is 822-210-2291 ✓
- Google Analytics: G-09HMHWDE5K (8-Bit Legacy)
- Google Business Profile: tristanaddi1@gmail.com

**The correct Google Ads account (822-210-2291) IS linked.** The previous audit docs flagging this as "still wrong" were stale — the issue has been resolved (likely by Tristan's manual relinking). The "Re-link Google Ads account" action item should be permanently removed from future session handoffs.

---

## ✅ Task 4: Sale Price Variant Display Fix — GREEN

**When switching variants on sale products, the struck-through compare-at price now correctly shows/hides.**

**Root cause:** Two bugs in the theme's inline `selectCallback` function:
1. ComparePrice `<span>` elements were missing `class="money"` — needed for the theme's currency conversion system
2. The callback had no `else` clause for `compare_at_price` — when switching from a sale variant (e.g., Game Only with compare_at) to a non-sale variant (e.g., CIB without compare_at), the old struck-through price remained visible

**Fix applied to three files (same files as Task 1):**
- `sections/bs-product.liquid`
- `sections/product-2-columns-left.liquid`
- `sections/product-2-columns-right.liquid`

**Changes per file:**
1. Added `class="money"` to both ComparePrice spans (the `old-price` visible one and the `hide` fallback one)
2. Replaced the `if (variant.compare_at_price > variant.price)` block with full show/hide logic:
   - If variant has compare_at_price > price: update text, show compare price, show sale container
   - Else: hide compare price, remove sale styling

**Process:**
1. Duplicated live theme `bs-kidxtore-home6-v1-7-price-fix` (ID: 185254740002)
2. Created `Copy of bs-kidxtore-home6-v1-7-price-fix` (ID: 185256640546)
3. Applied both fixes via `themeFilesUpsert` mutation
4. Tested on preview theme against two products:
   - **Resident Evil 2 (PS1):** Game Only → $52.99 + ~~$66.50~~ ✓ | CIB → $109.99 alone ✓
   - **Chrono Trigger (SNES):** Game Only → $279.99 + ~~$299.99~~ ✓ | CIB → $502.99 alone ✓
5. Published as MAIN via `themePublish` mutation

**Current theme state (updated):**
- **MAIN (live):** `Copy of bs-kidxtore-home6-v1-7-price-fix` (ID: 185256640546)
- **UNPUBLISHED (backup 1):** `bs-kidxtore-home6-v1-7-price-fix` (ID: 185254740002) — has Task 1 fix only
- **UNPUBLISHED (backup 2):** `bs-kidxtore-home6-v1-7` (ID: 173344522274) — original, no fixes

---

## Screenshots

- Phantasy Star Online CIB $303.99 after variant switch (saved to disk during session)
- Google & YouTube Settings page showing 8222102291 connected (saved to disk during session)

---

## Technical Notes

### Shopify Admin API Access Pattern (updated)
The Shopify admin GraphQL API is accessible via:
```
POST https://admin.shopify.com/api/app_proxy/dpxzef-st?operation={OperationName}&version=unstable
Headers:
  Content-Type: application/json
  Accept: application/json
  X-CSRF-Token: {csrfToken from embedded script tag}
  Credentials: include
```

The CSRF token is embedded in a `<script>` tag on any admin.shopify.com page:
```js
const match = scriptContent.match(/"csrfToken":"([^"]+)"/);
```

This endpoint supports theme queries (`theme`, `themes`), mutations (`themeDuplicate`, `themePublish`, `themeFilesUpsert`), and file operations (`FetchThemeFiles`).

### Theme File Structure
Product price spans exist in three section files:
- `sections/bs-product.liquid` — line 203 and 214
- `sections/product-2-columns-left.liquid` — line 214 and 225
- `sections/product-2-columns-right.liquid` — line 213 and 224

All six spans now have `class="money"`.

---

## Action Items for Next Session

- [ ] Tristan: Enable Customer Reviews program in Merchant Center (pixel is already live)
- [ ] Monitor variant price + sale display on live site — confirm no regressions
- [ ] Consider renaming live theme to something cleaner (e.g., `bs-kidxtore-home6-v1-7`)
- [ ] Consider deleting oldest backup theme (173344522274) once confident in the fixes
- [ ] Note: The "FREE shipping over $50" badge on product pages still shows $50 even though the threshold was changed to $35 in the AM session. This is likely a hardcoded string in the theme that needs a separate fix.
- [ ] Note: The "-20%" sale badge on the product image doesn't update when switching variants — it's rendered server-side in Liquid. Low priority but worth noting.
