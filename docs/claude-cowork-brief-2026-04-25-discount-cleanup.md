# Claude Cowork Brief — 2026-04-25 — Delete Lingering Pixel-Fix Test Discounts

## Why this needs cowork

Three test discounts created during yesterday's pixel-fix experiments are still
active in Shopify and contaminating real orders. Specifically the
**automatic free-shipping discount** is auto-applying $0 to every customer
order, where they see the line `Test order free shipping v2 (pixel-fix 2026-04-24)`.

Main session can't delete via API — Shopify custom app token lacks
`write_discounts` scope. Browser-only fix.

## The task in one sentence

Delete three test discounts from Shopify admin → Discounts so they stop
appearing on customer-facing order summaries.

## Hard guardrails

- Do NOT delete or modify any other discount. Pre-existing real codes:
  `SHOPAGAINFOR10`, `SHOPEXTRA10` (Expired), `LUNCHBOX`, `8BITNEW` — leave alone.
- Do NOT create any new discounts.
- Do NOT touch the "Sale" collection or compare-at prices.

## Targets to delete (exact names)

| Type | Title / Code | Discount ID (if visible) |
|---|---|---|
| Automatic | `Test order free shipping v2 (pixel-fix 2026-04-24)` | 1415914815522 |
| Code | `TESTZERO-20260424-v2` | 1415914553378 |
| Code | `TESTZERO-20260424-v3` | 1415938375714 |

The automatic one is the urgent one — it's the only one auto-applying to live
customer orders. Codes are inert until someone types them in, but cleaning
them up keeps the Discounts page tidy.

## Step-by-step

1. **Sign in to Shopify admin** (`8bitlegacy.myshopify.com/admin`).
2. **Navigate:** left nav → Discounts.
3. **For the automatic discount:**
   - Filter or search for `pixel-fix` or `Test order free shipping v2`
   - Click into the row
   - Top-right ⋮ menu → **Delete discount**
   - Confirm
4. **For each of the two TESTZERO codes:**
   - Search for `TESTZERO`
   - For each row: click in → ⋮ → **Delete discount** → confirm
5. **Verify:** back on the Discounts page, search again — none of the three
   should appear. The remaining list should only contain
   `SHOPAGAINFOR10`, `SHOPEXTRA10`, `LUNCHBOX`, `8BITNEW`.

## Success criteria

- [ ] `Test order free shipping v2 (pixel-fix 2026-04-24)` no longer in
      Discounts list
- [ ] Both `TESTZERO-20260424-v2` and `TESTZERO-20260424-v3` gone
- [ ] Pre-existing 4 codes untouched
- [ ] Place a $1 cart in checkout (incognito) and confirm no `Test order free
      shipping v2` line appears at checkout

## Handoff

Write a short note in `docs/cowork-session-2026-04-25-discount-cleanup.md`:
- Which 3 discounts were deleted (paste IDs from above)
- Confirmation that a fresh checkout no longer shows the test line
- Anything weird (e.g., a discount couldn't be deleted because of a stuck
  reference)

Commit + Syncthing-propagate. No git push needed from cowork.

## What you are NOT doing

- Not touching API tokens or scopes
- Not editing any code
- Not interacting with the Google Ads campaign
- Not touching the Pokemon catalog or any product
