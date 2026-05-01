# Cowork Brief — 2026-04-29 — Pixel Verification (read-only)

## Goal

Two quick read-only checks to determine the actual state of Google Ads conversion tracking on 8-Bit Legacy. Tristan placed a real $0.54 test order at 1:27 PM ET today (order #1072) but Google Ads Conversions Summary showed Purchase as "Inactive". We need to disambiguate "pixel didn't fire" from "Google's verification is just lagging" before deciding whether to place another test order or flip the campaign.

**Total time: ~5 minutes. Both checks are read-only.**

## Hard guardrails

- ✗ Do NOT place any orders, do not check out, do not enter payment info
- ✗ Do NOT flip the Google Ads campaign
- ✗ Do NOT modify ANY setting in Google Ads or Shopify
- ✗ Do NOT click "Troubleshoot" / "Resubmit" / "Edit" / "Save" buttons
- ✗ Do NOT touch the Merchant Center
- ✗ Do NOT enter any credentials — if you hit a login wall, surface it and pause for Tristan

## Check 1 — Google Ads Purchase status on "Today" view

Open `ads.google.com` → confirm account selector shows **822-210-2291** (8-Bit Legacy).

Tools (wrench icon, top right) → **Conversions** → **Summary**.

The page will load with date filter likely showing "Last 7 days" = "Apr 22–28, 2026" which **excludes today (Apr 29)**. We need to change this:

1. Click the date picker (top right of the page, NOT the gear icon)
2. Select **"Today"** OR a **custom range that includes Apr 29, 2026**
3. Apply

After the page reloads with today's data:

Capture the status of all 7 web conversion actions (the ones starting with "Google Shopping App"):

| Action | Status (in column) | "All conv." count |
|---|---|---|
| Google Shopping App Purchase (1) | ___ | ___ |
| Google Shopping App Add To Cart (1) | ___ | ___ |
| Google Shopping App Begin Checkout (1) | ___ | ___ |
| Google Shopping App Page View (1) | ___ | ___ |
| Google Shopping App View Item (1) | ___ | ___ |
| Google Shopping App Search (1) | ___ | ___ |
| Google Shopping App Add Payment Info (1) | ___ | ___ |

Look for the **specific conversion ACTION row** (not the goal CATEGORY summary row). Status values you might see:
- "Recording conversions" → working ✅
- "No recent conversions" → armed but no data in window ⚠️
- "Inactive" → never received an event 🔴
- "Receiving conversions" → recent activity, fully verified ✅
- "Misconfigured" / "Unverified" → setup issue 🔴

Also click into the **Purchase action row** (Google Shopping App Purchase (1)) and check:
- The **Webpages** tab → list any URLs that appear (look for `8bitlegacy.com/thank_you` or `/checkouts/c/`)
- The **Diagnostic** or **Troubleshoot** tab if visible — capture whatever message Google shows

## Check 2 — Live pixel fire on storefront

Open a fresh **Chrome incognito window** (Cmd+Shift+N).

Navigate to `https://8bitlegacy.com` (type the URL — don't use a bookmark).

**BEFORE clicking anywhere on the page**: open DevTools (Cmd+Option+I) → **Network** tab → in the filter box at the top, type `googleads`.

Then perform these actions, watching the Network tab between each:

### 2A — Page load
- Do nothing, just let the homepage load
- Look for requests to `googleads.g.doubleclick.net/...`
- Check if URLs contain `AW-18056461576` (correct) and/or `AW-11389531744` (wrong/leftover)
- Capture: how many requests, which AW IDs appear

### 2B — Product view
- Click any product in the homepage grid
- Watch for new requests appearing in the Network tab
- Look for `view_item` or `--mzCPSd0KMcEIj6_qFD` (page_view token) or `5fn7CPed0KMcEIj6_qFD` (view_item token)
- Capture: did new googleads requests fire?

### 2C — Add to cart
- Click "Add to cart"
- Watch for new requests
- Look for `VJ6hCPGd0KMcEIj6_qFD` (the add_to_cart conversion token)
- Capture: did the add_to_cart request fire? What status code?

### 2D — Begin checkout
- Click the cart icon → click "Checkout" / "Check out"
- Watch for new requests on the checkout page load
- Look for `HDu_CO6d0KMcEIj6_qFD` (the begin_checkout conversion token)
- **STOP HERE**. Do NOT enter any info or proceed further.
- Capture: did the begin_checkout request fire? What status code?

## Handoff

Write `docs/cowork-session-2026-04-29-pixel-verify.md` with:

```markdown
# Cowork Session — 2026-04-29 — Pixel Verification

## Check 1 — Google Ads conversion statuses (TODAY filter)
Date filter applied: ___
| Action | Status | All conv. |
| Purchase | ___ | ___ |
| Add To Cart | ___ | ___ |
| Begin Checkout | ___ | ___ |
| Page View | ___ | ___ |
| View Item | ___ | ___ |
| Search | ___ | ___ |
| Add Payment Info | ___ | ___ |

Webpages tab on Purchase action: <URLs or "empty">
Troubleshoot/Diagnostic message (if any): <verbatim quote>

## Check 2 — Live pixel fire
2A — Page load:
  - Total googleads requests: ___
  - AW-18056461576 instances: ___
  - AW-11389531744 instances: ___
  - All status codes: ___

2B — View product:
  - New googleads requests fired: YES / NO
  - URL/token of any matching request: ___

2C — Add to cart:
  - add_to_cart request fired (token VJ6hCPGd0KMcEIj6_qFD): YES / NO
  - Status: ___

2D — Begin checkout:
  - begin_checkout request fired (token HDu_CO6d0KMcEIj6_qFD): YES / NO
  - Status: ___

## Verdict
Based on Check 1 + 2:
- [ ] Pixel infrastructure works, Google's verification is just lagging → wait it out, flip when ready
- [ ] Pixel fires for everything EXCEPT purchase → real bug at thank-you page level, need fresh test order
- [ ] Pixel doesn't fire at all → real broken config, deeper fix needed

## Anything weird
<free-form>
```

Commit + Syncthing-propagate. No git push needed (Tristan or main session handles that).

## What you are NOT doing

- Placing test orders
- Modifying ANY settings (Google Ads or Shopify)
- Flipping the campaign
- Touching billing
- Touching MC
- Logging in for Tristan — surface login walls if hit, don't bypass
