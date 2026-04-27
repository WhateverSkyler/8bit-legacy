# Cowork Brief — 2026-04-27 — Pixel Test Order

## Goal
Place a $0 test order to fire the Purchase pixel under the now-correctly-linked Google Ads account `822-210-2291`, verify it records, then clean up so nothing test-related leaks to real customers.

## Critical context (read once, then act)

- The Google & YouTube app's Ads link is now correct: `8222102291 (8-Bit Legacy)`. Verified.
- Storefront HTML is firing `AW-18056461576/<conversion-action-token>` on all 7 events. Verified live by main session via curl.
- Main session needs a real Purchase event to confirm it lands in account 822 before flipping the campaign to ENABLED.
- **PRIOR INCIDENT (4/24):** an auto-apply free-shipping discount got created during a pixel test and stayed live for ~24h, showing `Test order free shipping v2 (pixel-fix 2026-04-24)` on real customer checkouts. **Do NOT repeat this.** This brief uses a discount CODE only — no automatic discount. If you find yourself about to create an automatic discount for any reason, **stop and end the session.**

## Hard guardrails

- ✗ DO NOT create any **automatic** discount — code-only.
- ✗ DO NOT touch any pre-existing discount: `SHOPAGAINFOR10`, `SHOPEXTRA10` (Expired), `LUNCHBOX`, `8BITNEW`.
- ✗ DO NOT enable the paused Google Ads campaign — main session does that.
- ✗ DO NOT touch Merchant Center, theme, products, or env files.
- ✗ DO NOT leave the session without verifying the cleanup checklist at the bottom.

---

## Task 1 — Create discount code (2 min)

Shopify admin → Discounts → **Create discount** → **Amount off products**:

- Method: **Discount code** (NOT automatic)
- Code: `TESTZERO-20260427`
- Discount value: **Percentage** → **100%**
- Applies to: **Specific products** → search and select **"Abra (43/102) - Base"** (single product)
- Minimum requirements: **None**
- Customer eligibility: **All customers**
- Maximum discount uses: total uses **1**, "Limit to one use per customer" **checked**
- Active dates: starts now, ends today 11:59 PM ET
- **Save**

Capture the discount ID (visible in the URL or page after save). Note it in the handoff.

---

## Task 2 — Place test order (5 min)

1. Open `8bitlegacy.com` in **incognito** Chrome.
2. Add **Abra (43/102) - Base** to cart.
3. Go to checkout.
4. Apply code `TESTZERO-20260427` → product line goes to $0.00.
5. Shipping address: Tristan Addi, 103 Dogleg Dr, Moultrie GA 31788
6. Email: `tristanaddi1+pixeltest@gmail.com` (the `+pixeltest` suffix routes to the same inbox)
7. **Important:** if shipping is charged separately (since the discount is product-only, not free-shipping), the order total may be $4-$8 for shipping. **That's fine — proceed.** Do NOT create a free-shipping auto-discount to zero it out. Pay the shipping with a real card if needed; a few bucks is acceptable.
8. Complete the checkout.
9. **Capture:**
   - Order number (e.g. `#1071`)
   - Thank-you page URL
   - Final order total
   - Screenshot of the thank-you page

---

## Task 3 — Cancel order before fulfillment (2 min)

Shopify admin → Orders → find the just-placed order:

- Top-right **More actions** → **Cancel order**
- Reason: **Other**
- Staff note: `internal pixel verification test 2026-04-27`
- Restock: **checked**
- Customer notification: **unchecked**
- After cancel, click **Archive**

Confirm order shows **Canceled / Archived**.

---

## Task 4 — Cleanup checklist (3 min) — DO ALL OF THIS

This is the part that broke last time. Don't skip.

1. Shopify admin → Discounts → search `TESTZERO-20260427` → row → ⋮ → **Delete discount** → confirm.
2. Discounts page → search `TEST` (uppercase) → confirm **zero rows** appear.
3. Discounts page → filter by **Automatic** → confirm only the user's intended automatic discounts (if any) appear. There should be **zero discounts with "test" or "pixel" or "TESTZERO" anywhere in the title**.
4. Open `8bitlegacy.com` in a **fresh incognito** window (NOT the one used for the order). Add any product to cart, go to checkout. Confirm the order summary shows **no test-related discount line** and **no unexpected automatic discount**.
5. Verify pre-existing 4 codes still intact: `SHOPAGAINFOR10`, `SHOPEXTRA10` (Expired), `LUNCHBOX`, `8BITNEW`.

If ANY of steps 1–5 fail or look weird, **stop and write findings into the handoff. Do not delete anything you didn't create.**

---

## Handoff

Write `docs/cowork-session-2026-04-27-pixel-test-order.md` with:

```
## Task 1 — Discount code
- Code: TESTZERO-20260427
- ID: <fill>
- Status: created / failed

## Task 2 — Test order
- Order #: <fill>
- Thank-you URL: <fill>
- Final total: <fill> (shipping if any)
- Anything weird:

## Task 3 — Cancel
- Cancelled + Archived: YES / NO

## Task 4 — Cleanup checklist
- [ ] TESTZERO-20260427 deleted
- [ ] Discount search "TEST" returns zero rows
- [ ] Automatic discount filter shows nothing test-related
- [ ] Fresh incognito checkout shows no leaked discount line
- [ ] Pre-existing 4 codes intact

## Status for main session
- Test order placed: YES / NO
- Order # for Webpages-tab cross-reference: <fill>
- Cleanup verified: YES / NO
```

Commit + Syncthing-propagate. No git push needed.

---

## What you are NOT doing

- Not flipping the campaign — main session does that after verifying the Purchase event landed in account 822 (2-4h Google reporting lag)
- Not creating any automatic discount, ever
- Not touching merchant Center, themes, products, env, or the campaign
