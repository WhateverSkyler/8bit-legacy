# Ads Strategic Review — 2026-05-07 20:00 ET

## TL;DR

**Nothing material has changed since the 14:00 review six hours ago.** Same git HEAD, no new commits, no `eod-handoff-2026-05-06-*.md` or `eod-handoff-2026-05-07-*.md`, no documented `verify_cib_exclusion.py` run, no record of the 5/06 CIB rebuild completing. The 14:00 report's three open questions are still unanswered: **(1)** is the campaign currently ENABLED or PAUSED, **(2)** did the verifier exit 0, **(3)** is the today-inclusive Google Ads sync route deployed to the VPS. Live data is again unreachable from this runner (snapshot + storefront both 403 `host_not_allowed` from the egress gateway), so I cannot answer any of those three from here. **If Tristan reads this report and `verify_cib_exclusion.py` has not yet been run on his Mac, please run it before bed and paste the exit code into a one-line handoff doc. The 8 AM review needs ground truth or it'll be a third cycle of the same speculation.**

## What changed since last review (14:00 ET)

| Dimension | 14:00 state | 20:00 state | Delta |
|---|---|---|---|
| Latest commit on `main` | `74fe529` (the 14:00 review itself) | `74fe529` | None |
| 5/06 commit on ads-rebuild | None | None | None |
| 5/07 commit on ads-rebuild | None | None | None |
| EOD handoff for 5/06 or 5/07 | Missing | Missing | None |
| `verify_cib_exclusion.py` documented run | None | None | None |
| Snapshot endpoint reachable | No (403) | No (403) | None |
| Storefront reachable for pixel verify | No (403) | No (403) | None |
| Working tree | Clean | Clean (detached HEAD at `74fe529`) | None |

**Genuinely uneventful.** That is itself the finding.

## Live performance

Cannot retrieve. Snapshot endpoint returns `HTTP 403 — x-deny-reason: host_not_allowed`. The egress allowlist on this runner does not include `8bit.tristanaddi.com` or `8bitlegacy.com`. Both have been blocked since at least the 14:00 review; this is a runner-config issue, not a service outage.

If Tristan wants the 8 PM and 8 AM reviews to actually look at numbers, **the runner needs `8bit.tristanaddi.com` and `8bitlegacy.com` added to its egress allowlist**. Without that, every review under this cadence is an exercise in reasoning from stale repo state. That is acceptable for one cycle, marginal for two, and not useful for three.

## Bid math reality check

Same as 14:00 — no live data to update against. The break-even thresholds (~3.25% over_50 / ~1.4% 20_to_50) and the bid-down trigger ($0.35 → $0.20 if over_50 hits 100 clicks at <2.5% CVR) still hold. Refer to the 14:00 report (sections "over_50 tier", "20_to_50 tier", "Projected 7-day P&L scenarios"); nothing has occurred today that warrants restating that math.

## Strategic concerns

### 1. The runway is burning even though I can't see it

If the campaign re-enabled on 5/06 morning at $5/day, **today (5/07 20:00 ET)** is approximately Day 2 of fresh spend. At $5/day with zero conversions:

- 5/06 + 5/07 = up to ~$10 added on top of 5/05's $17.66
- Lifetime no-conversion ceiling = $50 → projected trip date ~5/13 if no Purchase fires
- That's **6 days of runway**, not 14, and the clock started ticking the moment the campaign came back on

If the campaign re-enabled but the pixel silently broke (5/01 redux), conversions would happen invisibly and the ceiling would still trip at $50 around 5/13. The first `Purchase` event firing in Google Ads is the single most important signal of the entire week — and from this runner I can't see whether one has fired or not.

### 2. The "we'll just check it tomorrow" pattern is becoming the dominant failure mode

5/06 had no commits because of the YT OAuth emergency. 5/07 morning had no commits. 5/07 afternoon had no commits. That's three consecutive review cycles where the answer to "what changed?" is "nothing." The 5/05 EOD handoff explicitly said "tomorrow morning, ~8 AM ET" with an 8-step checklist. That checklist was already 36 hours late at 14:00 today and is now 60 hours late.

This is not a criticism — Tristan is one person juggling YT OAuth, podcast, MC, and ads simultaneously, and recovery from 5/05's leakage is genuinely complex work. But the **operational risk** of letting an unfinished rebuild + paused-but-quota-fragile listing tree sit for a week is real:

- Stale state in the partial tree (5 structural + 2,000 item_id negatives + 2 leftover cl2 nodes) creates a window where a misclick or accidental `--rebuild-from-scratch` produces a different outcome than expected
- The `data/cib-offer-ids.txt` snapshot drifts from reality every day — new CIB variants added since 5/05 are not in the file
- Memory of "exactly which 2 cl2 leftover nodes need cleanup" decays. By 5/14 it's a re-investigate-from-scratch task, not a 30-min finish

**Recommendation (unchanged from 14:00):** even if Tristan can't run the full checklist tonight, he should at minimum run `python3 scripts/list_cib_offer_ids.py` to refresh the snapshot, and `git status && git stash list` on the Mac so we know whether 5/05's uncommitted changes are still uncommitted. Five minutes of work that prevents stale-state surprises later.

### 3. Snapshot endpoint allowlist — fix the meta-problem

The recurring agent runs every 6 hours. Two of the last two runs have produced reports that say "I cannot retrieve live data from this runner." If this is structural — the agent runner is a sandboxed environment that genuinely cannot egress to `tristanaddi.com` — then the cadence as currently designed produces near-zero marginal value on days where the repo state hasn't changed.

Two practical options:
- (a) Add the two domains to the runner's egress allowlist so the snapshot endpoint actually returns data
- (b) Accept that this agent's value is "repo-state synthesis 3x/day" and lower the bar — short reports are fine on quiet days, and the snapshot will be checked by Tristan on his Mac

(a) is strictly better. If it's a quick config tweak, it should be the next 30-minute task. Filing here so it doesn't get forgotten — every review until then opens with the same coverage gap.

### 4. Pixel paranoia is still warranted

5/05 audit confirmed Purchase = Active. That was 2 days ago. Pixel has broken three times in 30 days (4/24, 4/25, 5/01). Without storefront access from this runner I cannot re-verify. **If Tristan is at his Mac before bed, a 10-second `curl -s -A 'Mozilla/5.0' https://8bitlegacy.com/ | grep -oE 'AW-[0-9]+/?[A-Za-z0-9_-]*' | sort -u` settles whether `AW-18056461576` is still on the homepage.** Expected output is 1 plain ID + 7 token-suffixed entries. Anything less = pixel partially broken; absence entirely = emergency.

This is the single highest-value 10-second check anyone can do today.

## Recommended actions (priority order)

The top-priority actions from the 14:00 report are unchanged. Status update:

1. **[HIGH] Confirm 5/06 rebuild status.** *Status as of 20:00: still unknown.* Same recommendation: `git status && git log --since="2 days ago"` on Mac, run `verify_cib_exclusion.py`, paste exit code into `docs/eod-handoff-2026-05-07-*.md`.

2. **[HIGH] 10-second pixel verify from Mac.** New for 20:00 — promoted because pixel has the highest fragility-to-cost-of-checking ratio of any item on the list. One command, one minute, eliminates a class of silent failure for the next 24 hours.

3. **[HIGH] Pull the 5/05 search-term breakdown.** *Status: still pending.* `python3 scripts/ads_daily_report.py --since 2026-05-05`. Free margin recovery — those wasted-spend queries will recur on next live run regardless of CIB state.

4. **[MEDIUM] Add `8bit.tristanaddi.com` + `8bitlegacy.com` to recurring-agent egress allowlist.** New for 20:00. Without this, every recurring review is half-blind. One-time config change.

5. **[MEDIUM] Bid-down trigger pre-committed.** *Status: still informal.* If over_50 hits 100+ clicks post-leakage with CVR <2.5%, drop $0.35 → $0.20 same-day. Write it down so emotional bias under "just need a bit more data" doesn't override.

6. **[MEDIUM] Confirm VPS has the today-inclusive Google Ads sync route.** *Status: unknown.* Per 5/05 EOD, `dashboard/src/app/api/google-ads/sync/route.ts` was modified-but-uncommitted on Mac. If still uncommitted, the safety dashboard misreports spend.

7. **[LOW] `cib-exclusion-sync` as a 7th cron job.** *Status: still not filed.* Daily 4 AM ET. Prevents silent CIB drift from new product launches. Defer if not actionable; just file it.

## Coverage gaps

Same as 14:00:

| Dimension | Why blocked |
|---|---|
| Live campaign status (PAUSED vs ENABLED) | Snapshot 403 |
| 5/06–5/07 spend / clicks / impressions / conversions | Snapshot 403 |
| Current CVR by tier | Snapshot 403 |
| Storefront pixel state | Storefront 403 |
| Whether 5/06 rebuild ran or completed | No commit/doc record |
| `verify_cib_exclusion.py` exit code | Same |
| Search-term report from 5/05 | Requires GAQL via Mac |
| MC counts and "Limited" % | Authed API |
| VPS sync route deployment status | VPS HTTP access |
| Order #1076 outcome | Authed dashboard |
| 7th `cib-exclusion-sync` job existence | Authed dashboard |

**The 8 AM review is going to write the same coverage-gap table unless something material happens between now and then.** Either Tristan does the 10-min checklist before bed (verifier + pixel curl + git push of any uncommitted ads work), or tomorrow's 8 AM agent has nothing new to assess and produces a third "still don't know" report.

The shortest path to a useful 8 AM review is:

```bash
# On Mac, before bed (5 min):
git status && git log --since="2 days ago"
python3 scripts/list_cib_offer_ids.py
python3 scripts/verify_cib_exclusion.py; echo "EXIT=$?"
curl -s -A 'Mozilla/5.0' https://8bitlegacy.com/ | grep -oE 'AW-[0-9]+/?[A-Za-z0-9_-]*' | sort -u
git add -A && git commit -m "EOD 2026-05-07: verifier + pixel state captured" && git push
```

Five commands. Two minutes of typing, three minutes of waiting. Resets the paper trail so the recurring agent can actually do its job.
