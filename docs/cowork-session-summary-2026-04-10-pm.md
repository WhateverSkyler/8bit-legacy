# Cowork Session Summary — 2026-04-10 PM

**Operator:** Claude (cowork / browser session, Mac)
**Paired with:** Terminal Claude session
**Brief:** `docs/claude-cowork-brief-mac-2026-04-10-pm.md`
**Guardrails honored:** Did not touch `scripts/`, did not run anything with `--apply`, did not touch Google Ads, did not place test orders, did not modify the live theme, did not modify any secrets.

---

## What I did

Worked through all 6 investigation tasks (A–F) from the brief using Shopify admin + the live storefront via the browser tools. Produced 6 deliverable docs (1 edit-in-place, 5 new) and this summary. No code, no scripts, no ad spend, no theme edits.

| # | Task | Deliverable | Status |
|---|------|-------------|--------|
| A | 10% off email popup audit | `docs/email-popup-audit-2026-04-10.md` (new) | Done |
| B | Sale smart collection verification | `docs/sale-collection-status-2026-04-10.md` (new) | Done |
| C | Recheck Shop sales channel | `docs/ecommerce-infrastructure-audit-2026-04-06.md` Task 5 (in-place edit) | Done |
| D | Homepage redesign notes below DotW | `docs/homepage-redesign-notes.md` (new) | Done |
| E | VPS dashboard auth check | `docs/vps-dashboard-status-2026-04-10.md` (new) | Done (blocked) |
| F | Conversion tracking pre-flight audit | `docs/google-ads-launch-plan.md` "Phase 0.1 audit" section (appended) | Done |

---

## What I found (top-line per task)

### Task A — Email popup (HIGH)
The "10% off" popup on `8bitlegacy.com` is **theme-native**, not wired to any installed email app. It posts to `/contact` with `contact[tags]=newsletter` and nothing more. MailMunch is installed but shows 853 subscribers, 0 sends, Last Contacted blank for every contact — it is a dead mirror. The promised 10% off code is **never emailed** to anyone. Active discount codes found: `8BITNEW` (4 uses — likely the intended popup code), `SHOPAGAINFOR10` (2), `LUNCHBOX` (0, GameCube sale), and `SHOPEXTRA10` which is **expired**. Fix is to install Shopify Email (free up to 10k/month) and build a welcome flow that actually sends `8BITNEW` when someone subscribes, then delete `SHOPEXTRA10`.

### Task B — Sale smart collection (HIGH)
"On Sale" collection exists (ID `483677044770`), is a proper smart collection with rule **"Compare-at price is not empty"**, has 15 products, and is published to Online Store + POS + Facebook/IG + TikTok + Google & YouTube. Two cleanups: (1) **NOT published to the Shop sales channel** (white dot), should be published; (2) the main nav has **two "Sale" links** — one points to `/collections/special-products` (legacy) and one to `/collections/on-sale` (the correct one). Kill the legacy link.

### Task C — Shop sales channel (MED)
**Likely resolved.** The sidebar black-dot indicator that was showing next to "Shop" cleared after a single visit to the channel, which in Shopify admin convention means it was a "new/unread notification" marker, not a persistent "Action needed" error badge. No error badges or warning text visible anywhere in the Sales channels page or Shop app sidebar. Could not get the embedded Shop catalog iframe to fully render (Shopify admin routing quirk — `InvalidStateError` in console, unrelated to merchant health). Tristan should do a 2-minute manual sanity check in a normal browser to fully close this out, but based on the indirect signals Task 5 is done.

### Task D — Homepage redesign notes (MED)
Tristan's "half-finished" feeling is **real** and mostly traces to **four root causes**:

1. **Two empty `bs_banner_three_image` theme sections** render with **0px height** between DotW→GameCube and GameCube→Nintendo Classics. This is the single biggest contributor to the "half-assed" look. Fix: delete them (5 min, free win) or populate them (Pokemon hero, Sale hero).
2. **Pokemon is entirely absent from the homepage** below the fold despite 1,176+ live Pokemon products. No hero slot, no tile, no grid. Add a Pokemon TCG product strip below Sony Classics.
3. **GameCube section is thin** — only 8 product cards vs 20 in each Classics grid, making the middle of the page feel like a downgrade. Also implicitly tells visitors "we're a GameCube store" which isn't true.
4. **No sale/promo reinforcement** below DotW — the 15-product On Sale collection appears nowhere on the homepage outside the 5 DotW tiles.

Recommended ~55 min total work in the customizer on a **duplicated theme** (nothing published until Tristan approves). Full ranked list + fix options in the doc. I did NOT apply any changes per the brief.

### Task E — VPS dashboard (LOW)
**Blocked.** `https://8bit.tristanaddi.com` is unreachable — nginx basic auth (401) sits in front of the Next.js dashboard and no credentials were supplied, so the browser returns an error page state. I could not verify the 5 scheduled jobs, circuit breaker status, or anything else inside the dashboard. Recommended fix: replace nginx basic auth with the Next.js app's own auth layer (one auth layer < two). Until then, automated health checks of `shopify-product-sync`, `google-ads-sync`, `fulfillment-check`, `price-sync`, `pokemon-price-sync` from future Claude sessions are not possible.

### Task F — Conversion tracking (LOW)
**Phase 0.1 is unblocked — but in a non-obvious way.** `window.gtag` and `window.dataLayer` are both **undefined** on the live storefront and DevTools Network shows no `googletagmanager`/`gtag` requests at page load. This initially looks like "conversion tracking is missing." **It isn't.** Shopify's Web Pixel Manager loads third-party pixels in a sandboxed web worker specifically so they can't read/write the storefront DOM, which is why DevTools can't see them.

Searching the storefront HTML for the customer-events config turned up a fully populated Google Tag setup via the Google & YouTube Shopify app (pixel id `900628514`), targeting three tag IDs: `G-09HMHWDE5K` (GA4), `AW-18056461576` (Google Ads conversions), `GT-TBZRNKQC` (server-side tag container). All 7 standard ecommerce events (`page_view`, `search`, `view_item`, `add_to_cart`, `begin_checkout`, `add_payment_info`, `purchase`) are mapped to conversion action labels on `AW-18056461576`. Enhanced conversions (`MC-YLE2C6JRCH`) also present.

**Key implications:**
- Do **NOT** install a "real" gtag.js snippet in the theme — it would double-count everything.
- Verification must be done in **Google Ads → Tools → Conversions**, not DevTools.
- The real pre-launch blocker is NOT Phase 0.1 — it's still **Task 2 from the April 6 audit**: the Google & YouTube Shopify app is connected to `tristanaddi1@gmail.com` / Ads account `438-063-8976`, but the target Ads account is `822-210-2291` under `sideshowtristan@gmail.com`. That account linking is the thing that actually blocks ad spend.

Full details and the event→action-label table are in `docs/google-ads-launch-plan.md` under the new "Phase 0.1 audit — 2026-04-10" section.

---

## What's blocked / needs Tristan

1. **VPS dashboard credentials or auth replacement** (Task E). Without this, future Claude sessions can't monitor the 5 scheduled jobs. Recommended: replace nginx basic auth with Next.js-native auth so there's one auth layer.
2. **Google Ads account linking** (pre-existing, from April 6 audit Task 2). Google & YouTube Shopify app is pointed at the wrong Ads account. Either (a) add `tristanaddi1@gmail.com` as admin on `822-210-2291` under `sideshowtristan@gmail.com`, or (b) disconnect+reconnect the app using `sideshowtristan@gmail.com`. **This is the real Google Ads launch blocker, not conversion tracking.**
3. **Homepage redesign approval** (Task D). 5 ranked issues with 55 min total of customizer work, awaiting Tristan's go/no-go on each. Nothing happens until he says so.
4. **Email popup product decision** (Task A). Does Tristan want to install Shopify Email and build the welcome flow, or use something else? The popup is currently a dead end from the user's perspective.
5. **Nav cleanup approval** (Task B). Remove the duplicate `/collections/special-products` "Sale" link and publish "On Sale" to the Shop channel.
6. **Shop sales channel final sanity check** (Task C). 2-minute manual check in a normal browser to fully close out the April 6 Task 5 item.

---

## What I did NOT do (safety ledger)

- Did not touch any file in `scripts/`
- Did not run anything with `--apply`
- Did not touch Google Ads (no campaign created, no bid changes, no negative keywords added)
- Did not place a test purchase
- Did not install any tag, pixel, script, or theme code
- Did not modify the live theme or duplicate the theme
- Did not change brand colors, fonts, or section order
- Did not modify any `.env` or secret
- Did not bypass nginx basic auth
- Did not collect or transmit any PII
- Did not send any email, post to any social channel, or submit any form

---

## Handoff note

All findings are written down in the docs listed above. The terminal Claude session can pick up where this one left off — specifically, it can act on the Task A recommendation (install Shopify Email) or the Task B nav cleanup whenever Tristan green-lights them. The real blocker for the Google Ads launch is the April 6 Task 2 (wrong Ads account linked), and that remains a manual task for Tristan himself.
