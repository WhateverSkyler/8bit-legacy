# Claude Cowork Brief — 2026-04-25 — Discount Cleanup + Pixel Verification

## What this session is doing

Two browser-only tasks the main API-driven session can't reach:

1. **Delete 3 lingering test discounts** in Shopify admin (the auto free-shipping one is contaminating live customer orders right now)
2. **Verify the Google Ads Purchase pixel** by checking the Webpages tab for the
   thank-you URL of real order #1070 (placed 10:49 ET today, $146.92, 3 line items)

After this, main session can flip `8BL-Shopping-Games` from PAUSED to ENABLED.

## Hard guardrails

- Do NOT touch any other discount. Pre-existing real codes to leave alone:
  `SHOPAGAINFOR10`, `SHOPEXTRA10` (Expired), `LUNCHBOX`, `8BITNEW`.
- Do NOT create any new discounts.
- Do NOT click "Enable" on the paused Google Ads campaign — main session will
  handle that flip via the API after you report Webpages-tab status.
- Do NOT touch Merchant Center settings.

---

## Task 1 — Delete 3 test discounts (Shopify admin) — 5 min

**Why urgent:** the automatic free-shipping discount auto-applies to every
real customer order right now. Customers see a line `Test order free shipping
v2 (pixel-fix 2026-04-24)` at checkout. $0 dollar impact but obviously not
something we want on a live receipt.

### Targets

| Type | Title / Code | Discount ID |
|---|---|---|
| Automatic | `Test order free shipping v2 (pixel-fix 2026-04-24)` | 1415914815522 |
| Code | `TESTZERO-20260424-v2` | 1415914553378 |
| Code | `TESTZERO-20260424-v3` | 1415938375714 |

### Steps

1. Sign in to Shopify admin (`8bitlegacy.myshopify.com/admin`).
2. Left nav → **Discounts**.
3. For the **automatic** discount:
   - Search `pixel-fix` or `Test order free shipping v2`
   - Click row → top-right ⋮ → **Delete discount** → confirm
4. For each **TESTZERO** code:
   - Search `TESTZERO`
   - Click row → ⋮ → **Delete discount** → confirm
5. **Verify in incognito:** open `8bitlegacy.com`, add ANY game-only product
   to cart, go to checkout. Confirm no `Test order free shipping v2` line
   appears in the order summary. (You don't need to complete the order — just
   look at the line items section of checkout.)

### Success criteria

- [ ] All 3 deleted from Discounts list
- [ ] Pre-existing 4 codes still intact
- [ ] Incognito checkout shows no `Test order free shipping v2` line

---

## Task 2 — Verify Google Ads Purchase pixel via Webpages tab — 5 min

**Why:** Real order #1070 is the proper test of yesterday's 2C pixel fix
(uninstall+reinstall+migrate-tags). The main session's GAQL query has shown
0 Purchase conversions for the last 14 days, but the Ads UI's "Webpages" tab
shows the actual thank-you URLs where the pixel fired regardless of campaign
attribution. That's the authoritative pixel-fired check.

### Order facts (paste into Webpages tab search if it asks)

- **Shopify order:** `#1070`
- **Placed:** 2026-04-25 at 10:49 ET (UTC-4)
- **Total:** $146.92
- **Line items:** Tekken 3 (PS1), Monster Lab (PS2), Lucario ex (82/142) Stellar Crown
- **Confirmation page URL pattern:** `8bitlegacy.com/.../checkouts/.../thank-you` or `8bitlegacy.com/checkouts/c/.../thank_you`

### Steps

1. Open Google Ads (`ads.google.com`) — should resolve to account
   `822-210-2291` (8-Bit Legacy).
2. Top-right **Tools** (wrench icon) → **Conversions** → **Summary** (or
   "Conversion actions").
3. Click the row labeled **"Google Shopping App Purchase"**.
4. In the conversion-action detail page, click the **"Webpages"** tab.
   - This tab shows URLs where this conversion has fired.
5. **What to look for:**
   - Any URL from `8bitlegacy.com` that looks like a thank-you / order-confirm
     page (paths usually contain `/thank_you`, `/orders/`, or `/checkouts/`).
   - Bonus credit if you spot a URL referencing order #1070's checkout token
     (the Shopify order receipt URL contains a token, not the order number,
     but you can cross-reference timestamp).

### Outcomes — exactly what to report back

- **Found a thank-you URL with timestamp on/after 10:49 ET 2026-04-25:**
  → Pixel is confirmed working. Main session flips campaign.
- **Webpages tab is empty or only contains stale (pre-2026-04-24) URLs:**
  → Pixel still not firing. Yesterday's 2C fix didn't fully resolve. Needs
  next-pass diagnosis (see "If pixel still broken" below).
- **You see a thank-you URL but can't tell if it's order #1070:**
  → Treat as "fired." Main session will cross-reference. Just paste the URL
  and timestamp into the handoff doc.

### If pixel still broken (Webpages empty after 4+ hours)

Don't try to fix it in this session — write up findings and stop. Likely next
diagnosis pass involves:
- Checking if **MonsterInsights** is still injecting GA4 in parallel (it
  competed with the Google & YouTube app pre-fix; migration may have made
  G&Y canonical but didn't uninstall MI).
- The **Online Store contact-info confirmation** gate in the G&Y onboarding
  is still pending — could be blocking full tag injection.
- May need to install **Google Tag Assistant Companion** on the desktop and
  do a manual checkout while DevTools is open on the storefront tab to see
  what tags actually fire on the thank-you redirect.

### Success criteria

- [ ] Reported one of the 3 outcomes above with a URL + timestamp if found

---

## Handoff

Write `docs/cowork-session-2026-04-25-cleanup-and-pixel.md` with:

```
## Task 1 — Discount cleanup
- Deleted: <3 IDs>
- Incognito checkout test: PASS / FAIL (paste cart subtotal + screenshot of
  order summary if you have one)

## Task 2 — Pixel Webpages-tab verification
- Result: FIRED / NOT FIRED / AMBIGUOUS
- URL(s) seen (or "empty"):
- Earliest timestamp:
- Anything weird:
```

Commit + Syncthing-propagate. No git push needed.

## What you are NOT doing

- Not touching the Google Ads campaign status (main session does the flip)
- Not editing any code
- Not interacting with TrueNAS, the VPS, or Merchant Center
- Not modifying any product or order
