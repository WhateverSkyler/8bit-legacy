# Claude Cowork Brief — 2026-04-23 — Final Pre-Launch Gates

## The task in one sentence
Two small browser tasks that stand between the paused campaign and go-live: revert the free shipping threshold $35 → $50 in Shopify, and place a $5-10 test order so the Purchase conversion flips from Inactive → Active in Google Ads.

## Hard guardrails
- **DO NOT touch Google Ads.** Don't edit the campaign, don't enable it, don't touch budgets or bids. Main session will flip it via API after you confirm these tasks are done.
- **DO NOT modify anything outside the two tasks below.**
- **DO NOT commit secrets.**
- If anything unexpected, STOP and report — don't improvise.

## Context
- Store: https://8bitlegacy.com (Shopify admin: admin.shopify.com → 8-Bit Legacy)
- Current free shipping threshold: $35 (raised from $50 on 2026-04-13 when competing with DKOldies was the priority). User wants it back at $50 for better per-order margin — recent $45.98 order shipped free and cost $5 of profit that $50 threshold would have recovered.
- Conversion tracking state: Page View / Add to Cart / Begin Checkout / Purchase all show **Active** in Google Ads, but Purchase shows "No recent conversions" because no real purchase has fired the end-to-end funnel yet. A real test order flips it to "Recording" so we launch with proven end-to-end attribution.

---

## Task 1 — Revert free shipping threshold $35 → $50 (~2 min)

1. Sign in at https://admin.shopify.com → pick 8-Bit Legacy store
2. Settings → **Shipping and delivery**
3. Under **Shipping**, find the "General" shipping profile (the default one) → click **Manage rates** or the profile name
4. In the **Domestic** zone, you'll see two "Economy" rates:
   - **Free Economy** (currently $0.00 on orders **≥ $35**) → click → Edit → change the **Minimum order price** from `$35.00` to **`$50.00`** → Done
   - **Flat Economy** ($6.00 on orders **≤ $34.99**) → click → Edit → change the **Maximum order price** from `$34.99` to **`$49.99`** → Done
5. Click **Save** at the top of the page.
6. Verify: load a product page on 8bitlegacy.com in incognito → add a ~$40 item to cart → confirm shipping shows **$6.00** at checkout (not free). Then add another item to push the subtotal over $50 → shipping should show **$0.00**.

**Gate:** If you can't find the rates or the Save button doesn't clear, STOP and report.

---

## Task 2 — Place $5-10 test order end-to-end (~5 min)

**Goal:** fire the Purchase conversion action end-to-end so Google Ads marks it "Recording" (currently "No recent conversions" despite Active status — means attribution hasn't actually processed a real purchase yet).

**Important:** this is a REAL order with a REAL card. Tristan will refund it afterward from Shopify admin. No ad spend is involved (campaign is paused).

### Steps

1. Open a **fresh incognito window** (no ad blockers) → https://8bitlegacy.com
2. Pick the cheapest product you can find. Good targets:
   - Search "gbc" or "gameboy color" — usually has some $5-10 used game cartridges
   - Or "genesis" — Genesis titles routinely under $10
   - Confirm the product shows as "In Stock" / "Add to cart" (NOT out of stock)
3. Add to Cart → View Cart → **Checkout**
4. Fill in a real email (use Tristan's `tristanaddi1@gmail.com` or a throwaway like `testorder+[timestamp]@gmail.com`)
5. Shipping address: Tristan's real address (so it actually ships if we don't cancel in time). He'll provide.
6. Continue to Payment → enter a REAL card (Tristan's — ask him to type it; don't paste from memory or a password manager)
7. Click **Pay now** → confirm the order page loads ("Thank you, order #10XX")
8. **Screenshot the confirmation page** for the record.

### Immediately after

9. Go to Shopify admin → **Orders** → find the new order
10. **Refund it**:
    - Click the order → scroll to the top right action bar → Refund
    - Refund the full amount
    - Reason: "Test order — internal" (don't pick "customer changed mind" or any customer-facing reason)
    - Click **Refund**
11. The customer email will go out. That's fine — it's Tristan's own email.

### Post-refund

12. Tag the order `test-order` in Shopify admin so future profit reports can exclude it.
13. If the product was a real listing, Tristan should also decide whether to source it from eBay anyway (since a real customer would expect it). For a $5-10 test order, he may choose to just leave it refunded and move on.

**Gate:** If the checkout flow breaks (card declined, Shopify errors, pixel conflicts), STOP and report the exact error. The Purchase tag firing is the whole point of this task — if it doesn't get a real checkout, it won't flip to Recording.

---

## When you're done

1. Write a handoff note at `docs/cowork-session-2026-04-23-final-gates.md` with:
   - Task 1: confirmation that both shipping rates were updated + the incognito checkout verified $6 under $50 / free over $50
   - Task 2: order number, timestamp of payment, timestamp of refund, any screenshots
   - Any unexpected findings

2. Commit + push:
   ```bash
   cd ~/Projects/8bit-legacy
   git add docs/cowork-session-2026-04-23-final-gates.md
   git status  # verify no secrets staged
   git commit -m "Cowork 2026-04-23: shipping $35→$50 + test order for Purchase conversion"
   git push
   ```

3. Tell Tristan in chat: "both gates cleared — ready to flip the campaign." Main session (Claude Code) will then enable `8BL-Shopping-Games` via the Ads API and kick off the daily monitoring cadence.

---

## Success criteria
- [ ] Free shipping threshold = **$50.00** (Shopify settings)
- [ ] Flat rate ($6) applies to orders ≤ **$49.99**
- [ ] Incognito checkout confirms the thresholds work
- [ ] Real test order placed (order # recorded)
- [ ] Order refunded from Shopify admin
- [ ] Handoff doc written + pushed
- [ ] Tristan notified "both gates cleared"
