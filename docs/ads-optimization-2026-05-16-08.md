# Ads Strategic Review — 2026-05-16 08:00 ET

## TL;DR

Quiet overnight as expected. Zero commits since the 20:00 review (`15c07a0`, committed 20:11 ET 5/15) — Tristan is sleeping ahead of the morning launch-sequence checklist in `eod-2026-05-15.md`. **Both ENABLE gates are still open**: (a) truth-set rescan finished ~22:00 ET but classification has not been reviewed/applied, (b) CIB tree is still empty of negatives pending Google quota reset (~10 AM ET, ~2 hours from now). The only standing risk this morning is an accidental ENABLE flip in the ~2-hour window before the CIB rebuild can complete — campaign is paused and no automation touches campaign status, so the protection is "don't flip it." **No new asks; today's job is to land the morning checklist cleanly, in order.**

## What changed since 5/15 20:00

| Dimension | 5/15 20:00 | 5/16 08:00 | Delta |
|---|---|---|---|
| Latest commit on `main` | `15c07a0` (20:00 review) | `15c07a0` | None |
| New commits overnight | — | 0 | None |
| New docs (any) | — | 0 | None |
| `ads-on-hold.md` / `DO-NOT-ENABLE.md` sticky | Not written | Not written | The pre-launch sticky-note idea from yesterday §8 didn't get filed; not material since campaign hasn't been touched |
| Rescan PID 1411444 status | Running, ETA ~22:00 ET | Unknown from this runner — should be DONE | Verifiable only via TrueNAS SSH (Mac/desktop) |
| CIB tree state | 5 skeleton nodes, 0 item_id negatives | Unchanged (quota window still active) | Quota resets ~10 AM ET |
| Pixel state | Verified live in 5/15 15:55 session | Unverified this morning (egress block) | Pre-flip re-verify is still on the checklist (EOD §2) |
| Days to $700 promo expiry | 16 | **15** | -1 |
| Days to SST verdict | 7 | **6** | -1 |
| Agent cadence | Tristan-flagged for drop to weekly | Cron still firing 3x/day | Execution belongs to Tristan; not auto-fixable from this runner |

The shape of the overnight: nothing. That's what was expected and that's what happened.

## Live performance

Still blocked. Eighth consecutive review with `8bit.tristanaddi.com` and `8bitlegacy.com` both returning HTTP 403 (`host_not_allowed`). Snapshot is the only credentialed live-data source this agent has and it's been unreachable for 9 days running. **Reading this as structural now, not a config oversight** — the runner allowlist appears to be a property of how the cron is hosted, and Tristan would have changed it by now if the fix were one-line. The right framing has converged on "the snapshot link is for the worker that gets enabled when the cadence shifts back to active-campaign-monitoring," not "the missing piece of every quiet-day review."

The 5/15 15:55 in-session evidence (pixel present, 90 conv last 30d on Page View) is the freshest pixel signal and it's still good enough for re-launch planning. Pre-flip re-verify is the checkpoint that matters; this morning's blindness does not.

## Bid math reality check

Unchanged in shape from 5/15 20:00. No new data, no new commits affecting margin, no SST verdict yet. The 5/15 derivation stands:

- over_50: $0.35 bid, ~$94 mean retail, ~$11 net/sale (post-tax-leak), **3.2% break-even CVR**
- 20_to_50: $0.08 bid, ~$32 mean retail, ~$6 net/sale, **1.3% break-even CVR**

Post-truth-set the over_50 mean retail should nudge upward by $1–3 once corrupted SKUs reprice (Wii Party U class), pulling break-even CVR very slightly down. Not material until both the apply lands AND a clean week of post-flip data exists to compare against.

## Strategic concerns

### 1. The morning sequence has one ordering trap

Already flagged in §2 of yesterday's 20:00 report and worth re-stating because it's THE thing to not miss today:

**Re-refresh `data/cib-offer-ids.txt` AFTER the truth-set apply, BEFORE the CIB tree rebuild.** The 5/15 snapshot (6,112 IDs) is based on the pre-truth-set catalog. If the rescan reclassifies any items as CIB-or-not by changing prices that cross condition thresholds, or if quarantines remove items, the IDs in `data/cib-offer-ids.txt` will be stale for the rebuild. Mechanical, 30 seconds, but it's the most likely "thing we missed" failure in tomorrow's launch and it isn't called out explicitly in the EOD checklist steps 1–4 vs 6–9.

The fix is one extra step between EOD §1 (truth-set apply) and EOD §2 (CIB rebuild):

```bash
python3 scripts/list_cib_offer_ids.py  # refresh data/cib-offer-ids.txt
```

### 2. The ~2-hour window between now and quota reset is the highest-leverage "do nothing" window

CIB tree is currently empty. Campaign is paused. The only way today goes badly before 10 AM ET is if anything causes ENABLED state to flip during this window. Mitigations: no scheduled job touches campaign status (verified in `dashboard/src/lib/jobs.ts` per yesterday's read), and ENABLE is a manual UI action. **The protection is behavioral, not technical**: morning coffee should not include a "let me check Google Ads" → muscle-memory unpause flow. If Tristan is going to look at the campaign UI before the rebuild lands, the discipline is "look, don't touch."

If the EOD step 4 checklist is followed in order, this is a non-issue. Calling it out because it's the one cheap mistake that produces a disproportionate outcome.

### 3. Everything else carries over unchanged

The 5/15 20:00 report's strategic concerns (§3–§6: bid-math invalidation slightly, SST path unaffected, promo math now dominated by structural timing, cadence Tristan-flagged) all still apply, all still unchanged. Not restating — read together with this one as the standing brief.

## Recommended actions (priority order)

1. **[HIGH] Run the morning checklist from `eod-2026-05-15.md` in order**, with the §2-of-this-report insertion (re-refresh `cib-offer-ids.txt` AFTER truth-set apply, BEFORE tree rebuild). If the rescan classification is clean and verifier shows 3/3 PASS and pixel re-verifies, flip ENABLED. If any step fails, hold and diagnose; do not skip ahead.

2. **[HIGH] Pre-quota-reset discipline**: do not open the Google Ads UI campaign view between now and tree rebuild completion (~10:30 AM ET). Or if doing so, look only — no status changes.

3. **[MEDIUM] After truth-set applies, generate the "$ delta" summary** (carried from 5/15 20:00 §3). Sum (new − old) × recent units sold across the APPLY set. This is the quantified margin recovery and feeds the post-reset bid math better than today's hand-waved estimate.

4. **[MEDIUM] Drop this agent's cron cadence to weekly** (Mondays) once today's launch lands. Tristan-flagged, agreed-on, execution-side. Daily resumes day-of-flip and stays daily for the first 7–14 post-flip days when CVR data is bid-tunable.

5. **[MEDIUM] Carries over unchanged**: SST verdict state-by-state revenue split when it lands (~5/22), promo-credit spike decision before 5/24. No new information today.

6. **[LOW] Carries over unchanged**: 7th `cib-exclusion-sync` cron job idea, bid-down trigger pre-commit. Deferred.

## Coverage gaps

Same shape as 5/15 20:00 — no point re-tabulating. Today's specific blocks:

- **Rescan completion + classification counts** — should be done; verifiable via TrueNAS SSH from Mac/desktop, not from this runner.
- **CIB tree current state** — quota window not yet closed; ~10 AM ET resolves it.
- **Pixel state this morning** — egress 403; the 5/15 15:55 in-session verification is the freshest signal and is still good enough for the pre-flip re-verify step in the EOD checklist.
- **Live ad spend / clicks / conversions since 5/05** — snapshot 403; campaign paused so the answer is "$0 / 0 / 0" with near-certainty.

## Honest meta-note

This is exactly the kind of report Tristan flagged as cron-vs-tempo mismatch. Today's substantive ads work happens between 10 AM and 12 PM ET; the 8 AM review fires before the inputs land and the 2 PM review will fire when the work is half-done. **The 8 PM review will be the one with real content this evening.** If today's launch sequence lands cleanly, this evening's report writes itself. If anything falls over in the morning checklist, the 2 PM review may be useful as a same-day pause-or-push input. Until then, this morning's job is just to flag the ordering trap (§1) and stay out of the way.

The right next review is 8 PM ET today (post-launch state) or 8 AM Monday 5/18 (if the cadence drop happens this morning). 14:00 today is plausibly skippable.
