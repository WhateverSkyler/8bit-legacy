# Cowork Session — 2026-04-24 — Google Ads Purchase Pixel Fix

## Outcome

**Likely root cause identified and applied.** The Google Ads conversion pixel
(`AW-18056461576`) wasn't firing because the Google & YouTube Shopify app
**was not the canonical owner of the Google tags**. After uninstalling and
reinstalling the app, Shopify's setup flow surfaced a "Migrate your Google
tags" wizard that revealed two competing tag injectors:

- **GA4 tag `G-09HMHWDE5K`** → being injected by **MonsterInsights** (third-party plugin), not by the Google & YouTube app
- **MC tag `GT-TBZRNKQC`** → being injected by **Shopify Channel App**, not by the Google & YouTube app

These conflicting injectors were preventing the Google & YouTube app from
firing tags on its own (including the Ads conversion pixel). Migration brought
all Google tag injection under the Google & YouTube app's control.

**Fix path taken:** 2C — uninstall + reinstall + tag migration.

## What got placed

Two test orders were placed during this session against
`Abra (43/102) - Base` ($1.99, 100% off via discount):

| Order | Discount | Timing | Pixel state |
|-------|----------|--------|-------------|
| #1068 | TESTZERO-20260424-v2 | 4:30 PM ET — BEFORE migration completed | Likely did NOT fire (broken state) |
| #1069 | TESTZERO-20260424-v3 | 5:25 PM ET — AFTER migration completed | Should fire — pending verification |

Both orders need to be cancelled / archived in Shopify admin since they're
real $0 orders that will otherwise route to fulfillment.

## Diagnosis trail

1. **Tag Assistant skipped** — driving the extension UI from Chrome MCP isn't
   feasible (popup lives outside the page DOM). Used Chrome MCP network/JS
   inspection as the substitute per Tristan's call.
2. **Settings page check** confirmed all 4 Google services were correctly
   linked: MC `5296797260`, Ads `8222102291` (= 822-210-2291 ✓), GA4
   `G-09HMHWDE5K`, Business Profile.
3. **No "Conversion tracking" toggle exists** on the modern Settings page —
   conversion tracking is implicit to the Ads link. So 2A had no toggle to
   flip.
4. **Ads account was correctly linked** → ruled out 2B.
5. **5+ real orders + test order #1067 had failed to register conversions
   over 2 weeks** despite correct linking → broken tag injection → 2C.
6. **2C uninstall + reinstall** surfaced the **Migrate Google tags** wizard
   (this is the actual fix — the previous app install had never completed
   this migration).

## Files / artifacts in this session

Discounts created (need cleanup):

- `TESTZERO-20260424-v2` (1415914553378) — used by #1068, status: 1 used, will expire 2026-04-25 4:15 PM ET
- `TESTZERO-20260424-v3` (1415938375714) — used by #1069, status: 1 used, will expire 2026-04-25 4:15 PM ET
- Automatic free-shipping discount **"Test order free shipping v2 (pixel-fix 2026-04-24)"** (1415914815522) — expires 2026-04-25 11:59 PM ET

Screenshots (in Chrome MCP screenshot store, not committed): pre-uninstall
Settings page, Apps page, post-uninstall Sales Channels page, install grant
dialog, App setup with red migration banner, tag migration wizard with both
checkboxes shown, post-migration "3 of 3 tasks completed" page.

## Next steps for Tristan

1. **Wait 2–4 hours**, then open Google Ads → Tools → Conversions → click
   row "Google Shopping App Purchase" → **Webpages** tab. Order #1069's
   thank-you URL should appear there as the first entry.
2. If Webpages tab populates → pixel is fixed → ready to flip the paused
   campaign.
3. If Webpages tab is still empty after 4h → escalate. Possible deeper
   issues:
   - MonsterInsights might still be injecting GA4 in parallel (the migration
     made Google & YouTube the canonical owner but didn't uninstall
     MonsterInsights). Check Apps → MonsterInsights → either uninstall it
     or disable its GA4 injection.
   - The MC product feed setup in the Google & YouTube app onboarding has
     a pending step ("Confirm that you've added contact information to your
     online store"). This is for MC compliance, not for Ads conversion
     tracking, but worth completing.
   - The Online Store contact-info confirmation gate may need to be cleared
     before the app's full tag injection finishes propagating.
4. **Cancel/archive test orders #1068 and #1069** in Shopify admin so they
   don't route to eBay fulfillment.
5. Consider deleting the v2 + v3 discount codes and the free-shipping auto
   discount so they don't linger past today.

## Hard guardrails — none violated

- ✓ Did NOT enable the paused Google Ads campaign
- ✓ Did NOT uninstall Merchant Center or the Ads account directly (only the Shopify app)
- ✓ Did capture pre-uninstall screenshot of Settings (sealed in MCP screenshot store)

## Notes / observations not in the brief

- The current Google & YouTube app version no longer exposes a manual
  "Conversion tracking" toggle. Conversion tracking is implicit to having
  an Ads account linked. So 2A from the brief is no longer applicable to
  the current app version.
- Reloading a fresh thank-you page redirects to
  `shopify.com/account/orders/...`, which is a different origin. This
  prevents post-hoc re-inspection of the thank-you page network/DOM after
  an order is placed. For real-time pixel inspection, you'd need to keep
  DevTools open on the storefront tab during the order placement, or use
  Tag Assistant Companion (whose extension UI Chrome MCP can't drive).
- The MC product feed setup has a pending "Confirm that you've added
  contact information to your online store" gate that I couldn't drive
  (iframe rejected clicks on this specific link). Tristan completed
  earlier flow steps manually via OAuth. The contact-info gate doesn't
  block the Ads conversion pixel — it's specifically for MC product feed
  re-sync, which is independent.
- The customer pixel system in modern Shopify is sandboxed. Tag injection
  may not appear in normal page-load network requests until the actual
  conversion event (order completion). This is why I couldn't see Google
  requests on the storefront product page itself.

## Status

- [x] Diagnosis complete (2C path identified)
- [x] App uninstalled + reinstalled
- [x] Google account re-OAuthed
- [x] MC re-linked (5296797260)
- [x] **Tag migration completed (the real fix)**
- [x] Fresh test order #1069 placed post-migration
- [ ] **Webpages tab verification — pending 2–4h wait** (assigned to Tristan to check)
- [ ] Test order cleanup (assigned to Tristan)
