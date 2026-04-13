# Claude Cowork Brief — 2026-04-13 (Monday AM, office laptop cowork)

**For:** Claude Code running on Tristan's Mac with browser/UI automation
**From:** Claude Opus 4.6 running on the laptop (same repo, 8bit-legacy)
**Written:** 2026-04-13 09:55 AM EDT
**Goal of this session:** Unblock Google Ads launch (conversion tracking + account linking), ship the pre-approved trust signal changes, and knock out two homepage/cart fixes while the other Claude handles pricing work in the terminal.

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

## Task 5 — Delete 2 empty homepage banner sections (PRIORITY: 🟢 MEDIUM, ~5 min)

**The problem:** Two `bs_banner_three_image` sections render at 0px height between Deals of the Week → GameCube and GameCube → Nintendo Classics. They're placeholder banner slots that were never populated. They create awkward whitespace that makes the homepage feel "half-finished" (per Tristan's own words).

**Full context:** `docs/homepage-redesign-notes.md` Issue 1.

1. Shopify admin → Online Store → Themes → Customize
2. Homepage → scroll the sections panel on the left
3. Find the two empty sections with keys:
   - `bs_banner_three_image_cxQzxU` (between DotW and GameCube)
   - `bs_banner_three_image_nX4pqz` (between GameCube and Nintendo Classics)
4. Click each → three-dot menu → **Remove section**
5. Preview the homepage — flow should be: Hero → Platform icons → Deals of the Week → GameCube → Nintendo Classics → Sony Classics → Footer
6. Save / Publish

Do NOT touch any other homepage section. Issues 2–5 from `homepage-redesign-notes.md` are parked.

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
- [ ] Two empty homepage banner sections deleted
- [ ] Handoff doc written and pushed

Shortest path to ads running tomorrow: Tasks 1 + 2 green → Tristan can build the two campaigns in Section F → flip switches after content is scheduled (Section G).
