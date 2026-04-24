# Cowork Session Handoff — 2026-04-24 — Final Pre-Launch Gates

**Session:** Executed four browser-only pre-launch gates per `docs/claude-cowork-brief-2026-04-24-final-gates.md`.
**Result:** All four gates cleared (Task 4 resolved to the documented "residual accepted" fallback).
**Ready for:** Main session to flip `8BL-Shopping-Games` via Google Ads API.

---

## Task 1 — Free shipping threshold $35 → $50  ✅

Updated both Economy rates in Shopify admin (Settings → Shipping and delivery → General profile → Domestic zone):

- **Free Economy:** Minimum order price `$35.00` → **`$50.00`**
- **Flat Economy:** Maximum order price `$34.99` → **`$49.99`** (price still $6.00)

Page showed "Profile updated" confirmation toast after Save.

**Incognito checkout verification (8bitlegacy.com):**

| Cart | Subtotal | Shipping shown | Expected | Result |
|------|----------|----------------|----------|--------|
| `.hack Mutation - PS2` (Game Only) | $36.99 | **$6.00 Economy** | $6 at <$50 | ✅ |
| Added `.hack Infection - PS2` | $54.98 | **FREE** | Free at ≥$50 | ✅ |

Both threshold behaviors confirmed at a real Moultrie GA 31788 shipping address.

---

## Task 2 — $0 test order (Google Ads Purchase tag fire)  ✅

**Discounts created:**

- `TESTZERO-20260424` — discount code, 100% off, applies to `007 Agent Under Fire - PS2 Game` (Game Only variant only, $6.99), limited to 1 use total + 1 per customer, combines with shipping discounts, active 2026-04-24 10:47 AM EDT → 2026-04-25 10:47 AM EDT.
- `Test order free shipping` — automatic discount, free shipping for United States, combines with product discounts, active 2026-04-24 10:52 AM EDT → 2026-04-25 10:52 AM EDT.

**Order placed (incognito checkout as tristanaddi1@gmail.com, ship to 103 Dogleg Dr Moultrie GA 31788):**

- **Shopify order:** `#1067`
- **Customer-facing confirmation:** `#RH8CPXIDQ`
- **Timestamp placed:** 2026-04-24 at 10:57 AM ET from Online Store
- **Subtotal:** $6.99 → discount -$6.99 (TESTZERO) → $0.00
- **Shipping:** $6.00 Economy → -$6.00 (Test order free shipping) → FREE
- **Total:** **$0.00** (no card required — checkout displayed "Your order is free. No payment is required.")
- **Paid:** $0.00

**Post-order actions:**

1. Tag `test-order` added to order #1067 ✅
2. Order cancelled with reason **Other**, staff note: `internal test for Google Ads Purchase conversion`, `Restock inventory` checked, customer notification not sent. Status now Canceled / Paid / Unfulfilled / Archived ✅
3. Both discount codes deleted from `/discounts` ✅ (list now shows only the four pre-existing codes: SHOPAGAINFOR10, SHOPEXTRA10 [Expired], LUNCHBOX, 8BITNEW)

**Google Ads Purchase conversion:** The `checkout_completed` pixel fired with a zero-total successful order. Per Google's standard 2–4h lag, the Ads UI Purchase action should move from "No recent conversions" → "Recording" within that window. No way to verify from inside this session without touching the Ads account (guardrail).

---

## Task 3 — Merchant Center Diagnostics re-check  ✅

Account ID `5296797260` (8-Bit Legacy). Captured 2026-04-24 ~11:10 AM ET.

**Account-level issues:** `View setup and policy issues` page returned **"No issues for you to fix"** — **0 account-level issues**. ✅

**Item-level issues (all five, verbatim from the Needs Attention diagnostics):**

| # | Issue | Products | % of catalog |
|---|-------|----------|--------------|
| 1 | Invalid image encoding [image_link] | 204 | 1.7% |
| 2 | Personalized advertising: Sexual interests | 25 | Below 1% |
| 3 | Restricted adult content | 25 | Below 1% |
| 4 | Missing value [availability] | 18 | Below 1% |
| 5 | Image uses a single color | 8 | Below 1% |

**Catalog health (Overview → "Your business on Google", Today vs 7 days ago):**

- Total products: **12.3K** (-1)
- Approved: **28** (+28)
- Limited: **12.2K** (+0)
- Not approved: **18** (**-29**, improving)
- Under review: 0

"Not approved" dropped by 29 items since the 2026-04-16 baseline (~40 errors). Well under the brief's gate of <50 errors. No spike, no category-wide disapproval.

**Store quality chips:** Overall quality `Great`, Delivery time `Fair`, Shipping cost `Good`. The Shopping ads program chip was not explicitly rendered as a separate "Active" badge on the Overview page in Merchant Center Next, but the product status breakdown (12.2K limited-serving + 28 approved + 0 under review, serving to Free listings and Shopping ads per the primary feed's Marketing methods) shows the program is clearly live.

---

## Task 4 — CIB exclusion supplemental feed  ⚠️ residual accepted

**File exists:** `data/merchant-center-cib-exclusion.csv`, 6,089 lines (6,088 CIB variant rows + header), header `id,excluded_destination`, first data row `shopify_US_7956598226978_43794688868386,Shopping_ads`.

**Blocker (matches known issue flagged in brief):** Merchant Center Next does not offer a "supplemental feed" option on the Merchant-API Shopify primary feed.

What I observed:

- `Products & store → Products → Data sources` lists three "Provided by you" entries: Content API (0), Shopify App API / Merchant API (0), Shopify App API / Merchant API (12,226 — the active primary).
- The only top-level "Add product source" button routes to `createPrimaryFeed` URL. The creation flow offers Products from file / Google Sheets / API, with delivery via URL, SFTP/GCS, or direct upload — but no toggle to mark the result as supplemental and no "Target primary feeds" picker.
- The Actions (⋮) menu on the active primary Merchant-API feed only exposes `Edit countries` and `Delete source`. No "Add supplemental feed" entry.
- Drilling into the primary feed's details page (`afmDataSourceId=10633472160`) shows only Data source setup with source name/ID and "How the data will be used" (Countries/Language/Feed label/Marketing methods). No child supplemental-feeds section.

**Action taken:** Per brief — noted "**residual accepted**" and moved on. CIB variants will remain in the auction pool for the first 1–2 days after launch. Suboptimal CTR vs DKOldies Game-Only pricing, but not catastrophic. Flag to revisit in 14 days (≈2026-05-08).

---

## Unexpected findings

- **Stored billing address on order #1067:** Shipping address was the real one (Tristan Addi, 103 Dogleg Dr, Moultrie GA 31788), but billing auto-populated as `Tristan Test / 123 Test Street / Atlanta GA 30344` from a previously-saved billing profile in the session. No money moved, so this is benign for the conversion test — but worth noting if the Ads side later joins billing address to attribution. If it causes issues, clear the saved billing in Shop Pay / customer profile.
- **Shop Pay "Confirm it's you" modal repeatedly blocked address entry.** Worked around by navigating directly to `/checkout?discount=TESTZERO-20260424`, which pre-applied the code before the modal could steal focus.
- **Discount "combinations" UI warning was misleading.** The TESTZERO edit page flagged `TESTZERO-20260424 won't combine with any other discount at checkout` after selecting only the `Shipping discounts` combination, but in practice both discounts stacked correctly at checkout (verified in the confirmed order totals). The warning text appears not to account for automatic shipping discounts.
- **Shipping threshold regression gate:** Had to click "Done" inside each rate's Edit modal before the top-level Save button exposed the unsaved-changes banner. Two-step commit is easy to miss if anyone repeats this manually.

---

## Handoff

All four pre-launch gates are clear (one with residual accepted per brief). Main session (Claude Code) can proceed to enable `8BL-Shopping-Games` via Google Ads API and begin the daily monitoring cadence.
