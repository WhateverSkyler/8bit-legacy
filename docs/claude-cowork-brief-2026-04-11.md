# Claude Cowork Brief — 2026-04-11 (cart spacing + site audit + Shop app dispute check)

**For:** Claude running on Tristan's MacBook with browser/UI automation capability
**From:** Claude Opus 4.6 on Linux desktop (same repo, 8bit-legacy)
**Written:** 2026-04-11 afternoon
**Context:** Tristan spotted a layout bug on the cart page where the "Check Out" button visually collides with the Shop Pay / PayPal / G Pay express-checkout row. He suspects there are similar layout bugs scattered across the site. Separately he recalls a past false chargeback that temporarily blocked him from selling on the Shop app and wants confirmation that's resolved.

---

## Session start — pull first

```bash
cd ~/Projects/8bit-legacy   # wherever the repo lives on Mac
git pull --ff-only
```

There are uncommitted docs on Linux as of writing this brief. If `git pull` reports nothing new, ask Tristan to push from Linux first, or run your own work on a branch and rebase later. Do NOT force push.

**Key context docs:**
- `docs/google-ads-launch-plan-v2.md` — the campaign we're trying to launch. The cart page bug is a direct blocker for ads because clicks land on a broken checkout.
- `docs/ads-pre-launch-checklist.md` — Section C (homepage trust fixes) is adjacent to the work in this brief.
- `~/.claude/projects/-home-tristan-Projects-8bit-legacy/memory/project-website-todos.md` — task list reference.
- `Screenshot_20260411_135833.png` in `~/Screenshots/` — the reference screenshot showing the cart collision.

---

## Task 1 — Fix the cart page button spacing (CRITICAL, 15 min)

### The bug (from desktop Claude's analysis of the live HTML + CSS)

On `https://8bitlegacy.com/cart`, the theme renders two sibling containers inside `.cart__footer`:

```html
<div class="cart__ctas">
  <button class="cart__checkout-button button">Check out</button>
</div>
<div class="cart__dynamic-checkout-buttons additional-checkout-buttons">
  <!-- Shopify dynamic-checkout wallet grid: Shop Pay, PayPal, G Pay -->
</div>
```

The theme CSS (`component-cart.css`) produces two visible problems:

1. **Too tight spacing between the two divs.**
   - Mobile: `.cart__dynamic-checkout-buttons { margin-top: 0 }` → zero gap
   - Desktop: `.cart__dynamic-checkout-buttons { margin-top: 1rem }` → 16px gap, not enough with the button's drop shadow
   - Result: the orange "Check Out" button visually collides with the top of the wallet row.

2. **Alignment staircase at ≥750px.**
   - At desktop, `.cart__ctas` becomes `display: flex; gap: 1rem` but does not set `justify-content` → defaults to `flex-start`, so the button left-aligns inside its container
   - The wallet grid meanwhile has `[data-shopify-buttoncontainer]{justify-content:flex-end}` → right-aligns
   - Result: Check Out left, wallets right, diagonal staircase look

### The fix

Shopify admin → Online Store → Themes → current live theme → **Customize** (NOT "Edit code" yet — we want to work on a draft first).

1. **Duplicate the live theme to a draft** (three-dot menu → Duplicate). Work on the duplicate. Publish only after we verify the fix.

2. On the duplicate, go to **Edit code** → `assets/base.css` (or whichever stylesheet the theme loads last globally; Dawn-based themes typically have `base.css` as the trailing sheet). Scroll to the bottom and append:

```css
/* 2026-04-11 — fix cart footer Check Out + express checkout collision */
.cart__dynamic-checkout-buttons,
.cart__dynamic-checkout-buttons.additional-checkout-buttons {
  margin-top: 2rem !important;
}

.cart__ctas {
  justify-content: center !important;
}

.cart__ctas > .cart__checkout-button {
  width: 100% !important;
  max-width: 36rem !important;
  margin: 0 auto !important;
}

@media screen and (min-width: 750px) {
  .cart__dynamic-checkout-buttons,
  .cart__dynamic-checkout-buttons.additional-checkout-buttons {
    margin-top: 2.5rem !important;
  }
  /* Right-align the express-checkout buttons with the Check Out button */
  [data-shopify-buttoncontainer] {
    justify-content: center !important;
  }
}
```

3. Save.

4. **Preview the draft** on the cart page with a real item in the cart (use any $30+ retro game from the Winners list so there's a subtotal). Verify:
   - Check Out button is full-width (or ≤36rem) and center-aligned
   - Clear vertical gap (≥24px) between Check Out and the wallet row
   - Shop Pay / PayPal / G Pay are also center-aligned so the column feels unified
   - Mobile view (375px viewport) renders the same way with the gap

5. If preview looks good → **Publish the draft theme**.

### If the base.css approach fails or feels fragile

Alternative: put the CSS in a new file at `assets/custom-cart-fix.css` and `{% render 'custom-cart-fix' %}` style-inject it via `layout/theme.liquid` right before `</head>`. But appending to `base.css` is simpler and harder to lose.

### Why the `!important`s

The theme's default CSS uses specific selectors and the `!important`s here defeat media-query-scoped re-declarations. Yes, !important is usually bad practice, but we're on a closed theme we don't want to fork, and the theme's own CSS uses !important liberally (e.g. `border-radius:0!important` on the wallet buttons — see existing CSS). Adding targeted !important overrides is the pragmatic move.

---

## Task 2 — Site-wide layout/spacing audit (30–45 min)

Tristan believes there are similar layout bugs elsewhere. Audit these pages and screenshot anything that looks broken, then fix with the same targeted-CSS approach if the issue is obviously in the theme.

### Pages to audit (desktop 1440w AND mobile 375w for each)

1. **Homepage** `/` — already has known issues (stale countdown timer, empty banner sections, GameCube block to delete). Focus on any NEW layout issues not in `docs/ads-pre-launch-checklist.md` Section C.
2. **Cart** `/cart` — verify the Task 1 fix landed, no regressions.
3. **Product detail page** — visit `/products/galerians-game-only-ps1-game` (or any other Winners list product). Check:
   - Variant selector spacing
   - Add to Cart + Buy with Shop Pay button row
   - Trust badges row (free shipping, warranty, etc.)
   - Related products / recommended products strip below the fold
4. **Collection page** — `/collections/all` or `/collections/nintendo-64-games`. Check:
   - Filter + sort dropdown row alignment
   - Product card grid spacing + consistency
   - Load more / pagination spacing
5. **Checkout page** — `/checkouts/...` (you'll need to have a real item in cart to get here). Check for express-checkout-vs-native-checkout button collisions similar to the cart bug.
6. **Search results** — `/search?q=mario` — autocomplete dropdown, results layout
7. **Account login** `/account/login` — form spacing, field alignment
8. **Policies pages** — `/policies/refund-policy`, `/policies/shipping-policy`, `/policies/privacy-policy` — any text-overflow or weird line-height issues
9. **Footer** (on every page) — newsletter form, social icons row, payment method icons row

### What counts as a "fix now" bug vs a "flag for later"

**Fix now (same approach as Task 1 — append targeted CSS to base.css):**
- Overlapping elements
- Buttons running off the edge of the viewport
- Text obviously cut off / truncated without ellipsis
- Image placeholders showing broken-image icons
- Forms where the submit button is inaccessible

**Flag for later in this brief's output section (don't touch):**
- Typography/font-size preferences (Tristan will judge)
- Color/contrast concerns (could be brand-intentional)
- "Could look nicer" — subjective
- Anything requiring template/Liquid changes (that's a bigger refactor)

### For each bug found

Add a section at the bottom of this brief (or a sibling doc `docs/site-audit-2026-04-11.md`) with:
- Page path
- Desktop or mobile (or both)
- Screenshot file path
- DOM + CSS diagnosis (1–2 sentences)
- Fix applied (the CSS snippet) or "flagged, not fixed"

---

## Task 3 — Shop app / chargeback dispute status check (10 min)

Tristan recalls that a false chargeback was accepted by the bank and he was at least temporarily blocked from selling on the Shop app. He wants confirmation that's resolved.

**Desktop Claude could not verify this via the Shopify Admin API** — the dashboard access token doesn't have `read_shopify_payments_disputes` or `read_shopify_payments_payouts` scope (both returned 403). The `docs/ecommerce-infrastructure-audit-2026-04-06.md` Section 5 notes the prior "Action needed" on the Shop channel was actually just the CIB-out-of-stock issue, NOT a dispute flag. There is no mention of a chargeback anywhere in the repo or memory.

### What to check in Shopify admin (browser automation)

1. **Shopify admin → Finances → Shopify Payments → Disputes**
   - If the page exists and is accessible, count open disputes, won disputes, lost disputes over the last 90 days
   - Screenshot any entry showing "Lost" or "Accepted" status
   - Note the dispute ID + amount + product, if any

2. **Shopify admin → Settings → Payments → Shopify Payments → Payout schedule**
   - Confirm payouts are NOT on hold
   - Look for any "Action required" or "Verification needed" banner
   - Note the next payout date

3. **Shopify admin → Sales channels → Shop**
   - Open the Shop channel admin view (Catalog, Analytics, etc.)
   - Look for any seller status banner, "limited", "paused", "review" language
   - If it loads an iframe that errors with `InvalidStateError`, that's the known Shopify admin routing quirk (per `ecommerce-infrastructure-audit-2026-04-06.md`) — not a merchant-facing issue
   - Take a screenshot of the main Shop dashboard

4. **Shopify admin → Home dashboard**
   - Check for any top-banner alerts ("Your store requires attention", "Payment verification needed", etc.)
   - Screenshot any banner that appears

5. **Shopify admin → Orders → filter by Financial status = Disputed or Voided**
   - List any disputed orders
   - For each, note: order number, customer name (redact to last initial), amount, current status

### What to report

At the bottom of this brief or in `docs/shop-app-dispute-check-2026-04-11.md`, write:

```
## Shop app dispute status (2026-04-11)

- Open disputes count: X
- Recent disputes (last 90 days): [list or "none"]
- Payouts on hold: yes / no
- Shop channel status: healthy / action needed / unknown
- Any admin dashboard banners: [list or "none"]
- Overall assessment: [one-sentence judgment]
```

If everything is clean, we can close this concern and Tristan can stop worrying about it. If there IS a lingering dispute, we document it and figure out if Tristan needs to contact Shopify support to appeal.

---

## Task 4 — Trust signal changes (Tristan-approved, 15 min)

Tristan has signed off on these changes — just execute them in Shopify admin. Do NOT ask for further confirmation.

### 4a. Free shipping threshold: $50 → $35

**Why:** Closes the gap with DKOldies (who offer free shipping at $20). At $50 we were 2.5x worse; at $35 we're only 1.75x worse and most of the Winners list ($30–$49 retro games) now qualifies for free shipping, which materially affects conversion rate on Google Shopping clicks.

**How:**
1. Shopify admin → Settings → Shipping and delivery
2. Click the shipping profile that applies to US orders
3. Find the "Free shipping" rate (currently $50 minimum)
4. Edit → change minimum order price to **$35.00**
5. Save

**Verify:** Add a ~$36 product to cart and confirm shipping shows "Free" at checkout.

### 4b. Return policy: 30 days → 90 days

**Why:** Matches Lukie Games (another retro-games dropshipper who's figured out the math). Still dropship-safe because our eBay supplier refund windows are typically 60 days, which we can stretch to 90 with buyer-funded return shipping on a case-by-case basis. The 30-day policy was unnecessarily conservative and made us look amateur vs DKOldies (365 days) and Lukie (90 days).

**How:**
1. Shopify admin → Settings → Policies → Refund policy → edit
2. Find all instances of "30 days" / "30-day" / "thirty days" and replace with "90 days" / "90-day" / "ninety days"
3. Save the refund policy text
4. Check the announcement bar: Online Store → Themes → Customize → announcement bar section. If the bar text hardcodes "30 day returns", change to "90 day returns".
5. Check product page footer / trust badges row: some themes render the return window in a hardcoded section. If present in theme customizer or in a Liquid snippet you can spot, update.
6. Search theme code for "30 day" in the edit-code view (Shopify admin → Themes → Edit code → search). Update any hardcoded occurrences.

**Verify:** Load a product page and confirm any visible return-window text says 90 days.

### 4c. Reviews — DO NOT install Shopify Product Reviews

**Reversal from earlier draft:** Tristan does not want a Shopify review app installed. His reasoning: reviews on a 10,000+ product used-goods store make the business look *smaller* than it is (most products will have 0 reviews forever because inventory is sparse and non-repeating), and Shopify review apps give approximately zero algorithmic benefit for Google Shopping ads since they're not Google-native reviews.

**Do instead: Enable Google Customer Reviews** (this is a real Google program, free, lives inside Merchant Center):

1. Sign in to Merchant Center 5296797260
2. Growth → Manage programs → Customer Reviews → Enable
3. Accept the agreement
4. Enable the "Customer Reviews opt-in" on the Shopify checkout:
   - The Google & YouTube Shopify app should have this toggle under its settings. Find it and turn it on.
   - If the toggle isn't visible in the app, add the Google Customer Reviews opt-in module snippet to `checkout-post-purchase.liquid` / order confirmation per the Merchant Center setup guide that surfaces after enabling.
5. Leave it running. At 100 store reviews + 12 months of data, the seller-rating star extension becomes eligible to show on Google Shopping ads — that IS the algorithmic benefit Tristan was asking about.

**Why this is different from a Shopify review app:** Google Customer Reviews feeds Google's own seller rating system directly. Shopify app reviews (Loox, Judge.me, Shopify Product Reviews) do not; they only render on the storefront. Seller ratings in Shopping ads are a real conversion lift and Google gates them behind their own review program.

**Do NOT install:** Loox, Judge.me, Shopify Product Reviews, Yotpo, Stamped, etc. If any of these are already installed, uninstall them — Tristan wants them gone.

---

## Commit + push when you're done

Per `CLAUDE.md` sync rules, commit and push from Mac when you finish so desktop Claude can see the work:

```bash
git add -A   # or specific files
git commit -m "Fix cart footer button spacing; site audit + Shop app dispute check

- Cart page: resolved Check Out button collision with express checkout row
- Site-wide audit: [X issues fixed, Y flagged]
- Shop app dispute check: [one-sentence summary]

Co-Authored-By: Claude <noreply@anthropic.com>
"
git push
```

Drop a line in `docs/handoff-2026-04-11-evening.md` (create if it doesn't exist) summarizing what you did so the next session can pick up.

---

## Scope guardrails

- **Do NOT** touch pricing, product content, order data, or scheduled jobs. This brief is CSS + audit + one dispute-status report only.
- **Do NOT** publish any theme changes that affect pages outside the audit scope without Tristan's approval.
- **Do NOT** refactor. If a fix would require changing Liquid templates or adding new sections, flag it and stop.
- **Do** err on the side of asking before publishing the draft theme. The duplicate is free insurance.

---

## Success criteria

- [ ] Cart page Check Out button no longer overlaps the express-checkout row on desktop or mobile
- [ ] Draft theme published (or left as draft with clear handoff if you want Tristan to review first)
- [ ] Site audit of the 9 pages above, screenshots of any bugs found, fixes applied where the CSS-only pattern fits
- [ ] Shop app dispute status definitively answered (open / closed / unknown-with-reason)
- [ ] Free shipping threshold lowered to $35 in Shopify settings (Task 4a)
- [ ] Return policy text updated to 90 days in Shopify policies + theme (Task 4b)
- [ ] Google Customer Reviews enabled in Merchant Center 5296797260 (Task 4c)
- [ ] Commit + push from Mac, handoff note written
