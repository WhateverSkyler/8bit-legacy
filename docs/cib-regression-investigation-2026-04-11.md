# CIB Inventory Regression — Investigation 2026-04-11

## TL;DR

All 6,112 CIB variants currently have `inventoryPolicy: CONTINUE` (always purchasable regardless of qty) AND `qty=10000`. Root cause of the periodic regression is unknown but **not** in any Python script in this repo or any TypeScript code in the dashboard. Mitigation: add `fix-cib-inventory.py` to the scheduler so it re-sets qty daily.

## State of the world (2026-04-11 after re-fix)

Sample of 10 products (verified via `scripts/check-cib-tracked.py`):

```
Game Only: policy=DENY    qty=10000 tracked=True
CIB:       policy=CONTINUE qty=10000 tracked=True
```

Full catalog sweep (`scripts/set-cib-continue-policy.py --dry-run`):
- 7,290 active products
- 6,112 CIB variants total
- 6,112 already have policy=CONTINUE
- 0 need fixing

So purchasability on Shopify is currently fine. The issue is specifically about the `inventoryQuantity` value, which Merchant Center uses to decide "in stock" for the Google Shopping feed.

## What I ruled out

Searched the entire repo for code that writes to `inventory_levels`, `inventoryQuantity`, or `inventoryItem.tracked`:

| File | Touches inventory? |
|------|---|
| `scripts/price-sync.py` | No — only `productVariantUpdate.price` |
| `scripts/full-price-refresh.py` | No — only `productVariantsBulkUpdate` with `price` |
| `scripts/search-price-refresh.py` | No — same pattern |
| `scripts/manage-sales.py` | No — only `compareAtPrice` |
| `scripts/pokemon-card-importer.py` | No — creates products, doesn't set inventory |
| `scripts/optimize-product-feed.py` | No — only `productUpdate` with tags + SEO title |
| `dashboard/src/lib/*` | No — nothing in lib/ references inventory writes |
| `dashboard/src/app/api/automation/price-sync/run/route.ts` | No — only reads |
| `scripts/fix-cib-inventory.py` | Yes — intentional writer, sets qty=10000 |

So nothing in our code is doing it.

## Hypothesized causes (unverified)

1. **Google & YouTube Shopify app inventory sync.** The app is connected to Merchant Center 5296797260 and may two-way sync availability. If Merchant Center had a stale read of one variant as qty=0, it could push that back to Shopify.
2. **A Shopify app installed in the admin** (not in this repo) — something with `write_inventory` scope. Should audit installed apps.
3. **Shopify's own "set inventory to 0 on archive/unpublish/re-publish" behavior** — if a bulk operation was run on products (e.g. via the Shopify admin), that could reset inventory.
4. **Manual edit** by the store operator via the Shopify admin UI's bulk editor.

## Recommended fix

Since the root cause can't be pinned down without more evidence, make the repair idempotent and automatic:

### Option A (recommended): Scheduled daily resync

Add `fix-cib-inventory.py` to the dashboard scheduler as a daily job at 2 AM ET. Pros: catches regressions within 24h, low risk. Cons: doesn't prevent the regression, just papers over it.

### Option B: Set `tracked: false` on all CIB variants

Makes inventory untracked entirely — Shopify always reports as in-stock regardless of qty. Matches dropship reality. Pros: immune to regressions. Cons: loses the ability to track supply issues (e.g. "we can't source this game anymore"); order validator in `dashboard/src/lib/order-validator.ts` currently catches unfulfillable orders at fulfillment time, so the signal isn't lost, just moved.

### Option C: Find the culprit app

Audit installed Shopify apps (admin → Apps) and disable any non-essential app with `write_inventory` scope. Would require user action in Shopify admin.

## Action items

- [x] Document findings (this file)
- [ ] User decision: Option A, B, or C?
- [ ] If Option A: add to dashboard scheduler in `src/lib/scheduler.ts`
- [ ] If Option B: update `fix-cib-inventory.py` to also set `inventoryItem.tracked: false` on CIB variants
- [ ] Update `CLAUDE.md` CIB note with the new mitigation

## Notes for future sessions

- `scripts/set-cib-continue-policy.py` exists and is idempotent — run it if you suspect CIB variants have regressed to DENY policy. Current state shows all 6,112 are CONTINUE.
- `scripts/check-cib-tracked.py` is a 10-product sample probe for quick eyeballing.
- `scripts/fix-cib-inventory.py` is the canonical "fix qty=10000" script. Requires no special scopes beyond read/write inventory.
- The ecommerce audit from 2026-04-06 (`docs/ecommerce-infrastructure-audit-2026-04-06.md`) noted the issue originally as Merchant Center "Out of stock" alerts on CIB variants.
