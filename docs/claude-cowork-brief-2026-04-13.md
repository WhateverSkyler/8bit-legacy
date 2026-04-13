# Claude Cowork Brief — 2026-04-13 (Monday AM, office laptop cowork)

**For:** Claude Code running on Tristan's Mac with browser/UI automation
**From:** Claude Opus 4.6 running on the laptop (same repo, 8bit-legacy)
**Written:** 2026-04-13 09:55 AM EDT
**Goal of this session:** Unblock Google Ads launch (conversion tracking + account linking), ship the pre-approved trust signal changes, and knock out the cart-footer spacing fix while the other Claude handles pricing work in the terminal.

---

## Session start — mandatory

```bash
cd ~/Projects/8bit-legacy
git pull --ff-only
```

If pull fails due to divergence, STOP and tell Tristan — do NOT rebase or force push without explicit permission.

**Then read, in order:**
1. `CLAUDE.md` — project rules
2. `docs/session-handoff-2026-04-12.md` — where the store stands as of last night
3. `docs/ads-pre-launch-checklist.md` — Sections A and D are the tasks below
4. `docs/claude-cowork-brief-2026-04-11.md` — the cart fix (Task 1 there) if it wasn't shipped yet; see Task 4 in this brief
5. This brief

The terminal Claude (running on the laptop) is handling all pricing work in parallel — specifically, refreshing the 1,618 stale loose prices from May 2025 and fixing the last 5 genuine CIB edge cases. **Do NOT run any pricing script or `manage-sales.py`. Do NOT run `search-price-refresh.py`, `full-price-refresh.py`, or `fix-cib-*.py`.**

---

## Ground truth (verified live, 2026-04-13 09:15 AM)

- CIB==Loose pricing bug: **FIXED**. 6,036 of 6,112 multi-variant games correct. 36 residual are false-positive console bundles + 5 edge cases (terminal Claude is fixing the 5 edge cases right now).
- Loose price freshness: 73% refreshed in April 2026, 27% still stale from May 2025 (terminal Claude is handling this in background).
- Google Ads $700 promo credit expires **2026-05-31** (48 days left). Spend must average $14/day to consume the full credit.

---

## Task 1 — Fix Google Ads conversion tracking (PRIORITY: 🔴 CRITICAL, ~20 min)

**Blocker for:** everything ads-related. You cannot launch until all 4 conversion goals are `Configured` (not `Misconfigured`) and the tag has fired real events.

**Full instructions:** `docs/ads-pre-launch-checklist.md` Sections A5 + A6.

**Current state (from 2026-04-11 screenshot):**
- Account `822-210-2291` is linked
- All 7 conversion actions EXIST (Purchase, Begin Checkout, View Item, Add to Cart, Add Payment Info, Search, Page View)
- But all 4 primary goal categories show **Misconfigured** (Add to cart, Begin checkout, Page view, Purchase)
- Purchase, Begin Checkout, Add Payment Info show **Inactive** (tag hasn't fired a recent event)

### 1a — Promote secondary actions to Primary

1. Log in to Google Ads → customer `822-210-2291`
2. **Goals → Conversions → Summary**
3. For each goal row showing `Misconfigured`:
   - Click the row → **Edit goal**
   - Find the secondary action named like `Google Shopping App Add To Cart` (or `Begin Checkout`, `Page View`, etc.)
   - Toggle it to **Primary action**
   - Save
4. Repeat for: **Add to cart**, **Begin checkout**, **Page view** goals
5. Purchase goal already has `Google Shopping App Purchase` as Primary — no change needed
6. While there, categorize the stray `Add Payment Info` conversion action (currently under "Other") into the **Add payment info** goal under Purchase — clears the "categorize your Other conversion actions" warning

### 1b — Fire live events to clear "Inactive"

1. Open https://8bitlegacy.com in an **incognito** window (no ad blockers, no DevTools extensions that strip tags)
2. Fire each event in sequence:
   - Navigate a product page → Page View + View Item
   - Use the store's search bar → Search
   - Click "Add to Cart" → Add to Cart
   - Proceed to checkout, enter email + address → Begin Checkout
   - Enter a real card, then **abandon** (don't complete) → Add Payment Info
3. Wait **2–4 hours** for Google Ads to register
4. Re-check the Conversions page — all 6 events should move from `Inactive` → `No recent conversions` or `Recording`

### 1c — Verify

Screenshot the Conversions page after 2–4 hours showing:
- All 4 goals NOT marked `Misconfigured`
- All 7 conversion actions NOT marked `Inactive`

Save the screenshot path and note in `docs/ads-conversion-tracking-verified-2026-04-13.md` (create it) with a one-line verdict: `GREEN` or `STILL BLOCKED (reason)`.

---

## Task 2 — Re-link Google Ads account (PRIORITY: 🔴 CRITICAL, ~10 min)

**The problem:** The Google & YouTube Shopify app is connected to the wrong Google Ads account. It currently points at `438-063-8976` (under `tristanaddi1@gmail.com`). The target is `822-210-2291` (under `sideshowtristan@gmail.com`).

**This must happen BEFORE any campaign launches.** If the app is pointed at the wrong account, conversions flow to the wrong place and the $700 promo credit is useless.

### Fix — pick ONE path

**Path A (preferred, less disruptive):** Add `tristanaddi1@gmail.com` as admin on `822-210-2291`.
1. Log into `ads.google.com` with `sideshowtristan@gmail.com`
2. Open account `822-210-2291`
3. Admin → Access and security → + icon → **Admin access**
4. Add `tristanaddi1@gmail.com` as admin
5. Accept the invitation email in `tristanaddi1@gmail.com`'s inbox
6. Go back to Shopify → Google & YouTube app → pick account `822-210-2291` from the dropdown (should now be visible)
7. Save

**Path B (fallback):** Disconnect + reconnect the Shopify app using `sideshowtristan@gmail.com`.
1. Shopify admin → Apps → Google & YouTube → uninstall
2. Reinstall from the App Store using `sideshowtristan@gmail.com`
3. Reconnect Merchant Center `5296797260` and Google Ads `822-210-2291`
4. CAUTION: reinstall may re-sync the product feed from scratch, could take 24–72h to re-approve 7,689 products

### Verify

Screenshot the Shopify → Google & YouTube app settings page showing Google Ads account `822-210-2291` connected. Add the verification to the same `docs/ads-conversion-tracking-verified-2026-04-13.md` doc.

---

## Task 3 — Trust signal changes (PRIORITY: 🟡 HIGH, ~15 min, pre-approved)

Tristan has already signed off on these. Just execute. Do NOT ask for re-approval.

### 3a — Free shipping threshold: $50 → $35

**Why:** Closes the gap with DKOldies ($20 threshold). Most Winners list products ($30–$49) now qualify for free shipping — materially affects conversion rate on Shopping ad clicks.

1. Shopify admin → Settings → Shipping and delivery
2. Open the US shipping profile
3. Find the **Free shipping** rate (currently $50 minimum)
4. Edit → change minimum to **$35.00** → Save
5. Add a ~$36 product to cart on the storefront, confirm shipping shows "Free"

### 3b — Return policy: 30 days → 90 days

**Why:** 30 days was unnecessarily conservative vs Lukie Games (90 days) and DKOldies (365 days). Dropship suppliers typically allow 60-day buyer returns; we can stretch to 90 with buyer-funded return shipping on edge cases.

1. Shopify admin → Settings → Policies → Refund policy → edit
2. Replace every instance of `30 day` / `30-day` / `thirty day` with `90 day` / `90-day` / `ninety day`. Save.
3. Check the announcement bar text: Online Store → Themes → Customize → announcement bar. If it hardcodes "30 day returns", update to "90 day returns".
4. Check theme code for any hardcoded `30 day` string: Online Store → Themes → Edit code → search across all files for `30 day`. Update any product page snippets / trust badge rows.
5. Load a product page, verify visible return-window text says 90 days.

### 3c — Enable Google Customer Reviews in Merchant Center

**Why:** Google-native reviews are what unlock seller-rating stars in Shopping ads (at 100+ reviews). Shopify review apps (Loox, Judge.me, Yotpo, Stamped) do NOT feed this — they only render on the storefront, zero algorithmic benefit for ads. **Do NOT install any Shopify review app.** If any are installed (check Apps list), uninstall them.

1. Sign in to Merchant Center `5296797260`
2. Growth → Manage programs → **Customer Reviews**
3. Enable → accept agreement
4. Enable the **Customer Reviews opt-in** on the Shopify checkout:
   - Google & YouTube Shopify app → Settings → look for "Customer Reviews opt-in" toggle → enable
   - If the toggle isn't visible, follow the setup guide that Merchant Center surfaces after enabling (may require a `checkout-post-purchase.liquid` snippet)
5. Don't expect immediate results — star eligibility needs 100+ reviews over 12 months

---

## Task 4 — Cart footer spacing fix (PRIORITY: 🟢 MEDIUM, ~15 min)

**Status check first:** Did the 2026-04-11 cowork session ship the cart fix? Open `https://8bitlegacy.com/cart` with an item in cart. If "Check out" button and Shop Pay/PayPal/G Pay row are cleanly spaced (≥24px gap, both center-aligned on desktop), **skip this task**. Only proceed if the collision is still present.

**Full instructions:** `docs/claude-cowork-brief-2026-04-11.md` Task 1 (complete fix recipe).

**TL;DR of the fix:**
1. Shopify admin → Online Store → Themes → current live theme → **Duplicate** (always work on a draft)
2. On the duplicate → Edit code → `assets/base.css` → scroll to bottom, append the CSS block from the 2026-04-11 brief (lines 61–89)
3. Preview the draft cart page (desktop + mobile)
4. If good → Publish the draft

---

## Task 5 — 🚨 Product page variant price display bug (PRIORITY: 🔴 CRITICAL, investigate + fix)

**Do this AFTER Tasks 1–4 are shipped.** This is the biggest find of the day.

### The bug

Backend is correct — each multi-variant product has separate Loose and CIB prices (verified 99.1% of 6,081 retro games have CIB > Loose, confirmed via live Shopify API 2026-04-13 10:58 AM). But **on the storefront product page, the displayed price does NOT change when the customer toggles between "Game Only" and "Complete (CIB)"** variants. Same number shown for both.

Tristan confirmed this live at 11:05 AM on `Phantasy Star Online Episode I & II - Gamecube Game` (`phantasy-star-online-episode-i-ii-gamecube-game`). Backend: Game Only $162.99, Complete (CIB) $303.99. Frontend: shows the same price regardless of variant selection.

This means every customer shopping the store sees "no premium for CIB" — the entire CIB pricing strategy is invisible. Almost certainly a major conversion killer and a direct contributor to the cold-traffic diagnosis in `docs/google-ads-launch-plan-v2.md`.

### Reproduce

1. Open https://8bitlegacy.com/products/phantasy-star-online-episode-i-ii-gamecube-game in an incognito window
2. Note the price shown with "Game Only" selected
3. Switch the variant selector to "Complete (CIB)"
4. Confirm: price display does NOT update (stays at the Game Only price or a wrong value)

Repeat on 2-3 more random products (pick from homepage Deals of the Week or Nintendo/Sony Classics grids) to confirm it's theme-wide, not product-specific.

### Diagnose

The theme is 8bit-legacy (Shopify theme id `23583179538466`). Likely suspects:

1. **`product.liquid` / `product-form.liquid` / `price.liquid`** — the price element isn't listening for the `variant:change` JavaScript event
2. **Theme's variant selector JS** — the `<variant-radios>` / `<variant-selects>` custom element isn't firing the price-update event
3. **Cached JSON `[data-product-json]`** — the variant data block at page load may have all variants rendered with the same price (theme bug in the Liquid layer)
4. **Tree-shaken JS** — a previous theme edit may have removed the price-refresh logic

### Investigate (Shopify admin → Online Store → Themes → Edit code)

1. Open the live theme's **snippets/** and **sections/** — search for `product-price`, `price-update`, `variant:change`, `variantChange`
2. Open the `product.liquid` template and the product-detail section. Find where `{{ current_variant.price }}` is rendered.
3. Open `assets/global.js` / `assets/theme.js` (whatever name the theme uses) and grep for `price` and `variant`. Confirm there is an event listener that reads `e.detail.variant.price` (or similar) and writes it to the price element.
4. Check `[data-product-json]` in a live product page — inspect the script tag that contains the product JSON. Confirm each variant actually has its own price in that block (it should — the backend data is right, but a theme bug could be flattening it).
5. Open the Dawn theme baseline at https://github.com/Shopify/dawn — diff the expected structure against the 8bit-legacy theme to see what was modified.

### Fix

Once root cause is pinned, the fix is likely one of:

- **If a JS event listener is missing or broken:** add/restore the listener, usually in `assets/product-form.js` or similar. Pattern: on `variant:change` event, update the `[data-product-price]` element's innerText to `formatMoney(e.detail.variant.price)`.
- **If Liquid is flattening variants:** fix the JSON block in `product.liquid` to emit each variant's real price instead of a single shared price.
- **If the price element itself isn't getting updated:** ensure the element has the correct data attribute the JS listens for (e.g. `data-product-price`), and that the listener has the right selector.

### Test + ship

1. **Always duplicate the live theme first** (Online Store → Themes → ⋯ → Duplicate). Work on the duplicate.
2. Apply the fix to the duplicate.
3. Preview on desktop (1440w) and mobile (375w):
   - Click "Game Only" → confirm correct loose price displays
   - Click "Complete (CIB)" → confirm CIB price displays (higher)
   - Toggle back → confirm it updates again
   - Test 5 different products across Nintendo, Sony, and Pokemon collections
4. Also verify **cart + checkout** show the correct price after variant change (the bug may extend past the product page if it's a JSON flattening issue).
5. If all green → publish the duplicate theme.

### If it's beyond a quick fix

If this is a deeper template rewrite than ~30 min, **stop** and write the diagnosis to `docs/variant-price-display-bug-2026-04-13.md` with:
- Root cause
- Proposed fix approach with complexity estimate
- Any files that need changing
- Whether we should keep searching OR punt to a Shopify theme dev

Then commit + push and let Tristan decide next steps.

### Impact

This is likely the single biggest conversion lever on the site. Fixing it could materially move the 22.7% margin / $101 AOV math before any ads spend happens. Worth prioritizing over anything in the Google Ads launch plan if the fix is more than trivial — a correct CIB price display is more valuable than any ad traffic.

---

## Hard guardrails

- **Do NOT run anything in `scripts/`** — terminal Claude owns those.
- **Do NOT run `manage-sales.py` or anything with `--apply`**.
- **Always duplicate themes before editing** — never edit the live theme directly.
- **Never commit secrets** — `.env.local`, `.env`, tokens, passwords.
- **If a decision needs Tristan** — ask him, don't guess.
- **If a task is already done** (cart fix) — skip it, note it in the handoff.

---

## When you're done

1. Commit any repo changes:
   ```bash
   git add docs/
   git status   # verify no secrets / no pricing script changes
   git commit -m "Cowork 2026-04-13: Google Ads conversion tracking + trust signals + homepage fixes"
   git push
   ```

2. Write a handoff doc: `docs/cowork-session-2026-04-13.md` with:
   - What shipped (per task, GREEN or BLOCKED + reason)
   - Screenshots referenced by path
   - What still needs Tristan (if anything)
   - Whether the Google Ads campaigns can now move to Section F of the pre-launch checklist

3. Tell Tristan in the session what to verify in Google Ads (he's the only one with account access for the 2–4 hour re-check).

---

## Success criteria

- [ ] All 4 Google Ads conversion goals show `Configured` (not `Misconfigured`)
- [ ] All 6 test events fired at least once (Page View, View Item, Search, Add to Cart, Begin Checkout, Add Payment Info)
- [ ] Shopify Google & YouTube app is connected to Google Ads account `822-210-2291`
- [ ] Free shipping threshold = $35 in Shopify settings
- [ ] Return policy text = 90 days everywhere visible
- [ ] Google Customer Reviews enabled in Merchant Center `5296797260`
- [ ] Cart page has clean spacing (if not already fixed)
- [ ] Product page variant selector updates displayed price when switching Loose ↔ CIB
- [ ] Handoff doc written and pushed

Shortest path to ads running tomorrow: Tasks 1 + 2 green → Tristan can build the two campaigns in Section F → flip switches after content is scheduled (Section G).
