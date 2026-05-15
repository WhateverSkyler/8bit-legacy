# Ads Strategic Review — 2026-05-15 08:00 ET

## TL;DR

**Sixth consecutive blind review; nothing material changed on the ads side.** Six new commits since the 14:00 ET / 20:00 ET reports yesterday, all of them on the YouTube Shorts pipeline (Rounds 19 → 20.1, latest at **01:04 ET this morning, `8df457b`** — Tristan worked past midnight on shorts again). Zero ads-relevant commits, zero `ads-on-hold-*.md`, zero touches to MC / pixel / CIB / `launch-log.md` (still pinned at 2026-04-25). Snapshot endpoint + storefront both still `HTTP 403 host_not_allowed` from this runner — same egress allowlist gap flagged in five prior reports. **Honoring the 20:00 report's commitment: this is the short report. No change. See `docs/ads-optimization-2026-05-14-20.md` for substantive recommendations.**

## What changed since last review (2026-05-14 20:00 ET)

| Dimension | 20:00 state | 08:00 state | Delta |
|---|---|---|---|
| Latest commit on `main` | `fc393c0` (17:47 ET 5/14) | `8df457b` (01:04 ET 5/15) | **+6 commits**, all shorts pipeline (rounds 19, 19.5, 20, 20.1, merge, EOD handoff) |
| Ads-relevant commits | 0 | **0** | None |
| `ads-on-hold-2026-05-1*.md` | None | **None** | Item #1 from prior report unactioned |
| `launch-log.md` last entry | 2026-04-25 | 2026-04-25 | None |
| Snapshot reachable | 403 | 403 | None |
| Storefront reachable | 403 | 403 | None |
| Days since last ads signal | ~10 | **~11** (since 5/05 EOD) | +1 |
| Days to promo expiry (5/31) | 17 | **16** | −1 |

The shape of last night: 20:33 ET round 19 → 21:17 round 19 follow-up → 21:48 round 19.5 → 23:44 round 20 → 00:11 round 20.1 → 01:04 EOD handoff. A six-hour overnight sprint, all on shorts. The shorts pipeline is unmistakably where attention is, and the EOD handoff explicitly leaves an unresolved Layer C strictness question for next session — so the pattern continues today too.

## Live performance

Cannot retrieve. Same egress block. Both hosts continue to return `x-deny-reason: host_not_allowed`. This is now the sixth report flagging the same allowlist gap — recording it for completeness, not re-arguing it.

## Bid math reality check

No new data. Break-evens (~3.2% over_50, ~1.3% 20_to_50) and pre-committed bid-down trigger ($0.35 → $0.20 if over_50 hits 100 clicks <2.5% CVR) carry over from 5/07 14:00 unchanged. The 5/12–5/13 lifetime-ceiling window is now ~3 days in the past; whichever of the three outcomes it was (paused throughout / auto-paused on ceiling / converting) has resolved itself and only ground-truth on Tristan's Mac can disambiguate.

## Strategic concerns

### 1. The reframe from 20:00 is reinforced, not weakened

Tristan didn't just choose shorts over ads during business hours — he chose shorts over ads on his own time, past midnight. That's a stronger "actively deprioritized" signal than yesterday. The implication is the same: write the explicit hold doc, drop or pause this cadence, stop running speculative reviews against a campaign nobody is operating.

### 2. The promo-credit clock is real but cheap to ignore

16 days to expiry, $5/day cap, no operator attention. Mathematically: even if the campaign were re-flipped this morning and ran clean through 5/31 at exactly $5/day, that's $80 spent against a $700 credit — best case ~11% capture. Anything realistic is single-digit-percent capture. **That is a fine outcome to accept** as long as the decision is made consciously and not by drift. The bad outcome is spiking spend in the last week to "use" the credit at CVRs that haven't been validated — that path amplifies real-dollar loss to recover unspent grant dollars, which is the wrong tradeoff.

### 3. Listing-tree drift continues at zero marginal cost

Every additional day the partial-CIB-rebuild state sits unfinished, the snapshot in `data/cib-offer-ids.txt` (2,000 of 6,102 negatives applied as of 5/05) drifts further from current Shopify reality. Not catastrophic, but cheaper to resolve now than at resume. Carried over from prior reports; still not actionable from this runner.

### 4. Pixel state still unverifiable

Three breakages in 30 days (4/24, 4/25, 5/01). Eleven days since last re-verify. Storefront 403 from here blocks the standard `grep 'AW-18056461576'` check. If ads is re-flipped without a fresh pixel verify, that's the asymmetric-risk scenario — quiet conversion-tracking failure burning budget for days. Not actionable today; carry forward.

## Recommended actions (priority order)

All carried over from 5/14 20:00. Material reordering or net-new items would be inappropriate given zero new ground-truth.

1. **[HIGH] Write `docs/ads-on-hold-2026-05-15.md`** *(or `-14`, doesn't matter which date)*. Single one-page doc capturing: campaign current status, reason for hold (almost certainly "prioritizing YT subscribers / shorts pipeline to unlock YouTube Shopping"), explicit resume trigger, and carry-forward state (CIB 2k/6.1k, snapshot drift expected). Resolves the speculation surface for every future cycle. **Unactioned across two reports now.**

2. **[HIGH] Drop this cadence to weekly or pause it.** Six consecutive reports against a dormant campaign with no live-data access is process motion. If item #1 above is written, weekly check-in is the right shape until resume trigger.

3. **[HIGH] Add `8bit.tristanaddi.com` + `8bitlegacy.com` to runner egress allowlist** *(only if cadence stays 3x/day)*. Carried for the sixth time. The fact that it hasn't been actioned is itself the signal — see item #2.

4. **[MEDIUM] Run the 5-command Mac checklist once before going on hold.** Reproduced from prior reports:
   ```bash
   git status && git log --since="11 days ago"
   python3 scripts/list_cib_offer_ids.py
   python3 scripts/verify_cib_exclusion.py; echo "EXIT=$?"
   curl -s -A 'Mozilla/5.0' https://8bitlegacy.com/ | grep -oE 'AW-[0-9]+/?[A-Za-z0-9_-]*' | sort -u
   git add -A && git commit -m "EOD 2026-05-15: state captured before hold" && git push
   ```

5. **[MEDIUM] Promo-credit decision by 5/25.** Either accept the loss explicitly or pre-decide a final-week posture. 10 days from today.

6. **[MEDIUM] Bid-down trigger pre-committed.** Same trigger; only relevant on resume.

7. **[LOW] `cib-exclusion-sync` as a 7th cron job.** Defer, but don't lose.

## Coverage gaps

Identical to 20:00. Same root cause (sandboxed runner egress). Not reproducing the full table for the third time — see `docs/ads-optimization-2026-05-14-20.md` §Coverage gaps. The single one that's moved is **promo balance / days to expiry — 16 days remain, still unverifiable from here.**

## Honest meta-note

This report is the shape promised in yesterday's 20:00 meta-note: short, acknowledging that nothing material changed, and pointing back to the prior report as the substantive content. Continuing to produce 200-400 line reviews 3x/day at this cadence — against a dormant campaign, with no live-data access, while the operator is shipping 6 commits a night on a different surface — is not serving the business. **The right next step is either an egress fix + cadence reset, or an explicit hold doc + cadence pause. Both belong on Tristan's Mac; neither is actionable from this runner.**
