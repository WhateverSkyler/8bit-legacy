# Cowork Brief — 2026-05-01 — MC Catalog Restoration

## Goal

Restore the Shopify → Merchant Center product sync for 8-Bit Legacy. Catalog has collapsed from ~25,000 products (4/29 noon) to **2 products** (now). Auth is intact, no suspension. The 4/29 deletion of the duplicate "US"-labeled feed (Source ID `10633472160`) most likely cascaded into Shopify de-listing all products that weren't explicitly bound to the surviving `USD_88038604834` market feed.

This brief diagnoses, then auto-executes low-risk recovery tiers, with a hard stop before high-risk actions.

Time budget: ~75 minutes (15 min active work + 2× 30-min verification waits).

## CRITICAL guardrails — read first

✗ Do NOT click "Delete" / "Remove data source" anywhere in MC or Shopify
✗ Do NOT click "Disconnect" on the Google account in the G&Y app — that's Tier 2C, **needs Tristan's explicit go-ahead** if Tier 2A and 2B both fail
✗ Do NOT uninstall the Google & YouTube app — that's Tier 2D, last resort, never without explicit go-ahead
✗ Do NOT add new MC data sources manually via "Add data source" wizard — Shopify owns the feed lifecycle
✗ Do NOT modify any product, metafield, tag, theme, or Shopify Markets config
✗ Do NOT touch the Google Ads campaign or the conversion-tracking pixel settings
✗ Do NOT touch billing
✗ Do NOT log in for Tristan — surface login walls if hit, don't bypass

If a screen has both a destructive button and "Cancel" — click Cancel before backing out. Document each decision.

## Phase 1 — Diagnose (read-only, ~5 min)

Capture VERBATIM. Do not edit/save anything in this phase.

### 1A. Shopify G&Y app — Manage products bulk editor

Path: Shopify Admin → Sales channels → **Google & YouTube** → Overview tab → look for a **"Manage products"** button or "View all products" link or "Product status" section with a "View all" arrow.

If you can reach the bulk editor:
- Total count shown at the top of the table
- Any filter chips/badges currently applied (status filter, country filter, etc.)
- Filter dropdown options exposed (specifically looking for "Status: Removed" / "Excluded" / "Country: International" / "Country: US")
- Sample any 3 product rows: does each show "Synced" / "Removed" / "Issues" / something else?

If the iframe blocks scroll/click (the 4/29 cowork hit this): try direct URL `https://admin.shopify.com/store/dpxzef-st/apps/google/products` or `/manage-products`. If still blocked, **document that and move on** — don't burn time.

### 1B. Shopify Admin → Settings → **Markets**

Path: https://admin.shopify.com/store/dpxzef-st/settings/markets

Capture verbatim:
- List of all markets (name + country + status)
- Which one is labeled "Primary market"
- Any market shown as Inactive / Paused / Draft / Coming soon
- The Primary market's currency

### 1C. G&Y app — Settings → Product feed → Countries / languages

Path: Sales channels → Google & YouTube → Settings → look for "Product feed" section → "Countries / languages" or "Additional settings to sync with Google Merchant Center".

Capture verbatim:
- List of countries currently enabled for sync
- Language(s) selected
- Any "Last updated" / "Last sync" timestamp anywhere on this page
- Any banner/badge indicating "Sync paused" / "Out of sync" / "Reconnect needed"

### 1D. Read-only sanity check on the G&Y Settings page

Same path: G&Y → Settings. Capture, without clicking anything that mutates:
- Google account email (expect: `tristanaddi1@gmail.com`)
- Connected Google services list (expect: Merchant Center `5296797260`, Google Ads `8222102291`, Business Profile)
- Any service shown as "Disconnected" / "Needs attention" / "Reconnect required"
- "Conversion measurement: On/Off" — capture as-is, **do not toggle**
- "Customer Match: On/Off" — capture as-is, **do not toggle**

## Phase 2 — Tiered restoration (auto-execute up through Tier 2B)

After Phase 1 inspection, decide which tier to start with:

| Phase 1 finding | Start at |
|---|---|
| Bulk editor shows ~7,689 products with "Removed"/"Excluded" badges | **2C** — STOP, surface back to Tristan |
| Bulk editor shows ~2 products + Markets are normal + countries config looks normal | **2A** |
| Bulk editor shows ~2 products + Country/Language list is missing US or shows partial state | **2B directly** (skip 2A) |
| Markets misconfigured (non-US primary market, recent change) | **STOP, surface to Tristan** — Markets is its own fix |
| Bulk editor inaccessible (iframe blocks) + Country/Language config visible | **2A first**, then 2B if 2A fails |

### Tier 2A — Re-save Country/Language (5 min, lowest risk)

Goal: trigger Shopify to re-evaluate market eligibility and push a fresh sync without changing any actual config.

Path: Sales channels → Google & YouTube → Settings → Product feed → Countries / languages → click "Edit" / "Manage" / pencil icon.

Steps:
1. Note the existing selection (don't change yet).
2. Look for an obvious "Sync products now" or "Resync" or "Refresh" button on this page or the Product feed section. If exposed → click it → DONE for 2A. Capture the confirmation message verbatim.
3. If no resync button exists → click into the country list, click "Save" without changing anything. If Save is greyed out, change one toggle (e.g. tick US off then back on, or change language and revert). Click Save.
4. Look for a confirmation toast / success message. Screenshot it.

**Do NOT remove "United States" without re-adding it in the same step.**

After Save: log the timestamp.

**Verification gate (wait 30 min):**
- Re-load Sales channels → Google & YouTube → Overview
- Expected: "Total products synced" ≥ 100 (rising trend, will keep growing for hours)
- If after 30 min still 2 → **2A failed, proceed to 2B**

### Tier 2B — Add/re-add US country (10 min, low-medium risk)

Path: same Countries / languages screen.

Steps:
1. If "United States" is NOT in the country list → click "Add country" → select United States → English (US) → Save.
2. If United States IS in the list:
   a. Click pencil/edit on the US row, **un-check** any "exclude" / "do not sync" / "paused" sub-toggle if visible.
   b. If no sub-toggle, **remove** United States, click Save. Then immediately click "Add country" → United States → English (US) → Save.
3. Log the timestamp of the final Save.

**Verification gate (wait 30 min):**
- Sales channels → Google & YouTube → Overview → "Total products synced" count
- Also: MC → Data sources → expect a NEW row (or reactivated row) labeled "Shopify App API" with feed label `US`, item count > 0
- If after 30 min Shopify count still ≤ 100 AND no new MC US-labeled feed appeared → **2B failed, STOP**

### Tier 2C / 2D — DO NOT execute

If 2A and 2B both fail, write up your findings and surface back to Tristan. Tier 2C requires disconnecting Google from the G&Y app + reconnecting. Tier 2D requires uninstalling the app. Both have material risks (conversion-action IDs reset, pixel work invalidated, full re-sync takes 4-24h). These are decisions for Tristan to make, not the cowork.

## Phase 3 — Final verification (5 min)

Whichever tier succeeded, document:

1. **Shopify G&Y app Overview** verbatim:
   - Total products synced
   - Approved / Limited / Not Approved / Under Review breakdown
2. **MC → Data sources** verbatim:
   - Each row's name + feed label + source ID + item count + last updated
3. **Spot-check 1 product**: Search MC for "Final Fantasy VII" → confirm at least 1 result appears with status Approved/Limited
4. **CIB exclusion sanity**: pick 1 CIB variant from the search results → confirm `destination_excluded: ["Shopping_ads"]` is still set in its Additional details panel

If all four are green → MC is restored. Note this clearly at the top of your handoff.

If verification fails → STOP, surface back to Tristan with the verbatim state.

## Handoff

Write `docs/cowork-session-2026-05-01-mc-restoration.md` with:

```markdown
# Cowork Session — 2026-05-01 — MC Catalog Restoration

## Outcome
- [ ] Catalog restored (≥ 5,000 products synced) at: <tier>
- [ ] Partially restored: ___ products, awaiting full propagation
- [ ] Restoration failed at tier ___, surfacing back to Tristan
- [ ] Phase 1 found a different cause (Markets misconfig, "Removed" filter, etc.) — surfacing back

## Phase 1 — Diagnostics
1A — Manage products bulk editor: <verbatim>
1B — Markets: <verbatim>
1C — Countries/languages: <verbatim>
1D — Settings page sanity: <verbatim>

## Phase 1 → Tier decision
Started at Tier: 2A / 2B / STOPPED-AT-DIAGNOSIS
Reasoning: <brief>

## Phase 2 — Tier 2A
Action taken: <verbatim, including timestamp>
Confirmation message: <verbatim>
Verification at +30 min: Synced count = ___
Verdict: PASS / FAIL → escalated to 2B / N/A

## Phase 2 — Tier 2B (if applicable)
Action taken: <verbatim, including timestamp>
Confirmation message: <verbatim>
Verification at +30 min: Synced count = ___, MC feed labels = <list>
Verdict: PASS / FAIL → STOP, surfacing to Tristan

## Phase 3 — Verification
Shopify G&Y Overview: <verbatim>
MC Data sources: <verbatim table>
Final Fantasy VII spot-check: <result>
CIB exclusion sanity: <result>

## Anything weird (free-form)
<verbatim screenshots / unexpected dialogs / banners / errors>
```

Commit + Syncthing-propagate. **Do NOT git push** (Tristan handles that).

## What you are NOT doing

- Disconnecting/reconnecting the G&Y Google account
- Uninstalling the G&Y app
- Adding/deleting MC data sources directly via MC
- Re-saving the supplemental feed CSV (the 4/29 supplemental disaster — never again)
- Modifying any product, metafield, tag, theme, Shopify Markets config
- Modifying any setting in Google Ads
- Logging into anything for Tristan
- Filing a Shopify or Google support ticket on Tristan's behalf

If anything unexpected happens (dialog you don't recognize, error message, "are you sure?" confirmation) — **screenshot, do not click, surface back to Tristan**.

## Time budget

- Phase 1 diagnosis: 5 min
- Tier 2A action + 30-min wait: 35 min
- Tier 2B action (if needed) + 30-min wait: 35 min
- Final verification: 5 min
- Total: ~75 min wall clock, ~15 min active work

If the session is going to exceed 90 min wall clock, surface progress to Tristan rather than burning more time blindly.
