# Pixel Re-link — DIY Playbook (post-cowork-stop 2026-04-27)

Goal: get the Shopify Google & YouTube app to fire conversion pixels at `AW-18056461576` (your real account `822-210-2291`) instead of the wrong `AW-11389531744`.

Cowork stopped because the G&Y app's iframe is cross-origin (`channel-app.google`) and Chrome MCP can't see inside it. Your normal Chrome session has no such limit — you'll see and click straight into it.

Try paths in order. Each takes 2–5 min. Stop as soon as one works.

---

## Path A — "Set up Google Ads conversion measurement" carousel button (most likely)

This card explicitly says "set up Google Ads conversion measurement without connecting a Merchant Center account" — strongly suggests an Ads-only OAuth flow that bypasses the MC-coupled main wizard. The cowork's clicks on it produced no visible reaction, but their Chrome MCP layer was eating the click.

1. Shopify admin → **Apps** → **Google & YouTube**.
2. On the right-side carousel, find the slide titled **"Just want to set up Google Ads conversion measurement?"** Click **"Get started"**.
3. Whatever flow opens — go through it. Sign in with your normal Google identity.
4. **At any account picker / consent screen, explicitly select Customer ID `822-210-2291` ("8-Bit Legacy")**. Reject any prompt to create a new account or accept Google's default.
5. After completion, jump to the **Verify** step at the bottom of this doc.

If the "Get started" button does nothing in your normal browser either, skip to Path B.

---

## Path B — Finish the onboarding to 5/5, then use the post-onboarding Settings page

The cowork found the app stuck at 3/5 onboarding tasks. Settings/sub-link management likely doesn't surface until 5/5.

Remaining tasks:
- ⊙ Check your online store requirements → sub-task: **Confirm contact information added** (this is the gate that's been mentioned in 2-3 prior session docs as outstanding)
- ⊙ Confirm your recommended store setup
- ⊙ Agree to the terms and conditions

1. Online Store → Preferences → confirm contact info (business name, address, phone, email) is filled in. Save.
2. Back in G&Y app, click the "Confirm contact information" sub-task — it should auto-resolve and tick green.
3. Click **"Confirm your recommended store setup"** — review what it shows, accept defaults if reasonable.
4. Click **"Agree to the terms and conditions"** — read, accept.
5. Wizard should flip to 5/5 and the app's main interface should change. Look for a **Settings** tab, **Linked accounts** card, or a **gear icon** that wasn't visible before.
6. Find the **Google Ads** section showing the linked account. If it's `AW-11389531744` / not-`822-210-2291`, click **Disconnect** → **Reconnect** → pick `822-210-2291` in the OAuth picker.
7. Verify (bottom of this doc).

---

## Path C — Revoke the link from the wrong-account side in Google Ads

Only if A and B fail. Requires that you have admin access to whatever Google Ads account `AW-11389531744` is — could be a Shopify-auto-created account in your same Google identity.

1. `https://ads.google.com` → top-right account-switcher → see if `AW-11389531744` (or any Shopify-created account) appears alongside `822-210-2291`. If yes:
2. Switch into that wrong account.
3. Tools (wrench) → **Setup** → **Linked accounts**.
4. Find the **Shopify** entry → **Unlink** / **Revoke**.
5. Switch back to `822-210-2291`. Tools → Linked accounts → confirm Shopify shows as **available to link** or already linked correctly.
6. Back in Shopify G&Y app, the link should auto-flip to `822-210-2291`. If not, redo Path A's "Get started" — the OAuth picker now has only one valid choice.

If `AW-11389531744` is NOT in your account-switcher (i.e. it's a Shopify-managed account you don't have direct access to), this path won't work — fall back to A or B, or contact Shopify Support and tell them: *"The Google & YouTube app on store dpxzef-st is firing pixels to AW-11389531744 instead of my actual Google Ads account 822-210-2291. Please re-link Ads to 822-210-2291."*

---

## Path D — Nuclear: full uninstall + reinstall of G&Y app (last resort)

The 4/24 cowork already did this once. It's what got us into the wrong-account state, but doing it again **with explicit account selection** at every OAuth step might thread the needle. Risk: loses the canonical-tag-owner state we won on 4/24, and may leave us in another wrong-state.

Don't do this unless A, B, and C all fail. If you reach this point, ping me first and I'll think through it before you click Uninstall.

---

## Verify (always run after any path completes)

Two checks. Both must pass.

### Check 1 — storefront HTML (immediate)

```bash
curl -s -A "Mozilla/5.0" https://8bitlegacy.com/ | grep -oE 'AW-[0-9]+' | sort -u
```

- Pass: only `AW-18056461576` appears.
- Fail: `AW-11389531744` still appears anywhere.

If fail: hard-refresh storefront a few times, wait 60 sec, re-run. Shopify caches the bootstrap config briefly. If still wrong after 5 min, the path didn't take — try the next path.

### Check 2 — fire a Purchase event (test order)

1. Shopify admin → Discounts → create code `TESTZERO-20260427` → 100% off "Abra (43/102) - Base" → 1 use total → save.
2. Incognito → `8bitlegacy.com` → add Abra → checkout → apply code → real shipping address → complete checkout (won't charge $0).
3. Note the order #, capture the thank-you URL.
4. Cancel + archive the order (More actions → Cancel → reason "Other" → restock checked → don't notify customer).
5. Delete the discount code.

Then ping me — I'll handle the 2–4h Google reporting lag, the Webpages tab confirmation in `822-210-2291`, and the campaign flip to ENABLED via API.

---

## Don't touch

- Merchant Center connection (`5296797260` is correct)
- GA4 (`G-09HMHWDE5K` is correct)
- The paused campaign `8BL-Shopping-Games` — I flip it via API after pixel confirmed
- Code, env files, themes, products, orders
