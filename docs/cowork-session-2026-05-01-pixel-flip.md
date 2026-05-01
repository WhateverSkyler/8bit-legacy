# Cowork Session — 2026-05-01 — App Pixel Flip to Always On

## Outcome

- [ ] All 3 app pixels successfully flipped to Always on
- [ ] Partial: Google & YouTube only (___ remaining)
- [ ] Failed at Phase ___ — surfacing back to Tristan
- [x] **Different state than expected — only TikTok needed flipping; Google & YouTube and Facebook & Instagram were already `Always on` at session start. TikTok flipped successfully.**

## Phase 1 — Customer events page

**URL loaded:** `https://admin.shopify.com/store/dpxzef-st/settings/customer_events`

**Page title:** "Customer events"

**Tabs visible:** `App pixels` (active default), `Custom pixels`

**App pixel list (verbatim, in display order — sorted by name asc):**

| Pixel | Status | Data |
|---|---|---|
| Amazon MCF and Buy with Prime | Disconnected | — |
| Facebook & Instagram | Connected | **Always on** |
| Google & YouTube | Connected | **Always on** |
| Mailchimp: Email & SMS | Disconnected | — |
| TikTok | Connected | **Optimized** ← *only one that needed flipping* |

The two `Disconnected` rows show `—` (em-dash) in the Data column — no data-sharing setting applies, nothing to flip.

(Did NOT switch to the Custom pixels tab — `Google Customer Reviews` lives there per project notes and the brief explicitly says do not touch it.)

## Phase 2 — Google & YouTube detail page

**Did NOT enter detail page** (and didn't need to). The Data column on the App pixels list already showed `Always on`. Confirmed visually: clicking the row exposes the inline `Connected ⌄` and `Always on ⌄` mini-dropdowns next to the existing values, not a navigation to a detail page. Hovering on the `Always on ⌄` would open a popover identical in shape to the TikTok one captured in Phase 5 — I deliberately did NOT click it open for G&Y, to avoid any chance of accidentally toggling the radio.

**Page heading:** Customer events list (no separate detail page on this Shopify version — the dropdown popover IS the detail UI)

**Data-sharing control label and section:** popover labeled "Mode", with two radio options: `Optimized [Recommended]` / `Always on`

**Current value before any change:** `Always on` ✓ — already correct, **no flip needed**.

## Phase 3 — Flip and save (Google & YouTube)

**Action taken: NONE.** Already `Always on` at session start. Did not click anything that could mutate this pixel.

## Phase 4 — Facebook & Instagram

**Same situation as G&Y — already `Always on` at session start.**

**Action taken: NONE.** No flip needed. Did not click anything that could mutate this pixel.

## Phase 5 — Third app pixel (apiClientId 4383523)

**Identified name: TikTok** (the only Connected App pixel besides G&Y and FB&I, so apiClientId `4383523` ≡ TikTok).

**Page heading:** popover from inline dropdown (same UI shape as G&Y).

**Sections in the popover:**
- *Header banner (yellow ⚠ — appears post-save):* "No referred traffic. Optimize data to intelligently allow data access." → this is Shopify's recommendation to switch *back* to Optimized; cosmetic, ignored per brief intent.
- **Status:** "All data access is paused" *(before flip)* → "TikTok can access all data" *(after flip)*
- **Mode** (with `(i)` info icon)
  - `Optimized [Recommended]` — "Shopify intelligently allows data access for optimal analytics and campaign performance."
  - `Always on` — "Allow access to all of your customer and business data without limitations."

**Current value before flip:** `Optimized` (Recommended) — selected.

### Action

1. Clicked the `Optimized ⌄` chip in the TikTok row to open the popover.
2. Selected the `Always on` radio.
3. Clicked the `Apply` button (was greyed out until step 2 selected a different value).

**Save click timestamp:** ~2026-05-01 10:25 ET (approximate — within the same minute as the toast appearing).

**Confirmation toast:** "Data access updated" (verbatim — small dark toast at bottom of viewport).

**Value after page refresh (F5):** `Always on` ✓ — persisted. After refresh, the `Always on` radio remains selected when reopening the popover, and the row's Data column shows `Always on ⚠` (warning icon = the "no referred traffic" recommendation, not an error).

## Phase 6 — Verification

I did NOT run the verification curl — the cowork sandbox proxy blocks `8bitlegacy.com` (`HTTP 403 blocked-by-allowlist`). For Tristan to verify locally:

```bash
curl -sL "https://8bitlegacy.com/" | grep -oE '"dataSharingState":"[^"]+"' | sort | uniq -c
```

**Expected output (per brief):** 3 occurrences, each `"dataSharingState":"always_on"` or `"dataSharingState":"unrestricted"` (Shopify uses `unrestricted` in serialized form for the "Always on" UI label).

**If any line still shows `"optimized"`:** that pixel's flip didn't save → revisit. Most likely candidate to fail this check is TikTok if the save somehow regressed; G&Y and FB&I have been `Always on` since before this cowork.

## Anything weird (free-form)

1. **Brief premise was partially incorrect.** The brief said "All three are currently throttled by Shopify's January 2026 default change, suppressing Google Ads conversion events." That was true for TikTok at session start, but G&Y and FB&I were already `Always on` — possibly Tristan flipped them in a prior session that didn't get logged, or the January default applied selectively. Either way, the only flip executed today was TikTok.
2. **The yellow ⚠ icon next to TikTok's `Always on` is benign.** Hovering/clicking reveals a tooltip: "No referred traffic. Optimize data to intelligently allow data access." Translation: Shopify hasn't seen TikTok-attributed traffic on the store and is suggesting we revert to Optimized (their default recommendation). We deliberately do NOT want Optimized — it's what was suppressing the Google Ads conversion events. The warning is informational only and can be ignored.
3. **"Status: All data access is paused"** was the state shown in the TikTok popover *before* the flip. After the flip, this changed to "TikTok can access all data". So the flip did fix a paused state, not just toggle a label.
4. **Custom pixels tab (containing `Google Customer Reviews` ID `149717026`) was NOT opened or touched** per brief guardrails.
5. **No "Are you sure?" confirmation dialog** appeared at any point. The flip was a single radio click + Apply button click + immediate toast.
6. **Two browser tabs were accidentally opened** during navigation (one G&Y app overview, one TikTok app — from clicking pixel name labels which are also links to the underlying apps). Both closed cleanly, no state changes.
7. The 1 mutation made today was scoped exactly to: TikTok App pixel → Mode = Always on. No other settings, pixels, apps, or accounts were touched.
