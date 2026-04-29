# Cowork Brief — 2026-04-29 — Clear MC Blockers, Prep for Flip

## Goal

Clear the 3 browser-only blockers (1, 2, 3 from `session-handoff-2026-04-27-ads-launch-blockers.md`) that are gating the `8BL-Shopping-Games` Google Ads launch. After this brief plus user actions on Blockers 4 + 5, the campaign can be flipped today.

**Faith level after a clean run of this brief + user actions: 60–65% positive ROI on launch.**

---

## Pre-existing state I verified this morning (2026-04-29 ~8:30 AM ET)

The 4/27 audit's Blocker 3 had a wrong premise. Tags exist correctly on Shopify; metafields aren't the storage location. **Don't redo the metafield check.**

### Confirmed via Shopify Admin API:
- **Custom label tags ARE present on all 7,142 active products** (stored as Shopify tags, not metafields):
  - `price_tier:under_20` — 4,322 products
  - `price_tier:20_to_50` — 1,849 products
  - `price_tier:over_50` — **971 products** (the high-bid targets)
  - `category:game` — 6,088 products
  - `category:pokemon_card` — 1,028 products (correctly excluded by ad strategy)
  - `category:console` — 15 / `category:accessory` — 11 / `category:sealed` — 0
- **CIB exclusion metafields ARE set correctly** on CIB variants:
  - Sampled 4 Final Fantasy products. Every CIB variant has `mm-google-shopping.excluded_destination = ["Shopping_ads"]`. Game Only variants have no exclusion (correct).
- **Supplemental feed CSV exists** at `data/merchant-center-cib-exclusion.csv` — 6,088 CIB variant rows ready for upload as a fallback if the metafield approach isn't propagating.

### What this means for your work

- Blocker 3's REAL fix is configuring the Shopify Google & YouTube app to map tag prefixes → `custom_label_0` / `custom_label_2` in the MC feed. The tags exist — they just aren't being passed through to the Custom Labels MC field.
- Blocker 2's REAL fix is either fixing the duplicate feed (likely root cause) OR uploading the supplemental CIB CSV as a Merchant Center supplemental feed.

---

## Hard guardrails

- ✗ Do NOT enable / pause / modify the `8BL-Shopping-Games` campaign (ID `23766662629`). Tristan flips it himself with explicit "flip" command.
- ✗ Do NOT modify any product on Shopify directly. The custom label tags are correct as-is.
- ✗ Do NOT touch billing in Google Ads. Tristan handles that personally.
- ✗ Do NOT place a test order. Tristan handles that personally with a real card.
- ✗ Do NOT delete any feed or supplemental feed without first confirming which is canonical (see Task 1).
- ✗ Do NOT edit the Shopify theme, discounts, or storefront.

---

## Task 1 — Resolve duplicate Merchant Center feeds (15 min)

Open Merchant Center (`merchants.google.com`), select account **5296797260** (8-Bit Legacy).

Navigate to **Data sources** (left nav) → see the list of feeds.

Two feeds are running per the 4/27 audit:
- `US` — 12,226 items (original)
- `USD_88038604834` — 13,252 items (created 2026-04-24 during G&Y app reinstall)

### 1A — Identify the canonical feed

For each feed, click into it and capture:
- Source type (Shopify channel app / Content API / supplemental / manual upload)
- Linked Shopify channel app installation date (if shown)
- Last fetch timestamp
- "Active items" vs "Inactive items" counts
- Any error/warning messages on the feed

The canonical feed should:
- Be the most recently created Shopify channel feed (probably `USD_88038604834` since it was created during the 2026-04-24 reinstall)
- Have the most recent fetch timestamp
- Be associated with the active Shopify Google & YouTube app installation

### 1B — Verify which feed has correct labels + exclusions

For the same well-known game (e.g. **"Final Fantasy VII - PS1 Game"** — product ID 7956663664674), look for it in BOTH feeds:

Per feed, click into the product and capture:
- Custom label 0 value (should show `over_50`, `20_to_50`, or `under_20`)
- Custom label 2 value (should show `game`)
- Excluded destinations (if any) on the **CIB variant** specifically — should show "Shopping ads" excluded
- Approval status

The "good" feed has correct labels visible AND correctly excludes CIB. The "bad" feed has missing labels or fails to exclude CIB.

### 1C — Disable the bad feed

Once identified, **disable** (don't delete yet) the bad feed:
- Data sources → click the feed → look for "Pause" or "Disable" toggle
- If only "Delete" is available, take a screenshot first, then delete.

If BOTH feeds appear to have correct labels + exclusions, **don't disable either** — write that finding in the handoff and let Tristan decide. Bid dilution from duplication is bad but breaking the working feed is worse.

### 1D — Verify counts after cleanup

Wait 5–10 min for MC to re-tally. Capture:
- Total products in MC after cleanup: ___
- Approved: ___ / Limited: ___ / Disapproved: ___

Target: ~12K items (matches Shopify reality), not ~25K.

---

## Task 2 — Configure Shopify Google & YouTube app custom label mapping (10 min)

This is the actual fix for Blocker 3. The custom label TAGS exist on Shopify products; the G&Y app needs to be told which tag prefix maps to which MC custom label slot.

### 2A — Open the G&Y app settings

Shopify Admin (`8bitlegacy.myshopify.com/admin`) → **Sales channels** → **Google & YouTube** (or **Apps** → Google & YouTube).

Navigate to **Settings** within the app. Look for a section labeled:
- "Product feed customization"
- "Custom labels"
- "Advanced settings"
- or similar

The exact UI varies by G&Y app version — search for "custom" or "label" if not obvious.

### 2B — Map tag prefixes to custom labels

The mapping should be:
| MC Custom Label | Shopify tag prefix | Example tag value |
|---|---|---|
| `custom_label_0` | `price_tier:` | `price_tier:over_50` |
| `custom_label_1` | `console:` | `console:ps1` |
| `custom_label_2` | `category:` | `category:game` |
| `custom_label_3` | `margin:` | `margin:medium` |

If the G&Y app doesn't natively support tag-prefix → label mapping, look for:
- A "rules" / "metafield mapping" section
- A way to set custom labels per-product based on a static rule
- A free-form text field where you can specify the mapping syntax

### 2C — Force a feed re-sync

After saving the mapping, find a "Sync now" or "Resubmit feed" button in the G&Y app. Click it.

If no manual resync button exists, the next scheduled sync will pick it up (usually within 24h, but Tristan can't wait that long today).

### 2D — Verify in MC after ~10 min

Back in Merchant Center → Products → click a known $50+ game (e.g. any from `price_tier:over_50` query result). Custom labels should now show:
- `custom_label_0`: `over_50`
- `custom_label_2`: `game`

If they still show empty, document what you tried and what the G&Y app UI looked like. Tristan will decide whether to manually upload the supplemental feed CSV (`data/merchant-center-cib-exclusion.csv` — already generated) or take a different path.

### 2E — Fallback if G&Y app doesn't support custom label mapping

If section 2B finds NO way to configure custom label mapping in the G&Y app, the fallback is a Merchant Center **supplemental feed**:

1. Generate a supplemental feed CSV with columns `id, custom_label_0, custom_label_2` mapping each Shopify product to its desired labels. **DO NOT generate this yourself** — note in your handoff that it's needed and Tristan/main session will generate it.
2. Tell Tristan in the handoff that the supplemental approach is required.

---

## Task 3 — Verify CIB exclusion in MC after Tasks 1 + 2 (5 min)

In Merchant Center, search for these 5 known products and confirm their **CIB variants** show "Excluded from Shopping ads" (or equivalent):

1. Crisis Core: Final Fantasy VII - PSP Game — variant `Complete (CIB)` ($21.99)
2. Final Fantasy VII - PS1 Game — variant `Complete (CIB)` ($55.99)
3. Final Fantasy VII Dirge of Cerberus - PS2 Game — variant `Complete (CIB)` ($40.99)
4. Final Fantasy VIII - PS1 Game — variant `Complete (CIB)` ($29.99)
5. Pick any random retro game — verify its CIB variant is excluded

For each, capture:
- Variant approved/limited/disapproved status for **Shopping ads** destination
- Whether "Excluded from Shopping ads" is visible

If 5/5 show as excluded → CIB exclusion working ✅
If any show approved for Shopping ads → flag in handoff. Tristan decides whether to upload the supplemental CSV.

---

## Handoff

Write `docs/cowork-session-2026-04-29-mc-fix-and-flip.md` with this structure:

```markdown
# Cowork Session — 2026-04-29 — MC Fix + Flip Prep

## Task 1 — Duplicate feed cleanup
- Feeds before:
  | Name | Source | Items | Last fetch | Verdict |
- Canonical feed identified: `___`
- Action taken: <disabled X / kept Y / both kept because…>
- Counts after cleanup: total ___ / approved ___ / limited ___ / disapproved ___

## Task 2 — Custom label mapping
- G&Y app settings section found: <path / "not found">
- Mapping configured: YES / NO / PARTIAL
- Resync triggered: YES / NO
- Verified in MC after wait: <custom_label_0 value, custom_label_2 value, on which product>
- Fallback needed (supplemental feed CSV)? YES / NO

## Task 3 — CIB exclusion verification
| Product | CIB variant excluded from Shopping ads? |
| Crisis Core FFVII PSP | YES / NO |
| FFVII PS1 | YES / NO |
| FFVII Dirge of Cerberus PS2 | YES / NO |
| FFVIII PS1 | YES / NO |
| <random> | YES / NO |

## Anything weird
<free-form>

## Faith level for flip
- All 3 MC blockers cleared cleanly? <yes/no/partial>
- Anything Tristan needs to know before placing test order or hitting flip?
```

Commit + Syncthing-propagate. No git push needed (main session pushes on EOD handoff).

---

## What you are NOT doing

- Not flipping the campaign
- Not modifying Shopify product data (tags / metafields / descriptions)
- Not paying the billing
- Not placing a test order
- Not generating supplemental feed CSVs (just identify if needed)
- Not optimizing winners landing pages or storefront UX (separate workstream)

---

## Reference files

- `docs/session-handoff-2026-04-27-ads-launch-blockers.md` — original 5 blockers
- `docs/google-ads-launch-plan.md` — bid math + tier strategy
- `docs/ads-launch-master-plan-2026-04-22.md` — original launch plan
- `data/merchant-center-cib-exclusion.csv` — 6,088-row CIB exclusion supplemental feed (already generated)
- Memory: `project_ads_launch_state.md`, `feedback_ads_strategy.md`, `project_cib_ads_exclusion.md`
