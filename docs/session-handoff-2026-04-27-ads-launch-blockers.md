# Session Handoff — 2026-04-27 — Ads Launch Blockers + Next Steps

**Status: HOLD ON FLIP. Five real blockers identified. Campaign remains PAUSED.**

## TL;DR

Today's session moved the pixel + automation infrastructure forward significantly. But a Merchant Center audit at 4 PM revealed the actual ad-side state is worse than memory suggested — duplicate feeds, broken CIB exclusion, missing custom labels, unverified pixel, paused billing. **Honest faith level if launched in current state: 25-35% positive ROI. After fixing all 5 blockers: back to 60-65%.**

Hold the flip. Estimated work to clear blockers: ~30-60 minutes, mostly browser-driven (cowork-able) + one real test order from you.

---

## What got DONE today (do not redo)

| Item | Status |
|---|---|
| Pixel re-linked from `AW-11389531744` (wrong account) → `AW-18056461576` (8-Bit Legacy 822-210-2291) | ✅ Storefront HTML verified — 7 events × `AW-18056461576/<token>` |
| Stale conversion actions removed (8 → 7 ENABLED Primary) | ✅ Done via API |
| Campaign budget tightened $22 → $20/day | ✅ Done via API |
| `dashboard/src/app/safety/` page — live KPI cards, per-check pass/fail, last-3-days table | ✅ Deployed to VPS, HTTP 200 |
| `dashboard/src/app/api/safety/ads-status/route.ts` — read-only safety status endpoint | ✅ Deployed |
| `dashboard/src/app/api/public/ads-snapshot/route.ts` — token-auth public endpoint for the recurring agent | ✅ Deployed, nginx allowlists `/api/public/`, token in `dashboard/.env.local` on VPS |
| VPS dashboard rebuilt + pm2 reloaded with latest code | ✅ Online |
| Test order #1071 placed + cancelled + cleaned up | ✅ Order archived, all test discounts deleted, no leaked discount lines on real customer checkouts |
| Claude Code Recurring agent created | ✅ ID `trig_01VHYi2ibCvAP9z8H6qU2tcG`, Opus 4.7, 3×/day at 8 AM/2 PM/8 PM ET, prompt rewritten for full strategic reasoning |
| GitHub auto-switch fixed (criticalmkt → WhateverSkyler for pushes) | ✅ Pushed `ef45405`, `55dc7b6` |

---

## P0 blockers — must clear BEFORE flipping the campaign

### 1. Duplicate Shopify feeds in MC (5 min, browser)
Two parallel Shopify App API feeds running:
- `US` (12,226 items) — original
- `USD_88038604834` (13,252 items) — created during 2026-04-24 G&Y app reinstall

Real Shopify product count is ~12K. MC shows 25.5K because of the duplication. **Bid budget gets diluted across phantom listings.** Likely also the cause of Blocker 2.

**Fix:** MC → Data sources → disable/delete the duplicate `USD_88038604834` feed.

**Caution:** Confirm WHICH feed has correct labels + exclusions before disabling. The original `US` feed may be the broken one and `USD_88038604834` may be the canonical now-current one (created post-reinstall when tags got migrated). Audit before deleting.

### 2. CIB exclusion broken in MC (verify after Blocker 1 cleared)

Verified via Shopify API today: the metafield `mm-google-shopping.excluded_destination = ["Shopping_ads"]` IS correctly set on CIB variants (e.g. Final Fantasy VII Dirge of Cerberus CIB).

But MC shows all 5 sampled CIB SKUs as Approved with Shopping ads + Dynamic remarketing + Cloud retail + Free listings ALL active. **The metafield isn't propagating.**

Most likely cause: the new duplicate feed `USD_88038604834` is ignoring the exclusion metafield. Cleaning up the duplicate (Blocker 1) likely fixes this automatically.

**Fix:** After Blocker 1, re-check 5 CIB SKUs in MC. If still showing Approved+Shopping_ads, this is a deeper Shopify-Channel-app config issue and we need to use the supplemental-feed CSV approach (`data/merchant-center-cib-exclusion.csv` per `project_ads_launch_state.md`).

**Why this matters:** Per memory `feedback_ads_strategy.md`, CIB has thin margins. Spending budget on CIB ad clicks = direct loss. The 6,112 CIB variants must be excluded.

### 3. Custom labels possibly missing from MC feed (verify, browser)

Verified via Shopify API today: 0 metafields for `custom_label_0` or `custom_label_2` exist on any of 5 random $50+ products checked.

The bid tier strategy depends on these labels:
- `custom_label_2 = game` → only nodes
- `custom_label_0 = over_50` → bid $0.35
- `custom_label_0 = 20_to_50` → bid $0.08
- everything else → excluded

If the labels aren't in the live feed, **every product either gets the default bid or gets excluded** — neither is what we planned.

The Shopify Google & YouTube app may inject these dynamically at sync time without storing them as metafields, OR the labels may simply be missing. **The cowork couldn't see them in MC product details.**

**Fix:** In MC → click into a $50+ game product → scroll to Custom Labels section → confirm `custom_label_0` shows `over_50` and `custom_label_2` shows `game`. If missing entirely, the bid tier strategy is broken and we need to add them via Shopify metafields or the G&Y app's custom-label settings.

### 4. Pixel pipeline not confirmed end-to-end

All 7 conversion actions show 0 conversions across 24h, 7-day, MTD. 5 actions are "Inactive", 2 are "No recent conversions." Webpages tab is empty. Test order #1071 did NOT register.

The Purchase action was created today (4/27) — #1071 was its very first chance and it failed.

Most likely cause: **cancellation race** — Google saw the Shopify cancellation and retracted the conversion before it landed in attribution. But that's a hypothesis, not a confirmed answer.

**Fix:** Place an UNCANCELLED test order with a real cheap product ($10-20). Let it actually fulfill, OR refund via Merchant Center after attribution lands (not via Shopify cancellation, which causes the race). Wait 4-6h post-order, then re-check Webpages tab.

This costs you ~$15-20 of real money + the eBay fulfillment cost, but it's the only way to disambiguate "pixel is broken" from "cancellation race." Do it AFTER blockers 1-3 are cleared so we're testing the corrected state.

### 5. Account billing paused

"Account paused — To run ads again, you'll need to make a payment" banner is up.

**Fix:** Google Ads → Billing → make payment. Hard prerequisite — campaign cannot serve until this clears, regardless of campaign status.

---

## P1 — fix during week 1 of running, not blocker

| # | Issue | Notes |
|---|---|---|
| 1 | 5 conversion actions show "Inactive" | After Blocker 4 resolves, re-check. Some may flip to Active automatically once they get any signal. |
| 2 | 418 products with "Invalid image encoding" | Fixable Limited reason. Likely affects ranking; probably doesn't fully exclude. Day 3-7 audit. |
| 3 | 24.9K products in "Limited performance" | Normal new-feed behavior — they auto-improve as Google sees impression data. NOT a blocker, NOT a fixable data issue. Will resolve organically once campaign runs. |

## P2 — month-2 strategic items

| # | Issue | Reference |
|---|---|---|
| 1 | eBay multi-state resale tax exemption (MTC certificates) | `project_ebay_resale_exemption.md` — ~$2-4/order leak on out-of-state sales |
| 2 | Storefront UX audit | Affects click-to-buy CVR; ad campaign can't fix it |
| 3 | Full SEO audit | `project_post_launch_todos.md` — once ads stabilize |
| 4 | Full MC listing-quality audit | `project_post_launch_todos.md` |

---

## Suggested next session sequence

1. **Spawn cowork** with the brief in `docs/claude-cowork-brief-2026-04-27-mc-cleanup.md` (TODO — write next session) covering Blockers 1, 2, 3 (browser MC work)
2. **Reactivate billing** in Google Ads (you only)
3. **Place real uncancelled test order** ($10-20 product, real address, real card)
4. **Wait 4-6h** for pixel attribution
5. **Re-check Webpages tab** in Google Ads → if Purchase event lands, all green
6. **Flip campaign** to ENABLED with explicit "flip" command

---

## System state snapshots

### Pixel (live storefront)
```
AW-18056461576 instances: 8 (1 in google_tag_ids + 7 in event action_labels)
AW-11389531744 instances: 1 (account-level fallback, non-blocking but cleanup item)
```

All 7 events firing with proper conversion-action tokens:
- search → AW-18056461576/hGTHCPqd0KMcEIj6_qFD
- begin_checkout → AW-18056461576/HDu_CO6d0KMcEIj6_qFD
- view_item → AW-18056461576/5fn7CPed0KMcEIj6_qFD
- purchase → AW-18056461576/TS3uCOud0KMcEIj6_qFD
- page_view → AW-18056461576/--mzCPSd0KMcEIj6_qFD
- add_payment_info → AW-18056461576/KowPCP2d0KMcEIj6_qFD
- add_to_cart → AW-18056461576/VJ6hCPGd0KMcEIj6_qFD

### Campaign (Google Ads API)
- Name: `8BL-Shopping-Games`
- ID: `23766662629`
- Status: **PAUSED** (do not flip yet)
- Budget: $20/day
- 334 phrase/exact-match negatives
- 7 ENABLED conversion actions, all Primary
- Listing tree: 4 nodes (custom_label_2=game subdivision; over_50=$0.35, 20_to_50=$0.08, else excluded)

### VPS dashboard
- Process: `8bit-dashboard` pm2, online
- `/safety` page (auth-walled): visible KPI cards + per-check pass/fail
- `/api/safety/ads-status`: returns current safety state JSON
- `/api/public/ads-snapshot?token=S4nBy7GHWAmq3g1QKX3Z8RfdQiBja86vkt6u6nQCSJE`: public token endpoint
- Nginx allowlists `/api/public/` past basic-auth wall
- Scheduled job `ads-safety-check`: registered, every 6h, will auto-pause on breach. Runs every 6h aligned with `google-ads-sync`.

### Recurring agent
- ID: `trig_01VHYi2ibCvAP9z8H6qU2tcG`
- Name: `8bit-legacy-ads-daily-review`
- Model: claude-opus-4-7
- Cadence: `0 12,18,0 * * *` UTC = 8 AM / 2 PM / 8 PM ET (3×/day)
- **Next run: 2026-04-28T00:06 UTC = TONIGHT 8:06 PM ET**
- Repo: github.com/WhateverSkyler/8bit-legacy
- Tools: Bash, Read, Write, Edit, Glob, Grep
- Live data via VPS public-token endpoint
- Output: `docs/ads-optimization-YYYY-MM-DD-HH.md` committed + pushed
- Mutation policy: advisory only

**Note:** Tonight's 8 PM run will see the campaign still PAUSED + this handoff doc + the cowork audit doc + the blockers list. The agent will produce the first real strategic review in the new format. Read it tomorrow morning when you're back.

### Most recent commits
```
55dc7b6 Public token-auth ads-snapshot endpoint for recurring agent
ef45405 Pixel re-link complete + Ad Safety dashboard panel
6ca3fc3 cowork 2026-04-27: pixel account re-link — STOPPED, UI materially different from brief
```

---

## Honest framing on launch decision

The work today shipped real infrastructure. The audits revealed real blockers. **Both can be true.**

If you'd flipped at noon when the pixel verified, **you'd be burning budget on phantom CIB inventory inside a duplicated feed with possibly missing tier labels and an unverified attribution pipeline.** Worst case: $50 of bad data + zero clarity on root cause when results came in poorly. Best case: lucky early conversions masking the structural issues.

Holding for ~1 hour of cleanup work + one real test order is the right call. Don't let momentum override the audit findings.

---

## Files referenced

- `docs/cowork-session-2026-04-27-mc-audit-and-pixel-check.md` — today's MC audit handoff
- `docs/cowork-session-2026-04-27-pixel-test-order.md` — test order #1071 handoff
- `docs/cowork-session-2026-04-27-pixel-account-relink.md` — pixel re-link STOPPED handoff
- `docs/claude-cowork-brief-2026-04-27-mc-audit-and-pixel-check.md` — MC audit brief
- `docs/claude-cowork-brief-2026-04-27-pixel-test-order.md` — test order brief
- `docs/claude-cowork-brief-2026-04-27-pixel-account-relink.md` — re-link brief
- `docs/pixel-relink-diy-playbook-2026-04-27.md` — DIY guide that worked
- `docs/ads-launch-master-plan-2026-04-22.md` — original launch plan (still ground truth)
- `docs/google-ads-launch-plan.md` — bid math + tier strategy
- Memory files: `project_ads_launch_state.md`, `feedback_ads_strategy.md`, `project_cib_ads_exclusion.md`
