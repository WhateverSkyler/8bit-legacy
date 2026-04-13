# Session Handoff — 2026-04-14 (Tuesday morning)

**Written:** 2026-04-13 04:42 PM EDT (Monday, end of laptop session)
**Target:** Tomorrow morning Tristan session (any machine)
**Status:** Massive progress today. One critical finding (synthetic CIB pricing) needs a durable fix next session.

---

## 🎯 Tomorrow's priority stack — ranked

### 🚨 1. Fix the synthetic CIB pricing problem (CRITICAL)

**The issue:** 1,184 of the ~6,112 multi-variant retro games have CIB prices set to `loose × 1.8` rather than real market data. Under-prices rare/valuable CIBs meaningfully. Full audit in `docs/synthetic-cib-audit-2026-04-13.md`, product list in `data/synthetic-cib-products.csv`.

**Worst offenders** (listed CIB vs real market):
- Earthbound SNES — $718.99 listed / ~$1,200-1,500 real
- Chrono Trigger SNES — $502.99 / ~$700-900 real
- 63 products over $100 loose-price; top 25 in the audit doc

**Immediate mitigation** (before anything else, 15 min):
```bash
# Manually look up the top 25 on PriceCharting in a browser, edit data/synthetic-cib-products.csv
# with real CIB market prices, then run a one-shot update script — or do individual Shopify admin edits
```
Focus: the 25 titles in `docs/synthetic-cib-audit-2026-04-13.md` "Top 25" table.

**Durable fix** (~2-3 hours, build this next session):
Build `scripts/refresh-cib-from-ebay.py`:
- Input: `data/synthetic-cib-products.csv`
- For each product, query eBay's `findCompletedItems` API with `{title} {console} complete in box`
- Filter: sold within last 30 days, condition=Used, exclude bulk lots
- Take median of last 30 sold prices as "real CIB market value"
- Apply 1.35× multiplier + round down to $X.99
- Update Shopify via `productVariantUpdate` mutation
- Safety: only update if new price differs from current by >10%, log every change
- eBay API creds are already in `.env` (`EBAY_APP_ID`)

Reference: the existing `scripts/ebay-finder.py` shows the API call pattern. Copy its auth setup.

**Why eBay and not PriceCharting retry:**
- We got IP-blocked from PriceCharting today after ~3K queries (block usually clears in 24-48h)
- Many of these synthetic-CIB products aren't findable via PC search even when PC has the data
- eBay sold listings are the gold standard for collector market — no rate-limit drama at 5K calls/day free tier

### 🟡 2. Pre-ads-launch: fix Legend of the Mystical Ninja SNES

**Why:** Only Winners-list product with a synthetic CIB (CIB $145.99 synthetic, real market ~$300-400). Ads will drive traffic directly to this product.

**Two options:**
- **A:** Manually set its CIB price to ~$350 via Shopify admin → Products → Legend of the Mystical Ninja - SNES Game → Variants → Complete (CIB) → Price. 2 min.
- **B:** Exclude this SKU from the Winners campaign when building the Google Ads campaign.

Recommend A — it's quicker and fixes the actual problem.

### 🟢 3. Build the 2 Google Ads Shopping campaigns (paused)

Follow `docs/ads-pre-launch-checklist.md` Section F. Create:
- `8BL-Shopping-Winners` at $6/day (Manual CPC, max $0.75, priority High, Winners SKUs only, campaign-level negatives from `docs/ads-negative-keywords-master.md`)
- `8BL-Shopping-Discovery` at $4/day (Manual CPC, max $0.35, priority Low, everything except Winners/Pokemon/under-$15/over-$200)

Leave both **Paused**. Enable only after Section G content gate (14 days of social + Podcast Ep 2 scheduled).

Can delegate this whole task to Mac Claude cowork if you prefer. Cowork prompt template in `docs/claude-cowork-brief-2026-04-13.md` for style.

### 🟢 4. Re-run stale-loose refresh overnight (if PC unblocks)

PriceCharting should unblock us 24-48h after today's lockout. When it does:

```bash
# Verify unblock status
python3 -c "import requests; r=requests.get('https://www.pricecharting.com/search-products?q=Crystalis+NES&type=videogames', headers={'User-Agent':'Mozilla/5.0'}, timeout=15); print(f'Status: {r.status_code}')"
# Should be 200, not 403

# Then kick off overnight sweep with longer pacing (10s delays vs today's 2s)
# Edit SEARCH_DELAY in scripts/search-price-refresh.py from 2.0 to 10.0 before running
python3 scripts/search-price-refresh.py --apply --only-ids-file data/nomatch-product-ids.json
# ETA ~6-8 hours with 10s delays, but safer from rate limits
```

Expected recovery: 200-400 of the remaining 1,100-ish stale products. Doesn't replace the eBay fix but complements it.

---

## 📊 What shipped today (Monday 2026-04-13) — for the record

### Pricing (terminal Claude)
- ✅ CIB==Loose bug confirmed fixed (99.1% of 6,081 games correct)
- ✅ 4 of 5 genuine CIB edge cases patched (Hot Shots Tennis, Hot Wheels Stunt Track, NBA 09 ×2; ECW below $1 noise floor)
- ✅ 1,618 stale May-2025 loose variant ids identified; 136 loose + 172 CIB prices refreshed from PriceCharting (24.9% match rate before PC blocked us)
- ✅ Full compare_at sweep — 8 stuck + 38 inverted Loose>CIB = 46 broken relationships fixed
- ✅ 55 more NO_MATCH products recovered via multi-query retry before PC blocked
- 🚨 **DISCOVERED:** 1,184 products have synthetic 1.8× CIB prices (not real market data)

### Theme + UX (cowork)
- ✅ Variant price display bug fixed — price updates when toggling Game Only ↔ CIB
- ✅ Sale price display bug fixed — struck-through price also updates + shows/hides correctly
- ✅ Google Customer Reviews Custom Pixel live (ID 149717026)
- ✅ Theme state: MAIN = `Copy of bs-kidxtore-home6-v1-7-price-fix` (185256640546), 2 backups retained

### Settings (cowork)
- ✅ Free shipping $50 → $35
- ✅ Return policy 30 → 90 days (refund policy + theme settings + announcement bar)
- ✅ Google Ads 822-210-2291 confirmed linked (stop asking — memory updated)

---

## 🔒 Decisions logged from today

1. **Email campaigns deferred** — user wants site + social + ads live first. `feedback_email_sequencing.md` in memory. Do NOT suggest the email welcome flow install until all three are live.
2. **GCR badge deferred** — wait until 25+ reviews accumulate. Empty badge looks worse than no badge.
3. **Shopify plan impact** — nothing we've shipped or queued increases the Basic plan cost. If future work needs Plus features, flag before doing anything.

---

## 🗂️ Files that matter for tomorrow

**Read these first:**
- This file
- `docs/synthetic-cib-audit-2026-04-13.md` (the critical finding)
- `data/synthetic-cib-products.csv` (the 1,184 products to fix)

**Reference:**
- `docs/ads-pre-launch-checklist.md` (Section F for campaign build)
- `docs/ads-winners-curation-list.md` (the 18 Winners)
- `docs/google-ads-launch-plan-v2.md` (full context)
- `docs/cowork-session-2026-04-13-pm.md` (what cowork shipped)

**Memory to pick up:**
- `~/.claude/projects/-Users-tristanaddi1-Projects-8bit-legacy/memory/MEMORY.md` (index)
- `project_cowork_audit.md` (updated with 2026-04-13 state)
- `feedback_email_sequencing.md` (email hold rule)

---

## 🧭 Suggested opening move tomorrow

```bash
cd ~/Projects/8bit-legacy
git pull --ff-only
```

Then tell whichever Claude you're using:

> Read `docs/session-handoff-2026-04-14.md` — the synthetic CIB pricing issue is the critical priority. Start by building `scripts/refresh-cib-from-ebay.py` per Option 1 in `docs/synthetic-cib-audit-2026-04-13.md`. Also manually fix Legend of the Mystical Ninja SNES CIB price before that so it's not blocking ads launch.

That's the cleanest path to getting the remaining pricing work done AND unblocking ads.

---

## Outstanding tech debt (no urgency)

- 107 uncategorized console products in the synthetic-CIB set (the audit script's "other" bucket) — minor tagging cleanup
- VPS dashboard nginx 401 — replace with Next.js-native auth
- 900+ PC-unfindable titles — tackled by eBay refresh (Option 1 above)
- CIB inventory regression monitoring — add `fix-cib-inventory.py` to scheduler as daily job

None of these block ads launch.
