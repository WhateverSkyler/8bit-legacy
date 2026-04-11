# Session Handoff — 2026-04-10 Evening

**From:** Mac Claude (terminal session) + Mac Claude (cowork browser session)
**To:** Whichever Claude session Tristan picks up next on the Linux desktop
**Date:** Friday, April 10, 2026, 8:12 PM EDT
**Status:** Session winding down. Tristan is moving to desktop to continue.

---

## Session start (mandatory)

```bash
cd ~/Projects/8bit-legacy
git pull --ff-only
```

Then read these in order to load context:

1. `CLAUDE.md` — full project instructions
2. `docs/handoff-2026-04-10-evening.md` — **this file**
3. `docs/cowork-session-summary-2026-04-10-pm.md` — what the browser cowork session found
4. `docs/email-popup-audit-2026-04-10.md` — the revenue leak details
5. `docs/homepage-redesign-notes.md` — ranked homepage fixes
6. `docs/sale-wave-dryrun-findings-2026-04-10.md` — sale script bugs
7. `docs/compare-at-price-bug-2026-04-10.md` — the compare_at fix that already shipped
8. `docs/google-ads-launch-plan.md` — full ads launch playbook (with the new Phase 0.1 audit section appended)
9. `docs/sale-wave-plan-april-2026.md` — sale strategy
10. `docs/sale-banner-concepts.md` — banner concepts (Concept 1 recommended)
11. `docs/claude-cowork-brief-mac-2026-04-10-pm.md` — the brief that ran today

---

## TL;DR — what's the state of the store

- **Google Ads is technically ready to launch.** Conversion tracking is already wired via the Google & YouTube Shopify app. The ONLY remaining blocker is that the app is connected to the wrong Google Ads account.
- **The store is cold** — 5 orders / 6 months, $508 revenue, 22.7% margin, $101 AOV. The bottleneck is traffic + trust, not conversion.
- **A real revenue leak was found** — 853 newsletter subscribers, zero welcome emails ever sent. Easy fix.
- **The homepage "half-assed" feeling has a root cause** — two empty banner sections rendering at 0px height. 5 minute fix.
- **The sale wave script has bugs** — would put 2,689 products on "sale" with $0.01-$0.10 discounts, and picks Pokemon singles which violate Layer 4. Don't run `--apply` on `manage-sales.py` until patched.

---

## 🔴 Tristan-only manual tasks (can't be delegated to Claude)

| # | Task | Why it matters | Effort |
|---|---|---|---|
| 1 | **Re-link Google Ads account** — disconnect Google & YouTube Shopify app and reconnect using `sideshowtristan@gmail.com` so it points at `822-210-2291` instead of `438-063-8976` | This is the **actual** blocker for the entire Google Ads launch | ~10 min |
| 2 | **Decide email tool** — Shopify Email (free, recommended) vs Klaviyo Free (better segmentation, but 250-contact cap < your 853 list) | Unblocks the 853-subscriber welcome flow fix | 5 min decision |
| 3 | **Sanity-check Shop sales channel** in a normal browser — confirm no "Action needed" badge | Fully closes April 6 audit Task 5 | 2 min |
| 4 | **VPS dashboard auth decision** — share basic-auth creds OR ask Claude to replace nginx auth with Next.js-native auth | Unblocks scheduler health checks from terminal sessions | 5 min decision |

---

## 🟡 Decisions you owe Claude before more terminal work happens

| # | Decision | What Claude will do once you decide |
|---|---|---|
| 5 | **Sale wave — patch or rewrite?** Patch `manage-sales.py` to add `--min-savings $1`, `--iconic` filter, and Pokemon exclusion? Or write a new `manage-iconic-sales.py` instead? | Make the sale layers safe to `--apply` |
| 6 | **Sale wave — depth + scope** for each layer (15% under-$20, 20% Deals of the Week, 12% N64 spotlight per the plan). Approve or adjust. | Run patched dry-runs for your final approval, then apply |
| 7 | **Homepage fixes** — approve Issue 1 (delete two empty banner sections, 5 min) at minimum? Cowork can knock out the rest in ~55 min | Hand off to cowork to apply on a duplicated theme |
| 8 | **Nav cleanup** — approve killing `/collections/special-products` and publishing "On Sale" to Shop channel? | Hand off to cowork |

---

## 🟢 Browser/cowork session can do once approved

- Apply homepage fixes (5 issues, ranked, in `docs/homepage-redesign-notes.md`)
  - **Issue 1 (5 min, free win):** delete the two empty `bs_banner_three_image` sections
  - **Issue 2 (15 min):** add Pokemon TCG product strip below Sony Classics
  - **Issue 3 (10 min):** beef up the GameCube section from 8 to 20 products, or re-theme it
  - **Issue 4 (10 min):** add an On-Sale promo section below DotW
  - **Issue 5 (10 min):** typography/spacing pass on section titles
- Apply nav cleanup (kill `/collections/special-products` link, publish "On Sale" to Shop)
- Install Shopify Email + build welcome flow (trigger: customer tagged `newsletter`, send code `8BITNEW`)
- Batch-send the welcome email to the 853 historical subscribers
- Delete the expired `SHOPEXTRA10` discount code
- Wire the two empty banner sections as Pokemon hero + Sale hero (Option B from homepage notes — only if Tristan provides artwork)

---

## ⏳ Blocked by external factors (no action possible)

- **Pokemon sets `me3` (Perfect Order) and `me2pt5` (Ascended Heroes)** — blocked on TCGPlayer pricing in the Pokemon TCG API. Auto-import will pick them up when pricing lands.
- **YouTube Shopping** — gated at 1,000 YouTube subscribers (currently growing via the new podcast)
- **Podcast episode 2** — biweekly cycle, next shoot ~April 23 per the schedule

---

## 🎯 Strategic moves on your roadmap (not urgent today)

- Tax strategy / LLC restructuring (gated on revenue growth — `project_roadmap.md`)
- Physical retail location (gated on $50K profit — `project_roadmap.md`)
- Website frontend revamp beyond homepage (broader brand styling pass — `project_website_revamp.md`)
- Monthly+ sales rotation cadence (`project_sales_rotation.md` — in motion via the sale wave plan)

---

## ✅ Shipped today (for the record)

### Terminal session (Mac, this Claude)
- All **7,689 products tagged** for Google Shopping (Phase 0.3 of ads launch). Custom labels: `price_tier:`, `console:`, `category:`, `margin:` + SEO titles. ~2h47m run, 0 failures. Log: `data/logs/feed-optimize-apply-20260410_132426.log`
- Wrote `scripts/fix-broken-compare-at.py`. Dry-ran, applied. **11 broken compare_at variants cleared** (Conker's CIB, Zelda Minish Cap CIB, 007 GoldenEye CIB, Grandia II CIB, Resident Evil 1+2 CIB, Mega Man X4 CIB, Metal Gear Solid CIB, GTA III CIB, Conker's Game Only, Zelda Minish Cap Game Only). Smart "Sale" collection no longer polluted.
- Sale wave Layer 1 + Layer 2 dry-runs. Found two real bugs:
  - **Layer 1 (under $20, 15% off)** would hit **2,689 products** with many discounts rounding to $0.01-$0.10 due to $X.99 floor logic
  - **Layer 2 (Deals of the Week)** picks RANDOM products including a $530 Steel Battalion and Pokemon TCG singles (which Layer 4 says never to discount)
- Wrote `docs/sale-wave-dryrun-findings-2026-04-10.md` with full analysis + proposed fixes
- Wrote `docs/compare-at-price-bug-2026-04-10.md`
- Wrote `docs/claude-cowork-brief-mac-2026-04-10-pm.md` — the brief the cowork session executed
- Updated memory: added `project_compare_at_bug.md`, `project_vps_dashboard.md`
- Ran fresh profit report: Jan 1 → Apr 10 = 2 orders, $139.58 revenue, $31.54 profit, 22.6% margin

### Cowork session (Mac, browser Claude)
- **Email popup audit** — 853 subscribers, **0 emails ever sent**. Popup is theme-native (posts to `/contact` with `newsletter` tag). MailMunch is a dead mirror. Discount `8BITNEW` is valid (4 uses) but never delivered. `SHOPEXTRA10` is expired. Fix: install Shopify Email + welcome flow.
- **"On Sale" smart collection** — exists with the correct rule (`compare_at_price > 0`), 15 products, 5 channels published, but NOT published to Shop channel. Main nav has TWO "Sale" links pointing at different collections.
- **Shop sales channel** — "Action needed" badge cleared (likely from CIB fix). Needs 2-min manual sanity check.
- **Homepage redesign notes** — root cause of "half-assed" feeling: two empty `bs_banner_three_image` sections rendering at 0px height between DotW→GameCube and GameCube→Classics. Plus Pokemon entirely absent below the fold despite 1,176+ products. 5 ranked issues with fix options.
- **VPS dashboard** — blocked, nginx 401, no creds. Recommended: replace nginx basic auth with Next.js-native auth.
- **Conversion tracking pre-flight** — **MYTH BUSTED.** `gtag`/`dataLayer` are undefined in DevTools because Shopify's Web Pixel Manager runs pixels in a sandboxed worker. The Google & YouTube Shopify app already has a fully-wired Google Tag setup (`G-09HMHWDE5K` GA4, `AW-18056461576` Ads conversions, `GT-TBZRNKQC` server-side container) with all 7 standard ecommerce events mapped. Phase 0.1 is NOT the launch blocker.

---

## ⚠️ The biggest finding from today

The Google Ads launch was thought to be blocked on conversion tracking. **It is not.** Conversion tracking is already wired up. The actual blocker is from the April 6 audit Task 2:

> The Google & YouTube Shopify app is connected to **`tristanaddi1@gmail.com` / Ads account `438-063-8976`**, but the target Ads account is **`822-210-2291` under `sideshowtristan@gmail.com`**.

**Two ways to fix:**
1. Add `tristanaddi1@gmail.com` as admin on `822-210-2291` under `sideshowtristan@gmail.com`, OR
2. Disconnect + reconnect the Google & YouTube Shopify app using `sideshowtristan@gmail.com`

**This is a manual Tristan task** — neither Claude session can do it. Once done, the conversion data immediately flows to the right account and ads can launch.

---

## 📊 Today's ground truth numbers

- **Past 6 months:** 5 orders, ~$508 revenue, 22.7% margin, $101 AOV
- **Past 100 days (Jan 1 → Apr 10):** 2 orders, $139.58 revenue, $31.54 profit, $69.79 AOV
- **Best sellers:** Galerians (PS1), Metal Gear Solid (PS1), Wii remote
- **Diagnosis:** Store is cold. Bottleneck is traffic + trust, not conversion.
- **Live products:** 7,689 in Shopify (~6,121 retro games + ~1,176 Pokemon cards + sealed)
- **Newsletter subscribers (untouched):** 853
- **Active sales (after compare_at cleanup):** 23 legitimate variants
- **Dashboard URL (auth required):** https://8bit.tristanaddi.com

---

## 🎯 Shortest path to "ads running"

1. **Tristan #1** — Re-link Google Ads account (~10 min, manual)
2. **Tristan #6** — Approve sale wave depths after Claude patches `manage-sales.py`
3. **Claude (terminal)** — Patch `manage-sales.py`, re-dry-run, apply approved layers
4. **Tristan** — Verify campaign in Google Ads UI, set $5/day Standard Shopping (per `google-ads-launch-plan.md` Phase 1)
5. **Tristan** — Enable campaign

Everything else (homepage, email flow, podcast, etc.) is polish or parallel growth work that doesn't block the campaign.

---

## 🪙 Highest ROI quick win

**Item #2 + Shopify Email install.** 853 latent subscribers + a 10% off promise we never delivered = the lowest-hanging fruit on the entire store. Building the welcome flow takes 30 min in Shopify Email and immediately activates a year's worth of warm leads.

---

## Git state at handoff

Latest commits on `main`:
```
d69a3a7 Cowork session: email popup audit, sale collection, homepage notes, conversion tracking audit
80ac84a Add feed optimizer apply log: 7,689 products tagged for Google Shopping
da7c9a8 Fix compare_at price bug and document sale wave dry-run issues
6aaa52c Add Google Ads launch plan, sale wave strategy, banner concepts, cowork brief
bcbfdd8 Add scheduler/Pokemon pages, collection sorting, and bulk automation scripts
```

All work is pushed to `WhateverSkyler/8bit-legacy` on GitHub. Desktop session can `git pull --ff-only` and pick up immediately.

---

## Background processes

None running. The optimize-product-feed background job completed successfully at ~2:46 PM ET. No leftover state on the Mac that needs cleanup on the desktop side.

---

## Questions worth asking the user up front (on desktop)

- Which item in the punch list do you want to tackle first?
- For the Google Ads re-linking — do you want to walk through it together or do it solo?
- For the sale wave script patch — patch in place or write a new `manage-iconic-sales.py`?
- For homepage Issue 1 (delete empty banners) — approve as a 5-min free win?
- For Shopify Email — install it now or wait?

Good luck. Everything you need is in this doc + the linked files.
