# Cowork Brief — 2026-04-29 — Custom Labels Supplemental Feed Upload

## Goal

Upload `data/merchant-center-custom-labels.csv` (13,254 rows) to Merchant Center as a supplemental data source linked to Feed B (USD_88038604834). After upload, verify MC accepts it and reports a high match rate. This is the last MC-side blocker before the `8BL-Shopping-Games` campaign can be flipped to ENABLED.

**Estimated time: 10–15 minutes.**

---

## Pre-existing state (do NOT redo)

From morning cowork session (2026-04-29) and main session work — all verified, don't re-check:

- ✅ Feed A (US, ID 10633472160) DELETED. Feed B (USD_88038604834, 13,252 items) is canonical.
- ✅ CIB exclusion confirmed working in Feed B via metafield (3 products spot-checked: Crisis Core FFVII PSP, FFVII PS1, .hack GU Rebirth).
- ✅ G&Y app shows Approved: 24,984 / Limited: 0 / Not Approved: 477. Account healthy. No account-level blockers.
- ✅ G&Y app has NO native UI for tag-prefix → custom_label_X mapping. **The supplemental feed CSV is the only path.** Confirmed 2026-04-29 cowork.
- ✅ Custom label tags exist on all 7,142 active Shopify products (`price_tier:over_50`, `category:game`, etc.) — they're correct on the Shopify side; the CSV bridges them to MC.
- ✅ Campaign `8BL-Shopping-Games` (ID `23766662629`) is PAUSED. Don't touch it.
- ✅ Pixel infrastructure verified correct: all 7 conversion action tokens in storefront HTML match real conversion actions in Google Ads account 822-210-2291 (verified via API).
- ✅ Tristan is placing a real test order separately and paying billing prerequisite. Don't touch either.

---

## Hard guardrails

- ✗ Do NOT touch the campaign `8BL-Shopping-Games` — Tristan flips it himself with explicit "flip" command after both timers complete.
- ✗ Do NOT modify any Shopify product, tag, metafield, theme, or storefront.
- ✗ Do NOT delete or modify the existing canonical Feed B (USD_88038604834) — it's the primary feed; you're attaching a supplemental.
- ✗ Do NOT touch billing in Google Ads. Tristan handles that.
- ✗ Do NOT place test orders or modify orders.
- ✗ Do NOT modify or delete any other supplemental feeds that already exist (if any). If you see one, document and leave it alone.

---

## Task — Upload the supplemental CSV (10 min)

### Step 1: Open Merchant Center

`merchants.google.com` → select account **5296797260** (8-Bit Legacy) → left nav → **Data sources**.

You should see Feed B listed: `USD_88038604834` (the post-4/24-reinstall Shopify channel feed, ~13,252 items). This is the primary feed you'll attach the supplemental to.

### Step 2: Add the supplemental data source

Click **Add data source** (typically top-right) → choose **Add supplemental data source**.

Configure:
- **Name:** `Custom Labels Supplemental`
- **Country and language:** match Feed B's country/language settings (likely "US" + "English" — confirm by checking Feed B first)
- **Linked primary data source:** select Feed B = `USD_88038604834`
- **Input method:** **Upload file** (NOT scheduled fetch, NOT Google Sheets — this is a one-time upload, can re-do periodically as catalog evolves)
- **File to upload:** `/Users/tristanaddi1/Projects/8bit-legacy/data/merchant-center-custom-labels.csv` (735 KB, 13,254 rows, columns: `id, custom_label_0, custom_label_2`)
- **Schedule:** **Daily** OR **Weekly** is fine — labels rarely change, but daily is safest in case we re-run the generator
- **Save / Continue / Upload**

### Step 3: Watch validation

After upload, MC will validate the file. This can take a few minutes. Expected results:

- **Total rows in CSV:** 13,254
- **Expected match rate:** >99% (the 13,254 row count was within 2 of Feed B's reported 13,252 items, suggesting the offer ID prefix `shopify_ZZ_` is correct)

Capture from the MC UI:
| Field | Value |
|---|---|
| Total rows uploaded | ___ |
| Rows matched to existing items | ___ |
| Rows with errors | ___ |
| Specific error types (if any) | ___ |

### Step 4: Decision based on match rate

**If match rate >95%** → ✅ Success. Document the numbers in the handoff. Move to Step 5.

**If match rate <50%** → ❌ The offer ID prefix `shopify_ZZ_` is wrong. STOP. Document:
- Sample of what the actual offer IDs look like in MC (click any product, look at the `id` field — copy 3 examples)
- The error message MC shows
- DO NOT delete the failed supplemental — leave it in place; main session will regenerate the CSV with the correct prefix and you can re-upload via "Replace file" in the same supplemental.

**If match rate 50–95%** → ⚠️ Partial. Document the numbers and flag for Tristan's review. Don't act.

### Step 5: Spot-check propagation (optional, if you have time)

Custom labels typically propagate within 4–24 hours. You probably won't see them yet right after upload. But if MC's validation finished quickly and you want to spot-check:

- MC → Products → search for any product with price ≥$50 (e.g. "Final Fantasy VII PS1" or any popular retro game)
- Click into the product detail
- Look for `custom_label_0` and `custom_label_2` fields — they may show "—" (not yet propagated) or already populated with `over_50` and `game`

Don't worry if they're still empty after upload — propagation is asynchronous.

---

## Handoff

Write `docs/cowork-session-2026-04-29-supplemental-upload.md` with this structure:

```markdown
# Cowork Session — 2026-04-29 — Supplemental Feed Upload

## Upload outcome
- Match rate: ___% (rows matched / rows uploaded)
- Total rows uploaded: ___
- Rows with errors: ___
- Error types (if any): <list>
- Decision path taken: <success / partial / mismatch — regenerate needed>

## Spot-check (if performed)
- Product checked: ___
- custom_label_0 visible: YES / NO / pending propagation
- custom_label_2 visible: YES / NO / pending propagation

## If mismatch path: actual offer ID samples seen in MC
1. ___
2. ___
3. ___

## Anything weird
<free-form>

## Status for flip
- MC supplemental: clean upload / blocked / partial
- Estimated propagation ETA: ___ (typically 4-24h)
- Anything Tristan needs to know before flip command?
```

Commit the handoff with message:
```
Cowork 2026-04-29: supplemental custom-labels feed uploaded
```

No git push needed — main session handles that on EOD.

---

## What you are NOT doing

- Not flipping the campaign
- Not modifying any product on Shopify
- Not paying billing
- Not placing test orders
- Not regenerating the CSV — if it fails, you flag it; main session regenerates
- Not deleting Feed B or any other existing feed
- Not changing MC settings outside of adding this one supplemental

---

## Reference files

- `data/merchant-center-custom-labels.csv` — the file to upload (13,254 rows)
- `scripts/generate-custom-labels-feed.py` — generator (FYI only — main session re-runs if needed)
- `docs/cowork-session-2026-04-29-mc-fix-and-flip.md` — earlier cowork session that cleared Blockers 1+2
- `docs/next-steps-2026-04-29-supplemental-feed-upload.md` — full launch plan
- `docs/session-handoff-2026-04-27-ads-launch-blockers.md` — original 5 blockers
- Memory: `project_ads_launch_state.md`, `reference_mc_feed_offer_ids.md`, `feedback_ads_strategy.md`
