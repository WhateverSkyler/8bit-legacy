# Cowork Brief — 2026-05-15 — eBay Tax Exemption follow-up fixes

**Type:** Mac cowork session (Preview re-sign + browser eBay UI).
**Estimated time:** 10 min.
**Mutations authorized:** YES — (a) sign + export the regenerated MTC PDF, (b) add business name + address to eBay account, (c) re-upload corrected MTC. No other account changes.
**Run this from the Mac** — signed PDFs are at `~/Documents/8bit-tax/`.

## 2026-05-15 update — PDF already regenerated

`scripts/fix-mtc-ga-only.py` was run and produced a fresh **unsigned** PDF at:
`~/Documents/8bit-tax/MTC-Uniform-Resale-Cert_8BitLegacy_FILLED_v2.pdf`

This new PDF has the GA permit `308837085` ONLY in the GA cell. All 34 other state cells are blank (verified programmatically: exactly 1 non-empty state cell, GA). IL/KS/MD were already blank by design. **No Preview rectangle redaction needed** — Step 1 below is now just sign + export.

## Why this exists

eBay's reviewer sent two rejection emails on 2026-05-15 ~07:50 ET re: the 2026-05-14 tax exemption submission:

1. **MTC rejected — "GA registration number in front of GA column only"** — eBay won't accept the home-state-permit-listed-across-all-states approach. Only the GA cell can have `308837085`; all other 34 state cells must be blank.
2. **Business name missing on eBay account** — eBay can't find "8-Bit Legacy, LLC" on the eBay account. Need to add it as the registration name (or as an additional shipping address).

SST cert was NOT flagged. Leave it alone for now. (If a separate SST rejection email arrives later, we'll iterate.)

**Strategic cost of complying with #1:** MTC effectively narrows from 35 states → GA only. We already have GA ST-5, so MTC becomes redundant. We lose ~15 states that are MTC-only (AK, AL, AZ, CA, CO, CT, FL, HI, ID, ME, MO, NM, PA, SC, TX). The remaining ~24 states stay covered by the SST cert (assuming it gets through). TX, FL, PA are the meaningful ones. Tristan accepted this trade — comply rather than push back.

## Step 1 — Sign the regenerated MTC PDF (Preview, ~3 min)

The corrected unsigned PDF is already on disk: `~/Documents/8bit-tax/MTC-Uniform-Resale-Cert_8BitLegacy_FILLED_v2.pdf`.

1. Open `MTC-Uniform-Resale-Cert_8BitLegacy_FILLED_v2.pdf` in Preview.
2. Visually verify the state grid on page 1: GA cell shows `308837085`, every other state cell is blank. IL/KS/MD blank too (as before).
3. **Check the "Retailer" checkbox** (top of page 1, "is engaged or is registered as a..." list) — pypdf's checkbox encoding may not have taken; click it manually.
4. **Sign the "Authorized Signature" line** at the bottom. Use Tools → Annotate → Signature, or your saved signature. Title (MEMBER) and Date (2026-05-14) are already filled.
5. **File → Export as PDF** → save as `~/Documents/8bit-tax/MTC-Uniform-Resale-Cert_8BitLegacy_SIGNED_v2.pdf`.

The original `_SIGNED.pdf` stays as a backup — do not overwrite it.

### Pause-and-ask
- **GA cell looks blank in Preview**: the field value is set programmatically — try zoom in, or open in Acrobat Reader to confirm. If still blank, ping me to re-run the script.
- **Retailer checkbox doesn't visually appear checked even after clicking**: try clicking it twice (Preview sometimes ghosts the state). If still no check, mark a clean checkmark with the annotate tool.

## Step 2 — Add business name to eBay account (~3 min)

eBay's email gave the path:
1. Sign in to eBay (the `circuitswapllc` business account that received the rejection emails).
2. Upper left corner: hover over "Hi, [name]" → **Account settings**.
3. **Personal Info** → **Addresses** → click **Edit** next to **Registration address, email and phone number**.
4. May prompt re-sign-in.
5. Click **Edit Owner name, address**.
6. Add / set:
   - **Business name:** `8-Bit Legacy, LLC` (exactly this — matches the cert)
   - **Address:** `103 Dogleg Dr, Moultrie, GA 31788`
7. Click **Save**.
8. Screenshot the saved-confirmation state.

### Pause-and-ask
- **Form requires Owner name be a person, not a business**: add `8-Bit Legacy, LLC` as an **additional shipping address** instead (per eBay's email — they explicitly said this works). Account → Addresses → "Add new address" → name field = `8-Bit Legacy, LLC`, address as above.
- **Form rejects the comma in `8-Bit Legacy, LLC`**: try `8-Bit Legacy LLC` (no comma) — matches the cert too (the cert says `8-BIT LEGACY LLC`).
- **Can't find Personal Info → Addresses**: screenshot the Account settings page you DO see; UI may have moved. Don't guess.

## Step 3 — Re-upload corrected MTC (~5 min)

1. Navigate to the same Tax Exemption upload page used on 2026-05-14 (per `docs/claude-cowork-brief-2026-05-14-ebay-tax-exemption-upload.md` — Account Settings → Tax Information / Sales Tax Exemption section).
2. **Find the existing MTC entry** that got rejected. There should be a way to either:
   - Replace the file (preferred — keeps the same submission record), OR
   - Delete the rejected one and upload fresh
3. Upload the new file: `~/Documents/8bit-tax/MTC-Uniform-Resale-Cert_8BitLegacy_SIGNED_v2.pdf`.
4. **State selection:** if eBay asks for states again, select **GA only** this time (since the cert now only has GA filled). DO NOT select the 34 other states — that mismatch is what they're rejecting.
5. Add a note in any "comments" / "additional info" field if available: `Resubmission per reviewer feedback 2026-05-15 — GA registration number now in GA column only, all other state cells blank as requested.`
6. Submit.
7. Screenshot the post-submit confirmation.

### Do NOT touch
- ❌ Do NOT modify or re-upload the SST certificate. It wasn't flagged. If we touch it we risk triggering a re-review.
- ❌ Do NOT delete the original GA ST-5 certificate.
- ❌ Do NOT change selling preferences, payment methods, or any other account setting.

## Step 4 — Report back

Reply with:
1. Screenshot of the cleaned MTC PDF (page 1, state grid) before re-upload — sanity check.
2. Screenshot of the eBay account showing business name added.
3. Screenshot of the MTC re-upload confirmation page.
4. Any error messages or unexpected UI states encountered.

I'll then update `docs/sales-tax-multistate-plan-2026-05-14.md` with the resubmission status and set a follow-up reminder.

## Critical context

```
Business name to add:    8-Bit Legacy, LLC  (or "8-Bit Legacy LLC" if comma rejected)
EIN:                     99-0541394
GA Sales Tax Number:     308837085 (KEEP in GA cell on MTC, REMOVE from all other state cells)
Business address:        103 Dogleg Dr, Moultrie, GA 31788
eBay account:            circuitswapllc (per the rejection emails)
Files:
  Original signed MTC:   ~/Documents/8bit-tax/MTC-Uniform-Resale-Cert_8BitLegacy_SIGNED.pdf  (keep as backup)
  Corrected MTC:         ~/Documents/8bit-tax/MTC-Uniform-Resale-Cert_8BitLegacy_SIGNED_v2.pdf  (new — upload this)
  SST cert:              ~/Documents/8bit-tax/SSTGB-F0003_8BitLegacy_SIGNED.pdf  (DO NOT touch)
Reviewer turnaround:     5 business days → expect verdict by ~2026-05-22
```

## What's NOT in scope

- SST cert iteration (wait for separate verdict)
- IL/KS/MD state-specific permits (deferred, requires separate registrations)
- CA tax leak (no nexus, accept)
- The 15 MTC-only states we're losing coverage on (TX/FL/PA/etc.) — accepted trade
