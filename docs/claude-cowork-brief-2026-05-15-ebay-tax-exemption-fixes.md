# Cowork Brief — 2026-05-15 — eBay Tax Exemption follow-up fixes

**Type:** Mac cowork session (Preview PDF edit + browser eBay UI).
**Estimated time:** 15 min.
**Mutations authorized:** YES — (a) edit + re-export the signed MTC PDF, (b) add business name + address to eBay account, (c) re-upload corrected MTC. No other account changes.
**Run this from the Mac** — signed PDFs are at `~/Documents/8bit-tax/`.

## Why this exists

eBay's reviewer sent two rejection emails on 2026-05-15 ~07:50 ET re: the 2026-05-14 tax exemption submission:

1. **MTC rejected — "GA registration number in front of GA column only"** — eBay won't accept the home-state-permit-listed-across-all-states approach. Only the GA cell can have `308837085`; all other 34 state cells must be blank.
2. **Business name missing on eBay account** — eBay can't find "8-Bit Legacy, LLC" on the eBay account. Need to add it as the registration name (or as an additional shipping address).

SST cert was NOT flagged. Leave it alone for now. (If a separate SST rejection email arrives later, we'll iterate.)

**Strategic cost of complying with #1:** MTC effectively narrows from 35 states → GA only. We already have GA ST-5, so MTC becomes redundant. We lose ~15 states that are MTC-only (AK, AL, AZ, CA, CO, CT, FL, HI, ID, ME, MO, NM, PA, SC, TX). The remaining ~24 states stay covered by the SST cert (assuming it gets through). TX, FL, PA are the meaningful ones. Tristan accepted this trade — comply rather than push back.

## Step 1 — Fix the MTC PDF (Preview, ~5 min)

1. Open `~/Documents/8bit-tax/MTC-Uniform-Resale-Cert_8BitLegacy_SIGNED.pdf` in Preview.
2. Tools → Annotate → Rectangle (or use the rectangle shape tool).
3. Set fill color to **white**, no border.
4. Cover the `308837085` text in **every state cell EXCEPT GA**. The state grid is on page 1. States to white-out:
   - AK, AL, AR, AZ, CA, CO, CT, FL, HI, ID, IA, KY, ME, MI, MN, MO, NE, NV, NJ, NM, NC, ND, OH, OK, PA, RI, SC, SD, TN, TX, UT, VT, WA, WI
   - That's **34 cells**. IL/KS/MD are already blank — leave them blank.
   - **DO NOT** white-out the GA cell (`308837085` should remain visible there).
5. Optional sanity: zoom in and confirm the GA row still shows the number, all others are blank.
6. **File → Export as PDF** → save as `~/Documents/8bit-tax/MTC-Uniform-Resale-Cert_8BitLegacy_SIGNED_v2.pdf` (new filename — keep the original `_SIGNED.pdf` intact as backup).

### Pause-and-ask
- **The white rectangles look obviously like white rectangles** (visible borders, off-white tint): try Tools → Annotate → Eraser instead, or set the rect to truly pure white (#FFFFFF) with zero stroke. eBay reviewers are lenient on cosmetics but cleaner is better.
- **Can't tell which cell is which** (state labels overlap weirdly): screenshot the page, send it to me, I'll mark up which cells to clear.

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
