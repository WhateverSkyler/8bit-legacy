# Claude Cowork Brief — 2026-04-24 — Fix Broken Google Ads Purchase Pixel

## The task in one sentence

The Google Ads Purchase conversion action has never fired (Webpages tab empty despite 5 real orders + 1 test order since 4/8/2026). Diagnose and fix so the tag actually records events before we flip the paused campaign.

## Hard guardrails

- **DO NOT enable the Google Ads campaign.** It stays PAUSED. Main session will flip it via API after pixel is verified working.
- **DO NOT uninstall Merchant Center or the Ads account** directly.
- **Only modify the Shopify `Google & YouTube` app** if needed.
- If anything unexpected happens, STOP and report.

## Context

- Google Ads customer ID: `822-210-2291`
- Merchant Center ID: `5296797260`
- Conversion action in question: `Google Shopping App Purchase` (inside Google Ads → Tools → Conversions)
- Tag ID per prior audits: `AW-18056461576` (also `G-09HMHWDE5K` for GA4, `GT-TBZRNKQC` server-side)
- Purchase action shows "Active" status but "No recent conversions" and the **Webpages tab is empty** — meaning the tag has never successfully fired to this conversion action for any URL.
- Today's $0 test order (#1067 via code `TESTZERO-20260424`, 10:57 AM ET) did NOT register after 4 hours. Neither did any of the 5 real orders in the last 2 weeks.
- We've verified the conversion action's settings look correct (Purchase category, Primary, $1 default for $0 orders, Enhanced Conversions enabled).

## Step 1 — Diagnose with Google Tag Assistant (5 min)

Purpose: figure out whether the tag is even firing on the storefront before we go changing anything.

1. Install the Chrome extension **"Tag Assistant Companion"** (by Google) from the Chrome Web Store.
2. Open a fresh incognito Chrome window **with the extension enabled**. In Tag Assistant, click **Add domain** → enter `8bitlegacy.com` → start debug.
3. In Shopify admin, quickly create a discount pair (same pattern as earlier today):
   - `TESTZERO-20260424-v2` — 100% off on one specific cheap in-stock product, one use, one per customer, combinable with shipping, active now, expires tomorrow.
   - Automatic free-shipping discount active now, combinable with amount-off discounts (or check whether the existing "Test order free shipping" rule is still active from earlier today).
4. In the incognito window: go to `8bitlegacy.com` → add that product → Checkout → apply `TESTZERO-20260424-v2` → confirm total is $0.00 → place order.
5. On the thank-you page, click the Tag Assistant icon and **screenshot** the tag list. Also expand each Google Ads tag so we can see the conversion label + value fields.

**What to report back:**
- Tag Assistant screenshot from the thank-you page
- Is there a tag with ID `AW-18056461576` firing a `purchase` conversion event on the thank-you page?
- Is there a DIFFERENT `AW-XXXXXXXXXX` tag firing instead?
- Or is there NO Google Ads tag at all (maybe only GA4 `G-XXXXXXXXX`)?

## Step 2 — Pick the ONE fix that matches the diagnosis

### 2A — Case: no Google Ads tag fires on the thank-you page

The Shopify Google & YouTube app isn't actually injecting the tag. Fix:

1. Shopify admin → **Apps** → **Google & YouTube** → Settings → find the **Conversion tracking** or **Measurement** toggle → turn OFF → wait 10 seconds → turn ON.
2. Create a fresh test order using a new 100%-off code `TESTZERO-20260424-v3`.
3. Re-verify with Tag Assistant on the thank-you page.
4. If still no tag, escalate to Step 2C.

### 2B — Case: a Google Ads tag fires but with a different `AW-XXXXXXXXXX` ID

The app is linked to the wrong Ads account. Fix:

1. Shopify admin → **Apps** → **Google & YouTube** → Settings → **Account linking** or **Linked accounts**
2. Confirm the linked Google Ads account is **822-210-2291** (8-Bit Legacy).
3. If it's a different account: disconnect, then reconnect → pick **822-210-2291**.
4. Test order + Tag Assistant check.

### 2C — Case: 2A didn't fix it, OR something else is clearly wrong

Nuclear option — uninstall and reinstall the Google & YouTube Shopify app.

**Before uninstalling — screenshot the current setup** for rollback reference:
- Apps page showing the Google & YouTube app version
- The app's main settings page showing current linked Merchant Center + Google Ads accounts
- The Merchant Center product count (should be ~12,000)

Uninstall steps:

1. Shopify admin → **Apps** → "Google & YouTube" → **Uninstall app**. Confirm.
2. Reinstall from the Shopify App Store: https://apps.shopify.com/google
3. During setup:
   - Link Merchant Center → pick existing account **5296797260** (do NOT create a new one)
   - Link Google Ads → pick **822-210-2291**
   - Enable Conversion tracking (Purchase, Add to Cart, Begin Checkout, Page View — all primary)
4. Wait 5 min for the app to re-inject tags.
5. Test order + Tag Assistant check.

**After reinstall verify these are still intact (do NOT need to re-do, just confirm):**
- Merchant Center → Products shows ~12,000 products (MC data is server-side, uninstall shouldn't touch it)
- A random CIB variant (e.g., `.hack GU Rebirth CIB`) still has its `mm-google-shopping.excluded_destination = ["Shopping_ads"]` metafield (variant metafields persist on the product, not in the app)

If either looks wrong, STOP and report — don't try to fix, main session will handle.

## Step 3 — Verify end-to-end (wait 2–4h after the fix-confirming test order)

1. Open Google Ads → Tools → Conversions → click row **"Google Shopping App Purchase"** → **Webpages** tab.
2. If there's at least one entry listed (with a URL like `/orders/xxx` or `/checkouts/xxx/thank_you`) → **PIXEL IS FIXED**. Report back.
3. If still empty after 4 hours → escalate back to Tristan. Do not apply more fixes.

## When you're done

Write handoff at `docs/cowork-session-2026-04-24-pixel-fix.md` with:
- Tag Assistant screenshot from Step 1
- Which fix path was taken (2A / 2B / 2C)
- Screenshot of the Webpages tab showing the new entry (proves Step 3)
- Any screenshots of "app settings" during Step 2
- Timestamps for the verification test order
- Any unexpected findings

Commit + push (Syncthing will sync locally):

```bash
cd ~/Projects/8bit-legacy
git add docs/cowork-session-2026-04-24-pixel-fix.md
git commit -m "Cowork 2026-04-24 pixel-fix: <short summary of what worked>"
git push  # OK if this fails on criticalmkt auth — Syncthing will propagate
```

Tell Tristan in chat: **"pixel is firing — Webpages tab shows the entry, ready to flip."** Main session will then bump budget to $22/day and enable the campaign via the Ads API.

## Success criteria

- [ ] Tag Assistant confirms `AW-18056461576` purchase tag fires on thank-you page of a $0 test order
- [ ] Google Ads → Purchase conversion action → Webpages tab shows at least one entry
- [ ] Handoff doc committed
- [ ] Tristan notified "pixel is firing"
