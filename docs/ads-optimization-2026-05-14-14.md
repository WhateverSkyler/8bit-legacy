# Ads Strategic Review — 2026-05-14 14:00 ET

## TL;DR

**Fourth consecutive blind review, and the gap has now stretched to 6 calendar days.** Latest commit on `main` is still `e341131` (the 5/08 08:00 review itself, authored 2026-05-08 12:11 UTC). No new commits, no new docs, no `eod-handoff-2026-05-{06..13}-*.md`, no `cowork-session-2026-05-{06..13}-*.md`. Snapshot endpoint and storefront both still return `HTTP 403 host_not_allowed` from this runner — the same egress allowlist gap flagged on 5/07 and 5/08. The 5/08 08:00 report's projection ("if live at $5/day with 0 conv, $50 ceiling trips ~5/12–5/13") **has now passed its window**: if the campaign was live, it has either auto-paused on the lifetime ceiling by now or it converted; either way the immediate operational urgency has receded into the safety net. **Honest call: the recurring cadence is producing zero marginal value in this configuration. Either fix the runner egress for `8bit.tristanaddi.com` + `8bitlegacy.com`, or pause the cadence until live data flows.**

## What changed since last review (5/08 08:00 ET)

| Dimension | 5/08 08:00 | 5/14 14:00 | Delta |
|---|---|---|---|
| Latest commit on `main` | `e341131` | `e341131` | **None — 6 days flat** |
| `eod-handoff-2026-05-{06..13}-*.md` | None | None | None |
| `cowork-session-2026-05-{06..13}-*.md` | None | None | None |
| `verify_cib_exclusion.py` documented run | None | None | None |
| Snapshot endpoint reachable | 403 | 403 | None |
| Storefront reachable for pixel verify | 403 | 403 | None |
| Working tree | Clean (detached at `68571a4`) | Clean (detached at `e341131`) | Forward by one commit (the 5/08 report itself) |
| `launch-log.md` last entry | 2026-05-05 | 2026-05-05 | None |
| Days since last ads-relevant signal | ~3 | **~9** | +6 |

The cadence itself appears to have been off for 6 days; this is the first run since 5/08 08:00. The repo on this runner reflects the same single committed state it has reflected since the launch-pause on 5/05.

## Live performance

Cannot retrieve. `8bit.tristanaddi.com` and `8bitlegacy.com` both return `HTTP/2 403 — x-deny-reason: host_not_allowed`. This is the egress allowlist on the runner, not a service outage. The fix is one config line; it has been the [HIGH] recommendation in the prior two reports and has not been actioned.

## Bid math reality check

Unchanged from 5/07 14:00. No new data → no update. The break-even thresholds (~3.2% over_50, ~1.3% 20_to_50) and bid-down trigger ($0.35 → $0.20 if over_50 hits 100 clicks at <2.5% CVR) still hold. Refer to `docs/ads-optimization-2026-05-07-14.md` lines 32–80 for the per-tier derivation.

What is new is the **time-elapsed implication**:

- 5/08 08:00 projection: at $5/day with 0 conv, lifetime spend hits the $50 ceiling around 5/12–5/13.
- Today is 5/14. **That window is in the past.** Three possibilities, all of them now self-resolving:
  1. **Campaign was paused throughout** (most likely given operator silence): no spend, no harm, no progress, ad account still in cold-start.
  2. **Campaign was live, no conv, ceiling tripped on schedule (~5/12–5/13):** safety net did its job, campaign is now auto-paused, ~$32–35 of incremental spend is sunk. Bad outcome but bounded.
  3. **Campaign was live, conv fired:** we should be celebrating, not auditing in the dark. Probability low absent any signal.

The asymmetry that mattered on 5/08 ("the campaign is committing the next $20 of spend without anyone watching") has largely played itself out. Whatever happened, happened. The next informative event is operator action, not agent reasoning.

## Strategic concerns

### 1. The cadence is producing nothing on this configuration

Four consecutive reports with the same coverage-gap table is a process failure, not a content problem. The 5/08 08:00 report explicitly committed to skip the next cycle if no inputs changed; instead the cycle skipped itself for 6 days and resumed today with the same blocked state. The honest read:

- Either the runner's egress to `8bit.tristanaddi.com` + `8bitlegacy.com` gets unblocked (one-line allowlist edit), in which case this cadence becomes immediately useful again.
- Or the cadence is paused / dropped to once-weekly with the explicit understanding that without live data it's repo-state synthesis, not strategic ads work.

There is no third option where blind 3x/day reviews produce value commensurate with the prompt's framing.

### 2. The 9-day operator silence on ads is itself a finding

The CIB rebuild was 1/3 done on 5/05 night (2,000 of 6,102 negatives). Quota was supposed to reset on 5/06 and the rebuild was supposed to complete that morning. Nine days later there is no committed evidence that:

- the quota reset was confirmed,
- the rebuild ran,
- `verify_cib_exclusion.py` was executed,
- the campaign was re-flipped or kept paused.

This is plausibly fine — Tristan is one person juggling YT OAuth, podcast, MC catalog, and ads simultaneously, and the campaign auto-paused at $5/day if it ran is a soft outcome. But operationally, every additional day the partial-tree state sits unfinished increases the risk that "the 2,000 of 6,102 negatives" snapshot in `data/cib-offer-ids.txt` drifts out of sync with whatever Shopify variants exist on 5/14. New CIB variants added since 5/05 are not in the file; new variants deleted are still in it. **Resuming from the 5/05 partial state is going to require re-running `list_cib_offer_ids.py` from scratch and diffing — which is the work that should have happened on 5/06, just nine days delayed.**

### 3. The asymmetric risks haven't moved

All previously flagged silent-failure risks are still real and still un-mitigated:

- **Pixel state unknown.** Three breakages in 30 days (4/24, 4/25, 5/01). No re-verify possible from this runner.
- **VPS today-inclusive sync route still presumed uncommitted.** No commits to `dashboard/src/app/api/google-ads/sync/route.ts` since 5/01. Safety dashboard's daily-spend cap is presumed cosmetic.
- **No `cib-exclusion-sync` cron job.** Listing tree of 5 jobs in `CLAUDE.md` is unchanged. Future product launches will silently leak CIB variants until manually resynced.
- **Stale `AW-11389531744` pixel** — week-2 cleanup, still pending.
- **$700 promo credit** — expires 5/31. If the campaign is still effectively cold, the entire credit will go unused. Even at $20/day that's ~$340 spend to expiry. Realistically: **the promo is going to substantially expire.** Don't chase it with high-bid hope; that's the loss-amplification path.

None of these have moved. None of them are the right thing to fix today without ground-truth on campaign state first.

## Recommended actions (priority order)

Carried over. Priority shuffled to reflect that "what to do about the campaign" is downstream of "what is the campaign doing."

1. **[HIGH] Add `8bit.tristanaddi.com` + `8bitlegacy.com` to recurring-agent egress allowlist.** Sole prerequisite for this cadence being worth running. Carried over from 5/07 20:00 (week+ stale).

2. **[HIGH] Run the 5-command Mac checklist.** Reproduced from 5/08 08:00. Two minutes of typing settles ~80% of the speculation surface for the next review:

   ```bash
   git status && git log --since="9 days ago"
   python3 scripts/list_cib_offer_ids.py
   python3 scripts/verify_cib_exclusion.py; echo "EXIT=$?"
   curl -s -A 'Mozilla/5.0' https://8bitlegacy.com/ | grep -oE 'AW-[0-9]+/?[A-Za-z0-9_-]*' | sort -u
   git add -A && git commit -m "EOD 2026-05-14: state captured" && git push
   ```

3. **[HIGH] Decide explicitly whether ads is paused-paused or paused-pending.** Nine days of silence is consistent with either "decided to deprioritize ads until podcast/YT are stable" or "intended to finish 5/06 morning, never got to it." Both are valid choices. The risk is the implicit third choice — drift. If ads is on hold for ≥2 weeks, write that down (`docs/ads-on-hold-2026-05-14.md` or similar) so future-Tristan and future-agents stop reasoning around an active campaign that isn't.

4. **[MEDIUM] Reset the cadence.** Either fix the runner egress (item 1) and keep 3x/day, or drop this agent to 1x/day or 1x/week until ads work resumes. Continuing 3x/day with `host_not_allowed` is throwing compute at no signal.

5. **[MEDIUM] Bid-down trigger pre-committed.** Carried over from 5/07. Same trigger ($0.35 → $0.20 if over_50 hits 100 clicks at <2.5% CVR), still informal.

6. **[MEDIUM] Confirm VPS has the today-inclusive Google Ads sync route.** Carried over from 5/05 EOD. Still unknown.

7. **[LOW] `cib-exclusion-sync` as a 7th cron job.** Carried over. Still not filed. Defer if not actionable; just don't lose it.

## Coverage gaps

Identical to 5/08 08:00. Every dimension below is blocked by the same root cause (sandboxed runner, no egress to either authenticated host or storefront):

| Dimension | Why blocked |
|---|---|
| Campaign status (PAUSED vs ENABLED vs auto-paused on ceiling) | Snapshot 403 |
| 5/06–5/14 spend / clicks / impressions / conversions | Snapshot 403 |
| Whether $50 lifetime ceiling tripped on schedule | Snapshot 403 |
| Current CVR by tier | Snapshot 403 |
| Storefront pixel state (`AW-18056461576` present?) | Storefront 403 |
| Whether 5/06 rebuild ran or completed | No commit/doc record |
| `verify_cib_exclusion.py` exit code | Same |
| Search-term report from 5/05 | Requires GAQL via Mac |
| MC counts and "Limited" % | Authed API |
| VPS sync route deployment status | VPS HTTP access |
| Order #1076 outcome | Authed dashboard |
| 7th `cib-exclusion-sync` job existence | Authed dashboard |
| **$700 promo credit balance / expiry status** | Authed Google Ads |

## Honest meta-note

This report exists primarily to mark the gap. The substantive content carries over from 5/07 14:00 and 5/08 08:00 unchanged; if the runner config doesn't get fixed the next report will say the same thing again. **The single most useful thing that can happen between now and the next review is the operator either (a) unblocking the runner egress, (b) running the 5-command checklist, or (c) explicitly putting ads on hold.** Anything else is process motion without progress.
