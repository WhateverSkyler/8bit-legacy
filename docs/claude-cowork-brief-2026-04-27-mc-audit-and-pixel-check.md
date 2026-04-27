# Cowork Brief — 2026-04-27 — MC Audit + Pixel Confirmation

## Goal

Two browser-only tasks the main session can't do:

1. **Merchant Center audit** — diagnose why MC shows ~36K total products when Shopify only has ~12K real products (suspected duplication), and explain what "Limited" means for THIS specific store's products.
2. **Final pixel verification** — check Google Ads Webpages tab for test order #1071's Purchase event (placed ~12:30 PM ET today, now ~3:45 PM ET = 3h+ post-order, should be in by now if it's going to land).

After this, main session decides whether to flip the campaign.

## Hard guardrails

- ✗ Do NOT modify any product, supplemental feed, MC setting, or ad campaign
- ✗ Do NOT click "Approve" / "Disapprove" / "Resubmit" anywhere
- ✗ Do NOT enable or pause the `8BL-Shopping-Games` campaign
- ✗ Do NOT touch Shopify discounts, themes, or anything outside the read-only Merchant Center + Google Ads UI
- ✗ Do NOT delete duplicates if you find them — just document. Main session decides what to do.

---

## Task 1 — Merchant Center duplication + Limited audit (15-20 min)

### 1A: Total counts breakdown

Open Merchant Center (`merchants.google.com`), select account `5296797260` (8-Bit Legacy).

Navigate to **Products** → **All products** (or "Need attention" + "Approved" combined).

Capture these top-line numbers:
- **Total products**: ___
- **Approved**: ___
- **Limited**: ___
- **Disapproved**: ___
- **Pending / Under review**: ___

Then navigate to **Products** → **Feeds**. List every feed with:
- Feed name
- Source (Content API, Shopify channel app, supplemental, manual upload, etc.)
- Item count
- Last updated

Tristan suspects duplication because Shopify only has ~12K real products, but MC shows ~36K. Likely cause is multiple feeds pointing at the same products, OR the Shopify Google & YouTube app is exporting both Game Only AND CIB variants as separate items (each Shopify product has 2 variants → could be 12K × ~2.5 = 30K+ MC items). Document what you find.

### 1B: Limited products audit

In **Products** filter by **Status: Limited performance** (or whatever the UI labels it).

For 5-10 random Limited products, click into each and capture:
- Product title (truncate to 50 chars)
- Custom label 0 (over_50 / 20_to_50 / under_20 / etc.)
- Custom label 2 (game / pokemon-card / etc.)
- The specific Limited reason(s) Google shows
- Approved destinations vs Limited destinations

The goal is understanding WHY they're limited. Common reasons we want to confirm or rule out:
- Missing GTIN
- Missing brand
- Title quality
- Image quality
- Inconsistent pricing (compare_at < price)
- "Limited performance" (low historical impressions)

Pay special attention to whether **over_50 tier products** (custom_label_0=over_50) are disproportionately Limited — that's the bid tier we're spending most heavily on, and if those are constrained, the campaign won't deliver volume.

### 1C: CIB-specific check

Per memory, all 6,112 CIB variants were excluded from Shopping ads on 2026-04-24 via the `mm-google-shopping.excluded_destination` metafield. Verify this exclusion is actually reflected in MC:

- Search MC for `Final Fantasy VII` or any well-known game
- For one product, confirm both the **Game Only** variant and the **CIB** variant appear
- Click each — the CIB variant should show **"Excluded from Shopping ads"** or equivalent
- If the CIB variant shows as Approved/Limited (not excluded), that's a problem

---

## Task 2 — Pixel Webpages-tab confirmation for #1071 (5 min)

Open Google Ads (`ads.google.com`), confirm account selector shows `822-210-2291` (8-Bit Legacy).

### 2A: Conversion summary check

Tools (wrench icon) → **Conversions** → **Summary**.

For each of these 7 conversion actions, capture the count under "All conv." for the **last 24h** filter:
- Google Shopping App Purchase
- Google Shopping App Add To Cart
- Google Shopping App Begin Checkout
- Google Shopping App View Item
- Google Shopping App Page View
- Google Shopping App Search
- Google Shopping App Add Payment Info

If all 7 show 0 → pixel still not landing events in this account.
If Page View / View Item / Add To Cart show counts > 0 but Purchase shows 0 → site events fire but Purchase pipeline broken (cancellation race or thank-you-page rule).
If Purchase shows ≥ 1 → pixel confirmed end-to-end.

### 2B: Webpages tab for Purchase

Click the **"Google Shopping App Purchase"** row → **Webpages** tab.

What URLs appear?
- Any URL from `8bitlegacy.com`?
- Any URL containing `/checkouts/c/` or `/thank_you`?
- Earliest timestamp shown?

Order #1071 facts (for cross-reference):
- Placed: 2026-04-27 ~12:30 PM ET
- Total: $0.00 (after TESTZERO-20260427 + free shipping discount)
- Confirmation #: 08TA7H0L2
- Then cancelled + archived ~5 min later

The cancellation may have caused Google to retroactively remove the conversion. If the Webpages tab is empty, that's a likely explanation — NOT necessarily a broken pixel.

### 2C: Tracking status of each conversion action

Still in Conversions → Summary, capture the **Tracking status** column for all 7 actions:
- "Recording conversions" → working ✅
- "No recent conversions" → armed but no data ⚠️
- "Inactive" / "Unverified" → broken ❌
- "Receiving conversions" → very recent activity ✅

This is the authoritative state per action.

---

## Handoff

Write `docs/cowork-session-2026-04-27-mc-audit-and-pixel-check.md` with this structure:

```
## Task 1A — MC counts
- Total: ___ / Approved: ___ / Limited: ___ / Disapproved: ___ / Pending: ___
- Feeds:
  | Name | Source | Item count | Last updated |
  | ... | ... | ... | ... |
- Duplication hypothesis: <yes/no/unclear, with evidence>

## Task 1B — Limited products sample
- Sampled 5-10 limited products. Common reasons:
  - <reason 1>: N products
  - <reason 2>: N products
- Are over_50 tier products disproportionately Limited? YES / NO / UNCLEAR

## Task 1C — CIB exclusion verification
- CIB variants showing "Excluded from Shopping ads" in MC? YES / NO / MIXED

## Task 2A — Conversion counts (last 24h)
| Action | All conv. |
| Purchase | ___ |
| Add To Cart | ___ |
| Begin Checkout | ___ |
| View Item | ___ |
| Page View | ___ |
| Search | ___ |
| Add Payment Info | ___ |

## Task 2B — Webpages tab (Purchase action)
- Empty / has URLs: ___
- URLs seen: <list or "none">
- Earliest timestamp: ___

## Task 2C — Tracking status per action
| Action | Status |
| Purchase | ___ |
| Add To Cart | ___ |
| ... | ___ |

## Anything weird
<free-form>
```

Commit + Syncthing-propagate. No git push needed.

---

## What you are NOT doing

- Not modifying any product, feed, or MC setting
- Not flipping the ad campaign
- Not editing code or env files
- Not investigating WHY Limited is happening at the code/feed-config level — just document what you observe in the UI
- Not fixing duplication — just document it
