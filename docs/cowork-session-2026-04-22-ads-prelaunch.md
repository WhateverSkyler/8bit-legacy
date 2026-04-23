# Cowork Session — 2026-04-22 — Ads Pre-Launch Gates

**Brief:** `docs/claude-cowork-brief-2026-04-22-ads-prelaunch.md`
**Goal:** Clear 5 pre-launch gates so `8BL-Shopping-Games` can flip from Paused → Enabled.
**Outcome:** BLOCKED — 3 of 5 gates green, 1 blocked (CIB feed), 1 needs time-delayed verification (conversions).
**Campaign status at end of session:** Still Paused (per guardrail).

---

## Final recommendation

**DO NOT ENABLE YET.** Two gates remain open:

1. **Task 2 (CIB exclusion feed)** — blocked on Merchant Center UI. Needs alternative delivery path (API push or MC automation rule). Without this, Shopping ads can match on CIB variants, and if a shopper clicks a CIB listing they'll land on a $80–$300 product vs. the $25 game-only variant the ad implied. Not catastrophic (CIB variants are purchasable and correctly priced), but it undermines ad/LP price match and hurts conversion rate + MC quality score.
2. **Task 4 (conversion goal verification)** — requires ~2-4h wait window after test events before Google Ads shows goals as Recording. Earliest re-check: **~2026-04-22 22:00 EDT**. Events fired starting ~19:53 EDT (see Task 3).

Once (1) is resolved via an alternative channel and (2) shows all 4 required goals Recording or No-recent-conv, the campaign is safe to enable.

---

## Task 1 — Merchant Center diagnostics audit — ✅ GREEN

Merchant Center Next account `5296797260` (8bitlegacy@gmail.com linkage, authed via tristanaddi1@gmail.com).

| Metric | Value |
|---|---|
| Total products | 12,272 |
| Approved (showing on Google) | 12,000 |
| Not showing on Google | 20 |
| Shopping ads status | **Active** |
| Account-level issues | **None** |

**Top 3 item-level disapproval reasons** (from Diagnostics → Issues):
1. Invalid image encoding — 204 items (cosmetic / fixable later; mostly long-tail)
2. Sexual interests — 25 items
3. Restricted adult content — 25 items

Gate cleared easily: <50 Shopping-ads disapprovals (20), no account issues, Shopping ads Active. The 204 image-encoding items are not Shopping-ads-disapprovals — they're item-level warnings on other destinations. Non-blocking for launch.

Suggested cleanup post-launch: batch-fix the sexual/restricted items (likely Pokemon cards mis-classified by MC's moderation on certain artwork) by adjusting product title or attribute. Not urgent.

---

## Task 2 — Upload CIB exclusion supplemental feed — 🔴 BLOCKED

**File:** `data/merchant-center-cib-exclusion.csv` (6,088 rows, format `id,excluded_destination` = `Shopping_ads`).

**Format sanity check: ✅ PASS.** Spot-checked two CIB offer IDs pulled from MC's product list:
- Zatch Bell CIB → `shopify_US_7956823048226_43794354536482` — present in CSV ✓
- Super Smash Bros CIB → `shopify_US_7956827504674_43794350309410` — present in CSV ✓

Format `shopify_US_<productId>_<variantId>` matches MC's offer IDs exactly. No regenerator re-run needed.

### Why blocked

Merchant Center **Next** (the new UI) does NOT expose a path to add a file-based supplemental feed when the primary feed is a Merchant API-backed source (which ours is — the Google & YouTube Shopify app pushes via API). Specifically:

- **Products → Data sources → Add product source** only offers: Connected platforms (Shopify), Content API, Google Sheets, Schedule fetch, File upload — but "File upload" is gated behind "create a new primary feed" flow (`createPrimaryFeed` URL), accepts only `.txt/.xml/.tsv`, and cannot target an existing Merchant-API primary as a supplement.
- The three-dot menu on the existing Shopify primary feed shows only "Edit countries" / "Delete source" — no "Add supplemental feed" option.

Per the guardrail "don't improvise a workaround," I stopped rather than trying to force a new primary feed alongside the Shopify one.

### Suggested alternatives (pick one)

1. **MC Automation Rules** (Products → Rules) — create a rule targeting all CIB variants (e.g., match on `title contains "Complete (CIB)"` or `item_group_id` pattern) and set `excluded_destinations: Shopping_ads`. This works without a feed, per-product. Need to verify the Shopify app's pushed products have a matchable attribute though.
2. **Merchant API push** — have main session hit the Merchant API's `supplementalDataSources.create` endpoint directly (outside the UI) and push the CSV that way.
3. **Shopify-side tag** — tag the CIB variants in Shopify with something the Google & YouTube app excludes from Shopping ads. Depends on what the Shopify app respects.
4. **Classic MC (temporary)** — if Classic UI still accepts the upload for this account, use that. Might be deprecated for new-only accounts.

Not a hot-fix; Tristan + main session will need to pick one.

---

## Task 3 — Fire test pixel events — 🟡 MOSTLY GREEN (4/5 events)

**Timestamp sequence (approximate, within the next ~2 minutes of the first):**
- `page_view` — **2026-04-22 19:53:40 EDT (23:53:40 UTC)**
- `search` — ~19:54 EDT ("super mario" query, 39 results returned)
- `view_item` — ~19:55 EDT (Super Mario World - SNES Game, $21.99, variant 43794963660834)
- `add_to_cart` — ~19:55 EDT (2 items now in cart, $79.98 subtotal)
- `begin_checkout` — ~19:56 EDT (Shopify checkout page loaded)
- `add_payment_info` — **NOT FIRED** (see below)

### Note on environment

Session was **not** a fresh incognito per the brief's spec. The checkout page auto-filled Tristan's email, name, and address from a prior logged-in session, meaning the pixel events are attributed to a known/returning user rather than a cookie-less anonymous visitor. For pixel-verification purposes this is still valid — the events will still register in Google Ads and flip goal status from Inactive → Recording. If a cleaner attribution test is wanted later, redo Task 3 from a true incognito window.

### Why add_payment_info didn't fire

At the card-entry step, the Chrome automation started returning "Cannot access a chrome-extension:// URL of different extension" errors — likely Shop Pay / 1Password / another extension injecting a popup that grabbed focus. Retries (Escape, click-through) also blocked. Since `add_payment_info` is listed as **optional** in the brief (the 4 required goals are page_view, view_item, add_to_cart, begin_checkout — all fired), further retries weren't worth the risk.

**To fire add_payment_info at any time:** Open the current checkout tab, scroll to Payment, type test card `4242 4242 4242 4242`, expiry `12/29`, CVC `123`, click Pay now. Payment will fail (expected with test digits on live Shopify Payments) but the event fires before submission.

---

## Task 4 — Verify conversion tracking — ⏳ PENDING (needs wait)

**Cannot complete in this session.** Events were fired at ~19:53 EDT; goals take 2-4h to surface in Google Ads → Conversions → Summary.

**Re-check window opens: ~2026-04-22 21:53 EDT** (2h after fire) → closes ~2026-04-22 23:53 EDT (4h after).

### How to re-check (brief spec)
1. https://ads.google.com → account `822-210-2291` (8-Bit Legacy)
2. Tools & Settings → Measurement → Conversions → Summary
3. Expected status after wait:

| Goal | Expected |
|---|---|
| Google Shopping App Page View | Recording / No recent conversions |
| Google Shopping App Add To Cart | Recording / No recent conversions |
| Google Shopping App Begin Checkout | Recording / No recent conversions |
| Google Shopping App Purchase | Inactive (OK — flips on first real order) |
| Add Payment Info | Inactive (expected — we didn't fire it) |

### Gate rule
- All 4 non-Purchase non-AddPaymentInfo goals Recording/No-recent → ✅ ENABLE.
- Any of Page View / Add To Cart / Begin Checkout showing Inactive / Misconfigured / Needs attention → 🔴 DO NOT enable. Re-fire events, wait another 2h, re-check. Two failures → pixel is broken; don't launch.

---

## Task 5 — 8BITNEW promo code verification — ✅ GREEN

Shopify Admin → Discounts → 8BITNEW:

| Field | Value |
|---|---|
| Status | **Active** |
| Type | 10% off |
| Start date | 2025-05-07 |
| End date | None (no expiry) |
| Uses | 4 |
| Revenue (4 redemptions) | $231.59 |

No action needed. Non-blocking; ready for MC Promotion submission in Task 6 if Tristan wants.

---

## Task 6 — MC Promotion submission — ⏭️ SKIPPED

Per brief: "Only do this if Tasks 1-5 are all green." Task 2 is BLOCKED, so skipped. Can be done in a follow-up session once Task 2 resolves.

---

## Preflight check

Not re-run at the end because the sandbox proxy blocks `oauth2.googleapis.com:443` (403 from the Anthropic sandbox proxy, not a real API failure). Main session verified 18/18 earlier today. No config was modified in this session (no API writes, no bids, no budgets, no negatives), so the 18/18 status is still valid.

---

## Handoff summary for Tristan

| Task | Status | Gate |
|---|---|---|
| 1. MC Diagnostics audit | ✅ GREEN | Cleared |
| 2. CIB exclusion feed upload | 🔴 BLOCKED | MC Next UI limitation — needs API/rules workaround |
| 3. Fire test pixel events | 🟡 4/5 events fired | add_payment_info optional, not blocking |
| 4. Verify conversion tracking | ⏳ PENDING | Re-check at 21:53 EDT+ |
| 5. 8BITNEW code verified | ✅ GREEN | Active, 10%, no expiry |
| 6. MC Promotion submission | ⏭️ SKIPPED | Task 2 blocked |

**Go/No-Go:** **NO-GO.** Two open gates (Task 2 delivery path + Task 4 2h wait). Fix Task 2 delivery path, re-check Task 4 at 22:00 EDT. If both green, safe to enable.

**Campaign state:** Paused ✓ (never touched).
