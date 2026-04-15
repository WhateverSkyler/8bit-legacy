# Session Handoff — 2026-04-15 (Wed afternoon)

**Written:** 2026-04-15 ~4:00 PM EDT
**Status:** CIB second-pass DONE. Synthetic-CIB count **605 → 0**. Two items flagged for manual review.

---

## TL;DR

1. **Loose pricing fully resolved** — Mon night's unified sweep updated 1,013 loose + 575 CIB, 0 errors.
2. **CIB second-pass DONE today** — 605 products processed in 56 min, 0 errors. 299 real-market eBay matches + 301 synthetic ratio/outlier repairs + 5 already-correct. Audit now shows **0 synthetic CIBs remaining**.
3. **TWO ITEMS NEED MANUAL REVIEW** before Google Ads goes live — see "Flags" section below.
4. **Then commit + push** and resume Google Ads prep.

---

## What changed today in `scripts/refresh-cib-second-pass.py`

Four fixes over the Monday-night version:

1. **`MIN_EBAY_SAMPLE = 2 → 3`** — smoke test showed 3-sample outliers like All-Star Baseball 2003 at ratio 4.55×. Bumped the floor.
2. **Console tag parsing fixed** — tags are `console:nes`, not bare `nes`. Added `console:` prefix strip before TAG_TO_CONSOLE lookup. Clears the NO_CONSOLE errors on 720 NES, Alien 3 SNES, etc.
3. **Graded listing filter** — added to bad-keyword list in `_is_cib_listing()`: `wata`, `vga`, `psa`, `cgc`, `pca`, `graded`, `authenticated`, `mint condition`, `museum`, `collector's grade`. These were polluting the `price desc` sort with $500+ graded copies.
4. **Outlier ceiling guard** — new constants `RATIO_CEILING = 3.5` and `OUTLIER_SAMPLE_THRESHOLD = 8`. If eBay says CIB/Loose > 3.5× with fewer than 8 samples, treat as thin-sample outlier and fall back to synthetic 1.8×. Logged as `synthetic_outlier_guard(ebay_was_X_n=Y)`.

25-product re-test confirmed the guards work: All-Star Baseball 2003 (was 4.55×, n=3) and Battle Bull (was 4.29×, n=3) both fell back to safe synthetic $19.99 and $62.99.

---

## Final run stats

```
Log: data/logs/cib-second-pass-20260415_145908.log
CSV: data/logs/cib-second-pass-20260415_145908.csv

Total products:      605
eBay CIB matches:    299  (real market data)
Synthetic repairs:   301  (1.8× fallback — either eBay failed or outlier-guard tripped)
Already OK (<$0.50): 5
Errors:              0
Time:                55.9 min
```

Audit verification:
```
python3 scripts/audit-synthetic-cib.py → "Synthetic-CIB products: 0"
```

**Also updated today:** `scripts/audit-synthetic-cib.py` now walks `cib-second-pass-*.csv`
in addition to the legacy patterns, so future audits will stay accurate.

---

## ⚠️ Flags — manual review needed before Google Ads goes live

### 1. Legend of the Mystical Ninja SNES — CIB came in LOW
```
Loose $86.99 | Old CIB $145.99 | New CIB $202.99 | ratio 2.33× | source: ebay(5)
Target per handoff: $300-400
```
This is a Winners-list ad product. 5 eBay comps isn't a huge sample. Consider:
- Manually verify current eBay SOLD CIB comps (not active listings) — sort: Recently Sold
- If real market is $300-400, override manually via Shopify admin
- If market really is closer to $200, accept and update the Winners audit doc

### 2. Chrono Trigger SNES — LOOSE price is WRONG
```
Loose $21.99 | Old CIB $502.99 | New CIB $1179.99 | ratio 53.66× | source: ebay(27)
```
CIB at $1179.99 is plausible ($800-1200 real market), but the LOOSE price of $21.99
is obviously corrupt. Real loose is ~$100-150. This bug is NOT from today's run —
the loose was already wrong going into the second-pass. Investigate:
- Check recent price-sync history for Chrono Trigger
- Possible cause: a PriceCharting title-match pulled the wrong product at some point
- Fix manually in Shopify admin, then figure out which script mis-matched it

Neither issue is from new damage — the second-pass did its job. These are pre-existing
or edge-case issues the second-pass surfaced.

---

## Next-session checklist (in order)

### 1. Handle the two flags above
- Fix Chrono Trigger loose price manually in Shopify admin
- Decide on Mystical Ninja CIB ($202.99 vs target $300-400)

### 2. Commit + push (if not already done this session)
Everything from today should already be committed. If not:
```bash
cd ~/Projects/8bit-legacy
git status
git add scripts/refresh-cib-second-pass.py scripts/audit-synthetic-cib.py \
        docs/session-handoff-2026-04-15.md \
        data/logs/cib-second-pass-20260415_* data/synthetic-cib-products.*
git commit -m "CIB second-pass apply — synthetic count 605 → 0"
git push
```

### 3. Spot-check a few more top-value CIBs (optional)
```bash
CSV="$(ls -1t data/logs/cib-second-pass-*.csv | head -1)"
# Top 20 by new_cib price
awk -F, 'NR>1 && $8=="APPLIED" {print $6, $1}' "$CSV" | sort -rn | head -20
```

---

## Then resume the real roadmap

1. **Google Ads Shopping campaigns** — build 2 campaigns PAUSED per `docs/ads-pre-launch-checklist.md` Section F:
   - `8BL-Shopping-Winners` — $6/day, Manual CPC $0.75, priority High
   - `8BL-Shopping-Discovery` — $4/day, Manual CPC $0.35, priority Low
   - Enable both only after content gate (14 days social + Podcast Ep 2).

2. **Winners audit final pass** — `docs/ads-winners-audit-2026-04-11.md`. Confirm Mystical Ninja CIB price post-second-pass.

3. **Outstanding tech debt (no urgency):**
   - 107 uncategorized console products in original synthetic-CIB set — minor tagging cleanup
   - VPS dashboard nginx 401 → Next.js-native auth
   - `fix-cib-inventory.py` daily scheduler job (Monday regression)

---

## Decisions still in force

- Email campaigns deferred until site + social + ads are live
- GCR badge deferred until 25+ reviews
- Shopify Basic plan protected — flag anything that would push into Shopify tier
