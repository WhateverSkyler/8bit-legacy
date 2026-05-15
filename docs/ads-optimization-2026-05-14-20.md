# Ads Strategic Review — 2026-05-14 20:00 ET

## TL;DR

**Fifth consecutive blind review, but with one new signal that flips the framing.** Since the 14:00 report there have been **7 commits today**, the most recent at **17:47 ET (`fc393c0`)** — all on the YouTube Shorts pipeline (rounds 13–18 plus an EOD handoff). Zero of those touch ads, MC, pixel, or CIB. Snapshot + storefront are still both `HTTP 403 host_not_allowed` from this runner. **What this means: the prior four reports framed the gap as "operator silence." Today's commits prove that's wrong — Tristan was demonstrably present on the repo all afternoon and chose to spend 100% of engineering time on the shorts pipeline. Ads is implicitly on hold, not accidentally stalled.** Top action: stop framing this as a missing-checklist problem and write the explicit `ads-on-hold-2026-05-14.md` so future cycles stop running this same speculative review.

## What changed since last review (14:00 ET today)

| Dimension | 14:00 state | 20:00 state | Delta |
|---|---|---|---|
| Latest commit on `main` | `e341131` (per 14:00 report) | `fc393c0` (2026-05-14 17:47 ET) | **+8 commits** (one is the 14:00 review itself, seven are shorts pipeline rounds 13–18 + EOD handoff) |
| Ads-relevant commits in the delta | — | **0 of 7 non-review commits** | New signal: operator was active, not silent |
| New ads/MC/pixel/CIB docs | — | **0** | None |
| New shorts pipeline docs | — | `docs/handoff/SHORTS-PIPELINE-2026-05-14-EOD.md` | Confirms 100% of today's effort was on YT |
| `launch-log.md` last entry | 2026-05-05 | 2026-05-05 | None |
| Snapshot endpoint reachable | 403 | 403 | None |
| Storefront reachable for pixel verify | 403 | 403 | None |
| Working tree | Clean (detached at `e341131`) | Clean (detached at `fc393c0`) | Forward by 8 |
| Days since last ads-relevant signal | ~9 | **~10** | +1 |

The actual shape of today: morning handoff → rounds 13.5, 14, 15, 15-followups, 16, 17, 18 → EOD handoff at 17:47 ET. The shorts pipeline got all of Tristan's attention.

## Live performance

Cannot retrieve. `8bit.tristanaddi.com` and `8bitlegacy.com` both return `HTTP/2 403 — x-deny-reason: host_not_allowed`. Same egress allowlist gap that has been the [HIGH] item in the prior four reports. **Note this has now been the highest-priority recommendation across five consecutive reports without being actioned.** That is itself a soft signal that the runner allowlist is either not editable in the current setup or that the cadence is no longer prioritized — both consistent with the "ads is on hold" reframe above.

## Bid math reality check

No new data. The 5/07 14:00 derivation still holds (~3.2% over_50 break-even, ~1.3% 20_to_50 break-even; bid-down trigger $0.35 → $0.20 at 100 over_50 clicks <2.5% CVR). There is no point repeating it for a fifth consecutive report. The numbers don't go stale; the absence of inputs does.

The 5/08 projection ("$50 lifetime ceiling trips ~5/12–5/13 if live") is now firmly in the past. Whichever of the three outcomes it was — paused throughout, auto-paused on ceiling, or quietly converting — has resolved itself two days ago. **The only thing that matters now is whatever ground-truth Tristan has on his Mac, which this runner cannot see.**

## Strategic concerns

### 1. The reframe: this isn't "silence," it's "active deprioritization"

For four reports the implicit model was *"operator hasn't gotten to ads yet, will surface."* Today's 7-commit shorts sprint disproves that model. Tristan is shipping aggressively — just not on ads. Plausible read: the YT Shorts pipeline is the bottleneck for getting to 1K subscribers (which unlocks YouTube Shopping per `CLAUDE.md`'s remaining-work list), and YT subscribers are higher-leverage right now than wringing the next $30 of margin out of a $5/day ad campaign that's competing on a partial-CIB tree. **That's a defensible call.** If true, the ad campaign should be explicitly paused with a written "resume after X" trigger, not left dangling in "partial CIB rebuild interrupted by quota."

### 2. The cadence is now mismatched to the work

A 3x/day strategic-ads agent presupposes there's strategic-ads work happening 3x/day. There isn't, and there hasn't been for ~10 days. Compute, model time, and Tristan's reading attention are all being spent on a recurring report that says "no change, fix the egress" five cycles in a row. The agent isn't doing anything wrong; the configuration is wrong for the current phase of the business.

### 3. The unfinished CIB rebuild is the real cost of leaving it implicit

If "ads is on hold pending YT growth" is the actual decision, that's fine. But the 5/05 EOD handoff captures a half-built state: 2,000 of 6,102 CIB negatives uploaded, 2 leftover `cl2` nodes in the listing tree, structural exclusions live. **That partial state degrades over time.** Every new product imported to Shopify since 5/05 is a CIB variant that's not in the negatives list. By the time ads is resumed (whether that's 5/20 or 6/20), the snapshot in `data/cib-offer-ids.txt` will have drifted enough that `list_cib_offer_ids.py` has to be re-run from scratch and diffed. The longer the gap, the longer the recovery. **Not catastrophic, but cheap to fix now and expensive to fix later.**

### 4. Promo credit timing pressure is still real

`$700 promo expires 5/31` — that's **17 days out**. At $5/day with no campaign mutation, even if ads is re-flipped tomorrow morning the realistic spend through 5/31 is ~$85, not $700. The promo is going to substantially expire. Two honest options:

- Accept the loss. Don't "use up" the promo by lifting daily caps to chase it; that's the loss-amplification path because the bid math doesn't get better at higher spend if the underlying CVR is still cold.
- Make a deliberate call before 5/25-ish on whether to spike to $20-25/day for the final week to capture some of it, knowing the per-click economics will be no better than at $5/day.

This decision belongs to Tristan. The agent's job is to surface the deadline and the asymmetry, not to volunteer a recommendation that boils down to "spend more for the sake of spending."

## Recommended actions (priority order)

Material reshuffle vs prior reports — top item changes today.

1. **[HIGH] Write `docs/ads-on-hold-2026-05-14.md`** — explicit one-page note recording: (a) campaign current status (paused/auto-paused/enabled), (b) reason for hold (e.g. "prioritizing YT subscribers to unlock YouTube Shopping"), (c) explicit resume trigger (date, subscriber count, podcast milestone — whatever applies), (d) carry-forward state (CIB rebuild was 2k/6.1k done as of 5/05, drift will need re-snapshot before resume). This single doc would resolve the speculation surface for every future review.

2. **[HIGH] Drop this cadence to 1x/week or pause it.** Carried over from 14:00, promoted to top-tier. Five consecutive reports with the same content is process motion without progress. If `ads-on-hold-*.md` gets written, the right cadence is "weekly check-in" until the resume trigger is hit, then re-enable 3x/day.

3. **[HIGH] Add `8bit.tristanaddi.com` + `8bitlegacy.com` to runner egress allowlist** *(if cadence stays 3x/day).* Carried over for the fifth time. Fact that this hasn't been done across five reports is itself evidence the cadence may not be the priority — see item 2.

4. **[MEDIUM] Run the 5-command Mac checklist once before going on hold.** Carried over. Lets the on-hold doc be written from ground truth instead of memory:
   ```bash
   git status && git log --since="10 days ago"
   python3 scripts/list_cib_offer_ids.py
   python3 scripts/verify_cib_exclusion.py; echo "EXIT=$?"
   curl -s -A 'Mozilla/5.0' https://8bitlegacy.com/ | grep -oE 'AW-[0-9]+/?[A-Za-z0-9_-]*' | sort -u
   git add -A && git commit -m "EOD 2026-05-14: state captured before hold" && git push
   ```

5. **[MEDIUM] Promo-credit decision by 5/25.** New for 20:00. Either accept the loss of the unused balance or pre-decide a deliberate end-of-month spike. Don't drift into 5/31 with no decision.

6. **[MEDIUM] Bid-down trigger pre-committed.** Carried over. Same trigger ($0.35 → $0.20 if over_50 hits 100 clicks at <2.5% CVR), still informal. Only relevant if/when ads resumes.

7. **[LOW] `cib-exclusion-sync` as a 7th cron job.** Carried over. Defer; just don't lose it.

## Coverage gaps

Identical to 14:00 — same root cause (sandboxed runner, no egress to either authenticated host or storefront). Reproducing the table once more for completeness, but every line has been blocked for ≥7 days now:

| Dimension | Why blocked |
|---|---|
| Campaign status (PAUSED vs ENABLED vs auto-paused on ceiling) | Snapshot 403 |
| 5/06–5/14 spend / clicks / impressions / conversions | Snapshot 403 |
| Whether $50 lifetime ceiling tripped on schedule | Snapshot 403 |
| Current CVR by tier | Snapshot 403 |
| Storefront pixel state (`AW-18056461576` present?) | Storefront 403 |
| Whether 5/06 CIB rebuild ran or completed | No commit/doc record |
| `verify_cib_exclusion.py` exit code | Same |
| Search-term report from 5/05 | Requires GAQL via Mac |
| MC counts and "Limited" % | Authed API |
| VPS sync route deployment status | VPS HTTP access |
| Order #1076 outcome | Authed dashboard |
| 7th `cib-exclusion-sync` job existence | Authed dashboard |
| **$700 promo credit balance / expiry status** | Authed Google Ads |

## Honest meta-note

The new fact today is that Tristan is actively shipping — just on shorts, not ads. That changes the recommendation from "please run the checklist" to "please write the explicit hold doc and shut this cadence off until ads resumes." Continuing to produce a 200-line strategic review three times a day for a campaign that's effectively dormant and a runner that can't see live data is the wrong shape for the moment. **If by the next review nothing has changed (no hold doc, no checklist, no egress fix, no ads commits), I'd argue the right output is a one-line file: "No change. See 5/14 20:00."** That's the honest call.
