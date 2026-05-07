# Ads Strategic Review — 2026-05-07 14:00 ET

## TL;DR

**Operating blind today.** This runner's network is allowlist-restricted — both the snapshot endpoint (`8bit.tristanaddi.com`) and the storefront (`8bitlegacy.com`) return HTTP 403 "Host not in allowlist". I have no live spend, conversion, pixel, or scheduler data; everything below is reasoning from the last committed state (EOD 2026-05-05 night) plus 36 hours of unaccounted time. **The single most important question Tristan needs to answer himself this morning: did the CIB item_id rebuild complete on 5/06 and did `verify_cib_exclusion.py` exit 0?** Until that's confirmed in writing, treat the campaign as a known-broken pre-flip — re-enabling without verifier-pass risks repeating the 5/05 leakage at a slower bleed rate.

Secondary concern: the bid math at the prompt's break-even thresholds (~3.25% over_50 / ~1.4% 20_to_50) is tight enough that one bad week of cold-traffic CVR will burn the remaining $700 promo without a conversion. Plan now for the bid-down trigger (over_50 → $0.20 if 100+ clicks with sub-2.5% CVR) so we don't sit and watch.

## What changed since last review

There is no prior `docs/ads-optimization-*.md` — this is the first report under the new cadence. Reference points:

- **2026-05-05 mid-day:** campaign flipped ENABLED at $20/day, ran 3h, paused after $17.66 spend / 71 clicks / 0 Purchase conv with leakage to Pokemon/console/CIB.
- **2026-05-05 evening:** root-caused (Shopify G&Y app does NOT propagate variant-level metafields to MC); pivoted to Google Ads `item_id` negative criteria; built `data/cib-offer-ids.txt` (6,102 IDs) + `scripts/verify_cib_exclusion.py`; daily mutation quota hit at 2,000/6,102 negatives created; budget lowered to $5/day; campaign **PAUSED**.
- **2026-05-06:** only ads-irrelevant commit on `main` is `bf79d6b` (YT OAuth keep-alive). **No commit, doc, or EOD handoff records what happened with the ads rebuild on 5/06.** Either it ran and the resulting state changes weren't documented, or it didn't run at all. Both are important to know which.
- **2026-05-07 (today):** no commits.

That gap in the paper trail is itself a finding — see Strategic concerns §1.

## Live performance

**Cannot retrieve.** Snapshot endpoint returned `HTTP 403 — Host not in allowlist` from this runner (size: 21 bytes). The endpoint is reachable from Tristan's machines; it's not down. I have zero live numbers to work with for this review.

Last numbers in repo (EOD 5/05 19:00 ET):
- Lifetime spend: **$17.66** / 71 clicks / 3,694 impr / **0 Purchase conversions**
- Daily budget: **$5/day** (lowered from $20 → $10 → $5 across the day)
- Status: **PAUSED**

If campaign re-enabled on 5/06 morning, ~36 hours of $5/day = ≤$10 additional spend. The lifetime no-conversion ceiling ($50) gives roughly **$32 of headroom** before that kill switch trips, which is ~6 days at $5/day with zero conversions. Useful runway, but not infinite — if no Purchase fires by ~5/13 the campaign auto-pauses regardless.

## Bid math reality check

Without live data, I can only check whether the **planned** thresholds are defensible. They're tight.

### over_50 tier ($0.35 bid, mean retail ~$94)

Per-sale economics (estimated, conservative):

| Line | Amount |
|---|---|
| Retail | $94.00 |
| Cost (eBay listing @ retail/1.35) | -$69.63 |
| eBay shipping/fees baked into supplier price | (already in cost) |
| Shopify fees (2.9% + $0.30) | -$3.03 |
| Multi-state sales-tax leak (~3-4%) | -$3.30 |
| Our outbound shipping (free ship over $50) | -$5–8 |
| **Net per sale (rough)** | **~$10–13** |

Break-even CVR at $0.35 CPC = $0.35 / $11 ≈ **3.2%**. That matches the prompt's ~3.25% estimate.

Cold-traffic Shopping CVR for niche/collectible categories typically lands **1.5–3.0%**. Retro-game-specific high-intent queries ("super mario galaxy 2 wii game") could plausibly run 3–5%. Generic browse queries ("retro games", "old nintendo") will be sub-1%. So **whether $0.35 works hinges entirely on search-term mix**.

If 5/05's 71 clicks across both tiers gave 0 conversions, that's directionally bad but not statistically meaningful — most of those clicks were on the wrong inventory anyway (Pokemon, CIB, consoles). The real first-100-click test on properly-filtered Game Only inventory hasn't happened yet.

### 20_to_50 tier ($0.08 bid, mean retail ~$32)

Per-sale economics:

| Line | Amount |
|---|---|
| Retail | $32.00 |
| Cost (eBay @ retail/1.35) | -$23.70 |
| Shopify fees | -$1.23 |
| Tax leak | -$1.10 |
| Outbound shipping (under-$50, customer pays) | ~$0 |
| **Net per sale (rough)** | **~$6** |

Break-even CVR at $0.08 = $0.08 / $6 ≈ **1.3%**. Matches prompt's ~1.4%. This tier has more room — even at 1.5% CVR it breaks even on bid alone, and the 4× volume of inventory (1,678 vs 802 products) offers more shots on goal.

### Projected 7-day P&L scenarios

Assuming campaign re-enabled and serving cleanly at $5/day from 5/06 onward (~$35 weekly spend):

| Scenario | Avg net/sale | CVR needed for break-even | Plausible? |
|---|---|---|---|
| All clicks on over_50, $11 net | 3.2% | At a cold store with no reviews, no | Optimistic |
| All clicks on 20_to_50, $6 net | 1.3% | Borderline — 50/50 | Realistic |
| 60/40 mix favoring over_50, ~$9 net | 1.9% | Probably no in week 1 | Modest hope |

**Honest read:** week 1 ROAS is much more likely to be 0–80% than 200%+. The campaign probably needs the $50 ceiling to fire (or a manual judgment call) before it produces a real signal. Plan for "first $50 is tuition" not "first $50 is profit."

## Strategic concerns

### 1. The 36-hour paper-trail gap (highest concern)

The 5/05 night EOD explicitly handed off to "tomorrow morning, ~8 AM ET" with a numbered checklist:
1. Quota reset → confirm
2. `python3 scripts/list_cib_offer_ids.py` → refresh
3. `python3 scripts/ads_launch.py --budget-micros 5000000 --skip-negatives` → finish rebuild
4. `python3 scripts/verify_cib_exclusion.py` → must pass all 3 checks
5. Verify contact page 200
6. Verify scheduler green / breakers armed
7. **Tristan flips campaign ENABLED**
8. Watch first hour, re-pause if anything off

There is no commit, no EOD handoff, no `cowork-session-2026-05-06-*.md`, no `eod-handoff-2026-05-06-*.md`, and no `docs/ads-*` doc dated 5/06 or 5/07. The only commit on 5/06 is YT OAuth (unrelated). That means one of the following is true:

- (a) Tristan did the work on 5/06, didn't document it, campaign is live
- (b) Tristan did the work, verifier failed, campaign is still paused
- (c) Tristan didn't do the work yet (5/06 was a YT-emergency day)
- (d) Tristan did everything but on Mac, hasn't synced commits to Linux yet (CLAUDE.md says repo syncs between macOS + Linux)

I cannot distinguish from this runner. Only Tristan can. **Whichever it is, the answer dictates the entire review.** If (c), my whole report below is moot — this is a "still paused" day. If (a) and CVR is on a 6-day path to the kill switch, that's a different conversation. If (b), the question is whether the verifier failure is a real signal or a stale-MC false alarm.

**Action:** Tristan should `git status && git log --oneline --since="2 days ago"` on the Mac and confirm the 5/06 ads work landed (or didn't). If the Mac has uncommitted state, sync it now so future runs have ground truth.

### 2. Item-ID negative tree at 6,102 entries — quota-fragile and silently degradable

The pivot to Google Ads item_id negatives is correct, but the operational characteristic to watch:

- 6,102 negatives is ~30% of Google Ads' 20k-criteria hard limit on a single ad group. Headroom exists but isn't infinite.
- Every CIB variant added to Shopify after 5/05 needs to land in `cib-offer-ids.txt` AND get pushed to the ad group as a new negative. The 5/05 build is a snapshot; new CIBs leak by default until the next sync.
- Drift detection currently relies on `scripts/list_cib_offer_ids.py` being re-run + `ads_launch.py` diffing. **Is this scheduled?** I don't see an automation entry for it in the 6 jobs list (the 6 are: shopify-product-sync, google-ads-sync, fulfillment-check, price-sync, pokemon-price-sync, ads-safety-check). If CIB sync is manual-only, leakage will silently grow over weeks.

**Asymmetric risk:** new product launches (e.g. when a fresh batch of 50 retro games gets added with both Game Only + CIB variants) → 50 new CIB variants serve at $0.35 immediately, possibly for $5–25 wasted spend per day, without any kill-switch firing because conversions still happen on the legitimate Game Only side.

**Recommendation:** add `cib-exclusion-sync` as a 7th scheduled job (daily 4 AM ET) that runs `list_cib_offer_ids.py → ads_launch.py --skip-negatives` and posts a Navi alert if the desired-vs-actual diff is nonzero. Defer if today's not the day, but file it.

### 3. Real-time spend tracking landed locally on 5/05 — was it pushed to VPS?

The 5/05 EOD says "Real-time spend tracking enabled (today's data now flows into local DB)" and lists `dashboard/src/app/api/google-ads/sync/route.ts — today-inclusive` among files modified-but-uncommitted. The 5/05 night EOD doesn't mention pushing it to VPS (the cowork session noted the VPS still showed `Processed=0` on its sync runs).

If today's spend isn't flowing into the VPS DB, then:
- `daily_spend_limit` check sees $0/day → won't trip the $40 cap
- `lifetime_no_conversion_ceiling` check sees the cumulative 5/05 $17.66 + nothing else → at $5/day spending it'd take 6 days to hit $50 in DB even though Google would record it daily. Maybe a feature, maybe not.
- The dashboard `/safety` panel shows misleading green "all checks pass" even if real spend is $20/day.

**Action:** confirm `dashboard/src/app/api/google-ads/sync/route.ts` is committed and deployed to VPS. The 5/05 EOD said it was uncommitted; I see no commit on `main` in the past 14 days touching that file. **Likely still uncommitted on Mac.** This is the second silent-failure risk after CIB drift.

### 4. Margin assumptions baked into the bid math may be optimistic

The $11 net per $94 over_50 sale assumes:
- eBay supplier price = retail / 1.35 (the multiplier inverse). This is true on average across the catalog, but the variance is high — some items may sell for retail/1.20 (thin margin) or retail/1.60 (fat). The bid is set to a tier average; thin-margin items in the same tier are loss leaders.
- No order-validator catches between checkout and fulfillment. The validator does fire every 30 min, but it creates an alert; doesn't auto-cancel. So a thin-margin order on a price-spiked eBay listing → manual decision under time pressure to refund or eat the loss.
- Multi-state sales tax leak still untreated (per `project_post_launch_todos.md`, MTC fix deferred until volume justifies). At low volume this is ~$2-4/sale; at higher volume the absolute number scales linearly, eating margin proportionally.

None of these change today's recommendation, but they all mean **observed ROAS will be 10-20% lower than the bid-math math suggests**. Bid breakeven at 3.25% effectively becomes "ROAS-positive at 3.5-4%."

### 5. Pixel state — I cannot verify

Both prior pixel breakages (4/24, 4/25, 5/01) suggest the storefront pixel is the campaign's most fragile dependency. The 5/05 cowork audit says Purchase = Active. I can't re-verify today (storefront blocked).

If the pixel silently breaks again:
- Ads serve, clicks happen, money spent
- Conversions don't fire → safety dashboard shows 0 conv → lifetime ceiling counts down
- Eventually $50 ceiling trips → campaign auto-pauses with no Purchase recorded
- Tristan thinks "campaign isn't converting" when actually conversions are happening but not tracking

**Mitigation:** the previously-coded but not-deployed Phase B server-side webhook backstop is the structural fix. Per 5/05 readiness audit: "Day 7-14 after launch" was the deployment target. Today is Day 2 (counting only enabled time). If the campaign re-enables this week, **deploy the webhook backstop by Day 7** even if pixel looks fine — relying on a single point of conversion truth that has already broken three times in 30 days is the recipe.

### 6. Asymmetric opportunity: drop over_50 bid early

If first 100+ clicks on Game Only over_50 inventory show CVR < 2.5%, the right move is **not** "wait and see" — it's "drop bid to $0.20 immediately." Math:

- At $0.20 with $11 net, break-even CVR = 1.8%
- Volume drops ~30-40% (Google's auction position decreases) → fewer impressions but with higher relative quality
- Net cost of being wrong (dropping when CVR was actually about to recover): ~30% volume hit for 1 week = maybe $15 of forgone revenue
- Net cost of NOT dropping (sustaining $0.35 with 2% CVR for a week): $35 spend × (1 - 2/3.25) net ≈ $13 lost. Plus you don't learn the lower-bid economics.

So the **information value** of dropping bid early > the cost of dropping bid early. Trigger: 100+ clicks on over_50 (post-leakage-fix) with CVR < 2.5% and zero or one conversion.

## Recommended actions (priority order)

1. **[HIGH] Confirm 5/06 rebuild status before any other action.** On Tristan's Mac: `git status && git log --since="2 days ago"`. Run `python3 scripts/verify_cib_exclusion.py`. If exit 0, campaign safely re-enableable. If exit non-zero or unrun, campaign should remain paused. Document the result in a `docs/eod-handoff-2026-05-07-*.md` so the next strategic review has ground truth.

2. **[HIGH] Pull search-term breakdown for the 5/05 wasted $17.66.** `python3 scripts/ads_daily_report.py --since 2026-05-05` (or query GAQL directly). Add 20-50 phrase-match negatives based on Pokemon TCG card-set names + console-related terms that leaked. This is free margin recovery — those queries will show up again on the next live run regardless of CIB exclusion state.

3. **[HIGH] Set the bid-down trigger now, in writing.** When over_50 hits 100+ clicks post-leakage with CVR < 2.5%, drop bid from $0.35 → $0.20 same-day. Don't deliberate. This needs to be a pre-committed rule because emotional bias under "we just need a bit more data" pushes toward over-spending.

4. **[MEDIUM] Schedule `cib-exclusion-sync` as a 7th cron job.** Daily 4 AM ET. Runs `list_cib_offer_ids.py → ads_launch.py --skip-negatives`. Posts a Navi alert on any nonzero diff. Prevents silent CIB drift from new product launches. Defer if not actionable today, but file it so it doesn't get forgotten.

5. **[MEDIUM] Verify VPS has the `today-inclusive` Google Ads sync route.** If `dashboard/src/app/api/google-ads/sync/route.ts` is still uncommitted on Mac, commit + deploy. Without this, the safety dashboard misreports spend, which makes the $40 daily cap and $50 lifetime ceiling cosmetic.

6. **[MEDIUM] Plan Phase B webhook backstop for Day 7.** If the campaign is live and the pixel is recording correctly through Day 7, deploy the server-side `orders/paid` webhook anyway. This is belt-and-suspenders — but the suspenders have failed three times in 30 days and we only have a belt.

7. **[LOW] Stale `AW-11389531744` pixel cleanup.** Acknowledged in 5/05 audit as week-2 work. Still pending. Not material until then.

8. **[LOW] $700 promo credit utilization.** Currently expiring 5/31 with $0 used. At $5/day that's $120 by end of month — leaves $580 unused. If after 7 days the campaign is unambiguously profitable (ROAS > 200%, multiple conversions, clean search terms), bump to $20-30/day to actually use the promo. **Don't bump on hope.**

## Coverage gaps

These are the dimensions I couldn't assess from this runner:

| Dimension | Why blocked |
|---|---|
| Live campaign status (PAUSED vs ENABLED) | Snapshot endpoint 403 |
| 5/06–5/07 spend, clicks, impressions, conversions | Snapshot endpoint 403 |
| Current CVR for over_50 vs 20_to_50 (separate) | Snapshot endpoint 403 |
| Storefront pixel state (`AW-18056461576` present?) | Storefront 403 |
| Whether campaign was actually re-enabled on 5/06 | No commit/doc record on Linux side |
| Whether `verify_cib_exclusion.py` passed | Same |
| Search-term report from 5/05 leakage | Snapshot returns aggregates only; need GAQL via Mac |
| Current MC product counts and "Limited" % | Requires authed API calls |
| Whether VPS has the today-inclusive sync route | Requires VPS HTTP access |
| Order #1076 (19-line bulk order on 5/05) outcome | Requires authed dashboard |
| Whether the 7th `cib-exclusion-sync` job exists yet | Requires authed dashboard |

Most of these are 1-command answers from Tristan's Mac. The two critical ones for the next review are: **(1) is the campaign live or paused right now**, and **(2) what does `verify_cib_exclusion.py` print**. With those two answers the next 14:00 ET review can be substantive instead of speculative.
