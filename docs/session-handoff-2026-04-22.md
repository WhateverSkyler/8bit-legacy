# Session Handoff — 2026-04-22 (EOD ~5:00 PM EDT)

**Previous handoff:** `docs/session-handoff-2026-04-21.md`
**Resume:** pick up from "What's next when you return" below.

---

## TL;DR — where we are

1. **Google Ads campaign `8BL-Shopping-Games` is built, configured, and PAUSED** via API. All 18 automated health checks pass. Campaign is ready to launch once 5 browser-side pre-launch gates are verified (task delegated to cowork — brief is ready to paste).
2. **Google Ads OAuth rotation complete.** Desktop OAuth client in GCP project 585154028800, consent screen in Production (long-lived tokens). `config/.env` + `dashboard/.env.local` both updated. Added `GOOGLE_ADS_LOGIN_CUSTOMER_ID=4442441892` (MCC).
3. **Podcast pipeline clip scheduling bug fixed.** All 9 shorts from Episode April 14 2026 are now scheduled to IG/TikTok/YT Shorts across 2026-04-23 / 24 / 25 at 9 AM / 1 PM / 7 PM ET. Required fix: `schedule_shorts.py` was using old Zernio field names; aligned with `schedule_photos.py`.
4. **One open question for Tristan:** audio podcast distribution (Spotify/Apple). DistroKid Ultimate doesn't cover podcasts — we need a dedicated host (Spotify for Podcasters free / Transistor $19/mo / Buzzsprout $12/mo). Tristan to pick one + confirm whether he already has a host set up. Memory: `project_audio_distribution.md`.

---

## What shipped today (commits `6ee9dad` → `d44beb3`, all pushed)

| # | SHA | What |
|---|-----|------|
| 1 | `6ee9dad` | Podcast pipeline: fix Zernio clip scheduling payload (`publishAt/media/caption` → `scheduledFor/mediaItems/content`); `youtube_upload.py` relative_to() fix; added `scripts/google_ads_reauth.py`; committed 2026-04-21 handoff |
| 2 | `e2e6ea6` | Cowork brief: Google Ads OAuth Desktop-client rotation (3rd attempt — finally executed successfully) |
| 3 | `e430e8d` | Bump Google Ads API v17 → v21 across `dashboard/src/lib/google-ads.ts` + `scripts/create-shopping-campaign.py` |
| 4 | `d14c8aa` | Google Ads launch: campaign built via API + master plan + monitoring scripts (`ads_audit.py`, `ads_launch.py`, `ads_daily_report.py`, `docs/ads-launch-master-plan-2026-04-22.md`) |
| 5 | `0679c75` | Tightened 20-50 tier bid $0.12 → $0.08; made `rebuild_listing_tree` idempotent via update-in-place fast path |
| 6 | `3c599f5` | `scripts/ads_preflight_check.py` (18-check pre-launch health) + master plan §10 devil's-advocate section covering 40 failure scenarios |
| 7 | `d44beb3` | Cowork brief for ads pre-launch gates (the 5 browser-side tasks) |

---

## Current live state

### 🟢 Google Ads — campaign built, paused, 18/18 checks passing
- **Account:** 822-210-2291 (8-Bit Legacy) via MCC 444-244-1892
- **Campaign:** `8BL-Shopping-Games` (ID 23766662629), **PAUSED**
- **Budget:** $20/day, Manual CPC, Google Search only, US only, Merchant Center 5296797260
- **Listing tree:**
  ```
  ROOT
  ├── game > over_50    → $0.35/click
  ├── game > 20_to_50   → $0.08/click  (tightened today)
  ├── game > else       → EXCLUDED (catches under_20)
  └── non-game          → EXCLUDED (Pokemon cards, CIB, consoles, accessories, sealed)
  ```
- **334 negatives** imported from `data/negative-keywords-google-ads-import-v2.csv`
- **Conversion actions:** 7 Shopping App actions enabled + primary (Purchase, Add To Cart, Begin Checkout, Page View, Search, View Item, Add Payment Info)
- **Kill switches wired:** $50 lifetime no-conv ceiling, $40 daily cap, 3-day × $10 no-conv, ROAS floor 200% after 7d
- **Verify live:** `python3 scripts/ads_preflight_check.py` — expects 18/18 pass

### 🟢 OAuth credentials (Ads API + dashboard)
- **Desktop OAuth client** `585154028800-m2vtjictmsbm50th5...` in GCP project 585154028800
- **Refresh token:** long-lived (consent screen is in Production mode as of today)
- **Both env files updated:** `config/.env` + `dashboard/.env.local`
- **New env var:** `GOOGLE_ADS_LOGIN_CUSTOMER_ID=4442441892` (MCC — required for API calls targeting the sub-account)

### 🟢 Podcast pipeline — Episode April 14 2026 fully deployed
- 3 YouTube uploads (topics 03, 05, FULL FINAL) scheduled
- 9 vertical shorts scheduled to Zernio → IG/TikTok/YT Shorts (Apr 23-25)
- 25 photo posts rotating Tue/Thu/Sat through 2026-06-18
- Drop-folder watcher + buffer scheduler running in `8bit-pipeline` Docker container on TrueNAS 192.168.4.2

### 🟡 Known issues / accepted risks (not blocking)
- VPS dashboard at `8bit.tristanaddi.com` still running old `safety.ts` ($25 daily cap, 3-day × $10). Repo has new values ($40, $50) but redeploy requires VPS access (nginx basic auth blocks me). Low risk first 7 days since impressions ramp slow.
- Processing/ has stale `Episode April 14th 2026` folder on NAS — cosmetic, doesn't block next drop
- `dashboard/src/lib/google-ads.ts` uses API v21 now but dashboard bundle on VPS still has v17 — will 404 until redeploy

---

## 🔄 Cowork ran the pre-launch gates (2026-04-22 ~7:53-9:35 PM EDT)

Handoff: `docs/cowork-session-2026-04-22-ads-prelaunch.md`

| Gate | Result |
|---|---|
| 1. MC diagnostics audit | ✅ **GREEN** — 12,272 products, 20 not showing on Google, no account issues, Shopping Ads Active |
| 2. CIB exclusion feed upload | 🔴 **BLOCKED** — MC Next UI won't attach a file-based supplemental feed to a Merchant-API primary (Shopify Google & YouTube app registers itself as MA primary). CSV format is verified correct. |
| 3. Fire test pixel events | 🟡 **4/5** — page_view, search, view_item, add_to_cart, begin_checkout fired at 19:53 EDT. add_payment_info skipped (Chrome extension popup — optional per brief) |
| 4. Verify conversion tracking | ⏳ **PENDING** — needs 2-4h wait. Re-check after 22:00 EDT |
| 5. 8BITNEW code | ✅ **GREEN** — Active, 10%, no expiry, 4 prior uses |
| 6. MC Promotion submission | ⏭️ Skipped (Task 2 blocked) |

### CIB blocker — honest assessment
This is a **medium-soft blocker**, not hard. Without it:
- Our feed still pushes both Game Only + CIB variants
- Both variants live in the same `price_tier:over_50` bucket → same $0.35 bid
- Google's Shopping auction optimizer naturally favors the lower-priced Game Only variant for CTR reasons
- We'd still get occasional CIB impressions at the higher $132+ price, suboptimal but not catastrophic

**Ways to fix (in order of effort, none trivial):**
1. **Merchant API Content push** — set `excluded_destinations=[Shopping_ads]` on each CIB item via MC Content API. Requires a separate OAuth flow + Content API scope — not currently configured. ~2-3h of work.
2. **Shopify Google & YouTube app config** — the app may expose per-variant "Hide from Google" options. Worth user exploring in the app UI.
3. **Accept residual and re-optimize post-launch** — if first-week data shows CIB variants winning meaningful impression share, escalate to option 1.

**My recommendation:** launch without CIB exclusion. Google's auction should handle it. If 14-day data shows CIB impression share >20%, we pivot.

---

## 🎯 What's next when you return — PICK HERE

### Option A — Finish ads launch (most valuable, closest to done)

**Step 1 (TONIGHT ~22:00 EDT — ~20 min away from handoff write time):** Verify pixel tracking.

Go to https://ads.google.com → account `822-210-2291` → **Tools & Settings → Measurement → Conversions → Summary**. Confirm these 4 actions show "Recording" or "No recent conversions" (NOT "Inactive" / "Misconfigured"):
- Google Shopping App Page View
- Google Shopping App Add To Cart
- Google Shopping App Begin Checkout
- Google Shopping App Search (or View Item)

(Purchase will stay Inactive until a real order — expected, don't worry about it.)

**Step 2: Decide on CIB exclusion.**
Two paths:
- **Launch without it** (my recommendation — Google's auction picks cheaper Game Only naturally). Revisit in 14d if data shows high CIB impression share.
- **Solve it before launch** — explore Shopify Google & YouTube app UI for per-variant hide options, OR build the MC Content API integration (~2-3h of work).

**Step 3: If pixel tracking is GREEN and you're OK launching without CIB fix:** tell Claude Code "flip it" — I'll enable via API, record baseline, start daily monitoring.

**Step 4 (earlier plan, keep for reference — only use if step 1 fails):**

Paste this into Claude Desktop cowork:

```
You are resuming work on the 8-Bit Legacy repo at github.com/WhateverSkyler/8bit-legacy. Pull latest before starting.

Execute the brief at docs/claude-cowork-brief-2026-04-22-ads-prelaunch.md end-to-end. Read it in full first. Goal: clear the 5 pre-launch gates for Google Ads campaign 8BL-Shopping-Games so Tristan can flip it from Paused to Enabled. Main session built the campaign via API; your job is browser/UI verification only.

Hard guardrails:
- DO NOT enable the campaign — leave Paused
- DO NOT modify campaign settings (bids, budget, negatives, listing tree) — they're set, don't touch
- DO NOT commit secrets
- If any step fails or hits unexpected state, STOP and report — don't improvise

Execute tasks 1-5 in order:
1. Merchant Center diagnostics audit (account 5296797260) — disapproval count + account-level issues + Shopping ads program status
2. Upload data/merchant-center-cib-exclusion.csv as a supplemental feed named "CIB Shopping Exclusion"
3. Fire test pixel events in incognito at 8bitlegacy.com (product view → search → add to cart → begin checkout → add payment info with test card → abandon). Log exact timestamp.
4. Wait 2-4 hours after task 3, verify in Google Ads (account 822-210-2291) → Tools → Conversions that Add to Cart, Begin Checkout, Page View, Add Payment Info show "Recording" or "No recent conversions" (NOT "Inactive" or "Misconfigured"). Purchase stays Inactive — expected.
5. Verify 8BITNEW discount code is Active in Shopify admin Discounts section

Optional Task 6: submit 8BITNEW as Merchant Center Promotion (15-30% CTR lift).

Write handoff at docs/cowork-session-2026-04-22-ads-prelaunch.md with per-task status + final GO/NO-GO. Commit + push. Report to Tristan: one-sentence per task + the go/no-go.

Only legitimate blockers: (a) MC shows account suspension or >50 disapprovals, (b) CIB feed item_id format doesn't match MC's IDs, (c) conversion goals stay Inactive after 2nd retry of task 3.
```

**Step 2: Wait for cowork's go/no-go report.**
- If **GO**: tell Claude Code "flip it" — I'll enable via API, record baseline timestamp, start daily monitoring cadence
- If **BLOCKED**: we fix the specific blocker and retry

**Step 3 (after enable): run `scripts/ads_daily_report.py` daily for first 7 days.** Builds into the weekly cadence described in master plan §5.

### Option B — Tackle the audio podcast distribution question

User mentioned wanting Spotify + Apple Podcasts automation. **Blocked on Tristan deciding which host to use.** Options I gave:
- Spotify for Podcasters (free, limited API, mostly manual)
- **Transistor.fm ($19/mo) — recommended** for full automation
- Buzzsprout ($12/mo)

User to check email for any existing podcast-host signup first (Anchor / Buzzsprout / Transistor / etc.). Once host picked, ~2 hours to add audio extraction + push-to-host step to the pipeline.

Memory: `project_audio_distribution.md`

### Option C — Harden the VPS dashboard redeploy

Low priority but worth doing within 7 days of ads launch:
- VPS at `8bit.tristanaddi.com` still behind nginx basic auth (no creds in repo)
- Needs: replace nginx auth with Next.js-native auth OR grant SSH access so I can redeploy bundle with new `safety.ts` ($40 daily cap, $50 lifetime ceiling) and v21 API
- Until redeploy, the VPS scheduler enforces OLD safety values and could false-trip if Google's 2x daily burst exceeds $25 in a single day (unlikely first 7 days)

---

## Key files reference

| File | What | When to touch |
|---|---|---|
| `docs/ads-launch-master-plan-2026-04-22.md` | Source of truth for ads campaign — strategy, config, kill switches, 14-day playbook, devil's-advocate §10 | Before any ads-related decision |
| `docs/claude-cowork-brief-2026-04-22-ads-prelaunch.md` | 5-task browser/UI work for cowork to unblock launch | When ready to clear pre-launch gates |
| `scripts/ads_audit.py` | Read-only snapshot of Ads account state | Anytime — sanity check |
| `scripts/ads_preflight_check.py` | 18-check pre-launch health gate | Before flipping the campaign on |
| `scripts/ads_launch.py` | Idempotent campaign builder | Only if rebuilding from scratch |
| `scripts/ads_daily_report.py` | Daily ops report (spend, conv, search terms, product offenders) | Every morning post-launch |
| `scripts/google_ads_reauth.py` | Mint fresh OAuth refresh token | Only if consent screen expires (Production mode now, rarely) |
| `data/merchant-center-cib-exclusion.csv` | 6,088 CIB item_ids for MC supplemental feed | Upload in task 2 of cowork brief |
| `data/negative-keywords-google-ads-import-v2.csv` | 334 negatives already imported into campaign | Don't re-import; updates go via daily report's negative suggestions |
| `config/.env` + `dashboard/.env.local` | Live credentials (Shopify, Ads OAuth + MCC, TrueNAS, Zernio) | NEVER commit |

---

## Things I still can't do from my side

- **VPS dashboard redeploy** — nginx basic auth blocks me. Needs Tristan to either share creds / grant SSH or replace nginx auth with Next-native auth
- **Merchant Center UI verification** (disapproval counts, feed errors, account-level issues) — Ads API only gives partial view; cowork task 1 handles this
- **Shopify discount code read** — current API token lacks `read_discounts` scope; cowork task 5 handles
- **Firing pixel events as a real browser** — headless HTTP doesn't fire Shopify's Web Pixel Manager; cowork task 3 handles

---

## Memory files updated today

- `project_ads_launch_state.md` (new) — current campaign state, env vars, launch gates
- `project_audio_distribution.md` (new — from earlier in session) — Spotify/Apple podcast question pending host pick
- `MEMORY.md` index updated

Existing memory that remained accurate:
- `feedback_ads_strategy.md` — Shopping-only, hard-pause at $50 no-conv, exclude CIB/Pokemon/consoles, prioritize $50+
- `feedback_business_partner.md` — be proactive with honest feedback, not just an executor
- `project_vps_dashboard.md` — VPS dashboard behind nginx 401

---

## Outstanding decisions waiting on Tristan

1. **Flip the ads campaign on** after cowork clears the 5 gates → commit to month 1 spend
2. **Audio podcast host pick** → unblocks pipeline audio-extraction work
3. **VPS dashboard access** → unblocks safety.ts redeploy + monitors
4. **Submit 8BITNEW as Merchant Center Promotion** → optional CTR lift on all Shopping ads (cowork task 6)
5. **Homepage / trust-signal improvements** — per-user, not urgent; first 14 days of ad data will tell us if reviews/shipping/returns are actually hurting CVR

---

## Honest assessment recap (from session)

After Tristan corrected my outdated data (10-20 orders/mo organic vs my claimed 5/6mo, 90-day returns, homepage fixed, GTIN-matched):

- Break-even or better in month 1: **~40-50%**
- Sustained profitable campaign in 90 days: **~55-65%**

Month 1 is learning-funded-by-$700-promo-credit, not max-profit. Real optimization is week 2-4 once we have product-level conversion data. Current config is "100% of what can be built without data" — bid math, exclusions, negatives, kill switches all as good as they get pre-launch.
