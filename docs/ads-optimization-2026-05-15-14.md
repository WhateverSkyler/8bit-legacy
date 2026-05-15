# Ads Strategic Review — 2026-05-15 14:00 ET

## TL;DR

**Sixth blind review, but the first one in 7 days with a substantive new fact that touches ad economics directly.** The new commit on `main` (`2d7f217`, 2026-05-15 12:33 ET) records that yesterday's eBay multi-state tax exemption submission was **partially rejected** — MTC narrows from 35 states → GA only; SST cert still pending verdict (~5/22). This is a real margin-economics input, not just process noise. Best case (SST approved): ~24 additional states get sales-tax-exempt sourcing, recovering ~$1.50–3.00 per sale and dropping over_50 break-even CVR from ~3.2% to ~2.5%. Worst case (SST also rejected): status quo, ~$3.30/sale tax leak persists. **Still no ads/MC/pixel/CIB ops work in 10 days. Still no `ads-on-hold-*.md` doc.** Snapshot + storefront still 403 from this runner — sixth report with that gap unactioned. Top action carries over: write the hold doc, fix the cadence.

## What changed since last review (2026-05-14 20:00 ET)

| Dimension | 5/14 20:00 | 5/15 14:00 | Delta |
|---|---|---|---|
| Latest commit on `main` | `fc393c0` (per 5/14 20:00 report, ads-irrelevant) | `2d7f217` (2026-05-15 12:33 ET) | **+1 ads-economics-relevant commit** (tax exemption follow-up) |
| Other new commits | — | 4 shorts-pipeline commits between 5/14 20:33 and 5/15 01:04 (rounds 19, 19.5, 20, 20.1 + handoff) | YT pipeline still the active workstream |
| New ads/MC/pixel/CIB ops docs | None | None | None |
| New tax-economics docs | None | `claude-cowork-brief-2026-05-15-ebay-tax-exemption-fixes.md` | **First substantive margin-economics signal in 10 days** |
| `launch-log.md` last entry | 2026-04-25 | 2026-04-25 | None (still 20 days stale) |
| `ads-on-hold-2026-05-14.md` | Not written | Not written | Top recommendation still un-actioned |
| Snapshot endpoint reachable | 403 | 403 | None |
| Storefront reachable for pixel verify | 403 | 403 | None |
| Days since last ads ops signal | ~10 | **~11** | +1 |
| Days to $700 promo expiry | 17 | **16** | -1 |

The shape of the last 18h: 4 shorts-pipeline commits (rounds 19→20.1) overnight, then a midday pivot at 12:33 ET to the eBay tax exemption rejection (referenced cowork brief authored on Mac, then committed). No ads-operational touches.

## Live performance

Cannot retrieve. Same egress block as the last five reports: `8bit.tristanaddi.com` and `8bitlegacy.com` both return `HTTP/2 403 — x-deny-reason: host_not_allowed`. Sixth report with this gap unfixed. This is now firmly evidence that either (a) the runner allowlist is not editable in the current setup, or (b) the cadence is no longer a priority for Tristan to invest in fixing — both of which are consistent with the "ads is implicitly on hold" framing.

## Bid math reality check

**The tax exemption development is the first input in 10 days that meaningfully shifts the bid math.** Worth re-running.

### Original 5/07 derivation (still anchoring)

| Tier | Bid | Mean retail | Net/sale (with ~$3.30 tax leak) | Break-even CVR |
|---|---|---|---|---|
| over_50 | $0.35 | $94 | ~$11 | **3.2%** |
| 20_to_50 | $0.08 | $32 | ~$6 | **1.3%** |

### After 5/14 multi-state filings (pending verdict)

The eBay tax exemption math is order-of-states-by-buyer-distribution-dependent and our actual state-level revenue split is unknown from this runner. But we can bracket the outcomes:

**Scenario A — SST approved (~24 states covered) + GA via ST-5; MTC GA-only:**
- ~25 states sales-tax-exempt on eBay sourcing
- Lost vs. original 35-state plan: 15 MTC-only states (notably TX, FL, PA, CA — large markets — but CA already accepted as "no nexus / accept" per the brief)
- Net tax leak narrows from ~3.5% revenue → estimate ~1.2–1.8% revenue (depends on buyer state mix; if buyers track US population, the 25 covered states represent ~55-60% of population, so leak shrinks roughly proportionally)
- **over_50 net/sale rises ~$1.50–2.50 → from $11 to $12.50–13.50**
- **over_50 break-even CVR drops from 3.2% to ~2.6%**
- **20_to_50 break-even CVR drops from 1.3% to ~1.1%**

**Scenario B — SST also rejected on a separate technicality:**
- Only GA covered (via ST-5 + GA-only MTC, redundant)
- Status quo: ~3-3.5% tax leak persists
- Bid math unchanged

**Scenario C — SST approved, but TX/FL/PA buyers happen to dominate (small store, high variance):**
- Lost coverage on largest e-commerce states could mean leak compression is closer to 1% than 2%
- over_50 break-even CVR drops only to ~3.0% — within statistical noise of the current threshold

**Honest read:** Scenario A is the most likely outcome (SST rejection was not flagged in the same email batch — independent of the MTC issue) and would meaningfully improve the bid math. But the improvement is not dramatic enough to change the launch decision: a campaign that needs 3.2% CVR to break even and is getting 2.5% CVR is still losing money at 2.6%. **It's a 15-20% margin recovery, not a campaign-rescue.** Useful, not transformative.

### What this changes operationally

- **Don't drop bids preemptively in anticipation of SST approval.** The Day-22 verdict is uncertain and the recovery is bounded. Wait for confirmation, then re-derive.
- **If SST is approved, the bid-down trigger ($0.35 → $0.20 if over_50 hits 100 clicks at <2.5% CVR) should be re-thresholded.** New trigger logic: bid-down if observed CVR < (break-even-CVR × 0.78). At 2.6% break-even, trigger at ~2.0% CVR instead of 2.5%.
- **If TX/FL/PA are top revenue states historically**, the SST-approved scenario is materially worse than the back-of-envelope number above. Tristan can check this in Shopify Orders → state breakdown once. Five-minute query, settles it.

### 7-day P&L scenarios remain unchanged in shape

Same as 5/07: at $5/day spend, week-1 ROAS is more likely 0-80% than 200%+. Tax exemption recovery doesn't change cold-start CVR — it just improves the slope of the eventual recovery if/when this campaign produces real conversions. **The bigger lever is still "does the pixel work and does any traffic convert at all," not "can we shave 0.6% off break-even CVR."**

## Strategic concerns

### 1. The tax exemption work is the right kind of off-cycle margin recovery

Even with ads paused, the tax filings are doing work that will pay off the moment ads resumes. This is exactly the kind of "while-ads-is-on-hold" preparatory move that should happen, and Tristan is doing it. **Implicit signal: ads-on-hold is not "give up on ads," it's "fix the underlying economics so the next launch isn't doomed by structural drag."** That framing argues against the dropped-cadence path from yesterday's report (because there IS strategic ads thinking happening, just not via campaign mutations) and toward the "weekly cadence" path (because daily granularity is wrong for paperwork that resolves on multi-day cycles).

### 2. The promo credit deadline is now inside three weeks

$700 promo expires **5/31 → 16 days out**. The realistic spend through 5/31 at $5/day from a resume-date of 5/22 (SST verdict) is ~$45. Realistic spend even at $20/day from 5/22 → $180. **At any plausible scenario, ≥$500 of the $700 promo is going to expire unused.** This is now baked in.

Two honest options haven't shifted from 5/14 20:00:
- **Accept the loss** — don't try to spend through it. Loss-amplification path is real.
- **Pre-commit a spike** — if SST approves on or before 5/22 and the verifier passes and pixel verifies and the first 24h of $5/day shows even one conversion: bump to $20/day for the final week. That captures ~$140 more of the promo at marginal-information-positive cost.

The decision belongs to Tristan. The agent's job is to surface the deadline math and the asymmetry, which I just did.

### 3. The hold doc still hasn't been written

Top recommendation for the last two reports. Status: still not written. This is not a blocker, but it's a recurring failure mode of this cadence to surface the same un-actioned recommendation. **Suggesting it again with the same priority is starting to feel like ritual.** Promoting it to a softer ask: if Tristan ever has 90 seconds, the smallest version of this is a one-line file:

```
docs/ads-on-hold.md
=================
Status: PAUSED since 2026-05-05.
Reason: prioritizing YT subscribers (→1k for Shopping unlock) + tax exemption recovery (~5/22 verdict).
Resume trigger: SST verdict + verifier-pass + pixel re-verify.
```

That alone resolves ~80% of the speculation surface for the next ten of these reviews.

### 4. The CIB-rebuild partial state is drifting at +10 days

Carried over from 5/14: 2,000 of 6,102 CIB negatives uploaded as of 5/05 night; new variants added since then are not in the snapshot. Today is +10d. At a rough estimate (12K total products, ~5-10 new per week), there are now ~15-30 CIB variants that exist in Shopify but are NOT in `data/cib-offer-ids.txt`. None of them would be excluded if ads re-flipped today. **This is fixable by re-running `list_cib_offer_ids.py` and re-running the rebuild before re-flip.** It's a checklist item, not a structural failure. But the cost grows linearly with time.

### 5. The pixel state has now been unverified for 14 days

The 5/01 fix was the last documented verification. Three breakages in the preceding 30 days; no re-verify since. **Statistically, the prior is now non-trivial that the pixel has regressed.** First action on any resume cycle has to be `curl https://8bitlegacy.com/ | grep AW-` before any other step. If Tristan flips ENABLED without that check, the asymmetric risk re-instates instantly.

## Recommended actions (priority order)

1. **[HIGH] Write `docs/ads-on-hold.md`** (one line is enough — see §3 above). Carried over from 5/14. This alone changes the next 10 reports from "I have no signal, here's what I'd think about if I did" to "I confirmed nothing material changed since the hold doc."

2. **[HIGH] Decide cadence.** Carried over. Adjusted framing: given the tax exemption is doing real prep-work, the right cadence is now **weekly** (Mondays?) not "1x/week or pause." The agent isn't useless — it's mis-paced. Daily would only become useful again once a campaign is enabled with live data flowing.

3. **[MEDIUM] When SST verdict arrives (~5/22), re-run the state-by-state revenue analysis once.** If TX/FL/PA are top revenue states, the post-recovery tax leak is bigger than the population-weighted estimate above and the bid math improvement is smaller than Scenario A suggests. Five-minute query in Shopify Orders. This is the single most useful piece of information Tristan can pull next week.

4. **[MEDIUM] Decide promo-credit spike strategy before 5/24.** New for today (carried from 5/14 20:00 but tightened). Three branches:
   - SST approved + verifier passes by 5/22 → spike to $20/day from 5/24 to 5/31, capture ~$140 more of the promo.
   - SST approved but verifier needs work → defer spike, run at $5/day, accept ~$580 promo loss.
   - SST rejected → run normal $5/day or stay paused, accept full promo loss.

5. **[MEDIUM] Re-run `scripts/list_cib_offer_ids.py` before any re-flip.** Snapshot will have drifted 10+ days. Mechanical, not a debate.

6. **[MEDIUM] Pixel re-verify is non-negotiable on resume.** `curl -s https://8bitlegacy.com/ | grep -oE 'AW-[0-9]+/?[A-Za-z0-9_-]*' | sort -u` should show ≥7 entries with the `AW-18056461576` prefix. If not, hold.

7. **[LOW] Bid-down trigger remains pre-committed but un-triggered** (no live data to evaluate). Slightly adjusted post-SST (see §1 bid math).

8. **[LOW] `cib-exclusion-sync` as a 7th cron job.** Filed; deferred. Carried over.

## Coverage gaps

Same shape as 5/14 — same root cause, same blocked dimensions. Marking only new lines:

| Dimension | Why blocked |
|---|---|
| Campaign status (PAUSED vs ENABLED) | Snapshot 403 |
| 5/06–5/15 spend / clicks / impressions / conversions | Snapshot 403 |
| Current CVR by tier | Snapshot 403 |
| Storefront pixel state (`AW-18056461576` present?) | Storefront 403 |
| Whether 5/06 CIB rebuild ran or completed | No commit/doc record |
| `verify_cib_exclusion.py` exit code | No commit/doc record |
| Search-term report from 5/05 leakage | Requires GAQL via Mac |
| MC counts and "Limited" % | Authed API |
| VPS sync route deployment status | VPS HTTP access |
| Order #1076 outcome | Authed dashboard |
| 7th `cib-exclusion-sync` job existence | Authed dashboard |
| $700 promo credit balance / expiry | Authed Google Ads |
| **State-by-state revenue split (TX/FL/PA share)** *(new — relevant for sizing the SST recovery)* | Authed Shopify |
| **SST verdict by 5/22** *(new — resolves Scenario A vs B)* | External, time-dependent |

## Honest meta-note

Today is the first review in a week with a non-trivial new input. The tax exemption work is genuinely strategic — it directly compresses break-even CVR — and Tristan acted on it within 24 hours of the rejection email. **That's the kind of operator behavior that argues the cadence is wrong, not the work.** Daily blind reviews of a paused campaign aren't catching this stuff because the cycle doesn't match the work tempo. A weekly review on Mondays would have surfaced the tax exemption move once and folded the bid-math implication into a single substantive write-up instead of stretching it across three reports.

If by next review (5/15 20:00) nothing new has happened — no hold doc, no SST update, no ads commits — the right output is a one-line file. The substantive content of this report is already the recurrent: read this 14:00 review and the 5/14 20:00 review together; they're the standing brief until SST resolves.
