# Cowork Brief — 2026-05-05 — Post-Launch Browser Audit

## Goal

The campaign `8BL-Shopping-Games` was just flipped to ENABLED. API-side everything looks healthy (78 impressions in 44 min, listing tree distributing correctly, no spend yet). But Google Ads + Merchant Center browser UIs surface things the API can't easily query: visual ad previews, recommendations panel, account diagnostics, policy warnings, ad strength scores.

This brief is **READ-ONLY** — capture verbatim what's visible, do NOT change anything.

Time budget: ~10 minutes.

## Hard guardrails — read first

✗ Do NOT click "Apply" on ANY recommendation in Google Ads
✗ Do NOT pause / enable / remove / edit any campaign, ad group, or product group
✗ Do NOT change budget, bid strategy, daily cap, or networks
✗ Do NOT add/remove negative keywords
✗ Do NOT modify any product attribute in Merchant Center
✗ Do NOT click "Set up Smart Bidding" / "Try Performance Max" / any campaign-type migration
✗ Do NOT click "Auto-apply recommendations" toggle
✗ Do NOT modify conversion goal settings
✗ Do NOT log in for Tristan — surface login walls if hit
✗ Do NOT take any "Optimization score" actions

If a confirmation dialog appears for any of the above — screenshot, click Cancel, surface back.

This is a *report only* audit. Look, capture, don't touch.

## Phase 1 — Campaign overview (2 min)

URL: `https://ads.google.com/aw/campaigns?campaignId=23766662629`

Or navigate: ads.google.com → Campaigns → 8BL-Shopping-Games

Capture verbatim:
- Campaign status badge (expected: "Eligible" or "Eligible (Limited)" — green or yellow icon)
- Today's metrics in the headline row (Impressions / Clicks / CTR / Avg CPC / Cost / Conversions / ROAS)
- Any **alert banner** at the top of the page (red/yellow/orange messages — common ones: "Budget limited by spend", "Policy issue", "Conversion tracking issue", "Low search volume")
- Any visible "Recommendations" / "Optimization score" widget — capture the score number AND list the top 3 recommendation titles (do NOT click into them)
- The "Status" pill on the campaign row — what color, what text

## Phase 2 — Ad group + Product group view (2 min)

Click into the **all-products** ad group, then **Listing groups** tab (or "Product groups" in some Google Ads UI versions).

Capture verbatim:
- The tree structure shown (we expect: ROOT → custom_label_0=over_50 (bid $0.35), custom_label_0=20_to_50 (bid $0.08), custom_label_0=else (excluded))
- Today's metrics per leaf (Impressions / Clicks / Cost) — should match the API showing 73 impr on over_50, 5 on 20_to_50
- Any product subdivision marked as "Disapproved" or showing a warning icon
- Whether the bids match what we set ($0.35 / $0.08)

## Phase 3 — Conversions page (1 min)

URL: `https://ads.google.com/aw/conversions/customerconversiongoals`

Or navigate: Tools (wrench icon) → Conversions

Capture verbatim:
- The "Customer conversion goals" table — for each row, capture the Status column value
- Specifically the **Purchase** row — should say "Active" with a green dot. If anything else (Inactive / Misconfigured / No recent conversions / Receiving conversions), capture the verbatim text
- Whether there's any banner at the top about conversion tracking issues

## Phase 4 — Account-level diagnostics (1 min)

URL: `https://ads.google.com/aw/overview` (account overview)

Capture:
- Any red/yellow alert at the top of the page
- Any "Account suspension warning" or policy issue banner
- The account-level "Optimization score" if visible

## Phase 5 — Merchant Center diagnostics (3 min)

URL: `https://merchants.google.com/mc/diagnostics?a=5296797260`

Capture verbatim:
- The "Item issues" / "Account issues" tabs — count of issues per severity
  - Errors (red): __
  - Warnings (yellow): __
  - Notifications (blue/gray): __
- For top 5 most-frequent issues: copy the issue title + affected item count
- Whether there's any **account-level** issue (these block the whole feed) — if yes, capture title verbatim

Then visit:

URL: `https://merchants.google.com/mc/products/list?a=5296797260`

- Click into any product where the title contains "over $50" tier (e.g. a Game Only NES game). Look for **Custom labels** section in the product detail panel.
- Capture: what custom_label_0, custom_label_1, custom_label_2, custom_label_3, custom_label_4 are showing (might still be empty — propagation in flight)

## Phase 6 — Ad preview (1 min)

Within the campaign or ad group, find the "Ad preview" or "Inventory" or "Products" tab.

Capture:
- A screenshot of what 1-2 sample products look like as Shopping ads (price + title + image)
- Whether the price displayed matches the storefront price
- Whether the title looks weird/truncated/spammy

If "Ad preview" is not directly available, use:
URL: `https://adspreview.google.com` (paste a search like "ace combat 2 ps1 game") — see what comes up

## Handoff

Write `docs/cowork-session-2026-05-05-campaign-audit.md` with:

```markdown
# Cowork Session — 2026-05-05 — Post-Launch Campaign Audit

## Outcome
- [ ] All checks passed — no action needed
- [ ] Issues found, listed below for Tristan

## Phase 1 — Campaign overview
URL: ___
Status badge: ___
Today's headline metrics: impr=___ clicks=___ cost=___ conv=___ ROAS=___
Top alert banners (verbatim, all of them): ___
Optimization score: ___
Top 3 recommendations (titles only): 1.___ 2.___ 3.___
Status pill: ___

## Phase 2 — Listing groups
Tree structure observed (paste verbatim from UI): ___
Per-leaf metrics today (impr/clicks/cost): ___
Any disapproved subdivisions: ___
Bids match $0.35 / $0.08: yes/no

## Phase 3 — Conversions
Purchase row status: ___
Other conversion action statuses (one line each): ___
Any conversion tracking banner: ___

## Phase 4 — Account overview
Any account-level alerts: ___
Optimization score: ___

## Phase 5 — Merchant Center diagnostics
Item issues — Errors: ___  Warnings: ___  Notifications: ___
Account-level issues: ___
Top 5 issues by frequency:
  1. ___ (n affected)
  2. ___ (n affected)
  3. ___ (n affected)
  4. ___ (n affected)
  5. ___ (n affected)
Sample product custom labels (paste from product detail UI): ___

## Phase 6 — Ad preview
Sample 1: title/price/image OK?: ___
Sample 2: title/price/image OK?: ___

## Anything weird (free-form)
<verbatim screenshots of unexpected dialogs / banners / errors>
```

Commit + Syncthing-propagate. **Do NOT git push** (Tristan handles that).

## Time budget

Phase 1: 2 min
Phase 2: 2 min
Phase 3: 1 min
Phase 4: 1 min
Phase 5: 3 min
Phase 6: 1 min
Total: ~10 min wall clock

If exceeding 20 minutes, surface progress to Tristan rather than burning more time.
