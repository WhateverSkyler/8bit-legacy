# Synthetic CIB Pricing Audit — 2026-04-13

**Status:** 🚨 **URGENT** — 1,184 products have CIB prices derived from a 1.8× loose multiplier instead of real PriceCharting CIB market data. Top 25 are likely under-priced by $100-$800+ per product — significant margin leak, especially if ads drive these to buyers.

**Source script:** `scripts/audit-synthetic-cib.py` (walks all `fix-cib-equals-loose-*.csv` logs + `search-refresh-*.csv` logs, applies latest-treatment-wins rule)

**Data files generated:**
- `data/synthetic-cib-products.json` — structured list (1,184 entries)
- `data/synthetic-cib-products.csv` — spreadsheet-friendly list

---

## How we got here

The `fix-cib-equals-loose.py` script was built to fix products where the CIB variant was priced identically to Loose (a seed bug). For each broken product it tries:

1. **PriceCharting search** → use real market CIB price × 1.35 (preferred)
2. **1.8× loose uplift fallback** → synthetic CIB = loose × 1.8, rounded to $X.99 psychology price

The fallback was designed as a "safe floor" because retro CIB premiums typically run 1.5×-3×. That works fine for common shovelware. But for **scarce/valuable titles**, the real CIB premium is often 3×-5× (sometimes 10×), so the synthetic price under-prices them badly.

### Distribution of the 1,184 synthetic-CIB products

**By console:**
| Console | Count |
|---|---|
| NES | 579 |
| PS2 | 125 |
| PS1 | 111 |
| Gameboy | 66 |
| Gamecube | 56 |
| PSP | 49 |
| Wii | 37 |
| Xbox | 35 |
| Dreamcast | 13 |
| Saturn | 6 |
| Other | 107 |

**By loose price band:**
| Band | Count | Risk |
|---|---|---|
| Under $20 | 618 (52%) | Low — synthetic is close enough for cheap games |
| $20-$50 | 331 (28%) | Moderate |
| $50-$100 | 172 (15%) | **High — these are collector titles** |
| **$100+** | **63 (5%)** | **🚨 Critical — significant under-pricing likely** |

---

## Top 25 most under-priced (by loose price)

These are the ones where a synthetic 1.8× almost certainly leaves the most money on the table:

| Loose | Synthetic CIB | Title |
|---|---|---|
| $399.99 | $718.99 | Earthbound — SNES |
| $279.99 | $502.99 | Chrono Trigger — SNES |
| $169.37 | $303.99 | Vanguard Bandits — PS1 |
| $162.64 | $291.99 | Torneko The Last Hope — PS1 |
| $152.00 | $272.99 | Resident Evil 2: Dual Shock Edition — PS1 |
| $148.41 | $266.99 | Run Saber — SNES |
| $148.20 | $265.99 | Ray Crisis — PS1 |
| $147.28 | $264.99 | Chiller — NES |
| $145.93 | $261.99 | Toxic Crusaders — NES |
| $145.00 | $260.99 | Tiny Toon Adventures: Scary Dreams — GBA |
| $144.99 | $259.99 | Tecmo Secret of the Stars — SNES |
| $144.64 | $259.99 | Ninja Gaiden III Ancient Ship of Doom — NES |
| $144.54 | $259.99 | Conan the Mysteries of Time — NES |
| $139.99 | $250.99 | Seaman [Mic Bundle] — Sega Dreamcast |
| $139.63 | $250.99 | Fox Hunt — PS1 |
| $135.88 | $243.99 | King of Dragons — SNES |
| $134.75 | $241.99 | Jet Grind Radio — GBA |
| $134.13 | $240.99 | Knights of the Round — SNES |
| $132.62 | $237.99 | Super Mario RPG — SNES |
| $132.52 | $237.99 | Super Adventure Island II — SNES |
| $131.54 | $235.99 | Axelay — SNES |
| $130.50 | $233.99 | Indiana Jones Infernal Machine — N64 |
| $128.45 | $230.99 | Shadow of the Beast II — Sega CD |
| $125.55 | $225.99 | Ultimate Muscle: Legends vs. New Generation — GameCube |
| $125.06 | $224.99 | Big Mountain 2000 — N64 |

**Example of the under-pricing problem:** Earthbound SNES CIB on PriceCharting is typically **$1,200-$1,500**. We're listing it at **$718.99**. That's a $500-800 per-sale margin leak if a customer buys it.

---

## Why PriceCharting refresh alone can't fix this

We've run `search-price-refresh.py` against these exact products multiple times today (AM stale-refresh + PM NO_MATCH retry + the fix-cib PC-first attempts) and they still failed to match. Reasons:

1. Some of these titles aren't indexed by PriceCharting's search (even when the game IS in PC's catalog under a slightly different title)
2. We hit PriceCharting's **IP rate limit** mid-afternoon after ~3,000+ queries — the block usually clears in 24-48h
3. The script's title-similarity scorer (0.3 threshold) may be rejecting close-but-not-exact matches

Retrying the PC path alone will recover some but not all.

---

## Proposed solutions (ranked by impact-to-effort)

### Option 1 — eBay sold-listings API as fallback data source (RECOMMENDED)
**Effort:** ~2-3 hours of Python dev
**Impact:** Fixes ~1,000 of the 1,184 products with accurate recent-sale data

eBay's Finding API (`findCompletedItems`) returns the last 30 days of closed sold listings for any search query. Building a pricing layer on top:

1. For each synthetic-CIB product, query eBay sold listings with `{title} {console} complete in box` (or `CIB`)
2. Filter to `Sold=True`, `Condition=Used`, exclude bulk lots and reproductions
3. Take median of the last 30 sold prices as the "real" CIB market value
4. Apply the same 1.35× multiplier + $X.99 rounding
5. Only update CIB if the new value differs from current synthetic by more than 10% (avoid churn)

Why it works: eBay sold prices are the gold standard for collector market data. The Finding API is free up to 5K calls/day — plenty for a nightly sweep of the 1,184 products.

**Deliverable:** `scripts/refresh-cib-from-ebay.py` + nightly scheduler job

### Option 2 — Manual tagging of the top 63 ($100+ band)
**Effort:** 2-3 hours of manual PC lookups + CSV edit
**Impact:** Fixes the 5% that represent 80% of the margin risk

For the 63 products with loose price ≥ $100 (the ones where synthetic is most likely wrong):
1. Manually look up each on PriceCharting by clicking through the catalog (bypasses search blocking)
2. Record the real CIB market price in a CSV
3. Run a one-shot update script to push the real values

Not scalable but fastest path to stopping the biggest margin leak.

### Option 3 — Slow overnight PC refresh with 10s-per-query pacing
**Effort:** Wait for IP block to clear (24-48h) + kick off a long-running job
**Impact:** Fixes ~200-400 of the 1,184 (same ~25% match rate as today, just completed rather than rate-limited)

Doesn't address the fundamental issue (some titles aren't in PC's search index) but gets whatever PC CAN give us without getting blocked.

### Option 4 — Hybrid (all three)
Run Option 3 overnight after block clears → Option 1 handles what PC can't → Option 2 audits the critical $100+ tier by hand as a belt-and-suspenders check.

---

## Immediate mitigation (before Google Ads launch)

Until the real fix ships, two quick moves:

1. **Exclude the $100+ synthetic-CIB products from the Winners / Discovery Google Ads campaigns.** We don't want to spend ads budget driving buyers to a CIB listing that's priced at half its real market value — those become the first sales and the biggest margin leaks. Verify via `docs/ads-winners-audit-2026-04-11.md` that none of the 17 Winners products are in the synthetic-CIB set. (Preview: Silent Hill 2 and a few GameCube cult titles are on the Winners list; need to cross-check them specifically against `data/synthetic-cib-products.json`.)
2. **Mark the catalog with a custom metafield `cib_price_source`** on each product: `pc_market` or `synthetic_uplift`. That way any future script / dashboard / reporting can filter. Good hygiene — doesn't fix anything but stops the state from being invisible.

---

## Recommended path forward

1. **Right now (terminal Claude):** write this doc — DONE — and verify whether any Winners-list products are synthetic-CIB
2. **Tomorrow or day after (once PC block clears):** kick off slow overnight refresh to recover what PC can give us
3. **This week (Tristan + Claude):** build Option 1 (`refresh-cib-from-ebay.py`) as the durable fix for the long tail
4. **Parallel:** manually verify the top 10-20 highest-price synthetic-CIB titles since those carry the most margin risk

---

## Audit metadata

- Run at: 2026-04-13 16:30 EDT
- Products scanned: 1,184 active, with confirmed live data
- Latest-treatment-wins rule applied: if a product was PC-matched AFTER a 1.8× uplift, it's NOT in the synthetic list
- Script: `scripts/audit-synthetic-cib.py`
