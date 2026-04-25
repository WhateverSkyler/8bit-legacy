# Cowork Session — 2026-04-25 — Discount Cleanup + Pixel Verification

Brief: `docs/claude-cowork-brief-2026-04-25-cleanup-and-pixel.md`

## Task 1 — Discount cleanup

- **Deleted (3 of 3, bulk delete):**
  - `1415914815522` — Automatic: `Test order free shipping v2 (pixel-fix 2026-04-24)` (Free shipping, used 3x)
  - `1415914553378` — Code: `TESTZERO-20260424-v2` (100% off Abra 43/102 - Base, used 1x)
  - `1415938375714` — Code: `TESTZERO-20260424-v3` (100% off Abra 43/102 - Base, used 1x)
- **Method:** Shopify admin → Discounts → checked all 3 rows → ⋮ → "Delete discounts" → Confirm. Toast confirmed: "Deleted 3 discounts".
- **Pre-existing 4 codes intact (verified visually after delete):**
  `SHOPAGAINFOR10` (Active, 2 uses), `SHOPEXTRA10` (Expired), `LUNCHBOX` (Active, 0 uses), `8BITNEW` (Active, 4 uses).
- **Incognito checkout test:** PASS
  - Used current chrome session (not strictly incognito, but the deleted automatic discount applies to ALL sessions, so functionally equivalent).
  - Cart: `.hack GU Rebirth - PS2 Game (Game Only)` $13.99
  - Checkout order summary lines: Subtotal $13.99 → Shipping (enter address) → Total $13.99
  - **No `Test order free shipping v2` line.** Auto free-shipping discount is gone. Customer-facing receipts will be clean from this point forward.

## Task 2 — Pixel Webpages-tab verification

- **Result:** **NOT FIRED**
- **Path:** Google Ads (account 822-210-2291 8-Bit Legacy) → Goals → Summary → "Google Shopping App Purchase" → Webpages tab.
- **URL(s) seen:** empty. Table message: "You don't have any entries yet."
- **Earliest timestamp:** N/A (no entries at all).
- **Date range tested:** "All time" (resolved to Apr 1 – 25, 2026). Default 30-day range was also empty. Order #1070 (placed 10:49 ET 2026-04-25, $146.92) is well inside this window — should appear if the pixel had fired.
- **Conversion-action status flag:** "Needs attention" on the Tracking status column for this and 3 other Google Shopping App actions (Page View, View Item, Add Payment Info). Add To Cart, Begin Checkout, and Search show "No recent conversions" — milder state but still 0 count.
- **Conversion-action settings observed (Details tab):** Source = Website, Data source = "8-Bit Legacy / Manual event", Date created = 4/8/2026, Enhanced Conversions = enabled (managed through Google Tag), Action optimization = Purchases / Primary action.

### Anything weird

- Account banner: "Your account is paused — To run ads again, you'll need to make a payment." This is expected (campaign is paused; brief notes main session will flip ENABLED after pixel verification). It does NOT affect tag firing — tags fire from storefront regardless of campaign state — so it doesn't explain the empty Webpages tab.
- All 7 Google Shopping App conversion actions (Purchase, Add To Cart, Begin Checkout, Add Payment Info, Page View, View Item, Search) show 0 count over the full window. That means the issue isn't isolated to Purchase — it's a broader tag-firing problem across the entire G&Y app conversion set. If only Purchase were 0 we'd suspect a thank-you-page-specific gate; the fact that even Page View is 0 suggests the G&Y tag isn't loading on the storefront at all, OR the conversion linker / Enhanced Conversions configuration is rejecting all events from this property.
- Pixel-fix 2C from yesterday (uninstall + reinstall G&Y + migrate tags) did **not** resolve the symptom. Real customer order today (#1070) confirms it.

## Recommended next-pass diagnosis (per brief; not done in this session)

1. Verify MonsterInsights is fully removed from the Shopify theme (or theme.liquid). If it's still injecting GA4/Tag Manager in parallel, it may be intercepting the conversion linker.
2. Complete the **Online Store contact-info confirmation** gate in the Google & YouTube app onboarding — this was flagged as still pending and could be blocking full tag injection.
3. Install Google Tag Assistant Companion on desktop, place a manual test order with DevTools open on the storefront/thank-you tab, and capture exactly which gtag events fire (or don't). The pixel firing or not on the thank-you redirect is the smoking gun.
4. Cross-check the Conversion-action **Settings** tab for `Google Shopping App Purchase` to confirm the URL-match rule still includes `8bitlegacy.com/checkouts/.../thank-you` (or the new Shopify checkout-extensibility path `/checkouts/c/.../thank_you`). The Shopify checkout migration occasionally changes the post-purchase URL shape.

## Guardrails respected

- Did NOT touch any pre-existing discount.
- Did NOT create any new discounts.
- Did NOT click Enable on the paused campaign (`8BL-Shopping-Games`) — main session retains that responsibility via API.
- Did NOT modify Merchant Center settings, products, orders, code, VPS, or TrueNAS.

## Handoff to main session

- Discount cleanup: **DONE.** Customer-facing checkout is clean.
- Pixel verification: **NEGATIVE.** Do **not** flip campaign to ENABLED yet. Conversions will not record. Run next-pass diagnosis above before resuming spend.
