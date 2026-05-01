# Cowork Brief — 2026-05-01 — MC Catalog Collapse Diagnosis (read-only)

## Why this is urgent

Yesterday/today the Merchant Center catalog appears to have collapsed. We need a clean read-only diagnosis before any fix attempt — the last two MC manipulations (supplemental feed disaster on 4/29 AM, then feed deletion 4/29 PM) both made things worse, so this brief is **strictly read-only** until Tristan understands what happened.

## Current state (as of 2026-05-01 09:00 ET, from Tristan)

- **Shopify Sales channel app (Google & YouTube → Overview):** Total products = **2**, Approved = **2** ⚠️
- **Merchant Center Overview (https://merchants.google.com):** Total = **~3.99K**, Approved = **~39** ⚠️
- **Shopify Admin product count (Admin API, just verified):** 7,689 ACTIVE products

This is a 4-way mismatch. Last known good state was **2026-04-29 ~12:00 ET** when Shopify G&Y app showed **24,984 Approved / 0 Limited / 477 Not Approved / 17 Under Review** (per `docs/cowork-session-2026-04-29-mc-fix-and-flip.md`).

Between 4/29 12:00 ET and 5/01 09:00 ET, only known mutations:
- 4/29 ~11:30: Feed A (`Source ID 10633472160`, 12,226 items) deleted from MC
- 4/29 ~10:00: Pilot custom_label metafields set on 1 product (3 Ninjas Kick Back, gid 7956600029218)
- 4/29 ~13:30: Test order #1072 placed
- (no other known MC or Shopify product mutations)

We need to determine:
- **Is this a sync collapse** (Shopify ↔ MC link broken) → most actionable
- **Is this a mass disapproval** (MC is rejecting most products) → fix at MC/account level
- **Is this an account-level suspension** (worst case, requires appeal) → must surface immediately

## Hard guardrails

- ✗ Do NOT click "Resubmit" / "Resync" / "Reconnect" / "Disconnect" / "Add data source" / "Edit feed" / "Delete feed" / any mutation button
- ✗ Do NOT change MC business info, shipping, return, or marketing-method settings
- ✗ Do NOT touch the Shopify Google & YouTube app's "Reconnect" or "Reauthorize" flow
- ✗ Do NOT touch any product, metafield, tag, or theme in Shopify
- ✗ Do NOT enter MC's "Get help" / contact-support flow yet — surface and pause
- ✗ Do NOT touch the Google Ads campaign (still paused, leave it)
- ✗ Do NOT log in for Tristan — surface login walls if hit, don't bypass

If a screen has both a destructive button and a "Cancel" button, click Cancel before backing out. Document everything verbatim.

## Check 1 — Shopify Google & YouTube app: actual sync status (~3 min)

Path: Shopify Admin → Sales channels → **Google & YouTube** → Overview tab.

Capture verbatim:
- The big number at top of the page (Total products synced)
- Approved / Limited / Not Approved / Under Review breakdown
- The "Last sync" or "Last updated" timestamp shown anywhere on the page
- Any red/yellow banner at the top of the page (verbatim quote)
- Any "Reconnect" / "Reauthorize" / "Sync error" prompt

Also click:
- **Marketing methods** sub-tab (or whatever it's called now) → list which channels are "Active" vs "Setup required"
- **Settings** → **Google services** → confirm:
  - Merchant Center ID (expected: `5296797260`)
  - Google Ads ID (expected: `8222102291`)
  - Google account email (whatever shows)
  - Whether any service shows "Disconnected" / "Needs attention" / "Reconnect"

## Check 2 — Merchant Center: feed inventory (~3 min)

Path: https://merchants.google.com → 8-Bit Legacy account `5296797260` → left nav → **Data sources**.

Capture for **each** data source row:
- Name
- Source type (Merchant API / Content API / Web crawl / Supplemental)
- Feed label
- Source ID (visible in URL when you click into the row, e.g. `?source=10643774057`)
- Item count
- Last updated timestamp
- Any "Error" / "Issue" / "Action needed" badge on the row

Specifically look for:
- The known canonical feed: `Shopify App API`, label `USD_88038604834`, source ID `10643774057` — does it still exist? What's its item count?
- Any new orphan/empty feeds that appeared since 4/29
- Any data source with a red error badge

DO NOT click into any feed's "Settings" or "Edit" — read-only inspection from the list page only.

## Check 3 — Merchant Center: Overview + Diagnostics (~3 min)

Path: Merchant Center → Overview (left nav).

Capture:
- The big "Total products" number + Approved / Limited / Not approved counts
- Date filter shown at top (default "Today" or whatever)
- Any banner at the top of Overview (verbatim) — especially red/orange suspension warnings
- "Items requiring attention" widget — top 5 issues with counts

Then go to **Diagnostics** (left nav, may be under "Improvements" or a "Need to know" section):
- Any "Account-level issue" entries (verbatim, in priority order)
- Any "Item-level issue" entries — top 5 by impact

## Check 4 — Merchant Center: Notifications + account status (~2 min)

Path: Merchant Center → top-right bell icon (or left nav → Notifications).

Capture all notifications from the last 7 days verbatim. Especially looking for:
- Any "Account suspended" / "Policy violation" / "Verification failed" / "Misrepresentation"
- Any "Feed sync failed" / "Authentication issue"
- Any "Domain not claimed" / "Website not verified"

Then path: Merchant Center → Settings (gear icon) → Business info / Account info → check:
- Account status banner at top (verbatim)
- Site verification status (Verified / Claimed)
- Whether the website URL shown matches `8bitlegacy.com`

## Check 5 — Compare counts across the 4 vantage points

Build this table in your handoff:

| Source | Total | Approved | Limited | Not approved | Under review | Last updated |
|---|---|---|---|---|---|---|
| Shopify Admin (raw products, ACTIVE status) | 7,689 (already known) | n/a | n/a | n/a | n/a | live |
| Shopify G&Y app Overview | ___ | ___ | ___ | ___ | ___ | ___ |
| Shopify G&Y app: Sum of feed-level "Items in this source" (if exposed) | ___ | n/a | n/a | n/a | n/a | ___ |
| MC Overview | ___ | ___ | ___ | ___ | ___ | ___ |
| MC Data sources (sum of item counts) | ___ | n/a | n/a | n/a | n/a | ___ |

This table is the diagnosis core. The pattern of mismatches will tell us which layer broke.

## Check 6 — Feed B health spot-check (~2 min)

If Feed B (`USD_88038604834` / source ID `10643774057`) still appears in Data sources, click into it (read-only). Capture:
- Item count (top of the page)
- "Last fetch" / "Last updated" timestamp
- "Items needing attention" if shown
- Any red error banner
- Per-item sample: click 1 random product → does the product detail page load? Status = Approved/Limited/Disapproved?

If Feed B is **GONE** from Data sources → that's the smoking gun. Surface immediately and stop the cowork.

## Handoff

Write `docs/cowork-session-2026-05-01-mc-collapse-diagnosis.md` with:

```markdown
# Cowork Session — 2026-05-01 — MC Collapse Diagnosis

## Verdict (one of these)
- [ ] Sync collapse: Shopify ↔ MC link broken (most actionable)
- [ ] Mass disapproval: products synced but MC rejected most (fix at MC/policy level)
- [ ] Account suspension: MC has flagged the account (requires appeal)
- [ ] Feed B deletion: Feed B is missing from Data sources (catastrophic, my fault from 4/29)
- [ ] In-progress propagation: numbers are mid-resync after 4/29 cleanup, will normalize on its own
- [ ] Other (describe)

## Check 1 — Shopify G&Y app
[fill]

## Check 2 — MC Data sources
[fill, table]

## Check 3 — MC Overview + Diagnostics
[fill]

## Check 4 — MC Notifications + account status
[fill]

## Check 5 — Cross-vantage comparison table
[fill]

## Check 6 — Feed B spot-check
[fill]

## Anything weird (free-form)
[fill — verbatim screenshots of any unexpected banner/error]
```

Commit + Syncthing-propagate. **No git push needed** (Tristan handles that).

## What you are NOT doing

- Reconnecting Shopify ↔ MC
- Resyncing any feed
- Editing/deleting/re-adding any data source
- Changing settings in MC or Shopify
- Logging in for Tristan
- Touching the Google Ads campaign or pixel
- Filing a Google support ticket on Tristan's behalf

If during the diagnosis you spot something so urgent it can't wait (e.g. account-suspension banner) — surface it at the top of the handoff in **bold** and stop. Tristan decides next steps.
