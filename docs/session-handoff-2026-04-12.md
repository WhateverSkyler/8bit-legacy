# Session Handoff — 2026-04-12 (Sunday PM) → 2026-04-13 (Monday, office laptop)

**Written:** Sunday April 12, 2026 3:27 PM EDT (Linux desktop)
**Target:** Tomorrow morning at the office, on the MacBook
**Status:** Everything committed and pushed. Clean start.

---

## Step 0 — Laptop setup (90 seconds)

```bash
cd ~/Projects/8bit-legacy
git pull --ff-only
```

If it reports "Already up to date." you're good.
Then read this file first, then `docs/session-handoff-2026-04-11.md` for yesterday's context.

---

## Where we stand

- **CIB pricing bug:** FIXED yesterday. 1,364 → 36 remaining (those 36 are false positives: console bundles + controllers + 5 edge cases). `docs/cib-pricing-fix-2026-04-11.md`.
- **SEO meta descriptions:** FIXED yesterday. All 7,290 products have templated descriptions.
- **Winners ads prep:** 17 products LIVE and audited. Tag bug (694 products) patched. Landing-page audit clean. `docs/ads-winners-audit-2026-04-11.md` + `docs/winners-landing-page-audit.md`.
- **Google Ads launch:** Gated on Section A of `docs/ads-pre-launch-checklist.md` — conversion tracking goals are still "Misconfigured" in the Google Ads UI. Browser-only fix; can't be delegated to Claude from a terminal.
- **Sale wave:** `manage-sales.py` has TWO known bugs. Do NOT run `--apply` until patched. See `docs/sale-wave-dryrun-findings-2026-04-10.md`.

---

## Today (Sunday April 12) — what got done

Nothing substantive. Session was a read-through of project docs for context + this handoff. All yesterday's commits are already on `origin/main`.

---

## 🎯 Tomorrow's priority stack (ranked by "does this unblock a revenue stream")

### 🔴 1. Fix Google Ads conversion tracking (MUST be first — all ads work depends on it)
**Where:** Google Ads web UI, not the repo.
**Time:** ~20 min.
**How:** Follow `docs/ads-pre-launch-checklist.md` Section A (A5 + A6).
- Promote secondary conversion actions to **Primary** for Add to cart, Begin checkout, Page view goals
- Fire live events on `8bitlegacy.com` in incognito (page view → view item → search → add to cart → begin checkout → add payment info → abandon)
- Wait 2–4 hours, re-check Conversions page
- Target state: all 7 actions show "Recording" or "No recent conversions", NOT "Inactive"
**Why first:** The $700 promo credit (expires 2026-05-31) is worthless without conversion tracking. Every other launch step is blocked until this is green.

### ~~🔴 2. Re-link Google Ads account~~ ✅ RESOLVED (2026-04-13 PM)
**Confirmed linked:** Google & YouTube → Settings shows Google Ads account **8222102291 (8-Bit Legacy)** = 822-210-2291. The correct account is connected. No action needed.

### 🟡 3. Build the two Phase 1 campaigns (Winners + Discovery)
Only after #1 and #2 are green. Follow `docs/ads-pre-launch-checklist.md` Section F. Campaigns stay **Paused** until Section G content schedule is green.
**Time:** ~45 min.

### 🟡 4. Trust-signal parity changes (Tristan decisions)
From the 2026-04-11 cowork brief Task 4 — these are already approved:
- Free shipping threshold $50 → $35 (Shopify → Settings → Shipping and delivery)
- Return policy 30 days → 90 days (Shopify → Settings → Policies + announcement bar)
- Enable Google Customer Reviews in Merchant Center 5296797260 (do NOT install a Shopify review app)

### 🟢 5. Email popup welcome flow (highest ROI quick win)
Install **Shopify Email**, build trigger: `customer tagged newsletter` → email 1: welcome + code `8BITNEW` → email 2: +3 days, curated deals. Then batch-send welcome to the existing 853 subscribers. Then delete the expired `SHOPEXTRA10` code.
**Time:** ~30 min.
**Why:** 853 subscribers who got zero welcome emails. Free warm traffic.

### 🟢 6. Homepage fixes (the free wins)
Issue 1 of `docs/homepage-redesign-notes.md` — delete the two empty `bs_banner_three_image` sections. 5 min, biggest impact-to-effort ratio on the page.

### 🟢 7. Sale wave script patch (if you want sales live for the ads launch)
`manage-sales.py` needs:
- `--min-savings $1.00` floor (Layer 1 would otherwise apply $0.01 discounts)
- `--iconic` allowlist filter for `--deals-of-week` (currently random — picked a $529 Steel Battalion and Pokemon singles)
- Pokemon card exclusion for `--deals-of-week`
- `--max-price` cap on `--deals-of-week`

Or write a new `scripts/manage-iconic-sales.py` that does the curated logic. See `docs/sale-wave-dryrun-findings-2026-04-10.md`.

---

## 📋 Outstanding tech debt (not urgent)

- **1,625 stale loose prices from May 2025** — separate from the CIB==Loose bug, 26.6% of loose variants haven't been refreshed. `search-price-refresh.py` matches ~45%, `full-price-refresh.py` matches ~5.8%. Needs a better title-matching approach.
- **5 CIB edge cases** — ECW Hardcore Revolution (DC), Hot Shots Tennis (PSP), Hot Wheels Stunt Track Driver (GBC), NBA 09 The Inside (PS2 + PSP). Can fix manually or let next scheduled refresh catch them.
- **VPS dashboard auth** — `https://8bit.tristanaddi.com` is behind nginx basic auth with no creds shared. Recommend replacing with Next.js-native auth.
- **CIB inventory regression** — root cause unknown. If Merchant Center shows CIB as "Out of stock" again, re-run `python3 scripts/fix-cib-inventory.py`. See `docs/cib-regression-investigation-2026-04-11.md`.

---

## 🗺️ Key doc map (for tomorrow's laptop session)

**Start here:**
- This file + `docs/session-handoff-2026-04-11.md` (yesterday's work)

**Google Ads launch:**
- `docs/google-ads-launch-plan-v2.md` — current plan, supersedes v1
- `docs/ads-pre-launch-checklist.md` — the linear checklist to launch
- `docs/ads-winners-curation-list.md` — the 17 LIVE products
- `docs/ads-winners-audit-2026-04-11.md` — live Shopify verification
- `docs/ads-negative-keywords-master.md` — ~400 negative terms
- `docs/winners-landing-page-audit.md` — 0 blocking, 16 warnings

**Fixes already shipped (for context, not action):**
- `docs/cib-pricing-fix-2026-04-11.md`
- `docs/cib-regression-investigation-2026-04-11.md`
- `docs/compare-at-price-bug-2026-04-10.md`

**Store/site work:**
- `docs/email-popup-audit-2026-04-10.md` — 853 subs, 0 emails ever
- `docs/homepage-redesign-notes.md` — 5 ranked fixes
- `docs/sale-wave-plan-april-2026.md` + `docs/sale-wave-dryrun-findings-2026-04-10.md`
- `docs/sale-banner-concepts.md` — Concept 1 ("Starter Pack") recommended

**Cowork briefs (for parallel Mac Claude sessions if you want to split the work tomorrow):**
- `docs/claude-cowork-brief-2026-04-11.md` — most recent, covers cart spacing + site audit + Shop dispute

---

## Git state at handoff

- Branch: `main`, up to date with `origin/main`
- Working tree clean (after this commit)
- All session logs from 2026-04-11 CIB/SEO runs committed
- Remote: `WhateverSkyler/8bit-legacy` on GitHub

Laptop can `git pull --ff-only` and resume immediately.

---

## The shortest path to ads running tomorrow

1. Fix conversion tracking (#1 above) — 20 min browser work
2. Re-link Google Ads account (#2) — 10 min browser work
3. Build the two campaigns, leave paused (#3) — 45 min browser work
4. Confirm content is scheduled (social + podcast ep 2)
5. Flip the switches — 1 min

Everything else is parallel polish.
