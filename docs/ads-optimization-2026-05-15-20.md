# Ads Strategic Review — 2026-05-15 20:00 ET

## TL;DR

**Today flipped from "uneventful, write a short report" to the most ads-economics-relevant day in 10 days.** Three substantive landings between 15:18 and 16:05 ET, all material:

1. **🚨 Pricing automation was actively corrupting catalog prices** (Wii Party U $60 → $12 class of errors, matcher confidently mismatching across consoles). Kill switch tripped (defense-in-depth, three layers). Hardened-matcher rescan running on TrueNAS until ~22:00 ET. **Implication for ads: store prices on an unknown slice of the 6,121-product retro catalog have been low for an unknown duration. MC has been feeding those low prices to Shopping.** Hard block on re-flip until truth-set is applied and verified clean.
2. **✅ Pixel verified live** — `AW-18056461576` present in storefront HTML, Page View action shows 90 conv in last 30d (organic traffic). The "pixel unverified 14 days" asymmetric risk I flagged this morning is **retired**.
3. **⚠️ CIB tree rebuild started but stuck.** 2,009 old nodes torn down, 5 skeleton nodes created, but quota cut off before pushing the 6,112 item_id negatives. **Tree currently has 0 CIB exclusions.** Safe only because campaign is still paused. Quota resets ~10am ET 5/16, rebuild needs ~5 min once unblocked.

**Top action:** Do NOT enable campaign until BOTH (a) pricing truth-set applied + breakers reset AND (b) CIB tree rebuild completed + `verify_cib_exclusion.py` shows 3/3 PASS. Both are tractable tomorrow morning. Don't shortcut either.

**Meta:** Tristan flagged the cadence issue himself in tonight's EOD ("Strategic ads agent still firing 3x/day on cron with 'no change.' Worth dropping cadence to 1x/week or pausing until ads is re-enabled."). Cadence change is now agreed-on; the only question is execution.

## What changed since 5/15 14:00

| Dimension | 5/15 14:00 | 5/15 20:00 | Delta |
|---|---|---|---|
| Latest commit on `main` | `2d7f217` (tax exemption brief) | `259ab4a` (EOD PM-session append, 18:46 ET) | **+6 commits, 3 ads-economics-relevant** |
| Ads/MC/pixel/CIB ops commits | 0 in 10 days | **+1** (`50edb7d`, 15:55 ET — CIB rebuild wrapper + ID refresh + pixel verify in-message) | First ads-ops commit in 10 days |
| Pricing/margin commits | 0 in 10 days | **+1** (`475a893`, 15:18 ET — full pricing reset, 3 kill switches) | Major margin-economics intervention |
| Pixel state (storefront) | Unverified 14 days | **VERIFIED live in-session** (per commit msg, 90 conv last 30d) | Asymmetric risk retired |
| CIB tree state | 2,000 of 6,102 IDs uploaded as of 5/05; assumed stale | **5 skeleton nodes + 0 CIB negatives** (mid-rebuild, quota-blocked) | New ENABLE-blocker |
| Pricing kill switches | None tripped (config not flagged) | **3 layers tripped**: `auto_apply_enabled=false` (config), `pricing` breaker (DB), `price-sync`+`pokemon-price-sync` jobs `enabled=false` | Hard pause |
| Pricing rescan in flight | None | TrueNAS PID 1411444 + watcher 1416617, ETA ~22:00 ET tonight | Auto-dry-run on completion |
| `ads-on-hold.md` (the 14:00 ask) | Not written | Not written — but EOD doc effectively supersedes it | Soft-resolved by EOD note |
| Days to $700 promo expiry | 16 | 16 | None |
| Days to SST verdict | 7 | 7 | None |

## Live performance

Cannot retrieve from this runner. `8bit.tristanaddi.com` and `8bitlegacy.com` both return HTTP 403 (host_not_allowed). Seventh review with this gap. **However** — the 15:55 commit message explicitly records:

- Campaign `23766662629` **STILL PAUSED**, $0 spend in 10 days
- Pixel `AW-18056461576` present in storefront HTML (this session, 5/15)
- Page View conversion action shows **90 conversions in last 30 days** (organic-traffic firing)
- `data/cib-offer-ids.txt` refreshed: **6,112 IDs, unchanged from prior snapshot** — no new CIB variants in the last 10 days

The "CIB drift at +10 days" worry from this morning's report is **resolved**: the snapshot didn't drift. The refresh found zero new variants.

## Bid math reality check

Pixel-confirmed-firing changes the read on break-even math slightly but doesn't move the threshold numbers. Pricing reset DOES change the read on past CVR/revenue assumptions, retroactively.

### What pixel-verified-firing changes

- Pre-today read: "pixel might be broken, all post-5/01 conversion attribution is suspect." Probability pixel is broken: moderate prior (it had broken 3× in 30 days through 5/01).
- Post-today read: pixel firing on **organic** traffic (90 conv / 30d). That's a strong signal it would fire on **paid** traffic too — the AW token is in the global page HTML, not behind any traffic-source gate.
- **Bid math threshold unchanged** (3.2% over_50 / 1.3% 20_to_50 break-even, same as 5/07 derivation). What changed is the **probability** that observed numbers would be trustworthy once ads spends — now high.

### What pricing-corruption-discovered changes

This is the bigger lever and the trickier read.

**The corruption pattern (per commit msg):** PriceCharting matcher confidently picked wrong products across console boundaries. Wii Party U (a Wii U title with $60 PC market) was matched to a Wii title with $12 market. Multiplier was applied to the wrong market price. Final retail in Shopify: ~$16 instead of ~$80.

**Three economic effects to disentangle:**

1. **Past sales (if any) on corrupted listings sold at deep loss.** Eg. a $60-market Wii U item sold at $16 retail: COGS on eBay ~$30, Shopify fee ~$0.76, tax leak ~$0.50, shipping cost ~$5. Loss per sale: ~$20. Not just "thin margin" — actually losing money on each sale. Past sales volume is unknown from this runner.
2. **Past Shopping ads (campaign was active briefly before 5/05 pause) advertised corrupted prices.** Any clicks on a corrupted SKU were burning budget against a sub-cost retail price. CTR may have been artificially elevated on those SKUs (cheaper price → more clicks). Confounds the early-CVR-vs-bid signal materially.
3. **Future ads economics improve once truth-set applied.** Affected SKUs will retail at correct (higher) prices. Net/sale on the previously-corrupted slice will rise materially. **This is a structural margin recovery, distinct from the SST tax recovery.**

**Honest sizing:**
- Unknown what % of catalog was corrupted. The fix-list will surface this when the rescan completes tonight.
- Even if it's 1–3% of 6,121 SKUs (~60–180 items), at avg $40 retail-correction per item, the in-store revenue uplift is real but not transformative.
- The bigger value is **eliminating sub-cost listings before any further ad spend hits them**. One single corrupted, ad-promoted, popular SKU could absorb a 1–2 day budget in a single weekend.

### 7-day P&L scenarios

Unchanged in shape from prior reviews. Updated reads:

| Scenario | Probability (subjective) | Week-1 ROAS estimate | Notes |
|---|---|---|---|
| Truth-set clean, CIB rebuild clean, SST approved, $5/day | ~25% | 60–150% | Most-likely launch state if everything tomorrow goes right |
| Truth-set clean, CIB rebuild clean, SST rejected, $5/day | ~30% | 40–100% | Status-quo margin, but the campaign starts on a clean catalog |
| Pricing reset reveals broader corruption needing extra week of cleanup | ~25% | n/a — no launch this week | Most-likely "delay" branch |
| Catastrophic finding (eg. 20%+ of catalog corrupted) | ~10% | n/a — multi-week pause | Tail risk; tomorrow's classification counts settle it |
| Pricing clean + CIB clean + SST approved + spike to $20/day from 5/24 | ~10% | 70–180%, higher variance | Captures ~$140 of promo, costs ~$100 if it stalls |

**Bottom line:** the discovery of corruption is bad news for past results, but a structural improvement for forward economics if the reset lands cleanly. The single most useful piece of forward information is tomorrow's CLASSIFICATION SUMMARY counts from the rescan.

## Strategic concerns

### 1. The CIB-tree "empty" state is a new asymmetric risk

The campaign is paused, so today's state is safe. But the mid-rebuild posture (5 skeleton nodes, 0 negatives) is fragile in one specific way: **if anything causes the campaign to flip to ENABLED before the rebuild finishes**, ads would advertise the ENTIRE catalog including all 6,112 CIB variants with no exclusion. CIB variants are higher-priced (because COGS is much higher), so they convert worse and burn more per click. **Estimated burn rate if this happened: 3–5× the original leak rate from 5/05.**

Concrete mitigations:
- Campaign status is paused; flipping ENABLED requires manual UI action (no dashboard auto-resume cron).
- No scheduled job touches campaign status in the cron set (verified by inspection of `dashboard/src/lib/jobs.ts` recently — pricing jobs are the only ones modifying production state, and they're now disabled).
- The pre-quota-reset window is ~14 hours.

The real protection is "don't flip it." Worth a sticky note.

### 2. Pricing reset must complete BEFORE CIB rebuild for a clean re-launch

Two independent ENABLE blockers, but they interact: if you rebuild CIB exclusions today and apply pricing fixes tomorrow that change which SKUs cross the $X.99 threshold or get quarantined, the offer-IDs in the CIB tree are based on a stale offer-ID list (refreshed today, but truth-set hasn't run). The cleanest sequence is:

1. Tonight: rescan finishes ~22:00 ET, watcher dry-runs apply, writes review-queue CSVs.
2. Tomorrow AM: review classification, spot-check Wii/NES/SNES/PS2/GameCube, especially Wii Party U + Wii Sports Resort (regression canaries).
3. Tomorrow AM: `apply-truth-set.py --apply` (after sample check passes).
4. Tomorrow AM: reset pricing breaker.
5. **Re-refresh `data/cib-offer-ids.txt` AFTER apply** — quarantined/repriced items may shuffle CIB status.
6. Tomorrow (after Google quota resets ~10am ET): `ads_rebuild_cib_tree.py`.
7. `verify_cib_exclusion.py` must show 3/3 PASS.
8. Re-verify pixel one more time before flip.
9. Flip to ENABLED in Google Ads UI (manual).

The morning checklist in `eod-2026-05-15.md` has steps 1–4 + 6–9 correct. **Step 5 (CIB-ID re-refresh after truth-set apply) is implicit but not called out.** Adding it removes the most likely "thing we missed" failure mode.

### 3. The pricing corruption invalidates the historical bid-math derivation slightly

The 5/07 break-even derivation assumed mean retail of $94 for over_50 tier. If 1–3% of the over_50 inventory was retail-corrupted downward, the actual served-impression mean retail in past spend was lower than $94 — by maybe $1–3. **This means past break-even CVR was actually higher than 3.2%, not lower.** Post-reset, the original 3.2% number is approximately right again. No bid-change recommended.

### 4. The SST verdict path is unaffected

Tax exemption work continues independently. Verdict expected ~5/22. If SST approves: ~24 states get sales-tax-exempt sourcing, narrows break-even by ~0.5–0.7%. If rejected: status quo. **Order this matters now: pricing reset > CIB rebuild > SST verdict.** First two are tomorrow-blockers; SST is a margin-improver but not a launch-blocker.

### 5. Promo credit math is becoming dominated by structural timing

$700 promo expires 5/31, 16 days out. Realistic spend at $5/day from a 5/16-or-later resume to 5/31 is ~$80. Realistic spend at $20/day (if Tristan triggers the spike) from 5/24 to 5/31 is ~$140 + ~$45 for 5/16–5/24 = ~$185. **At any plausible scenario, ≥$500 of $700 expires unused.** The decision-relevant fork is whether to spike to $20/day for the final week (~$140 of additional captured promo at ~$100 of real-cost-if-it-doesn't-convert), and that's only worth doing if the first 48h of $5/day after re-flip shows at least one paid conversion. Carry-over from 5/14 and 5/15 14:00.

### 6. Cadence decision is now Tristan-flagged, no longer agent-recommended

EOD 5/15 line 151: "Strategic ads agent still firing 3x/day on cron with 'no change.' Worth dropping cadence to 1x/week or pausing until ads is re-enabled." This converts the "drop to weekly" recommendation from my last two reports from a soft ask to an agreed item. Execution belongs to Tristan (it's a cron config on whichever host runs me).

Once enabled, daily becomes useful again — first 7–14 days post-flip are CVR-data-rich and bid-tunable. Until enabled, weekly is the right cadence.

## Recommended actions (priority order)

1. **[HIGH] Do NOT enable the campaign until BOTH gates pass:**
   - Truth-set applied + pricing breaker reset (tomorrow AM after rescan review)
   - CIB tree rebuilt + `verify_cib_exclusion.py` 3/3 PASS (tomorrow AM after Google quota reset)
   - Both pixel + storefront re-verified one more time pre-flip
   
   The sequencing in `eod-2026-05-15.md` is right; the only addition is to re-refresh `data/cib-offer-ids.txt` AFTER the truth-set apply but BEFORE the tree rebuild (see §2). Reprices may shuffle which variants are CIB.

2. **[HIGH] Sample-check the rescan classification before applying.** Per EOD step 1: review CLASSIFICATION SUMMARY counts, sample 30 APPLY rows across Wii/NES/SNES/PS2/GameCube, verify Wii Party U + Wii Sports Resort specifically. If the corruption pattern was Wii ↔ Wii U, those are the canaries. If counts show >5% of items moving by >50%, pause for second-look before apply. This is the moment where rushing costs more than waiting.

3. **[MEDIUM] After truth-set applies tomorrow, generate and review the "what changed in $ terms" list.** Sum the delta of (new_price - old_price) × (recent_units_sold) across affected SKUs. This is the actual margin-recovery quantification and feeds the post-reset bid math more concretely than today's hand-wavy estimate.

4. **[MEDIUM] Drop the cron cadence for this agent to weekly (Mondays).** Tristan has now flagged it himself. Until campaign is ENABLED, weekly is the right rhythm. Daily resumes the moment the campaign goes live.

5. **[MEDIUM] When SST verdict arrives (~5/22), run the Shopify state-by-state revenue split.** Carried from 5/15 14:00. Now slightly more urgent because the SST verdict + clean catalog + clean CIB tree all converge on the same launch week.

6. **[MEDIUM] Decide promo-credit spike strategy before 5/24.** Carry-over from 5/14 20:00, unchanged. New constraint: spike branch requires first 48h of post-re-flip data to be non-zero.

7. **[LOW] `ads-on-hold.md` standalone doc.** Soft-resolved by `eod-2026-05-15.md` which now records the hold reasons in writing. Not worth a separate file at this point.

8. **[LOW] Sticky-note the "do not flip ENABLED until tomorrow's checklist passes."** The 14-hour window between now and Google quota reset is the only window where an accidental flip would do disproportionate damage. A one-line `docs/DO-NOT-ENABLE.md` would be the minimum viable defense; alternatively a comment at the top of the morning checklist in `eod-2026-05-15.md` reaffirming the order.

## Coverage gaps

| Dimension | Why blocked | Likely settled by |
|---|---|---|
| 5/06–5/15 spend / clicks / impressions / conversions | Snapshot 403 | Tomorrow AM if Tristan runs `ads_daily_report.py --since 5/06` on Mac |
| Current CVR by tier (historical) | Snapshot 403 + campaign paused (no new data anyway) | Post-reflip + 7 days |
| Storefront pixel raw HTML this session | Storefront 403 | Already proxy-verified via 15:55 commit msg |
| Truth-set classification counts (APPLY / REVIEW / REJECT / QUARANTINE) | Rescan still running | ~22:00 ET tonight when watcher finishes |
| % of catalog that was corrupted | Same as above | ~22:00 ET tonight |
| Sub-cost listing count (any negative-margin SKUs?) | Same as above | ~22:00 ET tonight; this is the actual ad-economics risk number |
| `verify_cib_exclusion.py` exit code | CIB tree mid-rebuild | Tomorrow ~10:30 AM ET after rebuild completes |
| SST verdict | External | ~2026-05-22 |
| State-by-state revenue split (TX/FL/PA share) | Authed Shopify | Tristan, 5 min query |
| $700 promo credit balance | Authed Google Ads | Tristan |
| Order #1076 outcome | Authed dashboard | Tristan |
| 7th `cib-exclusion-sync` cron job existence | Authed dashboard | Tristan; deferred |

## Honest meta-note

This morning's 14:00 review was generated before the substantive landings (15:18 pricing reset, 15:55 CIB rebuild attempt, 16:05 EOD). It accurately reflected the state-of-world at 14:00 — but the gap between 14:00 generation and 18:09 commit explains why it reads "uneventful" while the day was actually pivotal. The cadence problem isn't that nothing happens; it's that the work tempo and the cron tempo are unaligned.

**By next review (Monday 5/18 8:00 ET, if cadence drops to weekly; or 5/16 8:00 ET if it doesn't):** the rescan classification counts are the headline. If APPLY count is reasonable (say <2,000 of 6,121 items) and REJECT/QUARANTINE counts are small (<5%), tomorrow's launch sequence runs as planned. If APPLY count is huge or the REJECT pile is big, the launch slips and the right call is "fix the catalog before any further ads spend hits it." That's the single most decision-relevant fact for the campaign right now.

Today's headline is the right one: **the most important thing happening to ad economics this week is not a campaign-side change — it's the discovery and repair of a structural pricing leak in the catalog.** That kind of finding is worth the cron cycle.
