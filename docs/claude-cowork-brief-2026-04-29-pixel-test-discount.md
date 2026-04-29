# Cowork Brief — 2026-04-29 — Pixel Test Discount Setup + Cart Staging

## Goal

Set up a working discount code (or pair) on Shopify for a pixel test order, then stage a cart with cheapest item + discount applied + advance to the payment page. **STOP at payment** — Tristan enters card info himself.

## Why this is happening

Pixel verification for the Google Ads `8BL-Shopping-Games` campaign requires a real, uncancelled, non-zero-total order on 8bitlegacy.com. Tristan wants to minimize the cost. He attempted the discount setup himself but Shopify's combinations UI is being uncooperative.

## Hard guardrails

- ✗ Do NOT enter Tristan's credit card or any payment info
- ✗ Do NOT click "Pay" or finalize the order — stop at the payment page
- ✗ Do NOT modify any other discount, product, theme, or storefront setting
- ✗ Do NOT touch the Google Ads campaign
- ✗ Do NOT cancel any existing orders
- ✗ Do NOT delete existing discount codes (there may be `PIXELTEST` already created from Tristan's earlier attempt — work with it, don't delete)

## Pre-existing state

- Tristan started creating a 90% off "PIXELTEST" discount but got stuck on the Combinations section. He may have a partial discount saved already.
- Shopify Admin URL: `8bitlegacy.myshopify.com/admin`
- Shopify plan: Basic

---

## Task 1 — Create or fix discount code(s) (10 min)

### Approach A (preferred): Two codes that combine

Need two discounts that stack:

**Discount 1 — PIXELTEST**
- Type: Amount off products
- Code: `PIXELTEST`
- Value: 99% off (use 99 not 90 — minimizes total without going to 100%)
- Applies to: All products
- Min purchase: None
- Customer eligibility: All
- Max uses: 1
- **Combinations: check "Shipping discounts"** (this is the critical step)

**Discount 2 — PIXELSHIP**
- Type: Free shipping
- Code: `PIXELSHIP`
- Eligibility: All customers
- Min purchase: None
- Max uses: 1
- **Combinations: check "Product discounts"** (the reciprocal)

### Approach B (fallback if combinations genuinely don't work)

If Approach A fails (Shopify doesn't honor the combination at checkout), DELETE both codes and create a single one:

**Discount — PIXELTEST**
- Type: Amount off products
- Code: `PIXELTEST`
- Value: **99% off**
- Applies to: All products
- Min purchase: None
- Max uses: 1
- Combinations: doesn't matter

This means the order will have shipping cost (~$5), but total stays cheap (~$5.05). Acceptable.

### Verification before moving on

Open an incognito tab → go to 8bitlegacy.com → add cheapest game to cart → go to checkout → apply codes:
- Approach A: enter both `PIXELTEST` and `PIXELSHIP`
- Approach B: enter just `PIXELTEST`

Confirm:
- Product subtotal shows ~99% reduction (e.g. $5 → $0.05)
- (Approach A only) Shipping shows $0.00
- Total is under $1 (Approach A) or under $6 (Approach B)

---

## Task 2 — Stage the cart for Tristan (3 min)

After Task 1 verification works, in the SAME incognito tab:

1. Cart should already have the cheapest game in it
2. Codes should already be applied
3. Advance through checkout: enter shipping address as **Tristan's home address** (you have it from the Shopify customer record — DO NOT make up an address; if you don't have access to it, STOP and tell Tristan to enter it himself)
4. Continue to the payment page
5. **STOP at the payment / card-entry step**
6. Take a screenshot showing:
   - Order subtotal
   - Shipping cost
   - Discount applied
   - Final total
   - "Pay [amount]" button visible
7. Tell Tristan in the handoff: "Cart is staged in incognito tab at [URL]. Final total is $X.XX. Enter your card and click Pay."

If you don't have access to Tristan's address (likely — incognito has no Shopify session), then SKIP staging and just tell Tristan in the handoff: "Discount codes are ready. Go to 8bitlegacy.com, add cheapest game, apply [PIXELTEST + PIXELSHIP / just PIXELTEST], complete checkout."

---

## Task 3 — Handoff

Write `docs/cowork-session-2026-04-29-pixel-test-discount.md` with:

```markdown
# Cowork Session — 2026-04-29 — Pixel Test Discount Setup

## Approach taken
- Approach A (two-code combination) / Approach B (single 99% off)
- Reason for fallback (if applicable): <e.g. "Shopify combinations didn't apply at checkout">

## Discount codes active
- PIXELTEST: <99% off products, 1 use limit, expires X>
- PIXELSHIP: <free shipping, 1 use limit, expires X> (or N/A if Approach B)

## Verification result
- Cart subtotal: $___
- Shipping: $___
- Total at checkout: $___

## Cart staging
- Staged URL: <if able> / Not staged (no address access)

## Anything weird
<free-form>
```

Commit with message: `Cowork 2026-04-29: pixel test discount setup`

---

## What you are NOT doing

- Entering payment info
- Placing the order
- Touching the Google Ads campaign
- Modifying products, theme, or other discounts
- Investigating MC / Feed B (separate workstream, recovery in progress autonomously)

---

## Reference

- `docs/next-steps-2026-04-29-supplemental-feed-upload.md` — broader launch plan
- Memory: `feedback_ads_strategy.md`, `project_ads_launch_state.md`
