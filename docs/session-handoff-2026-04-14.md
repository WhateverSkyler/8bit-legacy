# Session Handoff — 2026-04-14 (Tuesday morning)

**Written:** 2026-04-13 ~11:55 PM EDT (end of Monday-night session)
**Target:** Tomorrow's session (any machine)
**Status:** Main sweep landed cleanly. CIB second-pass script is built + smoke-tested but NOT YET APPLIED. Pick up there.

---

## TL;DR — where we are right now

1. **Full unified PC+eBay refresh completed tonight.** `scripts/refresh-prices-unified.py` ran the 1,678-product union (nomatch + stale-loose + synthetic-CIB) with `--apply`. Result: 1,013 loose + 575 CIB prices updated, 0 errors, 187 min runtime. Log: `data/logs/refresh-unified-20260413_203700.*`.
2. **Synthetic-CIB count dropped 1,184 → 605** after audit script was fixed to recognize the new log format.
3. **Second-pass CIB script exists.** `scripts/refresh-cib-second-pass.py` — targets those 605 remaining synthetic CIBs with relaxed eBay sampling + a ratio-sanity repair (`CIB ≥ Loose × 1.3`). Smoke-tested on 10 products tonight (report-only). Results look reasonable but need a spot-check before applying.
4. **Not yet run with `--apply`.** That's the first thing to do next session.

---

## Priority 1 — Finish the CIB second-pass (~30-60 min, mostly waiting)

The plan:

```bash
cd ~/Projects/8bit-legacy
git pull --ff-only

# 1) Quick sanity check on tonight's smoke test
cat data/logs/cib-second-pass-20260413_235147.csv
```

Look at the 10 rows. Tonight's smoke test flagged two issues to be aware of:

- **Two rows have `NO_CONSOLE` status** (`720 - NES Game`, `Alien 3 - SNES Game`). The console-lookup is falling through for some products. Likely because the product wasn't in `live` map or variants aren't tagged with console metadata the script expects. Worth a 5-min look before full run.
- **All-Star Baseball 2003 GBA** — got CIB $49.99 from only 3 eBay samples while Loose is $10.99 (ratio 4.55×). That's suspicious; cheap sports games shouldn't have a 4× premium. `MIN_EBAY_SAMPLE=2` may be too permissive. Consider bumping to 3 or 4.

Two low-risk paths forward:

**Path A — ship it as-is and log outliers.** The 605 products that need fixing are mostly cases where Loose updated but CIB didn't; broken ratios are the bigger risk. Running the script as-is applies the 1.8× synthetic fallback when eBay data is thin (which is what we have now) OR picks up a slightly-noisy eBay median (which is still better than the old unrepaired synthetic). Accept and audit.

**Path B — tighten first.** Before `--apply`, edit `MIN_EBAY_SAMPLE = 2` → `3` in `scripts/refresh-cib-second-pass.py`, re-run `--limit 25`, spot-check. Adds ~20 min.

Recommend **Path B** given Earthbound / Chrono Trigger etc. live in the 605 list and a mis-priced $600 CIB is ugly if a customer buys it.

Then:

```bash
# Full apply run — 605 products × ~3s each = ~30-40 min
systemd-inhibit --what=idle:sleep --who=claude --why="cib-second-pass refresh" \
  nohup python3 scripts/refresh-cib-second-pass.py --apply > /tmp/cib-pass2.out 2>&1 &

# Monitor
tail -F /tmp/cib-pass2.out
```

After it finishes:

```bash
# Regenerate synthetic audit
python3 scripts/audit-synthetic-cib.py
# Expected: synthetic count drops toward 0 (or near-0 with only ratio_repair fallbacks remaining)
```

---

## Priority 2 — Spot-check top-value CIBs

Regardless of how the second-pass goes, manually verify the **top 10 by price** in the resulting CIB changes. Real-market cross-reference should be fast:

- Earthbound SNES CIB — should be ~$1,200-1,500 (was $718 synthetic)
- Chrono Trigger SNES — ~$700-900
- Legend of the Mystical Ninja SNES — ~$300-400 (Winners-list ad product — MUST be correct before ads)
- Any other $300+ CIB changes in the second-pass log

If the script undershoots on these, manually set in Shopify admin. They're high-visibility.

---

## Priority 3 — Back to the real work

Once CIB pricing is clean:

1. **Google Ads Shopping campaigns** — `docs/ads-pre-launch-checklist.md` Section F. Build 2 campaigns PAUSED, enable after content gate.
2. **Winners product audit final pass** — `docs/ads-winners-audit-2026-04-11.md`. Legend of the Mystical Ninja CIB price specifically needs confirmation post-second-pass.
3. **Outstanding tech debt** — listed at bottom of old handoff text below, still applies.

---

## Tonight's script artifacts (reference)

- **`scripts/refresh-prices-unified.py`** (NEW, ~380 lines) — unified PC+eBay refresh. OAuth2 client-credentials for eBay Browse API. Single broad query per product, classifies loose vs CIB in code, title-similarity filter with Roman→Arabic numeral normalization to block ActRaiser 2 pollution. Supports `--apply`, `--limit`, `--resume`, `--ids-file`, `--no-ebay`.
- **`scripts/refresh-cib-second-pass.py`** (NEW, ~290 lines) — targeted CIB-only refresh for the 605 remaining synthetic products. Relaxed: `MIN_EBAY_SAMPLE=2`, title overlap 0.5, two-query eBay ("complete in box" + "cib" suffix, price DESC). Ratio sanity repair enforces `CIB ≥ Loose × 1.3`, uses 1.8× synthetic fallback when eBay samples are too thin.
- **`scripts/audit-synthetic-cib.py`** (MODIFIED) — now walks both `search-refresh-*.csv` AND `refresh-unified-*.csv`, accepts `NO_CHANGE` as a real-market override, filters to CIB-variant rows only.
- **`data/refresh-union-ids.json`** — 1,678 GIDs (full sweep input list).
- **`data/remaining-synthetic-ids.json`** — 605 GIDs (second-pass input list).
- **`data/logs/refresh-unified-20260413_203700.csv`** — full sweep results.
- **`data/logs/cib-second-pass-20260413_235147.csv`** — tonight's 10-product smoke test.

---

## Quick sanity snippet for opening tomorrow

```bash
cd ~/Projects/8bit-legacy && git pull --ff-only

# 1) How many synthetic CIBs remain right now?
python3 scripts/audit-synthetic-cib.py 2>&1 | grep "Synthetic-CIB"

# 2) Inspect tonight's smoke test
cat data/logs/cib-second-pass-20260413_235147.csv
```

Then decide Path A vs B above, run, audit, and you're done with pricing.

---

## (Preserved from earlier 04-14 handoff) — everything else still pending

### Pre-ads fix: Legend of the Mystical Ninja SNES CIB
Only Winners-list product with a synthetic CIB. Second-pass should fix it, but confirm the price lands in ~$300-400 range. If not, manually set via Shopify admin before enabling ads.

### Build 2 Google Ads Shopping campaigns (PAUSED)
Follow `docs/ads-pre-launch-checklist.md` Section F:
- `8BL-Shopping-Winners` — $6/day, Manual CPC $0.75, priority High, Winners SKUs only
- `8BL-Shopping-Discovery` — $4/day, Manual CPC $0.35, priority Low, everything except Winners/Pokemon/under-$15/over-$200

Leave both Paused. Enable only after Section G content gate (14 days social + Podcast Ep 2).

### Outstanding tech debt (no urgency)
- 107 uncategorized console products in the synthetic-CIB set — minor tagging cleanup
- VPS dashboard nginx 401 — replace with Next.js-native auth
- `fix-cib-inventory.py` daily scheduler job — for the CIB inventory regression we saw Monday

### Decisions still in force
1. Email campaigns deferred until site + social + ads live
2. GCR badge deferred until 25+ reviews
3. Flag any Shopify plan impact before shipping (Basic tier protected)
