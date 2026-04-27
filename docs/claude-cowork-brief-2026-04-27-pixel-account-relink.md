# Claude Cowork Brief — 2026-04-27 — Pixel Fix: Re-link Correct Google Ads Account

## TL;DR

The Google Ads pixel is firing to the **WRONG Google Ads account**. The Google & YouTube Shopify app is sending all 7 conversion events to `AW-11389531744`, but the user's actual account is `AW-18056461576` (Customer ID `822-210-2291`).

Your job: open Shopify admin → Google & YouTube app → disconnect the wrong Ads account, reconnect the right one, verify, then place a test order to confirm the pixel finally fires into the correct account.

This is the third pixel-fix attempt. Don't deviate from the steps below. Two prior attempts (4/24 uninstall+reinstall+migrate-tags, 4/25 cleanup+verify) failed precisely because the wrong-account link was never spotted. It has now been spotted via direct inspection of the live storefront HTML — see "How we know" below if you need confirmation context.

---

## How we know (proof, in case you need it for the handoff)

`curl https://8bitlegacy.com/` returns the Shopify Web Pixels Manager bootstrap inline. Inside `webPixelsConfigList`, the Google & YouTube app pixel (id `2414444578`, apiClientId `1780363`) has this `gtag_events` config:

```
"action_label": ["MC-67TSX3DX27","MC-YLE2C6JRCH","G-09HMHWDE5K","AW-11389531744"]
```

That `AW-11389531744` is the WRONG account.

The correct account is `AW-18056461576` (= Customer ID `822-210-2291`, the 8-Bit Legacy account where all conversion actions are defined and where the campaign `8BL-Shopping-Games` lives).

These are two different Google Ads accounts. Account `11389531744` ≠ `8222102291`. Events firing to the wrong account cannot show up in the right one. Hence:

- All 7 conversion actions show 0 conversions over 14+ days in account 822
- Webpages tab is empty in account 822
- Real order #1070 didn't appear in account 822

This was almost certainly caused by the 4/24 reinstall+migrate-tags wizard, which re-OAuthed and either (a) chose a Shopify-auto-created Ads account by default, or (b) the user's Google identity has another Ads account that was selected instead of 822-210-2291.

---

## Hard guardrails

- ✗ Do NOT touch Merchant Center settings (it's correctly linked, MC ID `5296797260`)
- ✗ Do NOT touch the Google Analytics 4 link (`G-09HMHWDE5K` is correct)
- ✗ Do NOT touch the Business Profile link
- ✗ Do NOT enable the paused Google Ads campaign (`8BL-Shopping-Games`, ID `23766662629`) — main session does that flip via API after you confirm pixel works
- ✗ Do NOT uninstall the Google & YouTube app a second time. The 4/24 session already did that. We don't want to lose the now-canonical tag injection. Only the **Ads account sub-link** needs swapping.
- ✗ Do NOT touch any Shopify discounts, products, orders, themes, or scripts beyond what's specified for Task 3
- ✗ Do NOT modify `config/.env`, dashboard env, or any code — this fix is 100% in the Shopify admin UI

---

## Task 1 — Re-link correct Google Ads account in Google & YouTube app — 5–10 min

### Steps

1. Sign in to Shopify admin (`8bitlegacy.myshopify.com/admin`).
2. Left nav → **Apps** → click **Google & YouTube** (the official channel app).
3. Once inside the app, find the **Settings** tab (or the gear/⚙ icon in the top-right of the app interface).
4. Look for the **"Google Ads"** section / card. It will show the currently-linked Ads account name and ID.
   - **Capture a screenshot** of this section before doing anything (we want a record of which account was wrongly linked — could be useful intel about how the migration went sideways).
5. Click **"Disconnect"** (or "Unlink", or the equivalent action) on the Ads account.
   - If the app prompts to also disconnect Merchant Center / GA4 / Business Profile, **say no / cancel**. Only the Ads link should be touched.
6. After disconnect, click **"Connect Google Ads"** (or equivalent re-link button).
7. Google OAuth popup appears. Sign in with the user's personal Google identity — **the same email used for the 8-Bit Legacy Google Ads account**. (User's primary email is `tristanaddi1@gmail.com` per the account profile, but defer to whatever the user is signed in with in the current Chrome session.)
8. **CRITICAL:** When the account-picker step asks which Google Ads account to connect, **pick the one with Customer ID `822-210-2291`** (display name: **"8-Bit Legacy"**). Do NOT pick any other account that appears in the list.
   - If only one account appears: that should be the right one — verify the displayed Customer ID is `822-210-2291` before clicking through.
   - If multiple accounts appear (likely — there's at least one wrong one in there): explicitly pick `822-210-2291`.
   - If `822-210-2291` does NOT appear in the picker: **STOP.** Do not connect anything. Write up the picker contents (account names + IDs visible) in the handoff and end the session. Could mean the OAuth identity is wrong.
9. Complete the connection flow. Wait until the app shows the Ads account as connected and the Customer ID `822-210-2291` is displayed.

### Success criteria

- [ ] Old Ads account disconnected (screenshot captured first)
- [ ] New Ads account connected
- [ ] Customer ID `822-210-2291` displayed in the Google & YouTube app's Settings → Google Ads section

---

## Task 2 — Verify the live storefront now references the correct AW ID — 2 min

This is the authoritative pixel-fired check. The Web Pixels Manager config gets re-rendered on the storefront when the app config changes, so the change should show up immediately after Task 1.

### Steps

1. Open a new **incognito** Chrome tab.
2. Open DevTools → Network tab (or just View Source on the page).
3. Navigate to `https://8bitlegacy.com/`.
4. View page source (Ctrl+U / Cmd+U) or use DevTools to inspect the rendered HTML.
5. **Search** the HTML for the string `AW-`.
6. Expected: every `AW-XXXXX` reference in the `action_label` arrays under `gtag_events` should be **`AW-18056461576`** (the correct account).
7. **Should NOT see:** `AW-11389531744` (the wrong account) anywhere on the page.

### What to do with the results

- All `AW-` refs are `AW-18056461576` and no `AW-11389531744` appears → ✅ pixel is now wired correctly. Proceed to Task 3.
- Still seeing `AW-11389531744` → the disconnect+reconnect didn't take effect. **Hard-refresh** the storefront (Ctrl+Shift+R), wait 60s, try again. Shopify sometimes caches the bootstrap config for ~30-60s after settings changes.
- After 5 min still seeing `AW-11389531744` → STOP. Write up findings in the handoff and end. Don't proceed to Task 3.
- Mixed (some `AW-18056461576`, some `AW-11389531744`) → STOP. This shouldn't happen but if it does, write it up and end.

### Success criteria

- [ ] All `AW-` references in storefront HTML are `AW-18056461576`
- [ ] Zero references to `AW-11389531744` anywhere

---

## Task 3 — Place a $0 test order to fire the Purchase pixel — 5 min

Only proceed if Task 2 passed cleanly. This generates a real conversion event under the (now correctly-linked) account.

### Setup

1. Create a 100% off discount code for a single product:
   - Shopify admin → Discounts → **Create discount** → **Amount off products**
   - Title: `TESTZERO-20260427-pixel`
   - Method: **Discount code**
   - Code: `TESTZERO-20260427-pixel`
   - Discount value: **Percentage** → **100%**
   - Applies to: **Specific products** → search and select **"Abra (43/102) - Base"** (the same low-value Pokemon card used in prior pixel fixes)
   - Minimum purchase requirements: None
   - Customer eligibility: All customers
   - Maximum discount uses: total uses **1**, "Limit to one use per customer" **checked**
   - Active dates: starts now, ends today 11:59 PM ET
   - **Save**.

2. Optionally also create an automatic free-shipping discount with a name that's clearly internal (e.g. `Test free shipping pixel-fix-2026-04-27`) so the user doesn't get charged shipping. **If you do this, note the ID for cleanup in Task 4.** Or just don't bother and let shipping be charged $0 if the test product has no shipping requirement.

### Place the order

1. Open `8bitlegacy.com` in a fresh incognito window (separate from the Task 2 verification tab to keep the analysis clean — but having DevTools Network open is fine and encouraged).
2. Add **Abra (43/102) - Base** to cart (any variant).
3. Go to checkout.
4. Apply discount code `TESTZERO-20260427-pixel` — order total should reduce to $0.00 (or $0 + shipping if shipping isn't covered).
5. Use real shipping address (Tristan, 103 Dogleg Dr, Moultrie GA 31788) so the order isn't flagged as fake. Email: `tristanaddi1+pixeltest27@gmail.com` (the `+pixeltest27` suffix routes to the same inbox but distinguishes the test order in receipts).
6. **Don't pay with a real card.** If checkout requires payment, use Shopify's test mode bogus gateway if enabled, or use a Shop Pay account if available without re-entering card. If no $0-friendly path exists, use the user's real card — Shopify won't charge $0.
7. Complete the checkout. Capture the thank-you page URL — paste it into the handoff.
8. Cancel the order immediately:
   - Shopify admin → Orders → find the just-placed order → top-right **More actions** → **Cancel order**
   - Reason: **Other** → staff note: `internal test for Google Ads pixel verification 2026-04-27`
   - Restock: **checked**
   - Customer notification: **unchecked**
   - Archive after cancel.

### Success criteria

- [ ] Test order placed at $0
- [ ] Thank-you page URL captured
- [ ] Order cancelled + archived
- [ ] Order DID NOT route to eBay fulfillment

---

## Task 4 — Cleanup — 2 min

1. Delete `TESTZERO-20260427-pixel` discount code (Discounts → search → row → ⋮ → Delete).
2. Delete the test free-shipping automatic discount (if you created one in Task 3).
3. Verify in Discounts list: only the user's pre-existing 4 codes remain (`SHOPAGAINFOR10`, `SHOPEXTRA10` Expired, `LUNCHBOX`, `8BITNEW`) plus zero test codes.

---

## Handoff

Write `docs/cowork-session-2026-04-27-pixel-account-relink.md` with this structure:

```
# Cowork Session — 2026-04-27 — Pixel Account Re-link

## Task 1 — Re-link Google Ads account
- Wrong account that was disconnected (name + ID): <fill in>
- Right account connected: 822-210-2291 (8-Bit Legacy)? YES / NO
- Picker contents at OAuth step (list all account name+IDs you saw): <fill in>
- Pre-disconnect screenshot captured: YES / NO
- Anything weird:

## Task 2 — Storefront pixel verification
- All AW- refs in HTML are AW-18056461576: YES / NO
- AW-11389531744 still appears anywhere: YES / NO
- Time between Task 1 completion and Task 2 verification: <minutes>
- Anything weird:

## Task 3 — Test order
- Order # placed:
- Thank-you URL:
- Order total at checkout:
- Order cancelled + archived: YES / NO
- Anything weird:

## Task 4 — Cleanup
- TESTZERO-20260427-pixel deleted: YES / NO
- Test free-shipping discount deleted (or N/A): YES / N/A
- Pre-existing 4 codes still intact: YES / NO

## Status for main session
- Pixel re-link completed: YES / NO
- Test order placed: YES / NO
- Webpages tab check: NOT DONE (main session will check after 2-4h Google lag)
```

Commit + Syncthing-propagate. No git push needed.

---

## What you are NOT doing

- Not flipping the campaign to ENABLED — main session does that via API after Webpages-tab confirmation
- Not editing any code, env file, theme, or product
- Not touching TrueNAS, the VPS, Merchant Center, or other linked services
- Not running another full reinstall of the Google & YouTube app — only swapping the Ads sub-link
- Not waiting for the 2-4h Google reporting lag to verify Webpages tab — main session will handle that handoff later

---

## If anything is ambiguous or breaks

Stop, write findings into the handoff doc, end the session. The user's last instruction is "make sure it gets done right" — so erring on the side of stopping and reporting is preferred over guessing. Specifically stop and report if:

- The OAuth picker doesn't show `822-210-2291`
- The storefront HTML doesn't update after 5+ min
- The test order won't reduce to $0 even with the discount
- Any UI flow looks materially different from these steps (Shopify could have changed the G&Y app interface)
