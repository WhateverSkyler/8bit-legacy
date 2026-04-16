# Claude Cowork Brief — 2026-04-16 (Merchant Center Full Audit)

**For:** Claude Code running on Tristan's Mac with browser access (Google Merchant Center)
**From:** Claude Opus running on the laptop (same repo, 8bit-legacy)
**Written:** 2026-04-16 4:50 PM EDT
**Goal:** Systematically audit EVERY page and setting in Google Merchant Center. Log everything that could be improved. Separate actionable fixes from noise/junk suggestions.

---

## Context

The Google Ads account is suspended (appeal submitted, waiting 1-5 business days). While we wait, we're optimizing Merchant Center for maximum organic performance. Free listings are LIVE with 12K+ products — improvements here help immediately.

The store is **8-Bit Legacy** (8bitlegacy.com) — retro video games + Pokemon cards, eBay dropship model. Merchant Center ID: 5296797260.

---

## How to do this audit

Go to https://merchants.google.com/ and visit EVERY section in the left sidebar and settings. For each page, note:
- What warnings, suggestions, or issues are shown
- Current status of each setting/feature
- Whether fixing it would help organic Shopping performance

**Be thorough.** Check sub-pages, tabs within pages, settings panels, everything. This is a full audit.

---

## Known Suggestions to Evaluate

Tristan sees these suggestions on the dashboard. For EACH one, investigate what's actually involved and give a verdict: **DO IT** (worth the effort), **SKIP** (not relevant or low value), or **INVESTIGATE** (need more info).

### 1. "12,273 products might have missing or inaccurate product details"
- **Check:** Click into this → what specific details are missing?
- **Likely:** Missing GTIN/UPC, missing product descriptions, missing product type
- **This is the #1 priority** — product data quality directly affects ad ranking and organic visibility
- Note the top issues by count

### 2. "Link your Business Profile to Business Manager"
- **Check:** Is there a Google Business Profile for 8-Bit Legacy?
- **Verdict likely:** SKIP unless there's an existing Google Business Profile. This is for brick-and-mortar stores mostly.

### 3. "Give customers flexible payment choices"
- **Check:** What payment methods can be displayed?
- **Likely:** Shop Pay, PayPal, credit cards — whatever Shopify supports
- This shows payment badges on product listings in Google Shopping

### 4. "Show your fastest shipping options to customers on Google"
- **Check:** What shipping settings are currently configured?
- **Important:** 8-Bit Legacy offers free shipping over $50. This should be configured so it shows on listings.
- **Also check:** Are shipping speeds set? (e.g., "Ships in 3-5 business days")
- Note: Since this is dropship from eBay, shipping speed varies. Don't promise faster than reality.

### 5. "Turn on email notifications"
- **Verdict:** SKIP — nice to have but not performance-affecting

### 6. "Show your loyalty program benefits on your products"
- **Verdict:** SKIP — 8-Bit Legacy doesn't have a loyalty program

### 7. "Let customers add loyalty cards to Google Wallet"
- **Verdict:** SKIP — no loyalty program

### 8. "Update descriptions for Nintendo Games — 1,295 products"
- **Check:** Click into this → which products are affected?
- **Important:** Are these products missing the `description` field entirely, or just have short descriptions?
- Note: Product descriptions were just bulk-updated today (30-day → 90-day returns). If descriptions are still flagged as missing, it's a different issue.

### 9. "Turn on automatic image improvements"
- **Check:** What does this actually do?
- **If it just removes promotional overlays:** Probably safe to enable since our images are product photos, not promotional
- **But:** Make sure it won't alter product images in a way that misrepresents the item

### 10. "Build trust with your customer service"
- **Check:** What customer service info is configured/missing?
- **Likely needs:** Contact email, phone number, return policy URL
- **This matters** — customer service info affects trust badges on listings

### 11. "Help shape Merchant Center" (feedback notifications)
- **Verdict:** SKIP

### 12. "Highlight your best deals and land more sales" (promotions)
- **Check:** What's involved in setting up promotions?
- **Context:** 8-Bit Legacy runs periodic sales. If promotions can be synced from Shopify compare_at_price, this could be valuable.
- Note whether this requires manual setup per promotion or can be automated

### 13. "Improve your product images with generative AI" (Product Studio)
- **Verdict:** SKIP — our product images are actual game box photos, not something AI should edit

---

## Additional Pages to Check

Beyond the suggestions, audit these areas:

### Products → Diagnostics
- How many products have item-level issues?
- What are the top issues by count?
- Any account-level issues?

### Products → All Products
- Spot check 5-10 products:
  - Do they show correct prices?
  - Are images loading?
  - Is the product type / Google product category correct?
  - Are custom labels (custom_label_0 through custom_label_4) populated?

### Products → Feeds
- What feeds are configured?
- When was the last successful fetch?
- Any feed processing errors?

### Growth → Manage Programs
- Which programs are enabled? (Free listings, Shopping ads, Buy on Google, etc.)
- Status of each program
- **Critical:** Is "Shopping ads" showing as suspended or pending?

### Settings → Shipping and Returns
- What shipping services are configured?
- Is the free shipping over $50 threshold set?
- Is the 90-day return policy configured?
- Transit time settings?

### Settings → Business Information
- Business name, address, phone
- Website URL — verified?
- Is everything filled in completely?

### Settings → Linked Accounts
- Is Google Ads (822-210-2291) linked?
- Any link issues or warnings?

### Settings → Taxes
- Tax settings (Shopify handles tax collection, but MC needs to know)

### Settings → Automatic Improvements
- What auto-improvements are enabled/disabled?
- Should any be toggled?

---

## Output Format

Write your findings to the chat as a structured report:

```
## Merchant Center Full Audit — 2026-04-16

### Account Overview
- Account ID: ...
- Total products: ...
- Products with issues: ...
- Programs enabled: ...

### HIGH PRIORITY (Do These)
1. [Issue] — What's wrong, how to fix, expected impact
2. ...

### MEDIUM PRIORITY (Worth Doing)
1. ...

### LOW PRIORITY / SKIP
1. [Suggestion] — Why it's not worth doing

### Settings Audit
- Shipping: [status]
- Returns: [status]
- Business info: [status]
- Tax: [status]
- Linked accounts: [status]

### Product Data Quality
- Missing GTIN: X products
- Missing descriptions: X products
- Missing images: X products
- Other issues: ...

### Recommended Actions (in order)
1. ...
2. ...
3. ...
```

---

## Hard Guardrails

- **Do NOT change settings** without noting what you're changing and why
- **DO enable** obviously beneficial toggles (like automatic image improvements) if they have no downside — but note that you did it
- **Do NOT modify product data** — that's done through Shopify, not MC directly
- **Do NOT mess with shipping/tax settings** without documenting current state first
- **Do NOT run any scripts or modify any repo files**
- Be thorough — check every page, every tab, every sub-section

---

## Important Context

- Store: 8bitlegacy.com
- Merchant Center ID: 5296797260
- Google Ads ID: 822-210-2291 (currently suspended, appeal pending)
- Business model: eBay dropship (no physical inventory)
- Shipping: Free over $50, otherwise flat rate. Ships from eBay sellers (3-7 business days typical)
- Returns: 90-day return policy
- Products: ~7,600 retro games + ~1,200 Pokemon cards + consoles + accessories
- The product description bulk update (30-day → 90-day) completed today for 6,086 products
