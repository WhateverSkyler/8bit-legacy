# Session Handoff — 2026-04-11

## What got done

### CIB Pricing Bug Fix (critical — user-reported)
- **Problem:** 1,364 of 6,112 multi-variant retro games (22.3%) had CIB priced identically to Loose
- **Root cause:** CIB variants seeded with loose price on creation + PriceCharting search had ~22% miss rate on long-tail titles, so unmatched products kept bad seed forever
- **Fix:** `scripts/fix-cib-equals-loose.py` — PriceCharting search first, 1.8x loose uplift fallback when no market data, $5 minimum CIB premium, $1 noise filter
- **Result:** CIB==Loose dropped from 1,364 (22.3%) → 36 (0.6%). Of the 36 remaining: 20 are console bundles (false positives), 11 are controllers (legitimately same price), 5 are edge cases (4 DNS errors during run, 1 filtered by noise floor)
- **Verification:** `scripts/scan-cib-equals-loose.py` re-scanned all 7,290 products and confirmed
- **Full write-up:** `docs/cib-pricing-fix-2026-04-11.md`

### SEO Meta Descriptions (store-wide)
- **Problem:** 100% of 7,290 active products had no SEO meta description — Google was falling back to truncated body HTML for every organic + Shopping result
- **Fix:** `scripts/set-seo-descriptions.py` — templated descriptions under 160 chars, console-aware, safe to re-run (`--only-missing` default)
- **Result:** 7,290 updated, 0 errors, 0 skipped

### Product Feed Optimizer Re-run
- **What:** Re-ran `scripts/optimize-product-feed.py` after the 694 miscategorized `category:console` tags were fixed earlier in the day
- **Result:** 409 products updated with correct custom labels, 7,280 already correct, 0 failed

### Network Resilience Patch
- **What:** Patched `scripts/optimize-product-feed.py` graphql() function after discovering it hung 2.5 hours on a zombie TCP socket during a network outage
- **Changes:** `timeout=30` on requests.post(), try/except RequestException with exponential backoff retry, `flush=True` on all print() calls (prevents tee/nohup buffering making output look dead)
- **Also discovered:** System idle-suspended mid-run for 50 minutes, stalling both fix-cib and set-seo. Fixed by registering `systemd-inhibit --what=idle:sleep` for the duration of the jobs

## Unpushed commit

```
3633664 Fix 1,364 CIB==Loose pricing bug + SEO descriptions store-wide
```

Sitting on local `main`, NOT pushed. Run `git push` when ready.

## Outstanding work

### Task #30 — Investigate 1,625 stale loose prices from 2025-05
- The CIB investigation found that 26.6% of loose variants haven't been refreshed since May 2025
- This is a separate issue from the CIB==Loose bug — even products where CIB > Loose may have stale base prices
- `search-price-refresh.py` only matches ~45% of products; `full-price-refresh.py` only matched 5.8% on its last run (brittle title normalization)
- Likely fix: improve title matching in the refresh scripts, or build a new hybrid approach

### Spot-check verification (manual)
- Check 10 random fixed CIB products on the live storefront to confirm the CIB variant shows a higher price than Loose
- Confirm no Winners/ads-relevant products got weird prices

### 5 remaining CIB edge cases
- ECW Hardcore Revolution (Dreamcast), Hot Shots Tennis (PSP), Hot Wheels Stunt Track Driver (GBC), NBA 09 The Inside (PS2 + PSP)
- Can re-run `python3 scripts/fix-cib-equals-loose.py --apply` against the regenerated `data/cib-equals-loose.json` (now contains only 36 entries) — but it'll try to fix all 36 including the false-positive bundles/controllers. Probably not worth the effort for 5 products; next scheduled price-refresh will catch them.

## New files created this session

```
scripts/fix-cib-equals-loose.py       — CIB pricing fix (PriceCharting search + 1.8x uplift fallback)
scripts/scan-cib-equals-loose.py      — Verification scanner for CIB==Loose count
scripts/set-seo-descriptions.py       — Store-wide SEO meta description writer
docs/cib-pricing-fix-2026-04-11.md    — Full investigation + results write-up
data/cib-equals-loose.json            — Current 36 remaining offenders (post-fix)
data/cib-equals-loose.pre-fix.json    — Original 1,364 offenders (pre-fix snapshot)
data/logs/fix-cib-equals-loose-20260411_150950.{csv,log}  — Apply run log
data/logs/seo-descriptions-apply-20260411_181931.log      — SEO apply run log
data/logs/feed-optimize-apply-20260411_181900.log         — Feed optimizer run log
data/logs/scan-cib-verify-20260411_200156.log             — Verification scan log
```

## Modified files

```
scripts/optimize-product-feed.py      — graphql() patched with timeout + retry + flush
```
