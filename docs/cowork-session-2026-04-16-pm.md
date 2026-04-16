# Cowork Session Handoff — 2026-04-16 PM (Ads Campaign Launch)

**Session:** 2026-04-16, ~12:30 PM – 2:30 PM EDT
**Agent:** Claude (Cowork mode, browser automation via Chrome extension)
**Brief:** `docs/claude-cowork-brief-2026-04-16-ads-launch.md`
**Guide:** `docs/google-ads-campaign-setup-guide.md`

---

## Summary

Created the `8BL-Shopping-All` Standard Shopping campaign in Google Ads and immediately paused it. Attempted product group subdivision and negative keyword import but both were **blocked by a Google Ads account suspension** discovered mid-session.

---

## Task Status

| # | Task | Status | Notes |
|---|------|--------|-------|
| 1 | Re-fire conversion tracking events | **DONE** | Browsed product page, searched, added to cart, proceeded to checkout with real email/address. All 6 non-purchase events fired. Events take 2-4 hours to register. |
| 2 | Re-authorize Google Ads API OAuth token | **BLOCKED** | Requires Tristan to log in with Google account credentials. Cannot be done by automation. |
| 3 | Create `8BL-Shopping-All` campaign | **DONE** | Campaign created and immediately paused. Campaign ID: `23766662629`. |
| 4 | Set up product group subdivisions | **BLOCKED** | Subdivision UI was configured correctly but save failed — account suspended. See details below. |
| 5 | Import 334 negative keywords | **BLOCKED** | Not attempted — account suspension prevents all write operations. |
| 6 | Pre-launch verification checklist | **PARTIAL** | See checklist below. |
| 7 | Write handoff doc | **DONE** | This document. |

---

## Campaign Created: `8BL-Shopping-All`

**Campaign ID:** 23766662629
**Account:** 822-210-2291 (8-Bit Legacy)

### Settings Confirmed

| Setting | Value | Status |
|---------|-------|--------|
| Campaign type | Standard Shopping | ✅ |
| Merchant Center | 5296797260 | ✅ |
| Country of sale | United States | ✅ |
| Networks | Google Search Network only | ✅ (Search Partners + Display unchecked) |
| Bidding | Manual CPC | ✅ |
| Enhanced CPC | N/A | ⚠️ **Deprecated** — option no longer exists in Google Ads for Shopping campaigns as of 2026. Campaign runs on plain Manual CPC. |
| Daily budget | $14.00 | ✅ |
| Campaign priority | High | ✅ |
| Status | **Paused** | ✅ |
| Ad group name | `all-products` | ✅ |
| Default max CPC | $0.40 | ✅ |

### Deviation from Guide: Enhanced CPC

The setup guide specified "Enhanced CPC: ON (checkbox under Manual CPC)." This option has been deprecated by Google for Shopping campaigns. The bid strategy dropdown only offers: Target ROAS, Maximize clicks, Manual CPC. No Enhanced CPC checkbox appears. The campaign is on plain Manual CPC, which is fine for launch — bid adjustments are made through product group subdivision anyway.

---

## CRITICAL BLOCKER: Google Ads Account Suspended

During the session, the Google Ads account (822-210-2291) was flagged as **suspended**:

> "Your account has been suspended. Your account doesn't comply with our Google Ads Terms and Conditions."

This blocks ALL write operations in the account — campaign edits, product group saves, negative keyword imports, and enabling the campaign.

### What Tristan Needs to Do

1. **Check suspension reason:** Go to Google Ads → the red banner at top → "Learn more" to see the specific policy violation
2. **Appeal if appropriate:** Google Ads → Account → Suspended account → Request review
3. **Common causes for new/dormant accounts:**
   - Billing issue (payment method declined or not verified)
   - Suspicious activity on a newly activated account
   - Policy review triggered by first campaign creation
   - Missing business information or identity verification
4. **Timeline:** Appeals typically take 1-3 business days. Some suspensions are auto-resolved within 24 hours if triggered by first-time campaign creation.

---

## Product Group Subdivisions — Ready to Apply

The subdivision was fully configured in the UI but could not be saved due to the suspension. Once the account is unsuspended, redo this from the Product groups page:

### Level 1: Subdivide "All products" → by Custom label 2 (category)

| Category | Max CPC | Action |
|----------|---------|--------|
| `game` | — | Subdivide further (see Level 2) |
| `console` | $0.35 | Set bid |
| `accessory` | $0.25 | Set bid |
| `sealed` | $0.30 | Set bid |
| `pokemon_card` | — | **EXCLUDE** |
| Everything else | — | **EXCLUDE** |

### Level 2: Subdivide `game` → by Custom label 0 (price_tier)

| Price Tier | Max CPC |
|------------|---------|
| `over_50` | $0.55 |
| `20_to_50` | $0.40 |
| `under_20` | $0.20 |

### How to Apply (once account is restored)

1. Go to campaign `8BL-Shopping-All` → Ad groups → Product groups tab
2. Click the `+` icon next to "All products"
3. Select "Custom label 2" from the "Subdivide by" dropdown
4. Click "Bulk add values manually" → paste: `game`, `console`, `accessory`, `sealed`, `pokemon_card` (one per line) → Confirm
5. Click "Continue to edit bids" → set each category's bid per the table above (click New max CPC cell → enter value or select Exclude → Save)
6. Click the page-level "Save" button
7. Then go back into the `game` product group → click `+` to subdivide again → by "Custom label 0" → add `over_50`, `20_to_50`, `under_20` → set bids per Level 2 table

---

## Negative Keywords — Ready to Import

334 negative keywords are prepared in two formats:

- **CSV for Google Ads Editor:** `data/negative-keywords-google-ads-import.csv`
- **Human-readable master list:** `docs/ads-negative-keywords-master.md` (400 terms across 10 categories)

### Fastest Method (Google Ads Editor)

1. Download Google Ads Editor: https://ads.google.com/intl/en/home/tools/ads-editor/
2. Download account → select `8BL-Shopping-All`
3. Keywords → Campaign Negative Keywords → Import from CSV
4. Post changes → upload

### Manual Method (Google Ads UI)

1. Campaign → Keywords (left sidebar) → Negative keywords → `+`
2. Paste all keywords from `docs/ads-negative-keywords-master.md` code blocks
3. Use **phrase match** (default)

---

## Pre-Launch Verification Checklist

| # | Check | Status | Notes |
|---|-------|--------|-------|
| 1 | Conversion tracking: 4 goals "Configured" | ⏳ | Events fired this session; check back in 2-4 hours |
| 2 | Conversion events: 7 events "Recording" | ⏳ | Same — need time to register |
| 3 | Merchant Center feed healthy (< 50 disapproved) | ✅ | 12,226 products, 98% approved per earlier check |
| 4 | Product pages show correct variant prices | ✅ | Fixed April 13, confirmed working |
| 5 | Free shipping badge shows $35 | ❓ | Not verified this session |
| 6 | Return policy shows 90 days | ❓ | Product description update was running in background (30→90 days) |
| 7 | Dashboard circuit breaker armed | ❓ | Dashboard at 8bit.tristanaddi.com — verify scheduler is running |
| 8 | 334 negative keywords loaded | ❌ | Blocked by account suspension |
| 9 | Product group subdivisions saved | ❌ | Blocked by account suspension |
| 10 | Google Ads account active (not suspended) | ❌ | **CRITICAL** — must resolve before launch |

---

## Technical Notes

### Angular Rendering Bug in Google Ads

The campaign creation wizard and product group pages have a persistent rendering bug where form fields and table rows exist in the DOM (with proper dimensions) but don't paint to screen. Workarounds used:

- **Campaign wizard Ad group step:** Used JavaScript `nativeInputValueSetter` pattern to programmatically set hidden Angular input values for ad group name and bid amount, then dispatched input/change/blur events to update Angular model state.
- **Product groups Edit bids page:** Initially blank; clicking Save once (which triggered the suspension error dialog) caused a full repaint that made rows visible. After that, individual bid editors worked normally.

### "No networks targeted" Display Quirk

The campaign creation summary page showed "Networks: No networks targeted" which looked alarming. After creation, the Campaign Settings page confirmed "Networks: Google Search Network" is correctly enabled. The summary page's label referred to additional networks (Search Partners, Display) being unchecked, not the primary Search Network.

---

## Remaining Work Before Launch

In priority order:

1. **Resolve Google Ads account suspension** — nothing else can proceed until this is fixed
2. **Re-authorize OAuth token** (Task 2) — Tristan must log in manually
3. **Save product group subdivisions** (Task 4) — follow instructions above
4. **Import 334 negative keywords** (Task 5) — follow instructions above
5. **Subdivide `game` by price_tier** — second-level subdivision per Level 2 table
6. **Exclude "Everything else" catch-all** — will appear after first subdivision save
7. **Verify conversion tracking events registered** — check 2-4 hours after this session
8. **Final pre-launch checks** — free shipping badge, return policy, circuit breaker
9. **Enable campaign** — change status from Paused to Enabled

---

## Files Modified This Session

None — all work was browser UI automation. This handoff doc is the only new file.

## Git

This document should be committed and pushed:
```bash
git add docs/cowork-session-2026-04-16-pm.md
git commit -m "Add PM cowork session handoff doc — ads campaign launch"
git push
```
