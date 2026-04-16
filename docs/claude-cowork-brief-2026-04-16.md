# Claude Cowork Brief — 2026-04-16 (Ads Launch Final Push)

**For:** Claude Code running on Tristan's Mac with browser/Shopify admin access
**From:** Claude Opus running on the laptop (same repo, 8bit-legacy)
**Written:** 2026-04-16 10:00 AM EDT
**Goal:** Clear every remaining browser/UI blocker so the Google Ads campaigns can launch. The laptop Claude is building scripts, dashboard tooling, and monitoring infrastructure in parallel.

---

## Session start — mandatory

```bash
cd ~/Projects/8bit-legacy
git pull --ff-only
```

If pull fails due to divergence, STOP and tell Tristan — do NOT rebase or force push.

**Then read, in order:**
1. `CLAUDE.md` — project rules
2. `docs/session-handoff-2026-04-16.md` — where things stand as of last night
3. `docs/ads-pre-launch-checklist.md` — master checklist (Sections A–H)
4. `docs/cowork-session-2026-04-13-pm.md` — what shipped on April 13
5. This brief

**The laptop Claude is handling:** all scripts, dashboard code, monitoring tools, negative keyword formatting, Winners verification scripts. **Do NOT run any Python scripts. Do NOT edit files in `dashboard/`, `scripts/`, or `config/`.**

---

## Ground truth (as of 2026-04-16 morning)

### Already done (do NOT redo):
- Variant price display bug: **FIXED** (class="money" on ProductPrice spans, 3 section files)
- Sale price variant display: **FIXED** (show/hide compare_at on variant switch)
- Google Customer Reviews pixel: **LIVE** (Custom Pixel ID 149717026)
- Google Ads account: **822-210-2291 CONFIRMED LINKED** in Shopify Google & YouTube app
- Free shipping threshold: **$35** (updated via Shopify API 2026-04-13)
- Return policy: **90 days** everywhere (policy page, theme settings, announcement bar)
- Pricing: **Accurate as of 2026-04-15** (PC-direct refresh, 1,303 variants fixed)
- Sale rotation: **Live** — 8 iconic titles at 15% off, console bundles still on sale
- CIB prices: **All fixed** — zero synthetic CIB prices remain
- Negative keyword master list: **400 terms ready** in `docs/ads-negative-keywords-master.md`

### Still needed (your tasks below + Tristan manual tasks):
- Conversion tracking: Events were fired 2026-04-13 but **never verified in Google Ads UI** (2–4 hour lag). Need to confirm status.
- Merchant Center feed health: **Not audited since April 10.** Need spot-check.
- "$50 shipping" badge on product pages: **Still shows $50** even though threshold is $35.
- Winners products: Need SEO meta descriptions for Shopping ad CTR.
- Campaign construction: **Not started.** Section F of the pre-launch checklist.
- Google Ads promo credit: **$700 expiring 2026-05-31** — 45 days left. ~$14/day to consume.

---

## Task 1 — Verify Conversion Tracking Status (PRIORITY: CRITICAL, ~10 min)

Conversion events were fired on 2026-04-13. They should have registered by now (3 days later). This is the single hardest gate to launching.

### Steps:
1. Open Google Ads (ads.google.com) → log in with access to account `822-210-2291`
2. Navigate to **Goals → Conversions → Summary**
3. Check each of the 4 goal categories:
   - **Purchase** — should show `Google Shopping App Purchase` as Primary, status should NOT be "Inactive"
   - **Add to cart** — should show `Google Shopping App Add To Cart` as Primary
   - **Begin checkout** — should show `Google Shopping App Begin Checkout` as Primary
   - **Page view** — should show `Google Shopping App Page View` as Primary

### If any goal still shows "Misconfigured":
- Click the row → **Edit goal** → toggle the `Google Shopping App ...` action to **Primary** → Save
- This was supposed to be done 2026-04-13 but may not have stuck

### If any action still shows "Inactive":
Fire the events again right now:
1. Open https://8bitlegacy.com in **incognito** (no ad blockers)
2. Browse a product page (Page View + View Item)
3. Use the search bar (Search)
4. Click Add to Cart (Add to Cart)
5. Proceed to checkout with real email + address (Begin Checkout)
6. Enter a card, then abandon (Add Payment Info)
7. Wait 2–4 hours, re-check

### Deliverable:
Create `docs/ads-conversion-tracking-status-2026-04-16.md` with:
- Screenshot description or copy-paste of each goal's status
- Verdict: `ALL GREEN` or `BLOCKED: [reason]`

---

## Task 2 — Merchant Center Feed Health Audit (PRIORITY: HIGH, ~15 min)

### Steps:
1. Log into Merchant Center (merchants.google.com, account 5296797260)
2. Navigate to **Products → Overview**
   - Record: total active, pending, disapproved counts
   - If disapproved > 50, list the top 5 reasons
3. Navigate to **Products → Diagnostics**
   - Screenshot or note any item-level issues
   - Record any "Limited" or "Not serving" products
4. Navigate to **Products → Feeds**
   - Confirm the Shopify Content API feed has synced in the last 24 hours
5. **Spot-check 10 random products** in the product viewer:
   - Title present and descriptive (should end with console name)
   - Image present and not broken
   - Price matches what's on 8bitlegacy.com
   - Availability = "in stock"
   - Custom labels populated (price_tier, console, category, margin_tier)
6. **Specifically check all 17 Winners products** (handles listed in `docs/ads-winners-curation-list.md`):
   - Search each by title in Merchant Center
   - Confirm: approved, in stock, image present, correct price

### Deliverable:
Create `docs/merchant-center-audit-2026-04-16.md` with:
- Product counts (active/pending/disapproved)
- Feed sync timestamp
- Any blocking issues found
- Winners product verification (17/17 approved or list any missing)
- Verdict: `FEED HEALTHY` or `NEEDS FIX: [issue]`

---

## Task 3 — Fix "$50 Shipping" Badge on Product Pages (PRIORITY: HIGH, ~20 min)

The free shipping threshold was changed from $50 to $35 on 2026-04-13 in Shopify shipping settings. But the **product page still shows a hardcoded "FREE shipping over $50" badge/text**. This needs to match the actual $35 threshold — especially before ads launch, since Shopping ad clicks land directly on product pages.

### Steps:
1. Open a product page on 8bitlegacy.com — find the "$50 shipping" text
2. In Shopify admin → Online Store → Themes → current live theme (`Copy of bs-kidxtore-home6-v1-7-price-fix`, ID: 185256640546)
3. **DUPLICATE the theme first** — never edit live directly
4. Edit code on the duplicate:
   - Search all files for `50` or `$50` or `shipping` to find the hardcoded string
   - Likely in: `sections/bs-product.liquid`, `snippets/product-trust-badges.liquid`, or `config/settings_data.json`
   - Replace "$50" with "$35" wherever it refers to the free shipping threshold
5. Preview the duplicate → verify product pages show "FREE shipping over $35"
6. Publish the duplicate as MAIN
7. Keep the old theme as unpublished backup

### Deliverable:
Note in `docs/ads-conversion-tracking-status-2026-04-16.md` (or the main session doc) which file was changed and that the fix is live.

---

## Task 4 — SEO Meta Descriptions for Winners Products (PRIORITY: MEDIUM, ~20 min)

Google Shopping CTR improves with proper meta descriptions. Currently all 17 Winners products are missing them (Shopify falls back to truncated body HTML).

### Pattern:
```
Buy [Title] for [Console] at 8-Bit Legacy. [Condition] tested and verified. Fast shipping, 1-year warranty, 90-day returns.
```

Where:
- [Title] = product title without the console suffix
- [Console] = full console name (PlayStation, Nintendo 64, GameCube, etc.)
- [Condition] = "Lightly Played" for Game Only, "Complete in Box" for CIB

### Steps:
1. For each of the 17 Winners products (list in `docs/ads-winners-curation-list.md`):
   - Open the product in Shopify admin
   - Scroll to "Search engine listing" → Edit
   - Set the meta description using the pattern above
   - Save
2. Alternatively, use the Shopify Admin GraphQL API to batch-update via `productUpdate` mutation:
   ```graphql
   mutation {
     productUpdate(input: {
       id: "gid://shopify/Product/[ID]",
       seo: { description: "[meta description]" }
     }) {
       product { id }
     }
   }
   ```

### Deliverable:
Note how many of 17 were updated. If batch API was used, record the mutation results.

---

## Task 5 — Enable Google Customer Reviews Program in Merchant Center (PRIORITY: MEDIUM, ~5 min)

The custom pixel is already live (fires on checkout_completed, pixel ID 149717026). But the **Customer Reviews program itself** may not be enabled in Merchant Center.

### Steps:
1. Log into Merchant Center 5296797260
2. Growth → Manage programs → **Customer Reviews**
3. If not already enabled: Enable → accept the agreement
4. This is the program that aggregates review data for seller-rating stars in Shopping ads (requires 100+ reviews over 12 months — won't help immediately, but needs to be accumulating from day 1)

### Deliverable:
Note: "Customer Reviews program: ENABLED" or "already enabled" in the session doc.

---

## Task 6 — Walk Tristan Through Campaign Construction (PRIORITY: HIGH, when Tristan is ready)

When Tristan is ready to build the campaigns, walk him through Section F of `docs/ads-pre-launch-checklist.md`. The full step-by-step is there. Summary:

### Campaign 1: `8BL-Shopping-Winners`
- Type: Standard Shopping (NOT Performance Max)
- Network: Search only
- Location: United States
- Bidding: Manual CPC, Enhanced CPC on, max $0.75
- Budget: **$6/day** (promo mode, up from baseline $3/day)
- Priority: High
- Products: Only the 17 Winners SKUs (filter by Item ID)
- Negative keywords: Paste all 10 categories from `docs/ads-negative-keywords-master.md`
- Status: **Paused** until all pre-launch items are green

### Campaign 2: `8BL-Shopping-Discovery`
- Type: Standard Shopping
- Bidding: Manual CPC, Enhanced CPC on, max $0.35
- Budget: **$4/day** (promo mode, up from baseline $1/day)
- Priority: Low
- Products: Everything EXCEPT Winners SKUs, EXCEPT Pokemon, EXCEPT under $20
- Same negative keywords
- Status: **Paused**

### Important notes:
- Do NOT use "Smart Campaign" or "Express" modes
- Do NOT enable Display Network or YouTube Partners
- Promo-mode budgets ($6 + $4 = $10/day) are intentionally higher to consume the $700 credit before 2026-05-31
- Both campaigns start PAUSED — Tristan flips them on after everything else is green

---

## Hard guardrails

- **Do NOT run any Python scripts** in `scripts/` — laptop Claude owns those
- **Do NOT edit `dashboard/`, `scripts/`, or `config/` directories** — laptop Claude owns those
- **Always duplicate themes before editing** — never edit the live theme directly
- **Never commit secrets** — `.env.local`, `.env`, tokens, passwords
- **If a decision needs Tristan** — ask him, don't guess
- **Do NOT touch pricing, sales, or inventory** — those are stable and correct

---

## When you're done

1. Commit any repo changes:
   ```bash
   git add docs/
   git status   # verify no script/dashboard/config changes
   git commit -m "Cowork 2026-04-16: Ads pre-launch — conversion tracking, feed audit, shipping badge fix, SEO meta"
   git push
   ```

2. Write a handoff section in `docs/ads-conversion-tracking-status-2026-04-16.md` (or create `docs/cowork-session-2026-04-16.md`) with:
   - Each task: GREEN / BLOCKED / SKIPPED + reason
   - Whether campaigns are ready for Section F (construction)
   - Anything still blocking launch

3. Tell Tristan what he needs to verify or do manually.

---

## Success criteria

- [ ] Conversion tracking: All 4 goals show `Configured`, all 7 actions NOT `Inactive`
- [ ] Merchant Center: <50 disapproved products, all 17 Winners approved + in stock
- [ ] Product pages show "FREE shipping over $35" (not $50)
- [ ] 17 Winners products have SEO meta descriptions
- [ ] Customer Reviews program enabled in Merchant Center
- [ ] Tristan briefed on campaign construction steps (Section F)
- [ ] Handoff doc written and pushed

**After cowork + Tristan builds the campaigns → ads are ready to enable.**
