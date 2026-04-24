# Claude Cowork Brief — 2026-04-24 — Final Pre-Launch Gates (v2, consolidated)

## The task in one sentence

Four small browser tasks that clear the last pre-launch gates between the paused Google Ads campaign `8BL-Shopping-Games` and go-live. All four are browser-only — no code, no API, no money moved beyond a refunded $5-10 test order.

## Hard guardrails

- **DO NOT touch Google Ads.** Don't edit the campaign, don't enable it, don't touch budgets or bids. Main session will flip it via API after you confirm these tasks are done.
- **DO NOT commit secrets.**
- If anything unexpected, STOP and report — don't improvise.

## Context

- Store: https://8bitlegacy.com (Shopify admin: admin.shopify.com → 8-Bit Legacy)
- Merchant Center: account 5296797260 — https://merchants.google.com
- Google Ads: account 822-210-2291 (read-only for you — hands off)
- 4 pre-launch gates: shipping threshold, test order, MC diagnostics, CIB exclusion feed
- Preflight check is currently 18/18 green (main session verified 2026-04-24 10:00 ET)

---

## Task 1 — Revert free shipping threshold $35 → $50 (~2 min)

**Why:** a recent $45.98 order shipped free and cost $5 of profit that a $50 threshold would have recovered. The $35 threshold from 2026-04-13 was to compete with DKOldies; user has since decided per-order margin matters more.

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

## Task 2 — Free test order via 100%-off code (~8 min)

**Why:** fire the Purchase conversion action end-to-end so Google Ads marks it "Recording" (currently "No recent conversions" despite Active status — means attribution hasn't actually processed a real purchase yet). Launching blind on attribution risks burning spend we can't measure.

**Goal state:** an order reaches Shopify's `checkout_completed` event at $0.00 total with no card used. That fires the Google Ads Purchase tag → "Recording" in Ads UI within 2-4h.

### Step 2a — Create a 100%-off one-time discount code

1. Shopify admin → **Discounts** → **Create discount** → **Amount off products**
2. **Method:** Discount code
3. **Code:** `TESTZERO-[YYYYMMDD]` (replace with today's date, e.g. `TESTZERO-20260424`) — randomize if you want
4. **Types:** Percentage → **100%**
5. **Applies to:** Specific products → pick ONE cheap in-stock product (search `gbc`, `genesis`, `atari` — aim for $5–15 list price so the discount amount stays small in reports). Confirm the product shows "Active" and "In stock."
6. **Minimum purchase requirements:** None
7. **Customer eligibility:** All customers
8. **Maximum discount uses:**
   - ☑ Limit number of times this discount can be used in total → **1**
   - ☑ Limit to one use per customer
9. **Combinations:** check **Free shipping discounts** so it combines cleanly
10. **Active dates:** Start now. End 24h later (safety — no dangling 100%-off code in the wild).
11. **Save**.

### Step 2b — Create an automatic free-shipping discount (if not already)

1. Discounts → **Create discount** → **Free shipping**
2. **Method:** Automatic
3. **Title:** `Test order free shipping` (Tristan will delete after)
4. **Countries:** United States
5. **Minimum purchase requirements:** None
6. **Combinations:** check **Amount off products discounts**
7. **Active dates:** Start now, end 24h later
8. **Save**.

If a free-shipping discount already exists as "Automatic" and is active, skip this — the order will just stack the $50 threshold rule from Task 1 with the manual code.

### Step 2c — Place the order

1. Open a **fresh incognito window** (no ad blockers) → https://8bitlegacy.com
2. Add the SAME product you picked in Step 2a to the cart.
3. **Checkout.** Use Tristan's real email (`tristanaddi1@gmail.com`).
4. Shipping address: Tristan's real address (he'll paste in chat).
5. Apply the discount code `TESTZERO-[YYYYMMDD]`.
6. **Confirm cart shows $0.00 product + $0.00 shipping = $0.00 total.** If it shows any non-zero total, **STOP and report** — don't pay; Shopify shouldn't ask for a card on $0 orders, so a non-zero total means one of the discounts didn't apply.
7. Place order. Order confirmation should load.
8. Screenshot the confirmation page.

### Step 2d — Don't fulfill; just tag

1. Shopify admin → Orders → find the new order.
2. Tag it `test-order`.
3. **Do NOT ship.** The order has $0 paid; there's nothing to refund. Cancel the order from the admin (reason: "other", note: "internal test for Google Ads Purchase conversion").
4. Delete the two discount codes you created (Step 2a + optional 2b) so they don't sit around live.

**Gate:** If checkout demands a card after discounts apply, or the order doesn't show in Shopify Orders within 60 seconds, STOP and report. The pixel can't fire if checkout didn't complete.

---

## Task 3 — Merchant Center Diagnostics re-check (~3 min)

**Why:** last audit was 2026-04-16 (8 days ago). Disapproval spikes caused by silent feed changes can sink the whole campaign — MC won't serve disapproved items. Needs a fresh look before we flip.

1. Go to https://merchants.google.com/ → pick account **5296797260** (8-Bit Legacy)
2. Left nav → **Products** → **Diagnostics**
3. Record the top-line numbers in your handoff note:
   - Account-level issues: should be **0**. If any exist, read them and capture full text.
   - Item-level issues: expect < 200 in "Warnings" and < 50 in "Errors" across the ~12K catalog.
4. If there's a big recent change (spike in errors, specific category disapproved), **STOP and report** — do not proceed to Task 4 until main session has eyes on it.
5. Also open **Products → Overview** and confirm the green "Shopping ads" program chip still shows Active (not "Paused" / "Disapproved").

**Gate:** If account-level issues exist or errors jumped dramatically vs the 2026-04-16 baseline (~40 errors, all minor), STOP and report.

---

## Task 4 — Upload CIB exclusion supplemental feed (~5 min)

**Why:** the Shopify feed emits both Game Only and CIB variants. Ads would auction on the higher CIB price (~$150+), hurting CTR vs DKOldies who advertise Game Only-equivalent prices. Strategy says **advertise Game Only only**. The supplemental feed marks each CIB `item_id` with `excluded_destination=Shopping_ads`.

**File already generated + committed:** `data/merchant-center-cib-exclusion.csv` in the repo (~6,088 rows).

1. Go to https://merchants.google.com/ → account 5296797260
2. Left nav → **Products** → **Feeds**
3. Click **+ Add supplemental feed**
4. Name: `CIB Shopping Exclusion`
5. Country: **United States**. Language: **English**.
6. Method: **Upload file** → select the CSV at `~/Projects/8bit-legacy/data/merchant-center-cib-exclusion.csv`
7. **Target primary feeds:** select the Shopify feed (it's the only primary).
8. Save.

Propagation takes 24–48h to fully apply. That's fine — we'll launch in parallel; worst case the first day or two has some CIB variants in the auction pool (suboptimal but not catastrophic).

**Gate:** if the UI refuses to accept the supplemental feed format, **STOP and report** the exact error. Merchant Center Next has rejected supplemental feeds on Merchant-API primary feeds before (known issue from a prior session). If it happens, we accept the residual risk and flag to revisit in 14 days.

---

## When you're done

1. Write a handoff note at `docs/cowork-session-2026-04-24-final-gates.md` with:
   - Task 1: confirmation that both shipping rates were updated + the incognito checkout verified $6 under $50 / free over $50
   - Task 2: order number, timestamp of payment, timestamp of refund, any screenshots
   - Task 3: MC Diagnostics error counts + any account-level issues copied verbatim
   - Task 4: feed upload confirmation (supplemental feed name + date), or "UI rejected, residual accepted" if it hits the known blocker
   - Any unexpected findings

2. Commit + push:
   ```bash
   cd ~/Projects/8bit-legacy
   git add docs/cowork-session-2026-04-24-final-gates.md
   git status  # verify no secrets staged
   git commit -m "Cowork 2026-04-24: shipping $50, test order, MC diag + CIB exclusion"
   git push
   ```

3. Tell Tristan in chat: **"all four gates cleared — ready to flip the campaign."**  The main session (Claude Code) will then enable `8BL-Shopping-Games` via the Ads API and start the daily monitoring cadence.

---

## Success criteria

- [ ] Task 1: Free shipping threshold = **$50.00**; flat $6 applies to orders ≤ **$49.99**; incognito verified
- [ ] Task 2: $0.00 test order placed using 100%-off code + free shipping, cancelled and tagged `test-order`, both discount codes deleted
- [ ] Task 3: MC Diagnostics numbers captured; no account-level issues
- [ ] Task 4: CIB supplemental feed uploaded (or residual accepted if UI blocks it)
- [ ] Handoff doc written + pushed
- [ ] Tristan notified "all four gates cleared"
