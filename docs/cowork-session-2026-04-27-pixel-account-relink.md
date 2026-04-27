# Cowork Session — 2026-04-27 — Pixel Account Re-link

## Status — STOPPED PRE-EXECUTION

Did not perform Task 1, 2, or 3. Stopped per brief's hard rule:

> *"If any UI flow looks materially different from these steps (Shopify could have changed the G&Y app interface) → Stop, write findings into the handoff doc, end the session."*

The Google & YouTube app's UI no longer matches what the brief assumed. Specifics below.

---

## Task 1 — Re-link Google Ads account — NOT ATTEMPTED

- Wrong account that was disconnected (name + ID): N/A — never reached a disconnect button
- Right account connected: NO
- Picker contents at OAuth step: never reached
- Pre-disconnect screenshot captured: NO
- Anything weird: see "What I actually saw" below

## Task 2 — Storefront pixel verification — NOT ATTEMPTED

- All AW- refs in HTML are AW-18056461576: NO (unchanged from start of session — still AW-11389531744)
- AW-11389531744 still appears anywhere: YES (presumably; not re-checked since no change was made)
- Time between Task 1 completion and Task 2 verification: N/A
- Anything weird: N/A

## Task 3 — Test order — NOT ATTEMPTED

- Order # placed: none
- Thank-you URL: N/A
- Order total at checkout: N/A
- Order cancelled + archived: N/A
- Anything weird: N/A

## Task 4 — Cleanup — NOT NEEDED

- TESTZERO-20260427-pixel deleted: N/A (never created)
- Test free-shipping discount deleted (or N/A): N/A
- Pre-existing 4 codes still intact: assumed YES (not touched)

## Status for main session

- Pixel re-link completed: **NO**
- Test order placed: **NO**
- Webpages tab check: NOT DONE — still pointless until pixel actually re-linked

---

## What I actually saw

**Entry path tried:**
- `https://admin.shopify.com/store/dpxzef-st/apps/google` → auto-redirected to `/apps/google/onboarding`
- Direct `/apps/google/settings` → empty page (404-ish, no UI)
- Left-nav "Google & YouTube" → same `/apps/google/onboarding`

**What `/apps/google/onboarding` shows:**
- Big title: "Get started with Google & YouTube"
- Single setup card titled "Set up your online store" with progress "**3 of 5 tasks completed**"
  - ✓ Your Google account
  - ✓ Connect your Google Merchant Center account (`5296797260`)
  - ⊙ Check your online store requirements (currently expanded; sub-tasks: ✓ Add valid payment method, ✓ Create online store, ✓ Add refund policy + ToS, ⊙ Confirm contact information added)
  - ⊙ Confirm your recommended store setup
  - ⊙ Agree to the terms and conditions
- Right-side carousel slide 1/2: a card titled **"Just want to set up Google Ads conversion measurement?"** with a "Get started" button. Body says "*You can set up Google Ads conversion measurement without connecting a Merchant Center account.*"

**What I did NOT see anywhere:**
- A **Settings tab** inside the app — there is no tabbed nav at all
- A **Google Ads section/card** showing "Currently linked: <name> / <Customer ID>" with a Disconnect button
- A **gear/⚙ icon** in the top right of the app interface

**The "⋯" menu in the top right of the app frame** contains only:
- Manage app
- Get support
- Review app
- Pin to your navigation
- Uninstall

None of those are an Ads-account sub-link manager.

**The app iframe is cross-origin** (`https://channel-app.google/...`), so:
- Accessibility-tree reads (`read_page`, `find`) cannot see anything inside the iframe
- Wheel scroll events at iframe coordinates do not scroll the iframe content
- Direct script access into the iframe is blocked
- Clicks at the visible "Get started" button (right carousel card) **did not produce any visible state change** — no popup, no new tab in this browser group, no navigation. Either the click did not register, or it tried to open in a window that's not in the MCP-controlled tab group, or the iframe handler discarded it. Could not diagnose further from outside the iframe.

**Chrome did crash once** mid-session (extension disconnected). After reconnecting, behavior was the same.

---

## Hypotheses for the main session to consider

1. **The G&Y app UI has been redesigned**. The brief assumed a Settings/gear-driven flow exposing each linked Google product (Ads / Merchant Center / GA4 / Business Profile) with individual disconnect buttons. What's currently rendered is an onboarding wizard that — at 3 of 5 task completion — does not expose those sub-links at all. The wizard may need to hit 5/5 before the post-onboarding "manage linked accounts" view becomes reachable.

2. **The "Just want to set up Google Ads conversion measurement?" carousel card may be the intended path** — clicking "Get started" on it may launch an OAuth flow that re-binds the Ads account to the channel-app config (which is exactly what we want, regardless of whether the wording says "set up" or "re-link"). My click attempts did not visibly trigger anything from outside the iframe; the user attempting this in their own (non-cowork) Chrome session would be a much better test, since the click would actually reach the iframe's event handlers without the Chrome-extension layer.

3. **There may be a "Manage linked accounts" deep-link inside the iframe I cannot reach.** Inside-iframe content is invisible to me. The user, looking at the same page in a normal tab, may immediately spot a "Manage" / "Linked services" / "..." control I literally cannot perceive.

4. **Re-OAuth via Merchant Center may be the only path.** Disconnecting and reconnecting Merchant Center could force a fresh OAuth that re-picks the Ads account by side effect. This is riskier than the brief intended (the brief explicitly said NOT to touch Merchant Center) so I did not do it.

5. **There may be an entirely different surface for managing Ads links** — e.g. directly in Google Ads (`ads.google.com` → Tools & Settings → Linked accounts → Shopify), where the wrong Ads account `11389531744` could revoke the Shopify link, after which the next OAuth from Shopify's side would have to pick a different account. This is also out-of-scope for the brief.

---

## Recommended next step (suggestion only — main session decides)

Have the user open the G&Y app themselves, in a normal (non-cowork) Chrome session, scroll through the entire onboarding page, and screenshot whatever they see — especially what's below the visible "Continue" button and what the "Get started" carousel button does when *they* click it. Then either re-issue the brief with corrected steps, or pivot to disconnecting `11389531744` from the Google Ads side.

---

## Untouched

Per the brief's guardrails: did not touch Merchant Center, GA4 link, Business Profile link, the paused `8BL-Shopping-Games` campaign, the G&Y app installation itself, any discount codes, products, orders, themes, or env files.
