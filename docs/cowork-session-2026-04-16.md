# Cowork Session — 2026-04-16

**Session goal:** Clear all remaining browser/UI blockers for Google Ads launch.
**Brief:** `docs/claude-cowork-brief-2026-04-16.md`

## Task Results

### Task 1: Conversion Tracking Verification — BLOCKED (Tristan action needed)
- **Status:** BLOCKED — events need re-firing
- **Details:** All 7 conversion actions exist and are set to Primary in their goal categories. The configuration is correct. However, 5 of 7 actions are Inactive — only Add to Cart is Active. This proves the Shopify Google & YouTube app integration works, but the specific events need to be re-triggered.
- **Deliverable:** `docs/ads-conversion-tracking-status-2026-04-16.md`
- **Tristan action required:**
  1. Open https://8bitlegacy.com in incognito (no ad blockers)
  2. Browse a product page (→ Page View + View Item)
  3. Use the search bar (→ Search)
  4. Click Add to Cart (→ Add to Cart)
  5. Proceed to checkout with real email + address (→ Begin Checkout)
  6. Enter a card, then abandon (→ Add Payment Info)
  7. Wait 2–4 hours, re-check Google Ads → Goals → Conversions
  8. For Purchase: place a real small order ($5–10 item)

### Task 2: Merchant Center Feed Health Audit — GREEN ✅
- **Status:** FEED HEALTHY
- **Details:** 12,200 products active, 47 not showing (<0.4%), zero disapproved. Feed synced today 7:12 AM. All spot-checked Winners products approved and in stock.
- **Deliverable:** `docs/merchant-center-audit-2026-04-16.md`
- **Minor items (post-launch):** 202 invalid image encodings (1.6%), 6 mismatched prices, Customer Reviews pixel needs debugging

### Task 3: "$50 Shipping" Badge Fix — SKIPPED
- **Status:** SKIPPED per Tristan's instruction
- **Reason:** Tristan decided to keep shipping threshold at $50 for now

### Task 4: SEO Meta Descriptions for Winners Products — GREEN ✅
- **Status:** 17/17 COMPLETE
- **Pattern used:** `Buy [Title] for [Console] at 8-Bit Legacy. [Condition] tested and verified. Fast shipping, 1-year warranty, 90-day returns.`
- **Products updated:**
  1. Galerians (PS1) — Game Only + CIB share handle
  2. Galerians Ash (PS2)
  3. Mystical Ninja Starring Goemon (N64)
  4. Legend of the Mystical Ninja (SNES)
  5. Phantasy Star Online Episode I & II (GameCube)
  6. Phantasy Star Online Episode I & II Plus (GameCube)
  7. Phantasy Star Online III: C.A.R.D. Revolution (GameCube)
  8. Aidyn Chronicles (N64)
  9. Space Station Silicon Valley (N64)
  10. Metal Gear Solid (PS1)
  11. Silent Hill 2 (PS2)
  12. Fatal Frame (PS2)
  13. Fatal Frame 2 (PS2)
  14. Custom Robo (GameCube)
  15. Geist (GameCube)
  16. Baten Kaitos Origins (GameCube)
  17. Eternal Darkness: Sanity's Requiem (GameCube)
- **Note:** All products already had generic meta descriptions (pattern: "Shop [title] for [console] at 8-Bit Legacy. Authentic retro game, fast shipping and 90-day returns.") — these were updated to the more specific Winners pattern with condition info and warranty mention.

### Task 5: Customer Reviews Program — GREEN ✅
- **Status:** ENABLED (agreement signed, program active)
- **Warning:** Survey opt-in hasn't fired in 30+ days. Custom pixel (ID 149717026) may need debugging.
- **Action:** Verify pixel is still active in Shopify admin → Settings → Custom Pixels. Test with a real order.

### Task 6: Campaign Construction Walkthrough — BRIEFED ✅
- **Status:** Tristan briefed on both campaigns
- **Campaign 1:** `8BL-Shopping-Winners` — Standard Shopping, Manual CPC max $0.75, $6/day, High priority, 17 Winners SKUs only
- **Campaign 2:** `8BL-Shopping-Discovery` — Standard Shopping, Manual CPC max $0.35, $4/day, Low priority, everything except Winners/Pokemon/under $20
- **Both start PAUSED** — enable after conversion tracking goes green

## What's Blocking Launch

1. **Conversion tracking events need re-firing** (Tristan manual task — ~10 min + 2-4 hour wait)
2. **Purchase conversion action needs a real order** (Tristan — place a small $5-10 order)
3. **Campaign construction** (Tristan — follow Section F of ads-pre-launch-checklist.md, ~30 min)

## What's Ready

- Feed: 12.2K products healthy ✅
- Winners products: all 17 approved, in stock, SEO meta descriptions set ✅
- Customer Reviews program: enabled ✅
- Negative keywords: 400 terms ready in `docs/ads-negative-keywords-master.md` ✅
- Campaign specs: documented and briefed ✅
- Promo credit: $700, expires 2026-05-31 (45 days left) ✅

## Launch Sequence

1. Tristan fires conversion events (incognito walkthrough)
2. Wait 2-4 hours
3. Verify all goals show Active in Google Ads
4. Build both campaigns per Section F
5. Set both to PAUSED
6. Final review
7. Enable campaigns → ads are live
