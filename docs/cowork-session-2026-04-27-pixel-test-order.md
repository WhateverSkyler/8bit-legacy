# Cowork Session — 2026-04-27 — Pixel Test Order

## Status for main session
- **Test order placed:** YES
- **Order # for Webpages-tab cross-reference:** **#1071**
- **Customer-facing confirmation #:** 08TA7H0L2
- **Cleanup verified:** YES (no test/temp discounts remaining)

## Task 1 — Discount code
- Code: TESTZERO-20260427
- ID: 1417265938466
- Status: created → applied to order #1071 → DELETED in cleanup

## Task 2 — Test order
- Order #: #1071
- Thank-you URL: https://8bitlegacy.com/checkouts/cn/hWNBRP2v1nYESnPpc2VQYFEo/en-us/thank-you
- Customer-facing Confirmation #: 08TA7H0L2
- Final total: **$0.00** (Subtotal $0.00, Shipping FREE, Tax $0)
- Email used: tristanaddi1+pixeltest@gmail.com
- Shipping address: Tristan Addi, 103 Dogleg Dr, Moultrie GA 31788
- Shipping method: Economy (5 to 8 business days)
- Discount lines on order: TESTZERO-20260427 (-$2.99) + TEST automatic free shipping 2026-04-27 (-$6.00)

### Anything weird / deviations from brief
- **Brief-specified product Abra (43/102) - Base was a Draft.** It 404'd on the storefront, so it could not be ordered. Per main-session redirect mid-session, switched to **Black - Xbox Game** (/products/black-xbox-game, $2.99) which is Active. Edited the existing TESTZERO-20260427 discount (didn't recreate) to apply to Black - Xbox Game instead of Abra.
- **Brief said code-only, no automatic discounts.** Black - Xbox Game incurs $6 shipping (storefront's "FREE shipping over $50" threshold). To get to $0 without paying real shipping, **created an additional automatic free-shipping discount** ("TEST automatic free shipping 2026-04-27", ID 1417272623138) per Tristan's explicit in-session authorization ("you can make an automatic free shipping discount code just remove it once u finish testing"). Both test discounts were deleted in cleanup. **The 4/24-style leak risk was mitigated by:** (a) clearly labeling with "TEST" prefix so cleanup search would catch it, (b) end date 2026-04-27 11:59 PM ET as auto-expiry safety, (c) verified deletion before session end.
- **Edited TESTZERO-20260427 to "Combines with shipping discounts"** (originally was "Can't combine") so the two test discounts could stack at checkout.
- **Cart had a stale item from a prior session** (.Hack GU Rebirth - PS2 Game, $13.99). Cleared via `/cart/clear.js` before the test.
- **Could not use literal incognito Chrome** — the Claude in Chrome extension drives a regular Chrome window. Used a fresh tab + cleared cookies/cart equivalent. Confirmed no logged-in customer state (TESTZERO applied without auto-detection).
- **Pay step:** total was $0.00, so checkout button changed to "Complete order" (no card needed). No payment was processed.

## Task 3 — Cancel
- Cancelled + Archived: **YES** (Shopify auto-archived on cancel)
- Order status: Canceled • Paid • Unfulfilled • Archived
- Reason: Other
- Staff note: "internal pixel verification test 2026-04-27"
- Restock: checked
- Customer notification: unchecked

## Task 4 — Cleanup checklist
- [x] TESTZERO-20260427 deleted (Discount code, ID 1417265938466)
- [x] TEST automatic free shipping 2026-04-27 deleted (Automatic discount, ID 1417272623138)
- [x] Discount search "TEST" returns zero rows ("No discounts found")
- [x] Automatic discount filter shows nothing test-related (zero automatic discounts exist on the store at all — all 4 remaining discounts are Method=Code)
- [x] Fresh-tab + cleared-cart checkout shows no leaked discount line (Subtotal $2.99, no chip, no auto-applied line)
- [x] Pre-existing 4 codes intact and unmodified:
  - SHOPAGAINFOR10 (Active, Code, Amount off order, Used: 2)
  - SHOPEXTRA10 (Expired, Code, Amount off product, Used: 0)
  - LUNCHBOX (Active, Code, Amount off product, Used: 0)
  - 8BITNEW (Active, Code, Amount off order, Used: 4)

## What is still pending for main session
- Verify Purchase pixel fired in Google Ads account 822-210-2291 (2-4h reporting lag — order placed ~12:25 PM ET, 2026-04-27)
- Then flip the paused Google Ads campaign to ENABLED (main session's call, not cowork's)
- No tax recorded on this order ($0 total), so tax-pixel data won't be present — only the Purchase event itself + line item data

## Files
- Brief: `docs/claude-cowork-brief-2026-04-27-pixel-test-order.md`
- This handoff: `docs/cowork-session-2026-04-27-pixel-test-order.md`
