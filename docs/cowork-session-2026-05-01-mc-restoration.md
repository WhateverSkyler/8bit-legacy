# Cowork Session — 2026-05-01 — MC Catalog Restoration

## Outcome

- [ ] Catalog restored (≥ 5,000 products synced) at: __
- [ ] Partially restored: __ products, awaiting full propagation
- [ ] Restoration failed at tier ___, surfacing back to Tristan
- [x] **STOPPED AT PHASE 1 DIAGNOSIS — surfacing back to Tristan**

**Reason for stopping:** the cowork browser cannot reliably interact with the Shopify-embedded Google & YouTube app's iframe. Specifically: (a) clicking the "Additional settings to sync with Google Merchant Center" expander does not open it, (b) wheel/keyboard scroll inside the iframe is intercepted, and (c) one earlier click drifted dangerously close to a `Disconnect` button (mitigated immediately, no harm done — but the proximity convinced me not to keep guessing at click coordinates). Tier 2A (the "re-save Country/Language" action) requires reliable interaction with that exact iframe region. Continuing blindly would risk hitting Tier 2C (`Disconnect` Google account) without your explicit go-ahead, which the brief forbids.

**Recommendation:** Tristan executes Tier 2A himself in a normal browser, where the iframe responds to clicks. Phase 1 below confirms this is safe: Markets are clean, all 3 Google services are still connected, conversion measurement is on, and there's no policy/suspension banner anywhere. Tier 2A is essentially "open the country/language editor and click Save (or Resync if exposed)" — a 30-second action when the UI cooperates.

## Phase 1 — Diagnostics

### 1A — Manage products bulk editor

**Not directly accessible.** Tried:
- `https://admin.shopify.com/store/dpxzef-st/apps/google/products` → redirects to `/overview`
- `https://admin.shopify.com/store/dpxzef-st/apps/google/manage-products` → redirects to `/overview`
- Clicking the underlined "Total" text on the GMC card on the Overview page → no navigation
- The "..." kebab on the GMC card → no menu opened (likely an iframe-routing miss)

The Overview's GMC card shows the same numbers as last cowork: **Total 2 / Approved 2 / Limited 0 / Not Approved 0 / Under Review 0**. No filter chips or product list exposed at this UI surface.

Per the brief: documented and moved on.

### 1B — Shopify Markets

URL: `https://admin.shopify.com/store/dpxzef-st/markets`

| Market | Type | Status | Includes | Currency | Catalogs | Domain / language |
|---|---|---|---|---|---|---|
| **United States** | Region | **Active** | United States | **US Dollar** | All products | 8bitlegacy.com • English |

- Only one market exists. No Inactive / Paused / Draft / Coming soon entries.
- Market URL ID is `88038604834` — same number that's in Feed B's label `USD_88038604834`. Confirms Feed B is bound to this market.
- Parent market: "Store default"
- "Create International Market" call-to-action is visible (would create a new market — did NOT click).

**Verdict: Markets are clean.** Decision-table branch "Markets misconfigured → STOP" does NOT apply.

### 1C — G&Y Settings → Product feed → Countries / languages

Navigated to `https://admin.shopify.com/store/dpxzef-st/apps/google/settings` and used a JS workaround (`iframe.style.height = '3000px'`) to force the iframe tall enough to be visible without internal scrolling.

**Product feed section captured:**
- **Product sync: On** — "Automatically syncs products that are available in your online store with Google Merchant Center"
- **Additional settings to sync with Google Merchant Center: 3** — *collapsed, attempts to expand it via clicks did not open it*. The "3" badge implies 3 sub-items; the brief implies these are the country / language / shipping toggles.
- **Shipping Information: On** — "Automatically syncs your Shopify shipping information to Google Merchant Center"

**No error banners** anywhere on this page: no "Sync paused" / "Out of sync" / "Reconnect needed".

**No "Last sync" / "Last updated" timestamp** is exposed at this UI surface.

**The country list itself is NOT directly visible** — it lives behind the collapsed "Additional settings" expander, which I could not reliably open. Whether US is checked + nothing else, or whether some toggle is in a degraded state, cannot be confirmed from the cowork session. **This is the gap that necessitates stopping.**

What I CAN say from indirect evidence: Product sync = On, Markets has the US market Active with USD currency, the canonical Feed B (`USD_88038604834` / source `10643774057`) still exists in MC. So the country/language config is *probably* intact, and Tier 2A's "re-save without changing anything" is the right next step — but it has to be executed by you.

### 1D — Settings page sanity

**Google services panel:**
- Google Account: `tristanaddi1@gmail.com` ✓
- Connected Google services: 3 — all 3 show a `Disconnect` button (i.e. all 3 connected, no `Reconnect`/`Needs attention`/`Disconnected` prompts)
  - Google Merchant Center: `5296797260` ✓
  - Google Ads: `8222102291 (8-Bit Legacy)` ✓
  - Google Business Profile: `tristanaddi1@gmail.com` ✓

**Data sharing and tag management panel:**
- **Conversion measurement: On** (banner: "Required for Google Ads, YouTube, Google Analytics, and to add and update tags for conversion measurement, site analytics, remarketing, and more")
- Additional conversion measurement settings: 3 (collapsed — did NOT expand or toggle)

**Additional Google Ads settings panel:**
- **Customer Match: Off** (description text: "Automatically creates lists using data collected from customers via your conversion tags and API to show personalized ads")

**Notifications panel:**
- Email notifications: 0 of 3 turned on (collapsed — did NOT expand or toggle)

No service shows "Disconnected" / "Needs attention" / "Reconnect required". Auth is healthy across the board.

## Phase 1 → Tier decision

**Started at Tier:** STOPPED-AT-DIAGNOSIS

**Reasoning:**

1. The decision-table row that *would* apply is "Bulk editor inaccessible (iframe blocks) + Country/Language config visible → 2A first, then 2B if 2A fails". The country/language *section* is partially visible (Product feed → Product sync = On, Shipping Info = On) but the *country list* itself is collapsed inside the "Additional settings" expander and that expander did not open in response to my clicks. I had partial visibility, not full.
2. Tier 2A's required action is to interact with the same iframe region: click into Country / language → click Save (or click an exposed Resync). Interaction in that region was not reliable in this session.
3. The brief's hard guardrail is to STOP if any unexpected obstacle threatens to drift toward Tier 2C (disconnect/reconnect) or Tier 2D (uninstall). One earlier click in this session was close enough to a `Disconnect` button that it may have opened a confirmation dialog — I pressed Escape and the page returned to a healthy state, no harm done, but it confirmed how thin the margin was.
4. Markets are clean and auth is intact, so the diagnosis points strongly at Tier 2A being the right next action — it just has to be done outside the cowork browser.

**Going to 2C/2D was never on the table** — both require your explicit go-ahead per the brief. Not done.

## Phase 2 — Tier 2A

**Not executed.** See "Reasoning" above.

## Phase 2 — Tier 2B

**Not executed.** Same reason.

## Phase 3 — Final verification

**Not run.** Catalog has not been changed since the previous diagnosis cowork wrapped up. State is identical to the 09:30 ET snapshot in `cowork-session-2026-05-01-mc-collapse-diagnosis.md`:
- Shopify G&Y app Overview: Total 2 / Approved 2 / Limited 0 / Not Approved 0 / Under Review 0
- MC Feed B (`USD_88038604834` / source `10643774057`): 2 products, Last updated `—`
- "Found by Google" web crawl: ~3,996 products, mostly Not approved (still rising during this session)

## Anything weird (free-form)

- The "Additional settings to sync with Google Merchant Center" expander icon is at roughly screen coords `(1357, 324)` after the iframe-height workaround. Clicking on the chevron, the row text, and the row body all failed to open it. The same iframe accepts clicks on `Disconnect` buttons (one of mine drifted near the Business Profile `Disconnect` row; pressing Escape returned the page cleanly with all 3 services still showing `Disconnect`, i.e. still connected — no actual disconnection occurred).
- The iframe is **cross-origin** from `admin.shopify.com` (the `iframe.contentDocument` is `null` from the parent page), so JS-injected clicks from the parent are blocked. The `iframe.style.height = '3000px'` workaround only changes the iframe's outer box; it doesn't grant access to the inner DOM.
- During this session the "Found by Google" web crawl count incremented from 3,993 → 3,996 → 3,998 — Google is still actively crawling the storefront and adding products to the auto-discovered pile. This is independent of Feed B and will keep growing whether or not Tier 2A is executed.
- "What to do next" notification: **3,956 → 3,959** products needing attention. Same web-crawl pile, growing.

## Suggested next move (for Tristan)

In a normal browser session (not the cowork tool):

1. Shopify Admin → Sales channels → Google & YouTube → Settings.
2. Scroll to the "Product feed" section.
3. Click into "Additional settings to sync with Google Merchant Center" (the row with the `3` badge) to expand it. This is the section that contains the country/language list.
4. Capture verbatim what's there. **If US is checked alongside the right language and shipping toggle**, this is Tier 2A territory — re-save without changes (or click any exposed "Sync products now" / "Resync") and wait 30 minutes.
5. **If US is NOT checked, or some toggle looks off**, that's Tier 2B territory — capture before/after, fix, save, wait 30 minutes.
6. Verify at +30 minutes via Shopify G&Y → Overview ("Total products synced" should rise above 2) and MC → Data sources (Feed B's item count should rise above 2). Spot-check Final Fantasy VII and a CIB variant per Phase 3.
7. If the count doesn't rise after 30 minutes, **STOP** rather than escalating to 2C/2D unilaterally — those are decisions worth a fresh think and possibly a Shopify support ticket.

I did not file any tickets, did not modify any setting, did not click any destructive button. State is exactly as you left it before this cowork.
