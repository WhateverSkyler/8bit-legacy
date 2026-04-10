# Compare-At Price Bug — 2026-04-10

**Discovered by:** Terminal Claude session, 2026-04-10 PM
**Severity:** Medium — not customer-visible (Shopify hides strike-through when `compare_at <= price`), but pollutes the smart "Sale" collection and breaks `manage-sales.py --list-active` reporting.

---

## What's wrong

11 variants currently have `compare_at_price` set to a value **lower than** the actual `price`. Likely fallout from the sequence:

1. CIB-fix script set `compare_at_price` on CIB variants to match the loose Game Only price
2. Subsequent price refresh updated CIB `price` upward (PriceCharting CIB > loose)
3. Result: `compare_at` (loose) < `price` (CIB) → "negative discount"

## Affected variants

| Product | Variant | compare_at | price | apparent "discount" |
|---|---|---:|---:|---:|
| Zelda Minish Cap - GBA Game | Game Only | $123.71 | $124.99 | -1.0% |
| Conker's Bad Fur Day - N64 Game | Game Only | $219.99 | $243.99 | -10.9% |
| Resident Evil - PS1 Game | Complete (CIB) | $95.00 | $109.99 | -15.8% |
| Metal Gear Solid - PS1 Game | Complete (CIB) | $44.92 | $58.99 | -31.3% |
| Resident Evil 2 - PS1 Game | Complete (CIB) | $66.50 | $109.99 | -65.4% |
| Mega Man X4 - PS1 Game | Complete (CIB) | $22.78 | $37.99 | -66.8% |
| Grand Theft Auto III - PS2 Game | Complete (CIB) | $8.46 | $14.99 | -77.2% |
| Conker's Bad Fur Day - N64 Game | Complete (CIB) | $219.99 | $438.99 | -99.5% |
| 007 GoldenEye - N64 Game | Complete (CIB) | $50.75 | $104.99 | -106.9% |
| Grandia II - Sega Dreamcast Game | Complete (CIB) | $40.30 | $84.99 | -110.9% |
| Zelda Minish Cap - GBA Game | Complete (CIB) | $123.71 | $304.99 | -146.5% |

## Customer-facing impact

**None directly visible.** Shopify suppresses strike-through display when `compare_at_price <= price`, so the storefront looks normal. But:

- The smart "Sale" collection (rule: `compare_at_price > 0`) will pull these in as if they were on sale, which is wrong
- Google Shopping may pick them up under sale pricing rules and create disapprovals
- `manage-sales.py --list-active` reports them as active sales when they're not

## Recommended fix

**Option A — Targeted clear (safest):**
For each broken variant, set `compare_at_price = null`. 11 variants, ~10 sec via Shopify GraphQL.

**Option B — Sweep fix (broader):**
Walk all products, for any variant where `compare_at < price`, clear `compare_at`. Catches any others I didn't see in the first pass.

**Option C — Walk + recompute:**
For CIB variants, set `compare_at` to a strict markup over the loose price (or just leave null until a real sale is applied via `manage-sales.py`).

I recommend **Option B** as a one-off cleanup script (`scripts/fix-broken-compare-at.py`), with `--dry-run` first.

## NOT recommended

- Modifying `manage-sales.py` to filter these out — that hides the bug rather than fixing it
- Bulk-clearing ALL `compare_at_price` values — would also wipe the legitimate ~23 active sales

## Status

- [x] Bug documented
- [ ] User decision on fix approach (A, B, or C)
- [ ] Cleanup script written + dry-run reviewed
- [ ] Cleanup applied
- [ ] `manage-sales.py --list-active` re-run to confirm
